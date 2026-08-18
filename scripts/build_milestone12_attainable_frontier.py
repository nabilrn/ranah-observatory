#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
M11_PREDICTIONS = ROOT / "data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv"
M11_MODEL_FRAME = ROOT / "data/analysis/engine/expected_performance_v2/m11-model-frame.csv"
M11_MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M7_CV = ROOT / "data/analysis/expected_performance/m7-ridge-selected-loocv-predictions.csv"
M7_WS = ROOT / "data/analysis/expected_performance/m7-west-sumatra-expected-performance.json"
M7_AUDIT = ROOT / "data/manifests/milestone7_expected_performance_audit.json"
METHOD_REGISTRY = ROOT / "data/registries/milestone12_frontier_method_qualification.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone12_design_gate.json"
SPEC = ROOT / "research/MILESTONE12_ATTAINABLE_FRONTIER_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/frontier_v1"
DISTRICT_OUT = OUT_DIR / "m12-district-frontier.csv"
SUMMARY_OUT = OUT_DIR / "m12-district-method-summary.csv"
NEIGHBOR_SENS_OUT = OUT_DIR / "m12-neighbor-sensitivity.csv"
NATIONAL_OUT = OUT_DIR / "m12-national-west-sumatra-frontier.json"
MANIFEST_OUT = ROOT / "data/manifests/milestone12_attainable_frontier.json"

TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
DIRECTION = {
    "poverty_rate": "lower_is_favorable",
    "unemployment_rate": "lower_is_favorable",
    "real_grdp_growth": "higher_is_favorable",
}
PRIMARY_FEATURES = [
    "mean_years_schooling",
    "labor_force_participation",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
]
LOW_Q = 0.10
HIGH_Q = 0.90
CALIBRATION_MIN = 0.04
CALIBRATION_MAX = 0.20
K_PRIMARY = 6
FAVORABLE_NEIGHBORS = 2
K_SENSITIVITY = [5, 7]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def median(values: list[float]) -> float:
    return quantile(values, 0.5)


def quantile(values: list[float], probability: float) -> float:
    if not values or not 0.0 <= probability <= 1.0:
        raise ValueError("invalid quantile request")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def f(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid numeric field {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric field {key}")
    return value


def fmt(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.12g}"
    return value


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("pearson requires paired values")
    mx = mean(x)
    my = mean(y)
    sx = sum((v - mx) ** 2 for v in x)
    sy = sum((v - my) ** 2 for v in y)
    if sx <= 0.0 or sy <= 0.0:
        raise ValueError("pearson undefined for constant input")
    covariance = sum((a - mx) * (b - my) for a, b in zip(x, y))
    return covariance / math.sqrt(sx * sy)


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        average_rank = (i + 1 + j) / 2.0
        for position in range(i, j):
            ranks[indexed[position][0]] = average_rank
        i = j
    return ranks


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(average_ranks(x), average_ranks(y))


def validate_prefit() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    m11 = json.loads(M11_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    methods = read_csv(METHOD_REGISTRY)
    if m11.get("milestone11_complete") is not True or m11.get("crossfit_prediction_count") != 342:
        raise ValueError("M12 requires completed M11 engine")
    expected_gate = {
        "schema": "ranah-observatory/milestone12-design-gate/v1",
        "district_primary_method": "conditional_favorable_residual_quantile",
        "district_alternative_method": "structural_neighbor_favorable_envelope",
        "district_target_ids": TARGETS,
        "lower_is_favorable_quantile": LOW_Q,
        "higher_is_favorable_quantile": HIGH_Q,
        "calibration_rate_min": CALIBRATION_MIN,
        "calibration_rate_max": CALIBRATION_MAX,
        "neighbor_k": K_PRIMARY,
        "neighbor_favorable_count": FAVORABLE_NEIGHBORS,
        "neighbor_k_sensitivity": K_SENSITIVITY,
        "national_target_id": "real_grdp_per_capita",
        "national_reference_year": 2024,
        "national_favorable_residual_quantile": HIGH_Q,
        "frontier_computed": False,
        "frontier_results_inspected": False,
        "milestone12_complete": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise ValueError(f"M12 prefit design-gate drift: {key}")
    for flag in [
        "methods_selected_before_frontier_results",
        "quantiles_selected_before_frontier_results",
        "calibration_band_selected_before_frontier_results",
        "neighbor_parameters_selected_before_frontier_results",
    ]:
        if gate.get(flag) is not True:
            raise ValueError(f"M12 prefit lock flag lost: {flag}")
    status = {row["method_id"]: row["qualification_status"] for row in methods}
    expected_status = {
        "conditional_favorable_residual_quantile": "qualified",
        "structural_neighbor_favorable_envelope": "qualified",
        "national_m7_favorable_residual_quantile": "qualified",
        "classic_dea": "rejected",
        "classic_halfnormal_sfa": "deferred",
        "linear_quantile_regression": "deferred",
    }
    if status != expected_status:
        raise ValueError(f"M12 method qualification registry drift: {status}")
    return m11, gate, methods


def favorable_quantile_for_target(target: str) -> float:
    return LOW_Q if DIRECTION[target] == "lower_is_favorable" else HIGH_Q


def unified_distance(target: str, observed: float, reference: float) -> float:
    if DIRECTION[target] == "lower_is_favorable":
        return observed - reference
    return reference - observed


def favorable_exceeded(target: str, observed: float, reference: float) -> bool:
    if DIRECTION[target] == "lower_is_favorable":
        return observed <= reference
    return observed >= reference


def neighbor_reference(
    focal: dict[str, str],
    same_year_peers: list[dict[str, str]],
    target: str,
    k_neighbors: int,
) -> tuple[float, list[str], list[float], list[float]]:
    if len(same_year_peers) != 18:
        raise ValueError("M12 neighbor method requires exact 18 same-year non-focal peers")
    feature_means: dict[str, float] = {}
    feature_scales: dict[str, float] = {}
    for feature in PRIMARY_FEATURES:
        column = f"lag1_{feature}"
        values = [f(row, column) for row in same_year_peers]
        mu = mean(values)
        scale = math.sqrt(mean([(value - mu) ** 2 for value in values]))
        if scale <= 1e-12:
            raise ValueError(f"M12 neighbor feature has zero scale: {feature}")
        feature_means[feature] = mu
        feature_scales[feature] = scale

    distances: list[tuple[float, str, dict[str, str]]] = []
    for peer in same_year_peers:
        squared = 0.0
        for feature in PRIMARY_FEATURES:
            column = f"lag1_{feature}"
            focal_z = (f(focal, column) - feature_means[feature]) / feature_scales[feature]
            peer_z = (f(peer, column) - feature_means[feature]) / feature_scales[feature]
            squared += (focal_z - peer_z) ** 2
        distances.append((math.sqrt(squared), peer["geography_id"], peer))
    distances.sort(key=lambda item: (item[0], item[1]))
    selected = distances[:k_neighbors]
    outcomes = [(f(peer, target), geo, distance) for distance, geo, peer in selected]
    reverse = DIRECTION[target] == "higher_is_favorable"
    favorable = sorted(outcomes, key=lambda item: (item[0], item[1]), reverse=reverse)[:FAVORABLE_NEIGHBORS]
    reference = mean([item[0] for item in favorable])
    return (
        reference,
        [geo for _value, geo, _distance in favorable],
        [value for value, _geo, _distance in favorable],
        [distance for _value, _geo, distance in favorable],
    )


def build_district_lane() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    predictions = read_csv(M11_PREDICTIONS)
    frame = read_csv(M11_MODEL_FRAME)
    if len(predictions) != 342 or len(frame) != 114:
        raise ValueError("M12 district inputs lost M11 footprint")
    frame_lookup = {(row["geography_id"], row["target_year"]): row for row in frame}
    geographies = sorted({row["geography_id"] for row in frame})
    if len(geographies) != 19:
        raise ValueError("M12 district lane requires 19 geographies")

    primary_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    preliminary_summary: dict[str, dict[str, Any]] = {}

    for target in TARGETS:
        target_predictions = [row for row in predictions if row["target_id"] == target]
        if len(target_predictions) != 114:
            raise ValueError(f"M12 expected 114 M11 predictions for {target}")
        benchmark_flags = {row["benchmark_qualified"] for row in target_predictions}
        if len(benchmark_flags) != 1:
            raise ValueError(f"M11 benchmark flag inconsistent within {target}")
        benchmark_qualified = benchmark_flags == {"true"}

        for prediction in target_predictions:
            focal_geo = prediction["geography_id"]
            target_year = prediction["target_year"]
            observed = f(prediction, "observed")
            expected = f(prediction, "expected")
            calibration = [
                f(other, "residual_observed_minus_expected")
                for other in target_predictions
                if other["geography_id"] != focal_geo
            ]
            if len(calibration) != 108:
                raise ValueError("M12 primary frontier calibration must exclude focal geography and contain 108 residuals")
            q = favorable_quantile_for_target(target)
            favorable_residual = quantile(calibration, q)
            primary_reference = expected + favorable_residual
            primary_distance = unified_distance(target, observed, primary_reference)
            exceeded = favorable_exceeded(target, observed, primary_reference)

            focal_frame = frame_lookup[(focal_geo, target_year)]
            peers = [
                frame_lookup[(geo, target_year)]
                for geo in geographies
                if geo != focal_geo
            ]
            alt_reference, favorable_neighbor_ids, favorable_neighbor_outcomes, favorable_neighbor_distances = neighbor_reference(
                focal_frame, peers, target, K_PRIMARY
            )
            alt_distance = unified_distance(target, observed, alt_reference)

            primary_rows.append({
                "target_id": target,
                "target_direction": DIRECTION[target],
                "geography_id": focal_geo,
                "geography_name": prediction["geography_name"],
                "target_year": int(target_year),
                "feature_year": int(prediction["feature_year"]),
                "observed": observed,
                "m11_expected": expected,
                "m11_prediction_interval_lower": f(prediction, "exploratory_prediction_interval_lower"),
                "m11_prediction_interval_upper": f(prediction, "exploratory_prediction_interval_upper"),
                "m11_benchmark_qualified": benchmark_qualified,
                "m11_support_warning": prediction["support_warning"] == "true",
                "primary_method": "conditional_favorable_residual_quantile",
                "primary_favorable_quantile": q,
                "primary_focal_excluded_calibration_residual_count": len(calibration),
                "primary_favorable_residual_quantile_value": favorable_residual,
                "primary_favorable_reference": primary_reference,
                "primary_distance_to_favorable_reference": primary_distance,
                "primary_observed_meets_or_exceeds_favorable_reference": exceeded,
                "alternative_method": "structural_neighbor_favorable_envelope",
                "alternative_k_neighbors": K_PRIMARY,
                "alternative_favorable_neighbor_count": FAVORABLE_NEIGHBORS,
                "alternative_favorable_neighbor_ids": "|".join(favorable_neighbor_ids),
                "alternative_favorable_neighbor_outcomes": "|".join(f"{value:.12g}" for value in favorable_neighbor_outcomes),
                "alternative_favorable_neighbor_distances": "|".join(f"{value:.12g}" for value in favorable_neighbor_distances),
                "alternative_favorable_reference": alt_reference,
                "alternative_distance_to_favorable_reference": alt_distance,
                "claim_type": "model_estimate",
                "frontier_scope": "empirical_favorable_peer_reference",
                "theoretical_maximum_claim": False,
                "causal_claim": False,
                "policy_counterfactual_claim": False,
                "monetary_wasted_potential_claim": False,
            })

            for k in K_SENSITIVITY:
                sens_reference, neighbor_ids, neighbor_outcomes, neighbor_distances = neighbor_reference(
                    focal_frame, peers, target, k
                )
                sensitivity_rows.append({
                    "target_id": target,
                    "geography_id": focal_geo,
                    "target_year": int(target_year),
                    "k_neighbors": k,
                    "favorable_neighbor_count": FAVORABLE_NEIGHBORS,
                    "favorable_neighbor_ids": "|".join(neighbor_ids),
                    "favorable_neighbor_outcomes": "|".join(f"{value:.12g}" for value in neighbor_outcomes),
                    "favorable_neighbor_distances": "|".join(f"{value:.12g}" for value in neighbor_distances),
                    "favorable_reference": sens_reference,
                    "distance_to_favorable_reference": unified_distance(target, observed, sens_reference),
                    "difference_vs_locked_k6_reference": sens_reference - alt_reference,
                    "sensitivity_can_replace_locked_k6": False,
                })

        target_primary = [row for row in primary_rows if row["target_id"] == target]
        exceed_count = sum(bool(row["primary_observed_meets_or_exceeds_favorable_reference"]) for row in target_primary)
        exceed_rate = exceed_count / len(target_primary)
        calibrated = CALIBRATION_MIN <= exceed_rate <= CALIBRATION_MAX
        preliminary_summary[target] = {
            "benchmark_qualified": benchmark_qualified,
            "primary_favorable_exceedance_count": exceed_count,
            "primary_favorable_exceedance_rate": exceed_rate,
            "primary_frontier_calibrated": calibrated,
        }

    # Attach calibration and interpretation gates after target-level calibration is known.
    for row in primary_rows:
        target_info = preliminary_summary[row["target_id"]]
        row["primary_frontier_calibrated"] = target_info["primary_frontier_calibrated"]
        row["primary_frontier_interpretation_authorized"] = (
            bool(row["m11_benchmark_qualified"])
            and bool(target_info["primary_frontier_calibrated"])
            and not bool(row["m11_support_warning"])
        )

    summary_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        rows = [row for row in primary_rows if row["target_id"] == target]
        primary_refs = [float(row["primary_favorable_reference"]) for row in rows]
        alt_refs = [float(row["alternative_favorable_reference"]) for row in rows]
        primary_distances = [float(row["primary_distance_to_favorable_reference"]) for row in rows]
        alt_distances = [float(row["alternative_distance_to_favorable_reference"]) for row in rows]
        sign_agreement = mean([
            1.0 if (a > 0.0) == (b > 0.0) else 0.0
            for a, b in zip(primary_distances, alt_distances)
        ])
        info = preliminary_summary[target]
        summary_rows.append({
            "target_id": target,
            "target_direction": DIRECTION[target],
            "row_count": len(rows),
            "m11_benchmark_qualified": info["benchmark_qualified"],
            "primary_favorable_quantile": favorable_quantile_for_target(target),
            "primary_favorable_exceedance_count": info["primary_favorable_exceedance_count"],
            "primary_favorable_exceedance_rate": info["primary_favorable_exceedance_rate"],
            "calibration_rate_min": CALIBRATION_MIN,
            "calibration_rate_max": CALIBRATION_MAX,
            "primary_frontier_calibrated": info["primary_frontier_calibrated"],
            "support_warning_row_count": sum(bool(row["m11_support_warning"]) for row in rows),
            "primary_interpretation_authorized_row_count": sum(bool(row["primary_frontier_interpretation_authorized"]) for row in rows),
            "primary_vs_alternative_reference_pearson": pearson(primary_refs, alt_refs),
            "primary_vs_alternative_reference_spearman": spearman(primary_refs, alt_refs),
            "primary_vs_alternative_distance_pearson": pearson(primary_distances, alt_distances),
            "primary_vs_alternative_distance_spearman": spearman(primary_distances, alt_distances),
            "positive_distance_sign_agreement_rate": sign_agreement,
            "median_absolute_reference_difference": median([abs(a - b) for a, b in zip(primary_refs, alt_refs)]),
            "alternative_k_neighbors": K_PRIMARY,
            "alternative_favorable_neighbor_count": FAVORABLE_NEIGHBORS,
            "method_disagreement_is_uncertainty_signal": True,
        })

    primary_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), row["geography_id"], int(row["target_year"])))
    sensitivity_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), row["geography_id"], int(row["target_year"]), int(row["k_neighbors"])))
    summary_rows.sort(key=lambda row: TARGETS.index(row["target_id"]))
    return primary_rows, summary_rows, sensitivity_rows, preliminary_summary


def build_national_lane() -> dict[str, Any]:
    cv = read_csv(M7_CV)
    ws = json.loads(M7_WS.read_text(encoding="utf-8"))
    m7_audit = json.loads(M7_AUDIT.read_text(encoding="utf-8"))
    if len(cv) != 37 or m7_audit.get("milestone7_complete") is not True:
        raise ValueError("M12 national lane requires qualified M7 37-province crossfit residuals")
    residuals = [f(row, "residual_log_observed_minus_predicted") for row in cv]
    q90 = quantile(residuals, HIGH_Q)
    predicted_log = float(ws["predicted_log_target"])
    observed = float(ws["observed_level"])
    frontier_log = predicted_log + q90
    frontier_level = math.exp(frontier_log)
    distance = frontier_level - observed
    observed_to_frontier = observed / frontier_level
    percent_distance = (1.0 - observed_to_frontier) * 100.0
    exceed_count = sum(value >= q90 for value in residuals)
    return {
        "schema": "ranah-observatory/milestone12-national-west-sumatra-frontier/v1",
        "geography_id": "idn.13",
        "geography_name": "Sumatera Barat",
        "reference_year": 2024,
        "target_id": "real_grdp_per_capita",
        "target_unit": "million_rupiah_per_person_constant_2010",
        "method": "national_m7_favorable_residual_quantile",
        "favorable_residual_quantile_probability": HIGH_Q,
        "non_sumbar_crossfit_residual_count": len(residuals),
        "favorable_log_residual_quantile": q90,
        "m7_predicted_log_target": predicted_log,
        "m7_smearing_corrected_expected_level_context": float(ws["smearing_corrected_expected_level"]),
        "observed_level": observed,
        "conditional_favorable_log_reference": frontier_log,
        "conditional_favorable_level": frontier_level,
        "distance_frontier_minus_observed_level": distance,
        "observed_to_favorable_reference_ratio": observed_to_frontier,
        "percent_distance_relative_to_favorable_reference": percent_distance,
        "non_sumbar_empirical_favorable_exceedance_count": exceed_count,
        "non_sumbar_empirical_favorable_exceedance_rate": exceed_count / len(residuals),
        "m7_all_features_inside_training_univariate_minmax": bool(ws["support"]["all_features_inside_training_univariate_minmax"]),
        "m7_maximum_absolute_training_standardized_z": float(ws["support"]["maximum_absolute_training_standardized_z"]),
        "claim_type": "model_estimate",
        "frontier_scope": "empirical_favorable_peer_reference",
        "theoretical_maximum_claim": False,
        "causal_claim": False,
        "policy_counterfactual_claim": False,
        "monetary_wasted_potential_claim": False,
        "population_aggregation_performed": False,
        "multi_year_loss_accumulation_performed": False,
    }


def build() -> dict[str, Any]:
    m11, gate, methods = validate_prefit()
    district_rows, summary_rows, sensitivity_rows, calibration = build_district_lane()
    national = build_national_lane()

    write_csv(
        DISTRICT_OUT,
        [
            "target_id", "target_direction", "geography_id", "geography_name", "target_year", "feature_year",
            "observed", "m11_expected", "m11_prediction_interval_lower", "m11_prediction_interval_upper",
            "m11_benchmark_qualified", "m11_support_warning", "primary_method", "primary_favorable_quantile",
            "primary_focal_excluded_calibration_residual_count", "primary_favorable_residual_quantile_value",
            "primary_favorable_reference", "primary_distance_to_favorable_reference",
            "primary_observed_meets_or_exceeds_favorable_reference", "primary_frontier_calibrated",
            "primary_frontier_interpretation_authorized", "alternative_method", "alternative_k_neighbors",
            "alternative_favorable_neighbor_count", "alternative_favorable_neighbor_ids",
            "alternative_favorable_neighbor_outcomes", "alternative_favorable_neighbor_distances",
            "alternative_favorable_reference", "alternative_distance_to_favorable_reference", "claim_type",
            "frontier_scope", "theoretical_maximum_claim", "causal_claim", "policy_counterfactual_claim",
            "monetary_wasted_potential_claim",
        ],
        [{key: fmt(value) for key, value in row.items()} for row in district_rows],
    )
    write_csv(
        SUMMARY_OUT,
        [
            "target_id", "target_direction", "row_count", "m11_benchmark_qualified", "primary_favorable_quantile",
            "primary_favorable_exceedance_count", "primary_favorable_exceedance_rate", "calibration_rate_min",
            "calibration_rate_max", "primary_frontier_calibrated", "support_warning_row_count",
            "primary_interpretation_authorized_row_count", "primary_vs_alternative_reference_pearson",
            "primary_vs_alternative_reference_spearman", "primary_vs_alternative_distance_pearson",
            "primary_vs_alternative_distance_spearman", "positive_distance_sign_agreement_rate",
            "median_absolute_reference_difference", "alternative_k_neighbors", "alternative_favorable_neighbor_count",
            "method_disagreement_is_uncertainty_signal",
        ],
        [{key: fmt(value) for key, value in row.items()} for row in summary_rows],
    )
    write_csv(
        NEIGHBOR_SENS_OUT,
        [
            "target_id", "geography_id", "target_year", "k_neighbors", "favorable_neighbor_count",
            "favorable_neighbor_ids", "favorable_neighbor_outcomes", "favorable_neighbor_distances",
            "favorable_reference", "distance_to_favorable_reference", "difference_vs_locked_k6_reference",
            "sensitivity_can_replace_locked_k6",
        ],
        [{key: fmt(value) for key, value in row.items()} for row in sensitivity_rows],
    )
    NATIONAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    NATIONAL_OUT.write_text(json.dumps(national, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    calibrated_targets = [target for target in TARGETS if calibration[target]["primary_frontier_calibrated"]]
    uncalibrated_targets = [target for target in TARGETS if not calibration[target]["primary_frontier_calibrated"]]
    method_status = {row["method_id"]: row["qualification_status"] for row in methods}
    manifest = {
        "schema": "ranah-observatory/milestone12-attainable-frontier/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 12,
        "district_scope": "current_sumbar_19_kabkota_2019_2024",
        "national_scope": "current_38_province_2024_m7_conditional_anchor",
        "district_target_ids": TARGETS,
        "district_row_count": len(district_rows),
        "district_method_summary_row_count": len(summary_rows),
        "neighbor_sensitivity_row_count": len(sensitivity_rows),
        "district_primary_method": "conditional_favorable_residual_quantile",
        "district_alternative_method": "structural_neighbor_favorable_envelope",
        "lower_is_favorable_quantile": LOW_Q,
        "higher_is_favorable_quantile": HIGH_Q,
        "calibration_rate_band": [CALIBRATION_MIN, CALIBRATION_MAX],
        "primary_frontier_calibrated_target_ids": calibrated_targets,
        "primary_frontier_uncalibrated_target_ids": uncalibrated_targets,
        "primary_frontier_calibrated_target_count": len(calibrated_targets),
        "neighbor_k": K_PRIMARY,
        "neighbor_favorable_count": FAVORABLE_NEIGHBORS,
        "neighbor_k_sensitivity": K_SENSITIVITY,
        "method_qualification_status": method_status,
        "m11_benchmark_qualified_target_ids": m11.get("benchmark_qualified_target_ids", []),
        "m11_required": True,
        "m7_national_anchor_required": True,
        "focal_geography_excluded_from_primary_frontier_calibration": True,
        "same_year_nonfocal_peers_only_for_neighbor_method": True,
        "frontier_distance_truncated_at_zero": False,
        "posthoc_quantile_retuning_performed": False,
        "posthoc_neighbor_parameter_replacement_performed": False,
        "classic_dea_computed": False,
        "classic_halfnormal_sfa_computed": False,
        "linear_quantile_regression_computed": False,
        "theoretical_maximum_claim": False,
        "causal_claim": False,
        "policy_counterfactual_claim": False,
        "monetary_wasted_potential_claim": False,
        "national_population_aggregation_performed": False,
        "national_multi_year_loss_accumulation_performed": False,
        "methods_selected_before_frontier_results": gate.get("methods_selected_before_frontier_results") is True,
        "quantiles_selected_before_frontier_results": gate.get("quantiles_selected_before_frontier_results") is True,
        "calibration_band_selected_before_frontier_results": gate.get("calibration_band_selected_before_frontier_results") is True,
        "neighbor_parameters_selected_before_frontier_results": gate.get("neighbor_parameters_selected_before_frontier_results") is True,
        "source_inputs": {
            str(M11_PREDICTIONS.relative_to(ROOT)): sha256(M11_PREDICTIONS),
            str(M11_MODEL_FRAME.relative_to(ROOT)): sha256(M11_MODEL_FRAME),
            str(M11_MANIFEST.relative_to(ROOT)): sha256(M11_MANIFEST),
            str(M7_CV.relative_to(ROOT)): sha256(M7_CV),
            str(M7_WS.relative_to(ROOT)): sha256(M7_WS),
            str(M7_AUDIT.relative_to(ROOT)): sha256(M7_AUDIT),
            str(METHOD_REGISTRY.relative_to(ROOT)): sha256(METHOD_REGISTRY),
            str(DESIGN_GATE.relative_to(ROOT)): sha256(DESIGN_GATE),
            str(SPEC.relative_to(ROOT)): sha256(SPEC),
        },
        "outputs": {
            "district_frontier": {"path": str(DISTRICT_OUT.relative_to(ROOT)), "sha256": sha256(DISTRICT_OUT)},
            "district_method_summary": {"path": str(SUMMARY_OUT.relative_to(ROOT)), "sha256": sha256(SUMMARY_OUT)},
            "neighbor_sensitivity": {"path": str(NEIGHBOR_SENS_OUT.relative_to(ROOT)), "sha256": sha256(NEIGHBOR_SENS_OUT)},
            "national_west_sumatra_frontier": {"path": str(NATIONAL_OUT.relative_to(ROOT)), "sha256": sha256(NATIONAL_OUT)},
        },
        "milestone12_complete": True,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return manifest


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
