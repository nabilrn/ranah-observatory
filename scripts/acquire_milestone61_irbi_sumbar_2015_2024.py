#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/processed/bnpb/irbi_sumbar_2015_2024"
SOURCE_OUT = OUT_DIR / "irbi-sumbar-2015-2024-source-native.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone61_irbi_sumbar_2015_2024_acquisition.json"
SOURCE_URL = "https://inarisk.bnpb.go.id/IRBI-2024/files/basic-html/page67.html"
PDF_URL = "https://www.bnpb.go.id/storage/app/media/Buku%20BNPB/BUKU%20IRBI%202024_BNPB_lowres.pdf"
YEARS = list(range(2015, 2025))
ROW_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s+((?:\d+\.\d{2}\s+){9}\d+\.\d{2})\s+(TINGGI|SEDANG|RENDAH)\s*$")


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(html.unescape(data))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "RanahObservatory/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def main() -> int:
    raw = fetch_text(SOURCE_URL)
    parser = TextExtractor()
    parser.feed(raw)
    text = "\n".join(parser.parts)

    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        number, name, values_blob, risk_class = match.groups()
        values = values_blob.split()
        if len(values) != 10:
            raise RuntimeError(f"M61 year-value footprint drift for {name}: {values}")
        row = {"NO": number, "KABUPATEN/KOTA": " ".join(name.split())}
        for year, value in zip(YEARS, values, strict=True):
            row[str(year)] = value
        row["KELAS RISIKO 2024"] = risk_class
        rows.append(row)

    if len(rows) != 19:
        raise RuntimeError(f"M61 official table row-count drift: {len(rows)}")
    if sorted(int(r["NO"]) for r in rows) != list(range(1, 20)):
        raise RuntimeError("M61 row-number footprint drift")
    names = [r["KABUPATEN/KOTA"] for r in rows]
    if len(set(names)) != 19:
        raise RuntimeError("M61 duplicate geography label")

    fields = ["NO", "KABUPATEN/KOTA", *map(str, YEARS), "KELAS RISIKO 2024"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with SOURCE_OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "schema": "ranah-observatory/milestone61-irbi-sumbar-2015-2024-acquisition/v1",
        "milestone": 61,
        "depends_on": [60],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "publisher": "Badan Nasional Penanggulangan Bencana",
            "publication": "Indeks Risiko Bencana Indonesia Tahun 2024",
            "official_book_page": 67,
            "basic_html_url": SOURCE_URL,
            "official_pdf_url": PDF_URL,
            "period": "2015-2024",
        },
        "source_native": {
            "row_count": 19,
            "year_count": 10,
            "value_count": 190,
            "years": YEARS,
            "risk_class_available_for_year": 2024,
            "geography_semantics_interpreted": False,
            "scores_recalculated": False,
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
