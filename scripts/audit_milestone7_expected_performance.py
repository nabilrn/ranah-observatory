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
MODEL_MANIFEST = ROOT / "data/manifests/milestone7_expected_performance_model.json"
FEATURE_MANIFEST = ROOT / "data/manifests/milestone7_feature_frame.json"
FEATURE_REGISTRY = ROOT / "data/registries/milestone7_expected_performance_features.csv"
MODEL_FRAME = ROOT / "data/analysis/expected_performance/m7-model-frame-2024.csv"
CV_SUMMARY = ROOT / "data/analysis/expected_performance/m7-ridge-loocv-summary.csv"
CV_PREDICTIONS = ROOT / "data/analysis/expected_performance/m7-ridge-selected-loocv-predictions.csv"
COEFFICIENTS = ROOT / "data/analysis/expected_performance/m7-model-coefficients.csv"
SUPPORT = ROOT / "data/analysis/expected_performance/m7-west-sumatra-support.csv"
ESTIMATE = ROOT / "data/analysis/expected_performance/m7-west-sumatra-expected-performance.json"
MODEL_SPEC = ROOT / "research/MILESTONE7_MODEL_SPEC.md"
DEFAULT_REPORT = ROOT / "data/manifests/milestone7_expected_performance_audit.json"

EXPECTED_FEATURES = [
    "m7_rls_age15_plus",
    "m7_hls_method_new",
    "m7_household_internet_access",
    "m7_household_pln_lighting",
]
EXPECTED_SELECTORS = {
    "m7_rls_age15_plus": ("1429", "0", "0"),
    "m7_hls_method_new": ("417", "0", "0"),
    "m7_household_internet_access": ("398", "191", "0"),
    "m7_household_pln_lighting": ("856", "191", "0"),
}
EXPECTED_LAMBDAS = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0]
FORBIDDEN_PRIMARY_FEATURES = {
    "poverty_rate",
    "gini_ratio",
    "unemployment_rate",
    "underemployment_rate",
    "neet_rate",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def close(a: Any, b: Any, *, atol: float = 1e-9, rtol: float = 1e-9) -> bool:
    if not finite(a) or not finite(b):
        return False
    return math.isclose(float(a), float(b), abs_tol=atol, rel_tol=rtol)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(lower)]
    weight = position - lower
    return ordered[int(lower)] * (1.0 - weight) + ordered[int(upper)] * weight


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [
        MODEL_MANIFEST,
        FEATURE_MANIFEST,
        FEATURE_REGISTRY,
        MODEL_FRAME,
        CV_SUMMARY,
        CV_PREDICTIONS,
        COEFFICIENTS,
        SUPPORT,
        ESTIMATE,
        MODEL_SPEC,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {
            "schema": "ranah-observatory/milestone7-expected-performance-audit/v1",
            "criterion": "one baseline expected-performance/frontier model",
            "errors": [f"missing required file: {path}" for path in missing],
            "milestone7_complete": False,
        }

    manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
    feature_manifest = json.loads(FEATURE_MANIFEST.read_text(encoding="utf-8"))
    estimate = json.loads(ESTIMATE.read_text(encoding="utf-8"))

    if manifest.get("schema") != "ranah-observatory/milestone7-expected-performance-model/v1":
        errors.append("Milestone 7 model manifest schema drift")
    if manifest.get("criterion") != "one baseline expected-performance/frontier model":
        errors.append("Milestone 7 criterion drift")
    if manifest.get("model_type") != "ridge_expected_performance_baseline":
        errors.append("Milestone 7 model type drift")
    if manifest.get("reference_year") != 2024:
        errors.append("Milestone 7 model year drift")
    if manifest.get("geography_regime") != "bps_current_38_province_2024plus":
        errors.append("Milestone 7 geography regime drift")
    if manifest.get("training_geography_count") != 37:
        errors.append("Milestone 7 must train on exactly 37 non-West-Sumatra provinces")
    if manifest.get("focal_holdout") != "idn.13":
        errors.append("Milestone 7 focal holdout drift")
    if manifest.get("west_sumatra_target_excluded_from_selection_and_fit") is not True:
        errors.append("West Sumatra target exclusion gate is not true")
    if manifest.get("causal_analysis_performed") is not False:
        errors.append("Milestone 7 must not claim causal analysis")
    if manifest.get("frontier_model_performed") is not False:
        errors.append("Milestone 7 baseline must not claim a production frontier")
    if manifest.get("monetary_wasted_potential_estimated") is not False:
        errors.append("Milestone 7 must not estimate monetary wasted potential")

    manifest_features = manifest.get("feature_ids")
    if manifest_features != EXPECTED_FEATURES or manifest.get("feature_count") != 4:
        errors.append("Milestone 7 primary feature set drift")
    if manifest.get("penalty_grid") != EXPECTED_LAMBDAS:
        errors.append("Milestone 7 ridge penalty grid drift")
    selected_penalty = manifest.get("selected_penalty")
    if selected_penalty not in EXPECTED_LAMBDAS:
        errors.append("selected ridge penalty is outside preregistered grid")
    if manifest.get("beats_naive_benchmark") is not True:
        errors.append("selected model does not beat naive benchmark")
    if manifest.get("completion_gate_passed") is not True:
        errors.append("model completion gate is not true")
    if manifest.get("errors") != []:
        errors.append("model manifest contains errors")
    if not finite(manifest.get("loocv_rmse_log")) or not finite(manifest.get("naive_loocv_rmse_log")):
        errors.append("model manifest validation metrics are non-finite")
    elif float(manifest["loocv_rmse_log"]) >= float(manifest["naive_loocv_rmse_log"]):
        errors.append("selected LOPO RMSE does not beat naive LOPO RMSE")

    if feature_manifest.get("schema") != "ranah-observatory/milestone7-feature-frame/v1":
        errors.append("Milestone 7 feature-frame manifest schema drift")
    if feature_manifest.get("year") != 2024 or feature_manifest.get("geography_count") != 38:
        errors.append("feature-frame year/geography contract drift")
    if feature_manifest.get("feature_ids") != EXPECTED_FEATURES or feature_manifest.get("feature_count") != 4:
        errors.append("feature-frame primary feature set drift")
    if feature_manifest.get("observation_count") != 152 or feature_manifest.get("model_row_count") != 38:
        errors.append("feature-frame cardinality drift")
    if feature_manifest.get("west_sumatra_present") is not True:
        errors.append("feature frame lost West Sumatra")
    if feature_manifest.get("target") != "real_grdp_per_capita":
        errors.append("feature-frame target drift")

    registry = read_csv(FEATURE_REGISTRY)
    if [row.get("feature_id") for row in registry] != EXPECTED_FEATURES:
        errors.append("feature registry order/content drift")
    if len(registry) != 4:
        errors.append("feature registry must contain exactly four primary predictors")
    for row in registry:
        feature_id = row.get("feature_id", "")
        if row.get("qualification_status") != "qualified_for_freeze":
            errors.append(f"feature {feature_id} is not qualified_for_freeze")
        if feature_id in EXPECTED_SELECTORS:
            expected = EXPECTED_SELECTORS[feature_id]
            actual = (row.get("bps_var_id"), row.get("bps_turvar_id"), row.get("bps_turth_id"))
            if actual != expected:
                errors.append(f"source selector drift for {feature_id}: {actual}")
        if feature_id in FORBIDDEN_PRIMARY_FEATURES:
            errors.append(f"forbidden Milestone 5 outcome used as predictor: {feature_id}")

    model_rows = read_csv(MODEL_FRAME)
    if len(model_rows) != 38:
        errors.append(f"model frame must contain 38 rows; got {len(model_rows)}")
    ids = [row.get("geography_id", "") for row in model_rows]
    if len(set(ids)) != len(ids):
        errors.append("model frame contains duplicate geographies")
    if ids.count("idn.13") != 1:
        errors.append("model frame must contain West Sumatra exactly once")
    for row in model_rows:
        for feature_id in EXPECTED_FEATURES:
            if not finite(row.get(feature_id)):
                errors.append(f"non-finite predictor {feature_id} for {row.get('geography_id')}")
        if not finite(row.get("real_grdp_per_capita")) or float(row["real_grdp_per_capita"]) <= 0:
            errors.append(f"invalid target for {row.get('geography_id')}")
        if not finite(row.get("log_real_grdp_per_capita")):
            errors.append(f"invalid log target for {row.get('geography_id')}")

    cv_summary = read_csv(CV_SUMMARY)
    if len(cv_summary) != 6:
        errors.append("CV summary must contain exactly six preregistered penalties")
    observed_lambdas: list[float] = []
    for row in cv_summary:
        if not finite(row.get("penalty")):
            errors.append("CV summary contains non-finite penalty")
            continue
        observed_lambdas.append(float(row["penalty"]))
        for metric in ("mse", "rmse", "mae", "naive_rmse", "naive_mae"):
            if not finite(row.get(metric)):
                errors.append(f"CV summary contains non-finite {metric}")
    if observed_lambdas != EXPECTED_LAMBDAS:
        errors.append("CV summary penalty order/grid drift")
    valid_cv_rows = [row for row in cv_summary if finite(row.get("mse")) and finite(row.get("penalty"))]
    if valid_cv_rows:
        recomputed_selected = min(valid_cv_rows, key=lambda row: (float(row["mse"]), -float(row["penalty"])))
        if not close(recomputed_selected["penalty"], selected_penalty):
            errors.append("manifest selected penalty is not the preregistered CV optimum")
        if not close(recomputed_selected["rmse"], manifest.get("loocv_rmse_log"), atol=1e-10):
            errors.append("manifest LOPO RMSE does not match CV summary")
        if not close(recomputed_selected["mae"], manifest.get("loocv_mae_log"), atol=1e-10):
            errors.append("manifest LOPO MAE does not match CV summary")
        if not close(recomputed_selected["naive_rmse"], manifest.get("naive_loocv_rmse_log"), atol=1e-10):
            errors.append("manifest naive RMSE does not match CV summary")

    cv_predictions = read_csv(CV_PREDICTIONS)
    if len(cv_predictions) != 37 or len({row.get("geography_id") for row in cv_predictions}) != 37:
        errors.append("selected-model LOPO predictions must cover exactly 37 unique non-Sumbar provinces")
    if any(row.get("geography_id") == "idn.13" for row in cv_predictions):
        errors.append("West Sumatra leaked into LOPO model-selection universe")
    cv_residuals: list[float] = []
    for row in cv_predictions:
        if not finite(row.get("observed_log_target")) or not finite(row.get("predicted_log_target")):
            errors.append("LOPO prediction contains non-finite target/prediction")
            continue
        observed = float(row["observed_log_target"])
        predicted = float(row["predicted_log_target"])
        residual = observed - predicted
        if not close(residual, row.get("residual_log_observed_minus_predicted"), atol=1e-10):
            errors.append(f"LOPO residual sign/value drift for {row.get('geography_id')}")
        cv_residuals.append(residual)
    if cv_residuals and not close(math.sqrt(sum(x*x for x in cv_residuals)/len(cv_residuals)), manifest.get("loocv_rmse_log"), atol=1e-10):
        errors.append("LOPO prediction residuals do not reproduce manifest RMSE")

    coefficients = read_csv(COEFFICIENTS)
    if len(coefficients) != 4 or [row.get("feature_id") for row in coefficients] != EXPECTED_FEATURES:
        errors.append("coefficient table must contain exactly four preregistered predictors")
    for row in coefficients:
        if not close(row.get("selected_penalty"), selected_penalty):
            errors.append(f"coefficient selected-penalty drift for {row.get('feature_id')}")
        if not finite(row.get("selected_standardized_coefficient")) or not finite(row.get("ols_standardized_coefficient")):
            errors.append(f"non-finite coefficient for {row.get('feature_id')}")

    support = read_csv(SUPPORT)
    if len(support) != 4 or [row.get("feature_id") for row in support] != EXPECTED_FEATURES:
        errors.append("West Sumatra support table must contain exactly four preregistered predictors")
    max_abs_z = 0.0
    all_inside = True
    for row in support:
        if not all(finite(row.get(field)) for field in ("west_sumatra_value", "training_min", "training_max", "training_mean", "training_scale", "west_sumatra_z")):
            errors.append(f"non-finite support statistic for {row.get('feature_id')}")
            continue
        lower = float(row["training_min"])
        upper = float(row["training_max"])
        value = float(row["west_sumatra_value"])
        inside = lower <= value <= upper
        if row.get("inside_univariate_minmax") != str(inside).lower():
            errors.append(f"support min/max flag drift for {row.get('feature_id')}")
        all_inside = all_inside and inside
        max_abs_z = max(max_abs_z, abs(float(row["west_sumatra_z"])))

    if estimate.get("schema") != "ranah-observatory/milestone7-west-sumatra-expected-performance/v1":
        errors.append("West Sumatra estimate schema drift")
    if estimate.get("geography_id") != "idn.13" or estimate.get("reference_year") != 2024:
        errors.append("West Sumatra estimate geography/year drift")
    if estimate.get("claim_type") != "predictive/model estimate":
        errors.append("West Sumatra estimate claim type drift")
    if estimate.get("target") != "real_grdp_per_capita":
        errors.append("West Sumatra estimate target drift")
    if not close(estimate.get("selected_penalty"), selected_penalty):
        errors.append("West Sumatra estimate selected penalty drift")
    ws_row = next((row for row in model_rows if row.get("geography_id") == "idn.13"), None)
    if ws_row is not None and not close(ws_row.get("real_grdp_per_capita"), estimate.get("observed_level"), atol=1e-9):
        errors.append("West Sumatra observed target does not match frozen model frame")
    if not all(finite(estimate.get(field)) for field in (
        "observed_level", "observed_log_target", "predicted_log_target", "uncorrected_exp_predicted_log_level",
        "duan_smearing_factor", "smearing_corrected_expected_level", "log_residual_observed_minus_predicted",
        "actual_to_expected_ratio", "percentage_residual_vs_expected", "loocv_empirical_residual_q025",
        "loocv_empirical_residual_q975",
    )):
        errors.append("West Sumatra estimate contains non-finite core statistics")
    else:
        observed = float(estimate["observed_level"])
        observed_log = float(estimate["observed_log_target"])
        predicted_log = float(estimate["predicted_log_target"])
        expected_level = float(estimate["smearing_corrected_expected_level"])
        if not close(math.log(observed), observed_log, atol=1e-9):
            errors.append("West Sumatra observed log target mismatch")
        if not close(math.exp(predicted_log), estimate.get("uncorrected_exp_predicted_log_level"), atol=1e-9):
            errors.append("West Sumatra uncorrected level retransformation mismatch")
        if not close(observed_log - predicted_log, estimate.get("log_residual_observed_minus_predicted"), atol=1e-9):
            errors.append("West Sumatra log residual sign/value drift")
        ratio = observed / expected_level
        if not close(ratio, estimate.get("actual_to_expected_ratio"), atol=1e-9):
            errors.append("West Sumatra actual-to-expected ratio mismatch")
        if not close((ratio - 1.0) * 100.0, estimate.get("percentage_residual_vs_expected"), atol=1e-8):
            errors.append("West Sumatra percentage residual mismatch")

    if cv_residuals:
        q025 = percentile(cv_residuals, 0.025)
        q975 = percentile(cv_residuals, 0.975)
        if not close(q025, estimate.get("loocv_empirical_residual_q025"), atol=1e-9):
            errors.append("empirical q025 residual drift")
        if not close(q975, estimate.get("loocv_empirical_residual_q975"), atol=1e-9):
            errors.append("empirical q975 residual drift")
        interval = estimate.get("exploratory_prediction_interval_level") or {}
        if not finite(interval.get("lower")) or not finite(interval.get("upper")):
            errors.append("exploratory prediction interval is invalid")
        else:
            lower = float(interval["lower"])
            upper = float(interval["upper"])
            pred_log = float(estimate["predicted_log_target"])
            if not close(lower, math.exp(pred_log + q025), atol=1e-8) or not close(upper, math.exp(pred_log + q975), atol=1e-8):
                errors.append("exploratory interval does not reproduce locked residual-quantile rule")
            if not lower < upper:
                errors.append("exploratory interval bounds are not ordered")

    support_summary = estimate.get("support") or {}
    if support_summary.get("all_features_inside_training_univariate_minmax") is not all_inside:
        errors.append("West Sumatra support summary min/max flag drift")
    if not close(support_summary.get("maximum_absolute_training_standardized_z"), max_abs_z, atol=1e-9):
        errors.append("West Sumatra maximum absolute z-score drift")
    sensitivity = estimate.get("sensitivity_ols") or {}
    for field in ("predicted_log_target", "duan_smearing_factor", "smearing_corrected_expected_level"):
        if not finite(sensitivity.get(field)):
            errors.append(f"OLS sensitivity output missing/non-finite: {field}")

    claim_limits = set(estimate.get("claim_limits") or [])
    required_limits = {
        "not a causal estimate",
        "not a production frontier",
        "not a counterfactual policy effect",
        "not an estimate of monetary value lost",
    }
    if not required_limits.issubset(claim_limits):
        errors.append("West Sumatra estimate lost required claim limitations")

    for contract_name, contract in (("source_hashes", manifest.get("source_hashes")), ("output_hashes", manifest.get("output_hashes"))):
        if not isinstance(contract, dict):
            errors.append(f"model manifest {contract_name} contract is missing")
            continue
        for rel_path, expected_hash in contract.items():
            path = ROOT / rel_path
            if not path.exists():
                errors.append(f"manifest hash target missing: {rel_path}")
            elif sha256(path) != expected_hash:
                errors.append(f"SHA-256 mismatch for {rel_path}")

    source_hashes = feature_manifest.get("source_hashes")
    if not isinstance(source_hashes, dict) or len(source_hashes) != 4:
        errors.append("feature-frame source-hash contract must contain four frozen normalized sources")
    else:
        for rel_path, expected_hash in source_hashes.items():
            path = ROOT / rel_path
            if not path.exists() or sha256(path) != expected_hash:
                errors.append(f"frozen feature-source SHA-256 mismatch for {rel_path}")

    output_hashes = feature_manifest.get("output_hashes")
    if not isinstance(output_hashes, dict) or len(output_hashes) != 3:
        errors.append("feature-frame output-hash contract must contain three outputs")
    else:
        for rel_path, expected_hash in output_hashes.items():
            path = ROOT / rel_path
            if not path.exists() or sha256(path) != expected_hash:
                errors.append(f"feature-frame output SHA-256 mismatch for {rel_path}")

    complete = not errors
    return {
        "schema": "ranah-observatory/milestone7-expected-performance-audit/v1",
        "criterion": "one baseline expected-performance/frontier model",
        "model_type": "ridge_expected_performance_baseline",
        "reference_year": 2024,
        "feature_count": len(registry),
        "model_geography_count": len(model_rows),
        "training_geography_count": 37,
        "focal_holdout": "idn.13",
        "cv_penalty_count": len(cv_summary),
        "selected_penalty": selected_penalty,
        "selected_loocv_rmse_log": manifest.get("loocv_rmse_log"),
        "naive_loocv_rmse_log": manifest.get("naive_loocv_rmse_log"),
        "beats_naive_benchmark": manifest.get("beats_naive_benchmark") is True,
        "west_sumatra_actual_level": estimate.get("observed_level"),
        "west_sumatra_expected_level": estimate.get("smearing_corrected_expected_level"),
        "west_sumatra_percentage_residual_vs_expected": estimate.get("percentage_residual_vs_expected"),
        "west_sumatra_all_features_inside_training_minmax": all_inside,
        "causal_analysis_performed": False,
        "frontier_model_performed": False,
        "monetary_wasted_potential_estimated": False,
        "errors": errors,
        "milestone7_complete": complete,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the frozen Milestone 7 expected-performance baseline.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = audit()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        report = {
            "schema": "ranah-observatory/milestone7-expected-performance-audit/v1",
            "criterion": "one baseline expected-performance/frontier model",
            "errors": [str(exc)],
            "milestone7_complete": False,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.require_complete and not report["milestone7_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
