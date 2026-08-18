#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/milestone8/source_text/bps-grdp-2005-2009.txt"
MANIFEST = ROOT / "data/manifests/milestone8_sumbar_appendix_probe.json"
SLICE_DIR = ROOT / "data/processed/milestone8/source_text/appendix-candidates"

GEOGRAPHIES = [
    ("idn.13.1301", "Kepulauan Mentawai", ["kepulauan mentawai", "mentawai"]),
    ("idn.13.1302", "Pesisir Selatan", ["pesisir selatan"]),
    ("idn.13.1303", "Solok", ["kabupaten solok", "kab. solok"]),
    ("idn.13.1304", "Sijunjung", ["sijunjung"]),
    ("idn.13.1305", "Tanah Datar", ["tanah datar"]),
    ("idn.13.1306", "Padang Pariaman", ["padang pariaman"]),
    ("idn.13.1307", "Agam", ["kabupaten agam", "kab. agam"]),
    ("idn.13.1308", "Lima Puluh Kota", ["lima puluh kota", "limapuluh kota", "50 kota"]),
    ("idn.13.1309", "Pasaman", ["kabupaten pasaman", "kab. pasaman"]),
    ("idn.13.1310", "Solok Selatan", ["solok selatan"]),
    ("idn.13.1311", "Dharmasraya", ["dharmasraya"]),
    ("idn.13.1312", "Pasaman Barat", ["pasaman barat"]),
    ("idn.13.1371", "Kota Padang", ["kota padang"]),
    ("idn.13.1372", "Kota Solok", ["kota solok"]),
    ("idn.13.1373", "Kota Sawahlunto", ["kota sawahlunto", "kota sawah lunto"]),
    ("idn.13.1374", "Kota Padang Panjang", ["kota padang panjang", "padang panjang"]),
    ("idn.13.1375", "Kota Bukittinggi", ["kota bukittinggi", "bukittinggi"]),
    ("idn.13.1376", "Kota Payakumbuh", ["kota payakumbuh", "payakumbuh"]),
    ("idn.13.1377", "Kota Pariaman", ["kota pariaman"]),
]


def norm(text: str) -> str:
    return " ".join(text.casefold().split())


def page_score(page: str, aliases: list[str]) -> dict[str, Any]:
    folded = norm(page)
    alias_hits = [alias for alias in aliases if alias in folded]
    has_pdrb = "pdrb" in folded or "produk domestik regional bruto" in folded
    has_constant = "harga konstan" in folded or "adh. pasar" in folded or "adh pasar" in folded
    has_2005 = "2005" in folded
    has_2009 = "2009" in folded
    numeric_lines = [
        " ".join(line.split())[:500]
        for line in page.splitlines()
        if re.search(r"(?:PDRB|Produk Domestik Regional Bruto|ADH\.?\s*Pasar)", line, flags=re.IGNORECASE)
        and re.search(r"\d", line)
    ][:12]
    score = (4 if alias_hits else 0) + (2 if has_pdrb else 0) + (2 if has_constant else 0) + (1 if has_2005 else 0) + (1 if has_2009 else 0)
    return {
        "score": score,
        "alias_hits": alias_hits,
        "has_pdrb": has_pdrb,
        "has_constant_signal": has_constant,
        "has_2005": has_2005,
        "has_2009": has_2009,
        "numeric_pdrb_lines": numeric_lines,
    }


def write_candidate_slice(pages: list[str], page_no: int) -> str:
    start = max(1, page_no - 1)
    end = min(len(pages), page_no + 1)
    path = SLICE_DIR / f"sumbar-source-pages-{start:03d}-{end:03d}.txt"
    chunks = []
    for number in range(start, end + 1):
        chunks.append(f"===== PDF PAGE {number} =====\n{pages[number - 1].rstrip()}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(chunks), encoding="utf-8")
    return str(path.relative_to(ROOT))


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]

    geography_reports: list[dict[str, Any]] = []
    candidate_pages: set[int] = set()
    for geography_id, name, aliases in GEOGRAPHIES:
        scored: list[dict[str, Any]] = []
        for page_no, page in enumerate(pages, start=1):
            if page_no < 90:
                continue
            report = page_score(page, aliases)
            if report["alias_hits"]:
                scored.append({"page": page_no, **report})
        scored.sort(key=lambda row: (-int(row["score"]), int(row["page"])))
        top = scored[:8]
        for row in top:
            if row["score"] >= 8:
                candidate_pages.add(int(row["page"]))
        geography_reports.append(
            {
                "geography_id": geography_id,
                "geography_name": name,
                "top_hits": top,
                "strong_candidate_count": sum(int(row["score"]) >= 8 for row in scored),
            }
        )

    slices = [write_candidate_slice(pages, page_no) for page_no in sorted(candidate_pages)]
    manifest = {
        "schema": "ranah-observatory/milestone8-sumbar-appendix-probe/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_plan_id": "m8_grdp_pre",
        "source_page_count": len(pages),
        "searched_page_min": 90,
        "geography_count": len(GEOGRAPHIES),
        "geographies": geography_reports,
        "strong_candidate_pages": sorted(candidate_pages),
        "candidate_slice_paths": slices,
        "complete_19x5_level_table_confirmed": False,
        "ocr_performed": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
