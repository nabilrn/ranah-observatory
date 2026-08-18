#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE11_EXPECTED_PERFORMANCE_V2_SPEC.md"
DESIGN_GATE = ROOT / "data/manifests/milestone11_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M10_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
FOUNDATION = ROOT / "data/manifests/research_foundation_complete.json"
MODEL_FRAME = ROOT / "data/analysis/engine/expected_performance_v2/m11-model-frame.csv"
PREDICTIONS = ROOT / "data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv"
TARGET_SUMMARY = ROOT / "data/analysis/engine/expected_performance_v2/m11-target-summary.csv"
SUPPORT = ROOT / "data/analysis/engine/expected_performance_v2/m11-support-diagnostics.csv"
COEFFICIENTS = ROOT / "data/analysis/engine/expected_performance_v2/m11-outer-fold-coefficients.csv"
SENSITIVITY = ROOT / "data/analysis/engine/expected_performance_v2/m11-sensitivity-summary.csv"

TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
PRIMARY_FEATURES = [
    "mean_years_schooling",
    "labor_force_participation",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
]
SENSITIVITY_FEATURES = [*PRIMARY_FEATURES, "annual_rainfall"]
TARGET_YEARS = list(range(2019, 2025))
PENALTY_GRID = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


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


def rmse(values: list[float]) -> float:
    return math.sqrt(mean([value * value for value in values]))


def mae(values: list[float]) -> float:
    return mean([abs(value) for value in values])


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires values")
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


def close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [
        SPEC,
        DESIGN_GATE,
        MANIFEST,
        M10_MANIFEST,
        FOUNDATION,
        MODEL_FRAME,
        PREDICTIONS,
        TARGET_SUMMARY,
        SUPPORT,
        COEFFICIENTS,
        SENSITIVITY,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {
            "schema": "ranah-observatory/milestone11-audit/v1",
            "milestone11_complete": False,
            "errors": [f"missing required file: {path}" for path in missing],
        }

    spec = SPEC.read_text(encoding="utf-8")
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m10 = json.loads(M10_MANIFEST.read_text(encoding="utf-8"))
    foundation = json.loads(FOUNDATION.read_text(encoding="utf-8"))
    frame = read_csv(MODEL_FRAME)
    predictions = read_csv(PREDICTIONS)
    summaries = read_csv(TARGET_SUMMARY)
    support = read_csv(SUPPORT)
    coefficients = read_csv(COEFFICIENTS)
    sensitivity = read_csv(SENSITIVITY)

    if foundation.get("initial_research_foundation_complete") is not True or foundation.get("completed_criterion_count") != 9 or foundation.get("errors") != []:
        errors.append("Research Foundation 9/9 must remain complete")
    if m10.get("milestone10_complete") is not True or m10.get("regime_id") != "sumbar_current_kabkota_2018_2025_v1":
        errors.append("M11 requires completed M10 Analytical Panel v1")

    expected_gate = {
        "schema": "ranah-observatory/milestone11-design-gate/v1",
        "regime_id": "sumbar_current_kabkota_lagged_structural_2019_2024_v1",
        "geography_count": 19,
        "target_start_year": 2019,
        "target_end_year": 2024,
        "target_year_count": 6,
        "target_ids": TARGETS,
        "primary_feature_ids": PRIMARY_FEATURES,
        "sensitivity_added_feature_id": "annual_rainfall",
        "feature_lag_years": 1,
        "penalty_grid": PENALTY_GRID,
        "model_fit": False,
        "residuals_inspected": False,
        "target_benchmark_results_known": False,
        "causal_claim_authorized": False,
        "frontier_claim_authorized": False,
        "counterfactual_claim_authorized": False,
        "monetary_wasted_potential_claim_authorized": False,
        "milestone11_complete": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            errors.append(f"M11 prefit design-gate drift: {key}")
    for flag in [
        "target_year_selected_before_model_fit",
        "targets_selected_before_model_fit",
        "features_selected_before_model_fit",
        "sensitivity_selected_before_model_fit",
    ]:
        if gate.get(flag) is not True:
            errors.append(f"M11 prefit lock flag lost: {flag}")

    expected_manifest = {
        "schema": "ranah-observatory/milestone11-expected-performance-v2/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 11,
        "regime_id": "sumbar_current_kabkota_lagged_structural_2019_2024_v1",
        "geography_count": 19,
        "target_year_count": 6,
        "model_frame_row_count": 114,
        "target_ids": TARGETS,
        "primary_feature_ids": PRIMARY_FEATURES,
        "sensitivity_feature_ids": SENSITIVITY_FEATURES,
        "feature_lag_years": 1,
        "penalty_grid": PENALTY_GRID,
        "crossfit_prediction_count": 342,
        "expected_crossfit_prediction_count": 342,
        "support_diagnostic_row_count": 1710,
        "outer_fold_coefficient_row_count": 684,
        "primary_predictions_cross_fitted_by_geography": True,
        "focal_geography_excluded_from_own_model_fit": True,
        "nested_inner_cv_used": True,
        "focal_geography_excluded_from_own_uncertainty_calibration": True,
        "same_year_marginal_support_reported": True,
        "imputation_performed": False,
        "target_specific_feature_search_performed": False,
        "posthoc_model_replacement_performed": False,
        "causal_analysis_performed": False,
        "frontier_model_performed": False,
        "counterfactual_policy_effect_estimated": False,
        "monetary_wasted_potential_estimated": False,
        "coefficient_causal_interpretation_authorized": False,
        "milestone11_complete": True,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            errors.append(f"M11 manifest contract drift: {key}")
    if manifest.get("target_years") != TARGET_YEARS:
        errors.append("M11 target-year list drift")

    for path_string, digest in manifest.get("source_inputs", {}).items():
        path = ROOT / path_string
        if not path.exists() or sha256(path) != digest:
            errors.append(f"M11 source-input checksum drift: {path_string}")
    output_paths = {
        "model_frame": MODEL_FRAME,
        "crossfit_predictions": PREDICTIONS,
        "target_summary": TARGET_SUMMARY,
        "support_diagnostics": SUPPORT,
        "outer_fold_coefficients": COEFFICIENTS,
        "sensitivity_summary": SENSITIVITY,
    }
    for key, path in output_paths.items():
        record = manifest.get("outputs", {}).get(key, {})
        if record.get("path") != str(path.relative_to(ROOT)) or record.get("sha256") != sha256(path):
            errors.append(f"M11 output checksum/path drift: {key}")

    if len(frame) != 114:
        errors.append(f"M11 model frame must contain 114 rows, got {len(frame)}")
    frame_keys = {(row.get("geography_id"), row.get("target_year")) for row in frame}
    if len(frame_keys) != 114:
        errors.append("M11 model-frame geography-year keys are not unique")
    geographies = sorted({row.get("geography_id", "") for row in frame})
    if len(geographies) != 19 or any(not geo.startswith("idn.13.") for geo in geographies):
        errors.append("M11 model frame lost exact 19 Sumbar geography footprint")
    for row in frame:
        try:
            target_year = int(row["target_year"])
            feature_year = int(row["feature_year"])
        except (KeyError, ValueError):
            errors.append("M11 model frame contains invalid target/feature year")
            continue
        if target_year not in TARGET_YEARS or feature_year != target_year - 1:
            errors.append(f"M11 lag-year contract drift: {row.get('geography_id')}/{target_year}")
        for feature in SENSITIVITY_FEATURES:
            try:
                f(row, f"lag1_{feature}")
            except ValueError as exc:
                errors.append(f"M11 model-frame feature error: {exc}")
        for target in TARGETS:
            try:
                f(row, target)
            except ValueError as exc:
                errors.append(f"M11 model-frame target error: {exc}")

    prediction_keys = {(row.get("target_id"), row.get("geography_id"), row.get("target_year")) for row in predictions}
    if len(predictions) != 342 or len(prediction_keys) != 342:
        errors.append("M11 crossfit prediction table must contain exact 342 unique target-geography-year rows")
    by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in predictions:
        target = row.get("target_id", "")
        by_target[target].append(row)
        if target not in TARGETS:
            errors.append(f"unexpected M11 target in predictions: {target}")
        if row.get("geography_id") not in geographies:
            errors.append("M11 prediction geography outside model frame")
        if row.get("target_year") not in {str(year) for year in TARGET_YEARS}:
            errors.append("M11 prediction year outside locked window")
        if row.get("selected_penalty") not in {str(value) for value in PENALTY_GRID} and row.get("selected_penalty") not in {"0", "0.01", "0.1", "1", "10", "100"}:
            errors.append(f"M11 selected penalty outside fixed grid: {row.get('selected_penalty')}")
        if row.get("sensitivity_selected_penalty") not in {"0", "0.01", "0.1", "1", "10", "100"}:
            errors.append(f"M11 sensitivity penalty outside fixed grid: {row.get('sensitivity_selected_penalty')}")
        for key in [
            "observed",
            "expected",
            "residual_observed_minus_expected",
            "naive_same_year_peer_mean",
            "naive_residual",
            "focal_excluded_empirical_residual_q025",
            "focal_excluded_empirical_residual_q975",
            "exploratory_prediction_interval_lower",
            "exploratory_prediction_interval_upper",
            "sensitivity_expected_plus_lagged_rainfall",
            "sensitivity_residual_observed_minus_expected",
            "sensitivity_expected_minus_primary_expected",
        ]:
            try:
                f(row, key)
            except ValueError as exc:
                errors.append(f"M11 prediction numeric error: {exc}")
        if not close(f(row, "observed") - f(row, "expected"), f(row, "residual_observed_minus_expected")):
            errors.append("M11 primary residual arithmetic mismatch")
        if not close(f(row, "observed") - f(row, "naive_same_year_peer_mean"), f(row, "naive_residual")):
            errors.append("M11 naive residual arithmetic mismatch")
        if not close(f(row, "observed") - f(row, "sensitivity_expected_plus_lagged_rainfall"), f(row, "sensitivity_residual_observed_minus_expected")):
            errors.append("M11 sensitivity residual arithmetic mismatch")
        if not close(f(row, "sensitivity_expected_plus_lagged_rainfall") - f(row, "expected"), f(row, "sensitivity_expected_minus_primary_expected")):
            errors.append("M11 sensitivity prediction-difference arithmetic mismatch")

    # Rebuild naive same-year peer means directly from the 114-row model frame.
    frame_lookup = {(row["geography_id"], row["target_year"]): row for row in frame}
    for row in predictions:
        target = row["target_id"]
        focal = row["geography_id"]
        year = row["target_year"]
        peer_values = [
            f(frame_lookup[(geo, year)], target)
            for geo in geographies
            if geo != focal
        ]
        if len(peer_values) != 18:
            errors.append("M11 naive peer benchmark footprint drift")
            continue
        if not close(mean(peer_values), f(row, "naive_same_year_peer_mean")):
            errors.append(f"M11 naive peer benchmark mismatch: {target}/{focal}/{year}")

    summary_by_target = {row.get("target_id", ""): row for row in summaries}
    if len(summaries) != 3 or set(summary_by_target) != set(TARGETS):
        errors.append("M11 target summary must contain exact three targets")
    qualified: list[str] = []
    failed: list[str] = []
    for target in TARGETS:
        rows = by_target.get(target, [])
        if len(rows) != 114:
            errors.append(f"M11 prediction count for {target} must be 114")
            continue
        summary = summary_by_target.get(target)
        if summary is None:
            continue
        residuals = [f(row, "residual_observed_minus_expected") for row in rows]
        naive_residuals = [f(row, "naive_residual") for row in rows]
        model_rmse = rmse(residuals)
        model_mae = mae(residuals)
        naive_rmse = rmse(naive_residuals)
        naive_mae = mae(naive_residuals)
        metrics = {
            "model_rmse": model_rmse,
            "model_mae": model_mae,
            "naive_same_year_peer_mean_rmse": naive_rmse,
            "naive_same_year_peer_mean_mae": naive_mae,
        }
        for key, value in metrics.items():
            if not close(f(summary, key), value, 1e-8):
                errors.append(f"M11 summary metric mismatch {target}/{key}")
        benchmark_qualified = model_rmse < naive_rmse and model_mae < naive_mae
        if (summary.get("benchmark_qualified") == "true") != benchmark_qualified:
            errors.append(f"M11 benchmark qualification mismatch: {target}")
        if (summary.get("substantive_expected_performance_interpretation_authorized") == "true") != benchmark_qualified:
            errors.append(f"M11 substantive interpretation flag mismatch: {target}")
        prediction_flags = {row.get("benchmark_qualified") for row in rows}
        interpretation_flags = {row.get("substantive_interpretation_authorized") for row in rows}
        expected_flag = "true" if benchmark_qualified else "false"
        if prediction_flags != {expected_flag} or interpretation_flags != {expected_flag}:
            errors.append(f"M11 row-level target qualification flag mismatch: {target}")
        (qualified if benchmark_qualified else failed).append(target)

        # Focal geography's own cross-fitted residuals must be excluded from uncertainty calibration.
        for row in rows:
            focal = row["geography_id"]
            calibration = [
                f(other, "residual_observed_minus_expected")
                for other in rows
                if other["geography_id"] != focal
            ]
            if len(calibration) != 108:
                errors.append("M11 uncertainty calibration must contain 108 other-geography residuals")
                continue
            q025 = quantile(calibration, 0.025)
            q975 = quantile(calibration, 0.975)
            if not close(q025, f(row, "focal_excluded_empirical_residual_q025"), 1e-8):
                errors.append(f"M11 q025 uncertainty mismatch: {target}/{focal}/{row['target_year']}")
            if not close(q975, f(row, "focal_excluded_empirical_residual_q975"), 1e-8):
                errors.append(f"M11 q975 uncertainty mismatch: {target}/{focal}/{row['target_year']}")
            if not close(f(row, "expected") + q025, f(row, "exploratory_prediction_interval_lower"), 1e-8):
                errors.append("M11 lower prediction interval arithmetic mismatch")
            if not close(f(row, "expected") + q975, f(row, "exploratory_prediction_interval_upper"), 1e-8):
                errors.append("M11 upper prediction interval arithmetic mismatch")

    if set(manifest.get("benchmark_qualified_target_ids", [])) != set(qualified):
        errors.append("M11 manifest qualified-target set mismatch")
    if set(manifest.get("benchmark_failed_target_ids", [])) != set(failed):
        errors.append("M11 manifest failed-target set mismatch")
    if manifest.get("benchmark_qualified_target_count") != len(qualified):
        errors.append("M11 manifest qualified-target count mismatch")

    support_key_rows: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in support:
        support_key_rows[(row.get("target_id", ""), row.get("geography_id", ""), row.get("target_year", ""))].append(row)
    if len(support) != 1710:
        errors.append(f"M11 support diagnostics must contain 1710 rows, got {len(support)}")
    for prediction in predictions:
        key = (prediction["target_id"], prediction["geography_id"], prediction["target_year"])
        rows = support_key_rows.get(key, [])
        if len(rows) != 5 or {row.get("feature_id") for row in rows} != set(PRIMARY_FEATURES):
            errors.append(f"M11 support footprint mismatch: {key}")
            continue
        all_inside = all(row.get("inside_same_year_marginal_minmax") == "true" for row in rows)
        if (prediction.get("all_primary_features_inside_same_year_marginal_minmax") == "true") != all_inside:
            errors.append(f"M11 support all-inside flag mismatch: {key}")
        if (prediction.get("support_warning") == "true") != (not all_inside):
            errors.append(f"M11 support-warning flag mismatch: {key}")
        for row in rows:
            focal = f(row, "focal_value")
            lower = f(row, "same_year_training_min")
            upper = f(row, "same_year_training_max")
            inside = lower <= focal <= upper
            if (row.get("inside_same_year_marginal_minmax") == "true") != inside:
                errors.append(f"M11 support row arithmetic mismatch: {key}/{row.get('feature_id')}")

    if len(coefficients) != 684:
        errors.append(f"M11 outer-fold coefficient diagnostics must contain 684 rows, got {len(coefficients)}")
    coefficient_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in coefficients:
        coefficient_groups[(row.get("target_id", ""), row.get("outer_holdout_geography_id", ""))].append(row)
        try:
            f(row, "coefficient")
        except ValueError as exc:
            errors.append(f"M11 coefficient numeric error: {exc}")
    if len(coefficient_groups) != 3 * 19 or any(len(rows) != 12 for rows in coefficient_groups.values()):
        errors.append("M11 coefficient groups must contain 12 parameters for each target × outer geography")

    sensitivity_by_target = {row.get("target_id", ""): row for row in sensitivity}
    if len(sensitivity) != 3 or set(sensitivity_by_target) != set(TARGETS):
        errors.append("M11 sensitivity summary must contain exact three targets")
    for target in TARGETS:
        row = sensitivity_by_target.get(target)
        if row is None:
            continue
        target_rows = by_target.get(target, [])
        sens_residuals = [f(prediction, "sensitivity_residual_observed_minus_expected") for prediction in target_rows]
        sens_rmse = rmse(sens_residuals)
        sens_mae = mae(sens_residuals)
        if not close(sens_rmse, f(row, "primary_plus_lagged_rainfall_rmse"), 1e-8):
            errors.append(f"M11 sensitivity RMSE mismatch: {target}")
        if not close(sens_mae, f(row, "primary_plus_lagged_rainfall_mae"), 1e-8):
            errors.append(f"M11 sensitivity MAE mismatch: {target}")
        if row.get("sensitivity_can_replace_primary") != "false":
            errors.append("M11 rainfall sensitivity must not replace primary model")
        if row.get("rainfall_claim_type") != "model_estimate" or row.get("causal_rainfall_interpretation_authorized") != "false":
            errors.append("M11 rainfall sensitivity semantic guardrail drift")

    required_phrases = [
        "The primary estimate is always out-of-geography.",
        "same-year peer-mean",
        "residuals are **not authorized for substantive expected-performance interpretation**",
        "The sensitivity model is not used to replace a primary result",
        "They are **not causal bottleneck estimates**",
        "the residual is wasted potential",
    ]
    for phrase in required_phrases:
        if phrase not in spec:
            errors.append(f"M11 spec lost required guardrail phrase: {phrase}")

    return {
        "schema": "ranah-observatory/milestone11-audit/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 11,
        "geography_count": 19,
        "target_year_count": 6,
        "target_count": 3,
        "model_frame_row_count": len(frame),
        "crossfit_prediction_count": len(predictions),
        "support_diagnostic_row_count": len(support),
        "benchmark_qualified_target_ids": qualified,
        "benchmark_failed_target_ids": failed,
        "benchmark_qualified_target_count": len(qualified),
        "prefit_design_gate_preserved": gate.get("model_fit") is False and gate.get("residuals_inspected") is False,
        "m10_complete": m10.get("milestone10_complete") is True,
        "foundation_9_of_9_complete": foundation.get("initial_research_foundation_complete") is True,
        "causal_analysis_performed": manifest.get("causal_analysis_performed") is True,
        "frontier_model_performed": manifest.get("frontier_model_performed") is True,
        "monetary_wasted_potential_estimated": manifest.get("monetary_wasted_potential_estimated") is True,
        "milestone11_complete": manifest.get("milestone11_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 11 Expected Performance Engine v2")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone11_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
