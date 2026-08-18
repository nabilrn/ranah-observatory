#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE17_SCENARIO_INTERVENTION_SPEC.md"
MANIFEST = ROOT / "data/manifests/milestone17_scenario_intervention.json"
LIBRARY = ROOT / "data/analysis/engine/scenario_intervention_v1/m17-scenario-library.csv"
MAPPINGS = ROOT / "data/analysis/engine/scenario_intervention_v1/m17-model-sensitivity-mappings.csv"

FEATURES = {
    "mean_years_schooling",
    "labor_force_participation",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
}
TARGETS = {"poverty_rate", "unemployment_rate", "real_grdp_growth"}
EXPECTED_SCENARIOS = {
    "m17_s1_mean_years_schooling",
    "m17_s2_labor_force_participation",
    "m17_s3_agriculture_share_grdp",
    "m17_s4_manufacturing_share_grdp",
    "m17_s5_rice_yield",
    "m17_b1_rainfall_labor_adaptation",
    "m17_b2_disaster_risk_reduction",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    for path in (SPEC, MANIFEST, LIBRARY, MAPPINGS):
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        return {"schema": "ranah-observatory/milestone17-audit/v1", "errors": errors, "milestone17_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    library = rows(LIBRARY)
    mappings = rows(MAPPINGS)

    for phrase in (
        "±0.5 training-fold standardized feature units",
        "No feature/target mapping may be dropped because its sign is inconvenient.",
        "No scenario is a policy recommendation.",
        "blocked_causal_mapping",
        "blocked_risk_mapping",
        "cost_not_qualified",
        "implementation_horizon_not_estimated",
    ):
        if phrase not in spec:
            errors.append(f"M17 spec lost guardrail: {phrase}")

    if manifest.get("schema") != "ranah-observatory/milestone17-scenario-intervention/v1":
        errors.append("manifest schema drift")
    if manifest.get("milestone17_complete") is not True:
        errors.append("M17 completion flag false")
    exact_counts = {
        "scenario_count": 7,
        "quantitative_model_sensitivity_scenario_count": 5,
        "blocked_intervention_scenario_count": 2,
        "model_sensitivity_mapping_count": 15,
        "feature_count": 5,
        "target_count": 3,
        "outer_fold_count_per_mapping": 19,
    }
    for key, expected in exact_counts.items():
        if manifest.get(key) != expected:
            errors.append(f"M17 count drift: {key}")
    if manifest.get("perturbation_standardized_units") != 0.5 or manifest.get("symmetric_perturbation") is not True:
        errors.append("M17 perturbation contract drift")
    if manifest.get("all_preregistered_feature_target_mappings_retained") is not True:
        errors.append("M17 no longer retains all preregistered mappings")

    false_guards = (
        "desired_direction_selected_after_coefficient_inspection",
        "causal_policy_counterfactual_estimated",
        "policy_recommendation_authorized",
        "forecast_authorized",
        "cost_benefit_analysis_performed",
        "implementation_horizon_estimated",
        "m14_rainfall_association_promoted_to_policy_effect",
        "m15_identification_blocks_overridden",
        "m16_risk_synthesis_block_overridden",
        "monetary_wasted_potential_estimated",
    )
    for key in false_guards:
        if manifest.get(key) is not False:
            errors.append(f"M17 false guard enabled: {key}")

    for key, rec in manifest.get("inputs", {}).items():
        path = ROOT / str(rec.get("path", ""))
        if not path.exists() or sha256(path) != rec.get("sha256"):
            errors.append(f"M17 input checksum drift: {key}")
    for key, rec in manifest.get("outputs", {}).items():
        path = ROOT / str(rec.get("path", ""))
        if not path.exists() or sha256(path) != rec.get("sha256"):
            errors.append(f"M17 output checksum drift: {key}")

    if len(library) != 7 or {row.get("scenario_id") for row in library} != EXPECTED_SCENARIOS:
        errors.append("M17 scenario library footprint drift")
    for row in library:
        for column in ("causal_effect_authorized", "forecast_authorized", "policy_recommendation_authorized", "cost_benefit_authorized"):
            if row.get(column, "").lower() != "false":
                errors.append(f"scenario improperly authorizes {column}: {row.get('scenario_id')}")
        if row.get("implementation_horizon") != "implementation_horizon_not_estimated":
            errors.append(f"scenario invented implementation horizon: {row.get('scenario_id')}")
        if row.get("cost_information") != "cost_not_qualified":
            errors.append(f"scenario invented cost information: {row.get('scenario_id')}")

    by_scenario = {row["scenario_id"]: row for row in library}
    if by_scenario.get("m17_b1_rainfall_labor_adaptation", {}).get("scenario_status") != "blocked_causal_mapping":
        errors.append("rainfall/labor scenario no longer blocked")
    if by_scenario.get("m17_b2_disaster_risk_reduction", {}).get("scenario_status") != "blocked_risk_mapping":
        errors.append("disaster-risk scenario no longer blocked")

    if len(mappings) != 15:
        errors.append("M17 mapping row count drift")
    mapping_keys = {(row.get("feature_id"), row.get("target_id")) for row in mappings}
    if mapping_keys != {(feature, target) for feature in FEATURES for target in TARGETS}:
        errors.append("M17 feature-target mapping grid incomplete")
    for row in mappings:
        if row.get("outer_fold_count") != "19":
            errors.append(f"mapping outer-fold count drift: {row.get('feature_id')} {row.get('target_id')}")
        if float(row.get("perturbation_standardized_units", "nan")) != 0.5:
            errors.append(f"mapping perturbation drift: {row.get('feature_id')} {row.get('target_id')}")
        if row.get("causal_interpretation_authorized", "").lower() != "false":
            errors.append(f"mapping causal interpretation enabled: {row.get('feature_id')} {row.get('target_id')}")
        if row.get("policy_effect_interpretation_authorized", "").lower() != "false":
            errors.append(f"mapping policy interpretation enabled: {row.get('feature_id')} {row.get('target_id')}")
        plus_median = float(row["plus_half_sd_delta_median"])
        minus_median = float(row["minus_half_sd_delta_median"])
        if abs(plus_median + minus_median) > 1e-12:
            errors.append(f"mapping lost symmetric perturbation: {row.get('feature_id')} {row.get('target_id')}")
        shares = sum(float(row[column]) for column in ("plus_delta_positive_fold_share", "plus_delta_negative_fold_share", "plus_delta_zero_fold_share"))
        if abs(shares - 1.0) > 1e-12:
            errors.append(f"mapping fold sign shares do not sum to one: {row.get('feature_id')} {row.get('target_id')}")

    return {
        "schema": "ranah-observatory/milestone17-audit/v1",
        "scenario_count": len(library),
        "mapping_count": len(mappings),
        "feature_count": len({row.get("feature_id") for row in mappings}),
        "target_count": len({row.get("target_id") for row in mappings}),
        "blocked_scenario_count": sum(row.get("scenario_status", "").startswith("blocked_") for row in library),
        "policy_recommendation_authorized": manifest.get("policy_recommendation_authorized"),
        "milestone17_complete": manifest.get("milestone17_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_complete and not report["milestone17_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
