#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
MODEL_FRAME = ROOT / "data/analysis/expected_performance/m7-model-frame-2024.csv"
FEATURE_REGISTRY = ROOT / "data/registries/milestone7_expected_performance_features.csv"
MODEL_SPEC = ROOT / "research/MILESTONE7_MODEL_SPEC.md"
OUTPUT_ROOT = ROOT / "data/analysis/expected_performance"
CV_SUMMARY_OUT = OUTPUT_ROOT / "m7-ridge-loocv-summary.csv"
CV_PREDICTIONS_OUT = OUTPUT_ROOT / "m7-ridge-selected-loocv-predictions.csv"
COEFFICIENTS_OUT = OUTPUT_ROOT / "m7-model-coefficients.csv"
SUPPORT_OUT = OUTPUT_ROOT / "m7-west-sumatra-support.csv"
ESTIMATE_OUT = OUTPUT_ROOT / "m7-west-sumatra-expected-performance.json"
MANIFEST_OUT = ROOT / "data/manifests/milestone7_expected_performance_model.json"
WEST_SUMATRA = "idn.13"
LAMBDA_GRID = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def rmse(residuals: list[float]) -> float:
    return math.sqrt(mean([value * value for value in residuals]))


def mae(residuals: list[float]) -> float:
    return mean([abs(value) for value in residuals])


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


def solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    if len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError("linear system has invalid shape")
    augmented = [list(matrix[i]) + [vector[i]] for i in range(n)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular or numerically degenerate model matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                augmented[row][j] - factor * augmented[column][j]
                for j in range(n + 1)
            ]
    return [augmented[row][n] for row in range(n)]


def parse_rows(feature_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in read_csv(MODEL_FRAME):
        geography_id = source["geography_id"]
        if geography_id in seen:
            raise ValueError(f"duplicate model geography: {geography_id}")
        seen.add(geography_id)
        features = [float(source[feature_id]) for feature_id in feature_ids]
        target = float(source["real_grdp_per_capita"])
        log_target = float(source["log_real_grdp_per_capita"])
        if any(not math.isfinite(value) for value in [*features, target, log_target]):
            raise ValueError(f"non-finite model value for {geography_id}")
        if target <= 0.0:
            raise ValueError(f"non-positive target for {geography_id}")
        if abs(math.log(target) - log_target) > 1e-9:
            raise ValueError(f"stored log target mismatch for {geography_id}")
        rows.append({
            "geography_id": geography_id,
            "geography_name": source["geography_name"],
            "features": features,
            "target": target,
            "log_target": log_target,
        })
    if len(rows) != 38 or WEST_SUMATRA not in seen:
        raise ValueError("model frame must contain exactly 38 provinces including West Sumatra")
    return sorted(rows, key=lambda row: row["geography_id"])


def fit_ridge(rows: list[dict[str, Any]], penalty: float) -> dict[str, Any]:
    if penalty < 0:
        raise ValueError("ridge penalty must be non-negative")
    p = len(rows[0]["features"])
    means = [mean([row["features"][j] for row in rows]) for j in range(p)]
    scales: list[float] = []
    for j in range(p):
        variance = mean([(row["features"][j] - means[j]) ** 2 for row in rows])
        scale = math.sqrt(variance)
        if scale <= 1e-12:
            raise ValueError(f"constant or near-constant predictor at column {j}")
        scales.append(scale)
    zrows = [[(row["features"][j] - means[j]) / scales[j] for j in range(p)] for row in rows]
    y = [row["log_target"] for row in rows]
    intercept = mean(y)
    centered_y = [value - intercept for value in y]
    gram = [[0.0 for _ in range(p)] for _ in range(p)]
    rhs = [0.0 for _ in range(p)]
    for z, target in zip(zrows, centered_y):
        for j in range(p):
            rhs[j] += z[j] * target
            for k in range(p):
                gram[j][k] += z[j] * z[k]
    for j in range(p):
        gram[j][j] += penalty
    beta = solve_linear(gram, rhs)
    return {"penalty": penalty, "means": means, "scales": scales, "intercept": intercept, "beta": beta}


def predict(model: dict[str, Any], features: list[float]) -> float:
    z = [(features[j] - model["means"][j]) / model["scales"][j] for j in range(len(features))]
    return model["intercept"] + sum(model["beta"][j] * z[j] for j in range(len(features)))


def cv_for_penalty(training_universe: list[dict[str, Any]], penalty: float) -> tuple[dict[str, float], list[dict[str, Any]]]:
    predictions: list[dict[str, Any]] = []
    residuals: list[float] = []
    naive_residuals: list[float] = []
    for test in training_universe:
        train = [row for row in training_universe if row["geography_id"] != test["geography_id"]]
        if len(train) != 36:
            raise ValueError("LOPO training fold must contain 36 provinces")
        model = fit_ridge(train, penalty)
        predicted = predict(model, test["features"])
        naive = mean([row["log_target"] for row in train])
        residual = test["log_target"] - predicted
        naive_residual = test["log_target"] - naive
        residuals.append(residual)
        naive_residuals.append(naive_residual)
        predictions.append({
            "geography_id": test["geography_id"],
            "geography_name": test["geography_name"],
            "observed_log_target": test["log_target"],
            "predicted_log_target": predicted,
            "residual_log_observed_minus_predicted": residual,
            "naive_predicted_log_target": naive,
            "naive_residual_log": naive_residual,
        })
    metrics = {
        "penalty": penalty,
        "mse": mean([value * value for value in residuals]),
        "rmse": rmse(residuals),
        "mae": mae(residuals),
        "naive_rmse": rmse(naive_residuals),
        "naive_mae": mae(naive_residuals),
    }
    return metrics, predictions


def build() -> dict[str, Any]:
    registry = read_csv(FEATURE_REGISTRY)
    feature_ids = [row["feature_id"] for row in registry]
    if len(feature_ids) != 4 or len(set(feature_ids)) != 4:
        raise ValueError("primary model must have exactly four unique registered predictors")
    rows = parse_rows(feature_ids)
    west_sumatra = next(row for row in rows if row["geography_id"] == WEST_SUMATRA)
    training = [row for row in rows if row["geography_id"] != WEST_SUMATRA]
    if len(training) != 37:
        raise ValueError("West Sumatra holdout must leave exactly 37 training provinces")

    cv_results: list[dict[str, float]] = []
    predictions_by_penalty: dict[float, list[dict[str, Any]]] = {}
    for penalty in LAMBDA_GRID:
        metrics, predictions = cv_for_penalty(training, penalty)
        cv_results.append(metrics)
        predictions_by_penalty[penalty] = predictions
    selected = min(cv_results, key=lambda row: (row["mse"], -row["penalty"]))
    selected_penalty = selected["penalty"]
    selected_predictions = predictions_by_penalty[selected_penalty]
    benchmark_passed = selected["rmse"] < selected["naive_rmse"]

    final_model = fit_ridge(training, selected_penalty)
    ols_model = fit_ridge(training, 0.0)
    selected_train_residuals = [row["log_target"] - predict(final_model, row["features"]) for row in training]
    ols_train_residuals = [row["log_target"] - predict(ols_model, row["features"]) for row in training]
    smearing = mean([math.exp(value) for value in selected_train_residuals])
    ols_smearing = mean([math.exp(value) for value in ols_train_residuals])

    ws_pred_log = predict(final_model, west_sumatra["features"])
    ws_uncorrected = math.exp(ws_pred_log)
    ws_expected = ws_uncorrected * smearing
    ws_log_residual = west_sumatra["log_target"] - ws_pred_log
    actual_to_expected = west_sumatra["target"] / ws_expected
    percentage_residual = (actual_to_expected - 1.0) * 100.0

    cv_residuals = [row["residual_log_observed_minus_predicted"] for row in selected_predictions]
    q025 = quantile(cv_residuals, 0.025)
    q975 = quantile(cv_residuals, 0.975)
    interval_lower = math.exp(ws_pred_log + q025)
    interval_upper = math.exp(ws_pred_log + q975)

    ols_pred_log = predict(ols_model, west_sumatra["features"])
    ols_expected = math.exp(ols_pred_log) * ols_smearing

    support_rows: list[dict[str, Any]] = []
    max_abs_z = 0.0
    all_inside = True
    for j, feature_id in enumerate(feature_ids):
        train_values = [row["features"][j] for row in training]
        ws_value = west_sumatra["features"][j]
        lower = min(train_values)
        upper = max(train_values)
        inside = lower <= ws_value <= upper
        z = (ws_value - final_model["means"][j]) / final_model["scales"][j]
        max_abs_z = max(max_abs_z, abs(z))
        all_inside = all_inside and inside
        support_rows.append({
            "feature_id": feature_id,
            "west_sumatra_value": f"{ws_value:.12g}",
            "training_min": f"{lower:.12g}",
            "training_max": f"{upper:.12g}",
            "training_mean": f"{final_model['means'][j]:.12g}",
            "training_scale": f"{final_model['scales'][j]:.12g}",
            "west_sumatra_z": f"{z:.12g}",
            "inside_univariate_minmax": str(inside).lower(),
        })

    cv_summary_rows = [{key: f"{value:.12g}" for key, value in result.items()} for result in cv_results]
    write_csv(CV_SUMMARY_OUT, ["penalty", "mse", "rmse", "mae", "naive_rmse", "naive_mae"], cv_summary_rows)
    cv_output_rows = [{key: (f"{value:.12g}" if isinstance(value, float) else value) for key, value in row.items()} for row in selected_predictions]
    write_csv(CV_PREDICTIONS_OUT, [
        "geography_id", "geography_name", "observed_log_target", "predicted_log_target",
        "residual_log_observed_minus_predicted", "naive_predicted_log_target", "naive_residual_log",
    ], cv_output_rows)
    coefficient_rows: list[dict[str, Any]] = []
    for j, feature_id in enumerate(feature_ids):
        coefficient_rows.append({
            "feature_id": feature_id,
            "selected_penalty": f"{selected_penalty:.12g}",
            "selected_standardized_coefficient": f"{final_model['beta'][j]:.12g}",
            "ols_standardized_coefficient": f"{ols_model['beta'][j]:.12g}",
        })
    write_csv(COEFFICIENTS_OUT, ["feature_id", "selected_penalty", "selected_standardized_coefficient", "ols_standardized_coefficient"], coefficient_rows)
    write_csv(SUPPORT_OUT, [
        "feature_id", "west_sumatra_value", "training_min", "training_max", "training_mean", "training_scale",
        "west_sumatra_z", "inside_univariate_minmax",
    ], support_rows)

    estimate = {
        "schema": "ranah-observatory/milestone7-west-sumatra-expected-performance/v1",
        "geography_id": WEST_SUMATRA,
        "geography_name": west_sumatra["geography_name"],
        "reference_year": 2024,
        "claim_type": "predictive/model estimate",
        "target": "real_grdp_per_capita",
        "target_unit": "million_rupiah_per_person_constant_2010",
        "selected_penalty": selected_penalty,
        "observed_level": west_sumatra["target"],
        "observed_log_target": west_sumatra["log_target"],
        "predicted_log_target": ws_pred_log,
        "uncorrected_exp_predicted_log_level": ws_uncorrected,
        "duan_smearing_factor": smearing,
        "smearing_corrected_expected_level": ws_expected,
        "log_residual_observed_minus_predicted": ws_log_residual,
        "actual_to_expected_ratio": actual_to_expected,
        "percentage_residual_vs_expected": percentage_residual,
        "loocv_empirical_residual_q025": q025,
        "loocv_empirical_residual_q975": q975,
        "exploratory_prediction_interval_level": {"lower": interval_lower, "upper": interval_upper},
        "support": {
            "all_features_inside_training_univariate_minmax": all_inside,
            "maximum_absolute_training_standardized_z": max_abs_z,
            "interpretation": "within marginal training support" if all_inside else "at least one predictor is outside marginal training support",
        },
        "sensitivity_ols": {
            "predicted_log_target": ols_pred_log,
            "duan_smearing_factor": ols_smearing,
            "smearing_corrected_expected_level": ols_expected,
        },
        "claim_limits": [
            "not a causal estimate",
            "not a production frontier",
            "not a counterfactual policy effect",
            "not an estimate of monetary value lost",
        ],
    }
    ESTIMATE_OUT.write_text(json.dumps(estimate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    outputs = [CV_SUMMARY_OUT, CV_PREDICTIONS_OUT, COEFFICIENTS_OUT, SUPPORT_OUT, ESTIMATE_OUT]
    manifest = {
        "schema": "ranah-observatory/milestone7-expected-performance-model/v1",
        "criterion": "one baseline expected-performance/frontier model",
        "model_type": "ridge_expected_performance_baseline",
        "reference_year": 2024,
        "geography_regime": "bps_current_38_province_2024plus",
        "training_geography_count": 37,
        "focal_holdout": WEST_SUMATRA,
        "feature_ids": feature_ids,
        "feature_count": len(feature_ids),
        "penalty_grid": LAMBDA_GRID,
        "selected_penalty": selected_penalty,
        "loocv_rmse_log": selected["rmse"],
        "loocv_mae_log": selected["mae"],
        "naive_loocv_rmse_log": selected["naive_rmse"],
        "beats_naive_benchmark": benchmark_passed,
        "west_sumatra_target_excluded_from_selection_and_fit": True,
        "causal_analysis_performed": False,
        "frontier_model_performed": False,
        "monetary_wasted_potential_estimated": False,
        "source_hashes": {
            str(MODEL_FRAME.relative_to(ROOT)): sha256(MODEL_FRAME),
            str(FEATURE_REGISTRY.relative_to(ROOT)): sha256(FEATURE_REGISTRY),
            str(MODEL_SPEC.relative_to(ROOT)): sha256(MODEL_SPEC),
        },
        "output_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in outputs},
        "completion_gate_passed": benchmark_passed,
        "errors": [] if benchmark_passed else ["selected ridge baseline does not beat naive LOPO mean-log-target benchmark"],
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": manifest, "west_sumatra_estimate": estimate}, ensure_ascii=False, indent=2, sort_keys=True))
    return manifest


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
