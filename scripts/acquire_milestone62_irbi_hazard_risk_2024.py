#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024"
SOURCE_OUT = OUT_DIR / "irbi-sumbar-hazard-risk-2024-source-native.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_acquisition.json"
BASE = "https://inarisk.bnpb.go.id/IRBI-2024/files/basic-html/page{page}.html"

HAZARDS = (
    ("flood", "Banjir", 210, 225),
    ("earthquake", "Gempabumi", 226, 243),
    ("tsunami", "Tsunami", 244, 253),
    ("volcanic_eruption", "Letusan Gunung Api", 254, 259),
    ("forest_and_land_fire", "Kebakaran Hutan dan Lahan", 260, 277),
    ("landslide", "Tanah Longsor", 278, 295),
    ("extreme_wave_and_coastal_erosion", "Gelombang Ekstrim dan Abrasi", 296, 307),
    ("drought", "Kekeringan", 308, 325),
    ("extreme_weather", "Cuaca Ekstrim", 326, 345),
)
ROW_RE = re.compile(
    r"(?:^|\s)(\d{1,4})\s+([A-Z][A-Z .'-]*?)\s+SUMATERA BARAT\s+(\d+\.\d{2})\s+(TINGGI|SEDANG|RENDAH)(?=\s|$)"
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(html.unescape(data))


def fetch(url: str, attempts: int = 6) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, headers={"User-Agent": "RanahObservatory/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            retryable = not isinstance(exc, urllib.error.HTTPError) or exc.code in {429, 500, 502, 503, 504}
            if not retryable or attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 12))
    raise RuntimeError(f"M62 official page fetch failed after {attempts} attempts: {url}: {last_error}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_name(value: str) -> str:
    return " ".join(value.split())


def main() -> int:
    records: list[dict[str, object]] = []
    pages_scanned: list[int] = []
    page_hits: dict[str, list[int]] = {}

    for hazard_id, hazard_label, start, end in HAZARDS:
        seen_for_hazard: set[str] = set()
        hit_pages: list[int] = []
        for page in range(start, end + 1):
            url = BASE.format(page=page)
            raw = fetch(url)
            parser = TextExtractor()
            parser.feed(raw)
            flat = " ".join(" ".join(parser.parts).split())
            pages_scanned.append(page)
            matches = list(ROW_RE.finditer(flat))
            if matches:
                hit_pages.append(page)
            for match in matches:
                source_rank, geography_name, score, risk_class = match.groups()
                geography_name = normalize_name(geography_name)
                if geography_name in seen_for_hazard:
                    raise RuntimeError(f"M62 duplicate {hazard_id} geography across pages: {geography_name}")
                seen_for_hazard.add(geography_name)
                records.append({
                    "year": 2024,
                    "irbi_hazard_id": hazard_id,
                    "source_hazard_label": hazard_label,
                    "source_rank": int(source_rank),
                    "source_geography_name": geography_name,
                    "score": f"{float(score):.2f}",
                    "risk_class": risk_class,
                    "source_page": page,
                    "source_url": url,
                })
        page_hits[hazard_id] = hit_pages
        if not seen_for_hazard:
            raise RuntimeError(f"M62 no Sumatera Barat rows found for {hazard_id}")

    keyset = {(str(r["irbi_hazard_id"]), str(r["source_geography_name"])) for r in records}
    if len(keyset) != len(records):
        raise RuntimeError("M62 duplicate hazard/geography key")
    if len({str(r["irbi_hazard_id"]) for r in records}) != 9:
        raise RuntimeError("M62 hazard footprint incomplete")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "year", "irbi_hazard_id", "source_hazard_label", "source_rank",
        "source_geography_name", "score", "risk_class", "source_page", "source_url",
    ]
    records.sort(key=lambda r: (str(r["irbi_hazard_id"]), int(r["source_rank"])))
    with SOURCE_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    coverage = {
        hazard_id: sum(1 for row in records if row["irbi_hazard_id"] == hazard_id)
        for hazard_id, _, _, _ in HAZARDS
    }
    manifest = {
        "schema": "ranah-observatory/milestone62-irbi-hazard-risk-2024-acquisition/v1",
        "milestone": 62,
        "depends_on": [61],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "publisher": "Badan Nasional Penanggulangan Bencana",
            "publication": "Indeks Risiko Bencana Indonesia Tahun 2024",
            "base_url": "https://inarisk.bnpb.go.id/IRBI-2024/files/basic-html/",
            "province_filter": "SUMATERA BARAT",
        },
        "source_native": {
            "hazard_count": 9,
            "record_count": len(records),
            "coverage_by_hazard": coverage,
            "page_hits_by_hazard": page_hits,
            "pages_scanned_count": len(set(pages_scanned)),
            "absence_interpreted_as_zero": False,
            "scores_recalculated": False,
            "cross_source_taxonomy_equivalence_authorized": False,
            "missing_values_inferred": False,
        },
        "output": {"path": SOURCE_OUT.relative_to(ROOT).as_posix(), "sha256": sha256(SOURCE_OUT)},
        "result": {"source_native_acquisition_complete": True, "canonical_mapping_authorized": False},
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["source_native"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
