#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE9_HYDROCLIMATE_CASE_STUDY_SPEC.md"
GATE = ROOT / "data/manifests/milestone9_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone9_hydroclimate_case_study.json"
FRAME = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-geography-frame.csv"
CORRELATIONS = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-correlations.csv"
LOO = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-leave-one-out.csv"

EXPECTED_OUTCOMES = {"flood_events", "landslide_events", "hydroclimate_event_count"}
EXPECTED_CLIMATE_METRICS = {"rainfall_z_2024", "rainfall_2024_mm"}
REQUIRED_SPEC_PHRASES = [
    "one climate/disaster case study relevant to West Sumatra",
    "selected **from the qualified disaster-source contract before inspecting the rainfall/disaster association**",
    "1981–2023",
    "descriptive climate/disaster case study",
    "does not estimate the causal effect of rainfall on disasters",
    "model_estimate",
    "zero BNPB count proves no disaster occurred",
    "climate-change attribution",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [SPEC, GATE, MANIFEST, FRAME, CORRELATIONS, LOO]
    for path in required:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        return {"schema": "ranah-observatory/milestone9-audit/v1", "errors": errors, "milestone9_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    frame = rows(FRAME)
    corr = rows(CORRELATIONS)
    loo = rows(LOO)

    for phrase in REQUIRED_SPEC_PHRASES:
        if phrase not in spec:
            errors.append(f"Milestone 9 spec lost required phrase: {phrase}")

    if gate.get("schema") != "ranah-observatory/milestone9-design-gate/v1":
        errors.append("Milestone 9 design-gate schema drift")
    locked_gate = {
        "study_year": 2024,
        "geography_count": 19,
        "baseline_start_year": 1981,
        "baseline_end_year": 2023,
        "baseline_year_count": 43,
        "primary_climate_metric": "rainfall_z_2024",
        "primary_association_statistic": "spearman",
        "secondary_association_statistic": "pearson",
        "zero_event_geographies_must_be_retained": True,
        "daily_rainfall_claim_authorized": False,
        "station_observation_equivalence_authorized": False,
        "causal_attribution_authorized": False,
        "climate_change_attribution_authorized": False,
        "association_computed": False,
        "milestone9_complete": False,
    }
    for key, expected in locked_gate.items():
        if gate.get(key) != expected:
            errors.append(f"Milestone 9 pre-analysis design gate drift: {key}")
    if set(gate.get("primary_disaster_outcomes", [])) != {"flood_events", "landslide_events"}:
        errors.append("Milestone 9 disaster-outcome contract drift")

    if manifest.get("schema") != "ranah-observatory/milestone9-hydroclimate-case-study/v1":
        errors.append("Milestone 9 case-study manifest schema drift")
    if manifest.get("criterion") != "one climate/disaster case study relevant to West Sumatra":
        errors.append("Milestone 9 criterion drift")
    if manifest.get("study_year_selected_before_association_inspection") is not True:
        errors.append("Milestone 9 study year must remain selected before association inspection")
    if manifest.get("geography_count") != 19 or manifest.get("frame_row_count") != 19:
        errors.append("Milestone 9 exact 19-geography frame lost")
    if manifest.get("baseline_year_count") != 43 or manifest.get("baseline_years") != [1981, 2023]:
        errors.append("Milestone 9 baseline footprint drift")
    if manifest.get("climate_claim_type") != "model_estimate":
        errors.append("CHIRPS must remain model_estimate evidence")
    if manifest.get("station_observation_equivalence") is not False:
        errors.append("Milestone 9 falsely claims station-observation equivalence")
    if manifest.get("independent_station_validation") != "pending":
        errors.append("Milestone 9 must preserve pending station-validation status")
    if manifest.get("bnpb_official_crosscheck") != "passed":
        errors.append("Milestone 9 BNPB official cross-check no longer passes")
    if manifest.get("zero_event_geographies_retained") is not True:
        errors.append("Milestone 9 dropped zero-event geographies")
    if manifest.get("causal_attribution_performed") is not False:
        errors.append("Milestone 9 must not perform causal rainfall-disaster attribution")
    if manifest.get("climate_change_attribution_performed") is not False:
        errors.append("Milestone 9 must not perform climate-change attribution")
    if manifest.get("daily_rainfall_claim_performed") is not False:
        errors.append("Milestone 9 must not claim annual CHIRPS as event-day rainfall")
    if manifest.get("annual_rainfall_temporal_resolution_limitation") is not True:
        errors.append("Milestone 9 lost annual-rainfall temporal-resolution caveat")
    if manifest.get("claim_classification") != "descriptive_climate_disaster_spatial_case_study":
        errors.append("Milestone 9 claim classification drift")
    if manifest.get("milestone9_complete") is not True:
        errors.append("Milestone 9 completion flag is false")

    for kind, record in manifest.get("inputs", {}).items():
        path = ROOT / str(record.get("path", ""))
        if not path.exists() or sha256(path) != record.get("sha256"):
            errors.append(f"Milestone 9 input checksum drift: {kind}")
    for kind, record in manifest.get("outputs", {}).items():
        path = ROOT / str(record.get("path", ""))
        if not path.exists() or sha256(path) != record.get("sha256"):
            errors.append(f"Milestone 9 output checksum drift: {kind}")

    if len(frame) != 19 or len({row["geography_id"] for row in frame}) != 19:
        errors.append("Milestone 9 frame must contain 19 unique geographies")
    for row in frame:
        try:
            numerics = [
                float(row["rainfall_2024_mm"]),
                float(row["baseline_1981_2023_mean_mm"]),
                float(row["baseline_1981_2023_sample_sd_mm"]),
                float(row["rainfall_anomaly_mm"]),
                float(row["rainfall_anomaly_percent"]),
                float(row["rainfall_z_2024"]),
                float(row["rainfall_baseline_percentile"]),
                float(row["flood_events"]),
                float(row["landslide_events"]),
                float(row["hydroclimate_event_count"]),
            ]
        except (KeyError, ValueError):
            errors.append(f"Milestone 9 invalid numeric frame row: {row.get('geography_id')}")
            continue
        if not all(math.isfinite(value) for value in numerics):
            errors.append(f"Milestone 9 non-finite frame row: {row.get('geography_id')}")
        if float(row["rainfall_2024_mm"]) < 0 or float(row["flood_events"]) < 0 or float(row["landslide_events"]) < 0:
            errors.append(f"Milestone 9 negative source value: {row.get('geography_id')}")
        if float(row["hydroclimate_event_count"]) != float(row["flood_events"]) + float(row["landslide_events"]):
            errors.append(f"Milestone 9 derived event-count mismatch: {row.get('geography_id')}")

    correlation_keys = {(row.get("climate_metric"), row.get("disaster_metric")) for row in corr}
    expected_correlation_keys = {(c, d) for c in EXPECTED_CLIMATE_METRICS for d in EXPECTED_OUTCOMES}
    if len(corr) != 6 or correlation_keys != expected_correlation_keys:
        errors.append("Milestone 9 correlation matrix must contain exact 2x3 preregistered outputs")
    for row in corr:
        try:
            values = [float(row["pearson"]), float(row["spearman"])]
        except (KeyError, ValueError):
            errors.append("Milestone 9 invalid correlation row")
            continue
        if not all(math.isfinite(v) and -1.0 <= v <= 1.0 for v in values):
            errors.append("Milestone 9 invalid correlation coefficient")
        if row.get("claim_scope") != "descriptive_spatial_association_not_causal":
            errors.append("Milestone 9 correlation claim scope drift")

    loo_keys = {(row.get("disaster_metric"), row.get("excluded_geography_id")) for row in loo}
    geographies = {row["geography_id"] for row in frame}
    if len(loo) != 57 or len(loo_keys) != 57:
        errors.append("Milestone 9 leave-one-out output must contain exact 3x19 rows")
    for outcome in EXPECTED_OUTCOMES:
        excluded = {row["excluded_geography_id"] for row in loo if row.get("disaster_metric") == outcome}
        if excluded != geographies:
            errors.append(f"Milestone 9 leave-one-out geography coverage drift: {outcome}")
    for row in loo:
        if row.get("remaining_geography_count") != "18":
            errors.append("Milestone 9 leave-one-out sample size must remain 18")
        try:
            values = [float(row["pearson"]), float(row["spearman"])]
        except (KeyError, ValueError):
            errors.append("Milestone 9 invalid leave-one-out row")
            continue
        if not all(math.isfinite(v) and -1.0 <= v <= 1.0 for v in values):
            errors.append("Milestone 9 invalid leave-one-out coefficient")

    return {
        "schema": "ranah-observatory/milestone9-audit/v1",
        "criterion": manifest.get("criterion"),
        "case_study": manifest.get("case_study"),
        "geography_count": len(frame),
        "correlation_row_count": len(corr),
        "leave_one_out_row_count": len(loo),
        "study_year_selected_before_association_inspection": manifest.get("study_year_selected_before_association_inspection") is True,
        "causal_attribution_performed": manifest.get("causal_attribution_performed") is True,
        "climate_change_attribution_performed": manifest.get("climate_change_attribution_performed") is True,
        "station_observation_equivalence": manifest.get("station_observation_equivalence") is True,
        "milestone9_complete": manifest.get("milestone9_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 9 hydroclimate disaster case study")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone9_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
