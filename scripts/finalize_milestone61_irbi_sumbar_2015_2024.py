#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone61_irbi_sumbar_2015_2024_acquisition.json"
SOURCE = ROOT / "data/processed/bnpb/irbi_sumbar_2015_2024/irbi-sumbar-2015-2024-source-native.csv"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
OUT = ROOT / "data/processed/bnpb/irbi_sumbar_2015_2024/irbi-sumbar-2015-2024-canonical-long.csv"
FINAL = ROOT / "data/manifests/milestone61_irbi_sumbar_2015_2024_final.json"
YEARS = list(range(2015, 2025))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_name_map() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    with GEOGRAPHIES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["parent_geography_id"] != "idn.13" or row["status"] != "current":
                continue
            if row["geography_level"] not in {"regency", "city"}:
                continue
            canonical = row["canonical_name"].strip()
            source_name = canonical.upper()
            if row["geography_level"] == "city":
                source_name = f"KOTA {source_name}"
            result[source_name] = (row["geography_id"].strip(), canonical)
    if len(result) != 19:
        raise RuntimeError(f"M61 Sumbar registry footprint drift: {len(result)}")
    return result


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    if acq["schema"] != "ranah-observatory/milestone61-irbi-sumbar-2015-2024-acquisition/v1":
        raise RuntimeError("unsupported M61 acquisition manifest")
    if sha256(SOURCE) != acq["output"]["sha256"]:
        raise RuntimeError("M61 source-native checksum drift")

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 19:
        raise RuntimeError(f"M61 source row-count drift: {len(rows)}")

    mapping = source_name_map()
    seen: set[str] = set()
    output: list[dict[str, object]] = []
    class_counts_2024: dict[str, int] = {}
    for row in rows:
        source_name = row["KABUPATEN/KOTA"].strip()
        if source_name not in mapping:
            raise RuntimeError(f"M61 unmapped source geography: {source_name}")
        geography_id, canonical_name = mapping[source_name]
        if geography_id in seen:
            raise RuntimeError(f"M61 duplicate geography: {geography_id}")
        seen.add(geography_id)
        risk_2024 = row["KELAS RISIKO 2024"].strip().lower()
        class_counts_2024[risk_2024] = class_counts_2024.get(risk_2024, 0) + 1
        for year in YEARS:
            score = float(row[str(year)])
            output.append({
                "year": year,
                "geography_id": geography_id,
                "geography_name": canonical_name,
                "source_geography_name": source_name,
                "irbi_score": f"{score:.2f}",
                "risk_class": risk_2024 if year == 2024 else "",
                "unit": "index_points",
                "claim_type": "official_index",
                "source_family": "BNPB IRBI 2024",
                "source_page": 67,
            })

    if len(seen) != 19 or len(output) != 190:
        raise RuntimeError("M61 canonical footprint drift")
    if class_counts_2024 != {"tinggi": 8, "sedang": 11}:
        raise RuntimeError(f"M61 2024 class footprint drift: {class_counts_2024}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0].keys()))
        writer.writeheader()
        writer.writerows(output)

    by_year: dict[int, list[float]] = {year: [] for year in YEARS}
    for row in output:
        by_year[int(row["year"])].append(float(row["irbi_score"]))
    mean_by_year = {str(year): round(sum(values) / len(values), 4) for year, values in by_year.items()}

    final = {
        "schema": "ranah-observatory/milestone61-irbi-sumbar-2015-2024-final/v1",
        "milestone": 61,
        "depends_on": [60],
        "source_manifest": {"path": ACQ.relative_to(ROOT).as_posix(), "sha256": sha256(ACQ)},
        "geography_registry": {"path": GEOGRAPHIES.relative_to(ROOT).as_posix(), "sha256": sha256(GEOGRAPHIES)},
        "methodology_boundary": {
            "index_components": ["hazard", "vulnerability", "capacity"],
            "hazard_and_vulnerability_treated_as_baseline_in_publication": True,
            "capacity_updated_periodically": True,
            "capacity_is_primary_driver_of_year_to_year_index_change_in_publication": True,
            "irbi_is_not_an_event_forecast": True,
            "irbi_is_not_an_observed_event_count": True,
            "lower_score_interpreted_as_lower_composite_risk": True,
        },
        "result": {
            "district_count": 19,
            "year_count": 10,
            "canonical_row_count": 190,
            "period_start": 2015,
            "period_end": 2024,
            "risk_class_year": 2024,
            "risk_class_counts_2024": class_counts_2024,
            "geography_mapping_complete": True,
            "dashboard_risk_timeseries_ready": True,
            "dashboard_risk_map_2024_ready": True,
            "hazard_specific_risk_dimension_present": False,
            "prediction_claim_authorized": False,
            "missing_values_imputed": False,
        },
        "derived_check_only": {"mean_of_19_district_scores_by_year": mean_by_year},
        "output": {"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OUT)},
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
