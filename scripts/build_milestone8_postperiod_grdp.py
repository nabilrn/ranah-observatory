#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/milestone8/source_text/candidate-pages/bps-grdp-2009-2013-pages-410-415.txt"
OUTPUT = ROOT / "data/analysis/quasi_causal/m8-postperiod-real-grdp-2009-2013.csv"
MANIFEST = ROOT / "data/manifests/milestone8_postperiod_grdp.json"

ROWS = [
    ("idn.13.1301", "Kepulauan Mentawai", "Kab. Kep. Mentawai"),
    ("idn.13.1302", "Pesisir Selatan", "Kab. Pesisir Selatan"),
    ("idn.13.1303", "Solok", "Kab. Solok"),
    ("idn.13.1304", "Sijunjung", "Kab. Sijunjung"),
    ("idn.13.1305", "Tanah Datar", "Kab. Tanah Datar"),
    ("idn.13.1306", "Padang Pariaman", "Kab. Padang Pariaman"),
    ("idn.13.1307", "Agam", "Kab. Agam"),
    ("idn.13.1308", "Lima Puluh Kota", "Kab. Lima Puluh Kota"),
    ("idn.13.1309", "Pasaman", "Kab. Pasaman"),
    ("idn.13.1310", "Solok Selatan", "Kab. Solok Selatan"),
    ("idn.13.1311", "Dharmasraya", "Kab. Dharmasraya"),
    ("idn.13.1312", "Pasaman Barat", "Kab. Pasaman Barat"),
    ("idn.13.1371", "Kota Padang", "Kota Padang"),
    ("idn.13.1372", "Kota Solok", "Kota Solok"),
    ("idn.13.1373", "Kota Sawahlunto", "Kota Sawah Lunto"),
    ("idn.13.1374", "Kota Padang Panjang", "Kota Padang Panjang"),
    ("idn.13.1375", "Kota Bukittinggi", "Kota Bukittinggi"),
    ("idn.13.1376", "Kota Payakumbuh", "Kota Payakumbuh"),
    ("idn.13.1377", "Kota Pariaman", "Kota Pariaman"),
]
YEARS = [2009, 2010, 2011, 2012, 2013]
LEVEL_PATTERN = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
GROWTH_PATTERN = re.compile(r"-?\d{1,2},\d{2}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_id_number(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def page(text: str, page_no: int) -> str:
    marker = f"===== PDF PAGE {page_no} ====="
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"missing PDF page marker {page_no}")
    next_marker = text.find("===== PDF PAGE ", start + len(marker))
    return text[start : next_marker if next_marker >= 0 else len(text)]


def ordered_regions(block: str, end_marker: str) -> list[tuple[tuple[str, str, str], str]]:
    positions: list[tuple[int, tuple[str, str, str]]] = []
    cursor = 0
    for row in ROWS:
        label = row[2]
        position = block.find(label, cursor)
        if position < 0:
            raise RuntimeError(f"missing expected row label {label!r}")
        positions.append((position, row))
        cursor = position + len(label)
    end = block.find(end_marker, positions[-1][0])
    if end < 0:
        raise RuntimeError(f"missing table end marker {end_marker!r}")

    regions: list[tuple[tuple[str, str, str], str]] = []
    for index, (position, row) in enumerate(positions):
        stop = positions[index + 1][0] if index + 1 < len(positions) else end
        regions.append((row, block[position:stop]))
    return regions


def parse_levels(text: str) -> list[dict[str, Any]]:
    block = page(text, 413)
    if "13.1.2" not in block or "Harga Konstan" not in block:
        raise RuntimeError("PDF page 413 lost Table 13.1.2 constant-price contract")
    output: list[dict[str, Any]] = []
    for (geography_id, geography_name, source_label), region in ordered_regions(block, "Sumber:"):
        values = LEVEL_PATTERN.findall(region)
        if len(values) != 5:
            raise RuntimeError(f"{source_label}: expected exactly five level values, got {values}")
        for year, source_value in zip(YEARS, values, strict=True):
            output.append(
                {
                    "geography_id": geography_id,
                    "geography_name": geography_name,
                    "year": year,
                    "real_grdp_constant_2000_million_rupiah": parse_id_number(source_value),
                    "source_value": source_value,
                    "source_table": "13.1.2",
                    "source_pdf_page": 413,
                    "revision_status": "revised" if year == 2012 else "preliminary" if year == 2013 else "unspecified",
                }
            )
    return output


def parse_growth(text: str) -> dict[tuple[str, int], float]:
    block = page(text, 414)
    if "13.1.3" not in block or "Pertumbuhan" not in block:
        raise RuntimeError("PDF page 414 lost Table 13.1.3 growth contract")
    output: dict[tuple[str, int], float] = {}
    for (geography_id, _geography_name, source_label), region in ordered_regions(block, "Sumber:"):
        values = GROWTH_PATTERN.findall(region)
        if len(values) != 5:
            raise RuntimeError(f"{source_label}: expected exactly five growth values, got {values}")
        for year, source_value in zip(YEARS, values, strict=True):
            output[(geography_id, year)] = parse_id_number(source_value)
    return output


def write_output(rows: list[dict[str, Any]]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "geography_id",
        "geography_name",
        "year",
        "real_grdp_constant_2000_million_rupiah",
        "source_value",
        "source_table",
        "source_pdf_page",
        "revision_status",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    if not SOURCE.exists():
        raise RuntimeError(f"missing post-period source slice: {SOURCE.relative_to(ROOT)}")
    text = SOURCE.read_text(encoding="utf-8")
    levels = parse_levels(text)
    growth = parse_growth(text)
    if len(levels) != 95:
        raise RuntimeError(f"expected 95 level observations, got {len(levels)}")
    if len({(row['geography_id'], row['year']) for row in levels}) != 95:
        raise RuntimeError("duplicate post-period geography-year keys")

    levels_by_key = {(row["geography_id"], row["year"]): row for row in levels}
    checks: list[dict[str, Any]] = []
    for geography_id, geography_name, _source_label in ROWS:
        for year in (2010, 2011, 2012, 2013):
            previous = float(levels_by_key[(geography_id, year - 1)]["real_grdp_constant_2000_million_rupiah"])
            current = float(levels_by_key[(geography_id, year)]["real_grdp_constant_2000_million_rupiah"])
            calculated = (current / previous - 1.0) * 100.0
            reported = growth[(geography_id, year)]
            difference = calculated - reported
            checks.append(
                {
                    "geography_id": geography_id,
                    "geography_name": geography_name,
                    "year": year,
                    "calculated_growth_percent": calculated,
                    "reported_growth_percent": reported,
                    "difference_percentage_points": difference,
                    "within_0_10_pp": abs(difference) <= 0.10,
                }
            )

    write_output(levels)
    failed = [row for row in checks if row["within_0_10_pp"] is not True]
    manifest = {
        "schema": "ranah-observatory/milestone8-postperiod-grdp/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_plan_id": "m8_grdp_post",
        "source_text_path": str(SOURCE.relative_to(ROOT)),
        "source_text_sha256": sha256(SOURCE),
        "source_level_table": "13.1.2",
        "source_growth_table": "13.1.3",
        "price_basis": "constant_2000",
        "unit": "million_rupiah",
        "geography_count": 19,
        "years": YEARS,
        "observation_count": len(levels),
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "growth_crosscheck_count": len(checks),
        "growth_crosscheck_tolerance_percentage_points": 0.10,
        "growth_crosscheck_failure_count": len(failed),
        "growth_crosscheck_passed": len(failed) == 0,
        "growth_crosscheck_failures": failed,
        "outcome_panel_combined": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
