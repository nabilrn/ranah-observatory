#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DLNA_SLICE = ROOT / "data/processed/milestone8/source_text/candidate-pages/dlna-2009-pages-96-103.txt"
EXPOSURE = ROOT / "data/analysis/quasi_causal/m8-shakemap-exposure-candidate.csv"
OUTPUT = ROOT / "data/analysis/quasi_causal/m8-housing-damage-validation.csv"
MANIFEST = ROOT / "data/manifests/milestone8_housing_damage_validation.json"

ROWS = [
    ("idn.13.1371", "Kota Padang", "Kota Padang"),
    ("idn.13.1377", "Kota Pariaman", "Kota Pariaman"),
    ("idn.13.1372", "Kota Solok", "Kota Solok"),
    ("idn.13.1374", "Kota Padang Panjang", "Kota Padang Panjang"),
    ("idn.13.1305", "Tanah Datar", "Kab. Tanah Datar"),
    ("idn.13.1306", "Padang Pariaman", "Kab. Padang Pariaman"),
    ("idn.13.1301", "Kepulauan Mentawai", "Kep. Mentawai"),
    ("idn.13.1303", "Solok", "Kab. Solok"),
    ("idn.13.1302", "Pesisir Selatan", "Kab. Pesisir Selatan"),
    ("idn.13.1307", "Agam", "Kab. Agam"),
    ("idn.13.1309", "Pasaman", "Kab. Pasaman"),
    ("idn.13.1312", "Pasaman Barat", "Kab. Pasaman Barat"),
]
EXPECTED_UNREPORTED = {
    "idn.13.1304", "idn.13.1308", "idn.13.1310", "idn.13.1311",
    "idn.13.1373", "idn.13.1375", "idn.13.1376",
}
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})*|\d+")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def page(text: str, page_no: int) -> str:
    marker = f"===== PDF PAGE {page_no} ====="
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"missing DLNA page {page_no}")
    next_marker = text.find("===== PDF PAGE ", start + len(marker))
    return text[start : next_marker if next_marker >= 0 else len(text)]


def int_number(value: str) -> int:
    return int(value.replace(",", ""))


def parse_table(text: str) -> list[dict[str, Any]]:
    block = page(text, 99)
    if "Table 3. 19 Summary of damage in the housing sector" not in block:
        raise RuntimeError("DLNA Table 3.19 title drift")
    if "Source: BNPB." not in block:
        raise RuntimeError("DLNA Table 3.19 source attribution drift")

    positions: list[tuple[int, tuple[str, str, str]]] = []
    cursor = 0
    for row in ROWS:
        source_label = row[2]
        position = block.find(source_label, cursor)
        if position < 0:
            raise RuntimeError(f"DLNA Table 3.19 missing row {source_label!r}")
        positions.append((position, row))
        cursor = position + len(source_label)
    total_pos = block.find("TOTAL", positions[-1][0])
    if total_pos < 0:
        raise RuntimeError("DLNA Table 3.19 total row missing")

    parsed: list[dict[str, Any]] = []
    for idx, (position, (gid, name, source_label)) in enumerate(positions):
        stop = positions[idx + 1][0] if idx + 1 < len(positions) else total_pos
        region = block[position:stop]
        values = NUMBER.findall(region[len(source_label):])
        if len(values) < 6:
            raise RuntimeError(f"DLNA row {source_label!r} has fewer than six numeric fields: {values}")
        houses, heavy, medium, light, total_damage, reported_pct = [int_number(value) for value in values[:6]]
        if heavy + medium + light != total_damage:
            raise RuntimeError(f"DLNA damage components do not sum for {source_label}")
        any_share = total_damage / houses
        heavy_share = heavy / houses
        reported_from_share = any_share * 100.0
        if abs(reported_from_share - reported_pct) > 1.0:
            raise RuntimeError(
                f"DLNA reported total-damage percent inconsistent beyond integer-rounding tolerance for {source_label}: "
                f"computed={reported_from_share:.3f} reported={reported_pct}"
            )
        parsed.append(
            {
                "geography_id": gid,
                "geography_name": name,
                "pre_disaster_housing_stock": houses,
                "heavy_damage_houses": heavy,
                "medium_damage_houses": medium,
                "light_damage_houses": light,
                "total_damaged_houses": total_damage,
                "reported_total_damage_percent": reported_pct,
                "heavy_housing_damage_share": heavy_share,
                "any_housing_damage_share": any_share,
                "computed_total_damage_percent": reported_from_share,
            }
        )
    if len(parsed) != 12:
        raise RuntimeError(f"expected exactly 12 named DLNA Table 3.19 geographies, got {len(parsed)}")
    return parsed


def average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        average = (i + 1 + j) / 2.0
        ranks[order[i:j]] = average
        i = j
    return ranks


def correlation(x: list[float], y: list[float]) -> dict[str, float]:
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    if len(xa) < 3 or np.std(xa) == 0 or np.std(ya) == 0:
        raise RuntimeError("correlation requires nonconstant vectors with at least three observations")
    pearson = float(np.corrcoef(xa, ya)[0, 1])
    spearman = float(np.corrcoef(average_ranks(xa), average_ranks(ya))[0, 1])
    return {"pearson": pearson, "spearman": spearman}


def main() -> int:
    table = parse_table(DLNA_SLICE.read_text(encoding="utf-8"))
    exposure_rows = read_csv(EXPOSURE)
    exposure_by_gid = {row["geography_id"]: row for row in exposure_rows}
    if len(exposure_by_gid) != 19:
        raise RuntimeError("ShakeMap exposure must retain exact 19-geography universe")
    reported_ids = {row["geography_id"] for row in table}
    unreported = set(exposure_by_gid) - reported_ids
    if unreported != EXPECTED_UNREPORTED:
        raise RuntimeError(f"DLNA unreported geography set drift: {sorted(unreported)}")

    output: list[dict[str, Any]] = []
    for row in table:
        exposure = exposure_by_gid[row["geography_id"]]
        enriched = dict(row)
        enriched["area_mean_pga_pct_g"] = float(exposure["area_mean_pga_pct_g"])
        enriched["area_mean_mmi"] = float(exposure["area_mean_mmi"])
        enriched["dlna_reported_geography"] = True
        enriched["zero_filled"] = False
        output.append(enriched)

    write_fields = list(output[0])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=write_fields)
        writer.writeheader()
        writer.writerows(output)

    pga = [float(row["area_mean_pga_pct_g"]) for row in output]
    mmi = [float(row["area_mean_mmi"]) for row in output]
    heavy = [float(row["heavy_housing_damage_share"]) for row in output]
    any_damage = [float(row["any_housing_damage_share"]) for row in output]
    manifest = {
        "schema": "ranah-observatory/milestone8-housing-damage-validation/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source": "government-led DLNA Table 3.19; source line BNPB",
        "source_pdf_page": 99,
        "reported_geography_count": len(output),
        "full_analysis_geography_count": 19,
        "unreported_geography_count": len(unreported),
        "unreported_geography_ids": sorted(unreported),
        "zero_fill_performed": False,
        "housing_damage_used_as_primary_exposure": False,
        "validation_role": "secondary hazard-vulnerability diagnostic only",
        "correlations": {
            "area_mean_pga_vs_heavy_damage_share": correlation(pga, heavy),
            "area_mean_pga_vs_any_damage_share": correlation(pga, any_damage),
            "area_mean_mmi_vs_heavy_damage_share": correlation(mmi, heavy),
            "area_mean_mmi_vs_any_damage_share": correlation(mmi, any_damage),
        },
        "correlation_threshold_preregistered": False,
        "correlation_used_as_identification_gate": False,
        "interpretation": "Correlation is descriptive validation of physical shaking versus realized housing damage/vulnerability among the 12 explicitly reported DLNA geographies; it does not establish treatment exogeneity or fill the seven unreported geographies.",
        "housing_damage_validation_complete": True,
        "outcome_model_fit": True,
        "causal_effect_estimated": False,
        "input_dlna_slice_path": str(DLNA_SLICE.relative_to(ROOT)),
        "input_dlna_slice_sha256": sha256(DLNA_SLICE),
        "input_exposure_path": str(EXPOSURE.relative_to(ROOT)),
        "input_exposure_sha256": sha256(EXPOSURE),
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
