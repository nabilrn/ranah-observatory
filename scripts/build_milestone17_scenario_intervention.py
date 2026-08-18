#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
M11_MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M11_COEFFICIENTS = ROOT / "data/analysis/engine/expected_performance_v2/m11-outer-fold-coefficients.csv"
M14_MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"
M15_MANIFEST = ROOT / "data/manifests/milestone15_causal_evidence_expansion.json"
M16_MANIFEST = ROOT / "data/manifests/milestone16_spatial_climate_risk.json"
OUT_DIR = ROOT / "data/analysis/engine/scenario_intervention_v1"
LIBRARY_OUT = OUT_DIR / "m17-scenario-library.csv"
MAPPINGS_OUT = OUT_DIR / "m17-model-sensitivity-mappings.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone17_scenario_intervention.json"

FEATURES = [
    "mean_years_schooling",
    "labor_force_participation",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
]
TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
TARGET_DIRECTIONS = {
    "poverty_rate": "lower_is_favorable",
    "unemployment_rate": "lower_is_favorable",
    "real_grdp_growth": "higher_is_favorable",
}
SCENARIO_IDS = {
    "mean_years_schooling": "m17_s1_mean_years_schooling",
    "labor_force_participation": "m17_s2_labor_force_participation",
    "agriculture_share_grdp": "m17_s3_agriculture_share_grdp",
    "manufacturing_share_grdp": "m17_s4_manufacturing_share_grdp",
    "rice_yield": "m17_s5_rice_yield",
}
SCENARIO_NAMES = {
    "mean_years_schooling": "human_capital_state_sensitivity",
    "labor_force_participation": "labor_participation_state_sensitivity",
    "agriculture_share_grdp": "agriculture_structure_state_sensitivity",
    "manufacturing_share_grdp": "manufacturing_structure_state_sensitivity",
    "rice_yield": "agricultural_productivity_state_sensitivity",
}
PERTURBATION_SD = 0.5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise RuntimeError("quantile requires non-empty values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def require_false(payload: dict[str, Any], key: str, label: str) -> None:
    if payload.get(key) is not False:
        raise RuntimeError(f"{label} guard drift: {key}={payload.get(key)!r}")


def main() -> int:
    m11 = json.loads(M11_MANIFEST.read_text(encoding="utf-8"))
    m14 = json.loads(M14_MANIFEST.read_text(encoding="utf-8"))
    m15 = json.loads(M15_MANIFEST.read_text(encoding="utf-8"))
    m16 = json.loads(M16_MANIFEST.read_text(encoding="utf-8"))

    if m11.get("schema") != "ranah-observatory/milestone11-expected-performance-v2/v1" or m11.get("milestone11_complete") is not True:
        raise RuntimeError("M11 expected-performance contract invalid")
    if m11.get("benchmark_qualified_target_ids") != TARGETS:
        raise RuntimeError("M17 expects all three fixed M11 targets benchmark-qualified in locked order")
    if m11.get("primary_feature_ids") != FEATURES:
        raise RuntimeError("M11 primary feature set drift")
    require_false(m11, "causal_analysis_performed", "M11")
    require_false(m11, "coefficient_causal_interpretation_authorized", "M11")
    require_false(m11, "counterfactual_policy_effect_estimated", "M11")
    if sha256(M11_COEFFICIENTS) != m11.get("outputs", {}).get("outer_fold_coefficients", {}).get("sha256"):
        raise RuntimeError("M11 coefficient checksum drift")

    if m14.get("schema") != "ranah-observatory/milestone14-bottleneck-association/v1" or m14.get("milestone14_complete") is not True:
        raise RuntimeError("M14 association contract invalid")
    if m14.get("stable_association_signal_count") != 1:
        raise RuntimeError("M14 stable association count drift")
    require_false(m14, "causal_analysis_performed", "M14")
    require_false(m14, "policy_priority_claim_authorized", "M14")

    if m15.get("schema") != "ranah-observatory/milestone15-causal-evidence-expansion/v1" or m15.get("milestone15_complete") is not True:
        raise RuntimeError("M15 causal evidence contract invalid")
    if m15.get("new_causal_model_fit_count") != 0 or m15.get("not_identification_ready_count") != 2:
        raise RuntimeError("M15 identification state drift")
    require_false(m15, "causal_claim_created_from_m14_association", "M15")
    require_false(m15, "same_data_m14_signal_upgraded_to_causal_model", "M15")

    if m16.get("schema") != "ranah-observatory/milestone16-spatial-climate-risk/v1" or m16.get("milestone16_complete") is not True:
        raise RuntimeError("M16 spatial/climate contract invalid")
    require_false(m16, "risk_synthesis_authorized", "M16")
    require_false(m16, "composite_risk_score_created", "M16")

    coefficient_rows = read_csv(M11_COEFFICIENTS)
    if len(coefficient_rows) != 684:
        raise RuntimeError(f"M11 coefficient footprint drift: {len(coefficient_rows)}")

    grouped: dict[tuple[str, str], list[float]] = {}
    holdouts: dict[tuple[str, str], set[str]] = {}
    for row in coefficient_rows:
        if row.get("model_variant") != "primary":
            continue
        if row.get("parameter_type") != "standardized_continuous_feature":
            continue
        target = row.get("target_id", "")
        feature = row.get("parameter_id", "")
        if target not in TARGETS or feature not in FEATURES:
            raise RuntimeError(f"unexpected M11 primary feature coefficient: {target} {feature}")
        key = (feature, target)
        value = float(row["coefficient"])
        if not math.isfinite(value):
            raise RuntimeError(f"non-finite coefficient: {key}")
        grouped.setdefault(key, []).append(value)
        holdouts.setdefault(key, set()).add(row["outer_holdout_geography_id"])

    expected_keys = {(feature, target) for feature in FEATURES for target in TARGETS}
    if set(grouped) != expected_keys:
        raise RuntimeError("M17 lost one or more preregistered feature-target mappings")

    mapping_rows: list[dict[str, Any]] = []
    for feature in FEATURES:
        for target in TARGETS:
            key = (feature, target)
            coefficients = grouped[key]
            if len(coefficients) != 19 or len(holdouts[key]) != 19:
                raise RuntimeError(f"M17 mapping does not contain 19 unique outer folds: {key}")
            plus = [PERTURBATION_SD * value for value in coefficients]
            minus = [-value for value in plus]
            positive = sum(value > 0 for value in plus)
            negative = sum(value < 0 for value in plus)
            zero = len(plus) - positive - negative
            mapping_rows.append(
                {
                    "scenario_id": SCENARIO_IDS[feature],
                    "feature_id": feature,
                    "target_id": target,
                    "target_direction": TARGET_DIRECTIONS[target],
                    "outer_fold_count": len(coefficients),
                    "perturbation_standardized_units": PERTURBATION_SD,
                    "plus_half_sd_delta_min": min(plus),
                    "plus_half_sd_delta_p10": quantile(plus, 0.10),
                    "plus_half_sd_delta_median": quantile(plus, 0.50),
                    "plus_half_sd_delta_p90": quantile(plus, 0.90),
                    "plus_half_sd_delta_max": max(plus),
                    "minus_half_sd_delta_min": min(minus),
                    "minus_half_sd_delta_p10": quantile(minus, 0.10),
                    "minus_half_sd_delta_median": quantile(minus, 0.50),
                    "minus_half_sd_delta_p90": quantile(minus, 0.90),
                    "minus_half_sd_delta_max": max(minus),
                    "plus_delta_positive_fold_share": positive / len(plus),
                    "plus_delta_negative_fold_share": negative / len(plus),
                    "plus_delta_zero_fold_share": zero / len(plus),
                    "dominant_sign_retention": max(positive, negative, zero) / len(plus),
                    "model_delta_unit": "target_percentage_points",
                    "uncertainty_basis": "dispersion_across_19_outer_fold_predictive_coefficients",
                    "causal_interpretation_authorized": False,
                    "policy_effect_interpretation_authorized": False,
                }
            )

    structural_omissions = (
        "joint_feature_movement;raw_unit_delivery_mapping;general_equilibrium_response;"
        "implementation_feasibility;causal_confounding;policy_package_design"
    )
    library_rows: list[dict[str, Any]] = []
    for feature in FEATURES:
        library_rows.append(
            {
                "scenario_id": SCENARIO_IDS[feature],
                "scenario_name": SCENARIO_NAMES[feature],
                "intervention_variable": feature,
                "assumed_change": "symmetric_plus_minus_0.5_training_fold_sd",
                "empirical_model_mapping": "M11_primary_outer_fold_predictive_coefficients",
                "mapping_count": 3,
                "evidence_strength": "benchmark_qualified_predictive_noncausal",
                "uncertainty": "cross_fold_coefficient_dispersion_not_statistical_treatment_effect_interval",
                "implementation_horizon": "implementation_horizon_not_estimated",
                "cost_information": "cost_not_qualified",
                "important_omitted_mechanisms": structural_omissions,
                "scenario_status": "quantitative_model_sensitivity_only",
                "causal_effect_authorized": False,
                "forecast_authorized": False,
                "policy_recommendation_authorized": False,
                "cost_benefit_authorized": False,
            }
        )

    library_rows.extend(
        [
            {
                "scenario_id": "m17_b1_rainfall_labor_adaptation",
                "scenario_name": "rainfall_labor_adaptation",
                "intervention_variable": "climate_resilience_or_labor_adaptation_mechanism_unidentified",
                "assumed_change": "not_authorized",
                "empirical_model_mapping": "M14_stable_association_plus_M15_identification_gate",
                "mapping_count": 0,
                "evidence_strength": "stable_association_identification_not_ready",
                "uncertainty": "causal_mechanism_and_independent_confirmation_unresolved",
                "implementation_horizon": "implementation_horizon_not_estimated",
                "cost_information": "cost_not_qualified",
                "important_omitted_mechanisms": "event_timing;station_validation;spatial_weather_dependence;adaptation_channel;labor_demand_channel;independent_confirmation",
                "scenario_status": "blocked_causal_mapping",
                "causal_effect_authorized": False,
                "forecast_authorized": False,
                "policy_recommendation_authorized": False,
                "cost_benefit_authorized": False,
            },
            {
                "scenario_id": "m17_b2_disaster_risk_reduction",
                "scenario_name": "disaster_risk_reduction",
                "intervention_variable": "exposure_vulnerability_capacity_reduction_package_unidentified",
                "assumed_change": "not_authorized",
                "empirical_model_mapping": "M16_spatial_component_readiness_gate",
                "mapping_count": 0,
                "evidence_strength": "spatial_components_incomplete_for_risk_synthesis",
                "uncertainty": "exposure_vulnerability_capacity_observed_impact_mapping_incomplete",
                "implementation_horizon": "implementation_horizon_not_estimated",
                "cost_information": "cost_not_qualified",
                "important_omitted_mechanisms": "exposure;vulnerability;capacity;asset_values;affected_population;observed_losses;intervention_effectiveness",
                "scenario_status": "blocked_risk_mapping",
                "causal_effect_authorized": False,
                "forecast_authorized": False,
                "policy_recommendation_authorized": False,
                "cost_benefit_authorized": False,
            },
        ]
    )

    write_csv(MAPPINGS_OUT, mapping_rows)
    write_csv(LIBRARY_OUT, library_rows)

    manifest = {
        "schema": "ranah-observatory/milestone17-scenario-intervention/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 17,
        "criterion": "transparent scenario semantics and predictive sensitivity with fail-closed intervention claims",
        "scenario_count": len(library_rows),
        "quantitative_model_sensitivity_scenario_count": 5,
        "blocked_intervention_scenario_count": 2,
        "model_sensitivity_mapping_count": len(mapping_rows),
        "feature_count": len(FEATURES),
        "target_count": len(TARGETS),
        "outer_fold_count_per_mapping": 19,
        "perturbation_standardized_units": PERTURBATION_SD,
        "symmetric_perturbation": True,
        "desired_direction_selected_after_coefficient_inspection": False,
        "all_preregistered_feature_target_mappings_retained": True,
        "causal_policy_counterfactual_estimated": False,
        "policy_recommendation_authorized": False,
        "forecast_authorized": False,
        "cost_benefit_analysis_performed": False,
        "implementation_horizon_estimated": False,
        "m14_rainfall_association_promoted_to_policy_effect": False,
        "m15_identification_blocks_overridden": False,
        "m16_risk_synthesis_block_overridden": False,
        "monetary_wasted_potential_estimated": False,
        "inputs": {
            "m11_manifest": {"path": str(M11_MANIFEST.relative_to(ROOT)), "sha256": sha256(M11_MANIFEST)},
            "m11_outer_fold_coefficients": {"path": str(M11_COEFFICIENTS.relative_to(ROOT)), "sha256": sha256(M11_COEFFICIENTS)},
            "m14_manifest": {"path": str(M14_MANIFEST.relative_to(ROOT)), "sha256": sha256(M14_MANIFEST)},
            "m15_manifest": {"path": str(M15_MANIFEST.relative_to(ROOT)), "sha256": sha256(M15_MANIFEST)},
            "m16_manifest": {"path": str(M16_MANIFEST.relative_to(ROOT)), "sha256": sha256(M16_MANIFEST)},
        },
        "outputs": {
            "scenario_library": {"path": str(LIBRARY_OUT.relative_to(ROOT)), "sha256": sha256(LIBRARY_OUT)},
            "model_sensitivity_mappings": {"path": str(MAPPINGS_OUT.relative_to(ROOT)), "sha256": sha256(MAPPINGS_OUT)},
        },
        "milestone17_complete": True,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
