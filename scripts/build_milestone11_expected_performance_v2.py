#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
INPUT_WIDE = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
INPUT_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
DESIGN_GATE = ROOT / "data/manifests/milestone11_design_gate.json"
SPEC = ROOT / "research/MILESTONE11_EXPECTED_PERFORMANCE_V2_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/expected_performance_v2"
MODEL_FRAME_OUT = OUT_DIR / "m11-model-frame.csv"
PREDICTIONS_OUT = OUT_DIR / "m11-crossfit-predictions.csv"
TARGET_SUMMARY_OUT = OUT_DIR / "m11-target-summary.csv"
SUPPORT_OUT = OUT_DIR / "m11-support-diagnostics.csv"
COEFFICIENTS_OUT = OUT_DIR / "m11-outer-fold-coefficients.csv"
SENSITIVITY_SUMMARY_OUT = OUT_DIR / "m11-sensitivity-summary.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone11_expected_performance_v2.json"

REGIME_ID = "sumbar_current_kabkota_lagged_structural_2019_2024_v1"
TARGET_YEARS = list(range(2019, 2025))
TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
TARGET_DIRECTIONS = {
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
SENSITIVITY_FEATURES = [*PRIMARY_FEATURES, "annual_rainfall"]
PENALTY_GRID = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0]
BASE_TARGET_YEAR = 2019


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires at least one value")
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
        raise ValueError("invalid linear-system shape")
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


def float_value(row: dict[str, str], key: str, context: str) -> float:
    raw = row.get(key, "")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"missing/non-numeric {key} in {context}: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key} in {context}")
    return value


def validate_prefit_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    m10 = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    if m10.get("schema") != "ranah-observatory/milestone10-analytical-panel/v1" or m10.get("milestone10_complete") is not True:
        raise ValueError("M11 requires completed M10 Analytical Panel v1")
    if m10.get("regime_id") != "sumbar_current_kabkota_2018_2025_v1":
        raise ValueError("unexpected M10 analytical regime")
    if m10.get("geography_count") != 19 or m10.get("wide_row_count") != 152:
        raise ValueError("M10 footprint drift before M11")
    if gate.get("schema") != "ranah-observatory/milestone11-design-gate/v1":
        raise ValueError("unexpected M11 design-gate schema")
    locked = {
        "regime_id": REGIME_ID,
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
    }
    for key, expected in locked.items():
        if gate.get(key) != expected:
            raise ValueError(f"M11 prefit design gate drift: {key}")
    if gate.get("target_year_selected_before_model_fit") is not True or gate.get("targets_selected_before_model_fit") is not True or gate.get("features_selected_before_model_fit") is not True:
        raise ValueError("M11 prefit selection flags are not locked")
    return m10, gate


def build_model_frame() -> tuple[list[dict[str, Any]], list[str]]:
    wide_rows = read_csv(INPUT_WIDE)
    if len(wide_rows) != 152:
        raise ValueError(f"M10 wide frame must have 152 rows, got {len(wide_rows)}")
    by_key: dict[tuple[str, int], dict[str, str]] = {}
    names: dict[str, str] = {}
    for row in wide_rows:
        geography_id = row.get("geography_id", "")
        year = int(row["analysis_year"])
        key = (geography_id, year)
        if key in by_key:
            raise ValueError(f"duplicate M10 wide key: {key}")
        by_key[key] = row
        names[geography_id] = row.get("geography_name", "")
    geographies = sorted(names)
    if len(geographies) != 19:
        raise ValueError(f"M11 expects exact 19 geographies, got {len(geographies)}")

    frame: list[dict[str, Any]] = []
    for geography_id in geographies:
        for target_year in TARGET_YEARS:
            feature_year = target_year - 1
            target_row = by_key.get((geography_id, target_year))
            feature_row = by_key.get((geography_id, feature_year))
            if target_row is None or feature_row is None:
                raise ValueError(f"missing M10 geography-year row for {geography_id} target={target_year}")
            record: dict[str, Any] = {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "geography_name": names[geography_id],
                "target_year": target_year,
                "feature_year": feature_year,
            }
            for feature in SENSITIVITY_FEATURES:
                record[f"lag1_{feature}"] = float_value(feature_row, feature, f"{geography_id}/{feature_year}")
            for target in TARGETS:
                record[target] = float_value(target_row, target, f"{geography_id}/{target_year}")
            frame.append(record)
    if len(frame) != 114:
        raise ValueError(f"M11 model frame must have 114 rows, got {len(frame)}")
    return frame, geographies


def fit_model(rows: list[dict[str, Any]], target: str, feature_ids: list[str], penalty: float) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot fit empty model")
    if penalty < 0:
        raise ValueError("ridge penalty must be non-negative")
    p = len(feature_ids)
    feature_columns = [f"lag1_{feature}" for feature in feature_ids]
    means = [mean([float(row[column]) for row in rows]) for column in feature_columns]
    scales: list[float] = []
    for j, column in enumerate(feature_columns):
        variance = mean([(float(row[column]) - means[j]) ** 2 for row in rows])
        scale = math.sqrt(variance)
        if scale <= 1e-12:
            raise ValueError(f"constant/near-constant predictor {column}")
        scales.append(scale)

    dummy_years = [year for year in TARGET_YEARS if year != BASE_TARGET_YEAR]
    parameter_count = 1 + p + len(dummy_years)
    gram = [[0.0 for _ in range(parameter_count)] for _ in range(parameter_count)]
    rhs = [0.0 for _ in range(parameter_count)]

    for row in rows:
        x = [1.0]
        for j, column in enumerate(feature_columns):
            x.append((float(row[column]) - means[j]) / scales[j])
        target_year = int(row["target_year"])
        x.extend(1.0 if target_year == year else 0.0 for year in dummy_years)
        y = float(row[target])
        for j in range(parameter_count):
            rhs[j] += x[j] * y
            for k in range(parameter_count):
                gram[j][k] += x[j] * x[k]

    # Penalize standardized continuous features only; intercept/year effects remain unpenalized.
    for j in range(1, 1 + p):
        gram[j][j] += penalty
    beta = solve_linear(gram, rhs)
    return {
        "target": target,
        "feature_ids": feature_ids,
        "feature_columns": feature_columns,
        "means": means,
        "scales": scales,
        "dummy_years": dummy_years,
        "penalty": penalty,
        "beta": beta,
    }


def predict(model: dict[str, Any], row: dict[str, Any]) -> float:
    x = [1.0]
    for j, column in enumerate(model["feature_columns"]):
        x.append((float(row[column]) - model["means"][j]) / model["scales"][j])
    year = int(row["target_year"])
    x.extend(1.0 if year == dummy_year else 0.0 for dummy_year in model["dummy_years"])
    return sum(value * coefficient for value, coefficient in zip(x, model["beta"]))


def inner_select_penalty(
    outer_training_rows: list[dict[str, Any]],
    outer_training_geographies: list[str],
    target: str,
    feature_ids: list[str],
) -> tuple[float, list[dict[str, float]]]:
    results: list[dict[str, float]] = []
    for penalty in PENALTY_GRID:
        residuals: list[float] = []
        valid = True
        for inner_holdout in outer_training_geographies:
            train = [row for row in outer_training_rows if row["geography_id"] != inner_holdout]
            test = [row for row in outer_training_rows if row["geography_id"] == inner_holdout]
            if len(train) != 17 * 6 or len(test) != 6:
                raise ValueError("M11 inner geography-fold footprint drift")
            try:
                model = fit_model(train, target, feature_ids, penalty)
            except ValueError:
                valid = False
                break
            for row in test:
                residuals.append(float(row[target]) - predict(model, row))
        if valid and len(residuals) == 18 * 6:
            results.append({
                "penalty": penalty,
                "rmse": rmse(residuals),
                "mae": mae(residuals),
            })
        else:
            results.append({"penalty": penalty, "rmse": math.inf, "mae": math.inf})
    available = [row for row in results if math.isfinite(row["rmse"])]
    if not available:
        raise ValueError(f"no valid M11 inner-CV penalty for {target}")
    selected = min(available, key=lambda row: (row["rmse"], row["penalty"]))
    return float(selected["penalty"]), results


def parameter_rows(
    model: dict[str, Any], target: str, outer_geography: str, model_variant: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    beta = model["beta"]
    rows.append({
        "target_id": target,
        "outer_holdout_geography_id": outer_geography,
        "model_variant": model_variant,
        "selected_penalty": model["penalty"],
        "parameter_type": "intercept",
        "parameter_id": "intercept_base_2019",
        "coefficient": beta[0],
    })
    for j, feature in enumerate(model["feature_ids"]):
        rows.append({
            "target_id": target,
            "outer_holdout_geography_id": outer_geography,
            "model_variant": model_variant,
            "selected_penalty": model["penalty"],
            "parameter_type": "standardized_continuous_feature",
            "parameter_id": feature,
            "coefficient": beta[1 + j],
        })
    offset = 1 + len(model["feature_ids"])
    rows.append({
        "target_id": target,
        "outer_holdout_geography_id": outer_geography,
        "model_variant": model_variant,
        "selected_penalty": model["penalty"],
        "parameter_type": "target_year_effect",
        "parameter_id": str(BASE_TARGET_YEAR),
        "coefficient": 0.0,
    })
    for j, year in enumerate(model["dummy_years"]):
        rows.append({
            "target_id": target,
            "outer_holdout_geography_id": outer_geography,
            "model_variant": model_variant,
            "selected_penalty": model["penalty"],
            "parameter_type": "target_year_effect",
            "parameter_id": str(year),
            "coefficient": beta[offset + j],
        })
    return rows


def support_rows_for_prediction(
    outer_training_rows: list[dict[str, Any]],
    heldout_row: dict[str, Any],
    target: str,
) -> tuple[list[dict[str, Any]], bool]:
    feature_year = int(heldout_row["feature_year"])
    same_year_training = [row for row in outer_training_rows if int(row["feature_year"]) == feature_year]
    if len(same_year_training) != 18:
        raise ValueError("M11 same-year support training footprint must contain 18 geographies")
    output: list[dict[str, Any]] = []
    all_inside = True
    for feature in PRIMARY_FEATURES:
        column = f"lag1_{feature}"
        values = [float(row[column]) for row in same_year_training]
        focal = float(heldout_row[column])
        lower = min(values)
        upper = max(values)
        inside = lower <= focal <= upper
        all_inside = all_inside and inside
        output.append({
            "target_id": target,
            "geography_id": heldout_row["geography_id"],
            "target_year": heldout_row["target_year"],
            "feature_year": feature_year,
            "feature_id": feature,
            "focal_value": focal,
            "same_year_training_min": lower,
            "same_year_training_max": upper,
            "inside_same_year_marginal_minmax": inside,
        })
    return output, all_inside


def run_crossfit(
    frame: list[dict[str, Any]],
    geographies: list[str],
    target: str,
    feature_ids: list[str],
    model_variant: str,
    retain_parameters: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    predictions: list[dict[str, Any]] = []
    support: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    for outer_holdout in geographies:
        outer_train = [row for row in frame if row["geography_id"] != outer_holdout]
        outer_test = [row for row in frame if row["geography_id"] == outer_holdout]
        outer_training_geographies = [geo for geo in geographies if geo != outer_holdout]
        if len(outer_train) != 18 * 6 or len(outer_test) != 6:
            raise ValueError("M11 outer geography-fold footprint drift")
        selected_penalty, inner_grid = inner_select_penalty(
            outer_train, outer_training_geographies, target, feature_ids
        )
        model = fit_model(outer_train, target, feature_ids, selected_penalty)
        if retain_parameters:
            coefficients.extend(parameter_rows(model, target, outer_holdout, model_variant))

        for heldout_row in sorted(outer_test, key=lambda row: int(row["target_year"])):
            expected = predict(model, heldout_row)
            observed = float(heldout_row[target])
            target_year = int(heldout_row["target_year"])
            same_year_train = [
                row for row in outer_train if int(row["target_year"]) == target_year
            ]
            if len(same_year_train) != 18:
                raise ValueError("M11 same-year naive benchmark requires 18 training geographies")
            naive = mean([float(row[target]) for row in same_year_train])
            prediction_row: dict[str, Any] = {
                "target_id": target,
                "target_direction": TARGET_DIRECTIONS[target],
                "geography_id": heldout_row["geography_id"],
                "geography_name": heldout_row["geography_name"],
                "target_year": target_year,
                "feature_year": int(heldout_row["feature_year"]),
                "model_variant": model_variant,
                "observed": observed,
                "expected": expected,
                "residual_observed_minus_expected": observed - expected,
                "naive_same_year_peer_mean": naive,
                "naive_residual": observed - naive,
                "selected_penalty": selected_penalty,
                "inner_cv_selected_rmse": next(
                    row["rmse"] for row in inner_grid if row["penalty"] == selected_penalty
                ),
            }
            if model_variant == "primary":
                support_rows, all_inside = support_rows_for_prediction(
                    outer_train, heldout_row, target
                )
                support.extend(support_rows)
                prediction_row["all_primary_features_inside_same_year_marginal_minmax"] = all_inside
                prediction_row["support_warning"] = not all_inside
            predictions.append(prediction_row)
    expected_count = 19 * 6
    if len(predictions) != expected_count:
        raise ValueError(f"M11 {model_variant} {target} crossfit count drift")
    return predictions, support, coefficients


def format_number(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.12g}"
    return value


def build() -> dict[str, Any]:
    m10_manifest, design_gate = validate_prefit_contract()
    frame, geographies = build_model_frame()

    model_frame_rows: list[dict[str, Any]] = []
    for row in frame:
        output = {
            "regime_id": row["regime_id"],
            "geography_id": row["geography_id"],
            "geography_name": row["geography_name"],
            "target_year": row["target_year"],
            "feature_year": row["feature_year"],
        }
        for feature in SENSITIVITY_FEATURES:
            output[f"lag1_{feature}"] = format_number(float(row[f"lag1_{feature}"]))
        for target in TARGETS:
            output[target] = format_number(float(row[target]))
        model_frame_rows.append(output)
    write_csv(
        MODEL_FRAME_OUT,
        [
            "regime_id",
            "geography_id",
            "geography_name",
            "target_year",
            "feature_year",
            *[f"lag1_{feature}" for feature in SENSITIVITY_FEATURES],
            *TARGETS,
        ],
        model_frame_rows,
    )

    primary_predictions: list[dict[str, Any]] = []
    sensitivity_predictions: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    coefficient_rows: list[dict[str, Any]] = []

    for target in TARGETS:
        primary, support, coefficients = run_crossfit(
            frame, geographies, target, PRIMARY_FEATURES, "primary", True
        )
        sensitivity, _, _ = run_crossfit(
            frame, geographies, target, SENSITIVITY_FEATURES, "primary_plus_lagged_rainfall", False
        )
        primary_predictions.extend(primary)
        sensitivity_predictions.extend(sensitivity)
        support_rows.extend(support)
        coefficient_rows.extend(coefficients)

    sensitivity_by_key = {
        (row["target_id"], row["geography_id"], int(row["target_year"])): row
        for row in sensitivity_predictions
    }
    if len(sensitivity_by_key) != 3 * 19 * 6:
        raise ValueError("M11 sensitivity prediction key drift")

    target_summaries: list[dict[str, Any]] = []
    sensitivity_summaries: list[dict[str, Any]] = []
    qualification_by_target: dict[str, bool] = {}
    target_metrics: dict[str, dict[str, Any]] = {}

    for target in TARGETS:
        rows = [row for row in primary_predictions if row["target_id"] == target]
        sens_rows = [row for row in sensitivity_predictions if row["target_id"] == target]
        residuals = [float(row["residual_observed_minus_expected"]) for row in rows]
        naive_residuals = [float(row["naive_residual"]) for row in rows]
        sens_residuals = [float(row["residual_observed_minus_expected"]) for row in sens_rows]
        model_rmse = rmse(residuals)
        model_mae = mae(residuals)
        naive_rmse = rmse(naive_residuals)
        naive_mae = mae(naive_residuals)
        sens_rmse = rmse(sens_residuals)
        sens_mae = mae(sens_residuals)
        qualified = model_rmse < naive_rmse and model_mae < naive_mae
        qualification_by_target[target] = qualified
        penalty_counts = Counter(format_number(float(row["selected_penalty"])) for row in rows[::6])
        sensitivity_penalty_counts = Counter(format_number(float(row["selected_penalty"])) for row in sens_rows[::6])
        support_warning_count = sum(bool(row.get("support_warning")) for row in rows)
        target_summaries.append({
            "target_id": target,
            "target_direction": TARGET_DIRECTIONS[target],
            "crossfit_prediction_count": len(rows),
            "outer_geography_count": 19,
            "target_year_count": 6,
            "model_rmse": model_rmse,
            "model_mae": model_mae,
            "naive_same_year_peer_mean_rmse": naive_rmse,
            "naive_same_year_peer_mean_mae": naive_mae,
            "rmse_improvement_vs_naive_percent": (1.0 - model_rmse / naive_rmse) * 100.0,
            "mae_improvement_vs_naive_percent": (1.0 - model_mae / naive_mae) * 100.0,
            "benchmark_qualified": qualified,
            "substantive_expected_performance_interpretation_authorized": qualified,
            "support_warning_prediction_count": support_warning_count,
            "outer_selected_penalty_counts_json": json.dumps(dict(sorted(penalty_counts.items())), sort_keys=True, separators=(",", ":")),
        })
        sensitivity_summaries.append({
            "target_id": target,
            "primary_rmse": model_rmse,
            "primary_mae": model_mae,
            "primary_plus_lagged_rainfall_rmse": sens_rmse,
            "primary_plus_lagged_rainfall_mae": sens_mae,
            "sensitivity_minus_primary_rmse": sens_rmse - model_rmse,
            "sensitivity_minus_primary_mae": sens_mae - model_mae,
            "sensitivity_better_rmse": sens_rmse < model_rmse,
            "sensitivity_better_mae": sens_mae < model_mae,
            "sensitivity_outer_selected_penalty_counts_json": json.dumps(dict(sorted(sensitivity_penalty_counts.items())), sort_keys=True, separators=(",", ":")),
            "sensitivity_can_replace_primary": False,
            "rainfall_claim_type": "model_estimate",
            "causal_rainfall_interpretation_authorized": False,
        })
        target_metrics[target] = {
            "model_rmse": model_rmse,
            "model_mae": model_mae,
            "naive_rmse": naive_rmse,
            "naive_mae": naive_mae,
            "benchmark_qualified": qualified,
            "sensitivity_rmse": sens_rmse,
            "sensitivity_mae": sens_mae,
        }

    # Attach sensitivity predictions, benchmark qualification, and focal-excluded empirical uncertainty.
    final_predictions: list[dict[str, Any]] = []
    for row in primary_predictions:
        key = (row["target_id"], row["geography_id"], int(row["target_year"]))
        sensitivity = sensitivity_by_key[key]
        other_residuals = [
            float(candidate["residual_observed_minus_expected"])
            for candidate in primary_predictions
            if candidate["target_id"] == row["target_id"]
            and candidate["geography_id"] != row["geography_id"]
        ]
        if len(other_residuals) != 18 * 6:
            raise ValueError("M11 focal-excluded uncertainty calibration footprint drift")
        q025 = quantile(other_residuals, 0.025)
        q975 = quantile(other_residuals, 0.975)
        expected = float(row["expected"])
        final_predictions.append({
            **row,
            "benchmark_qualified": qualification_by_target[row["target_id"]],
            "substantive_interpretation_authorized": qualification_by_target[row["target_id"]],
            "focal_excluded_empirical_residual_q025": q025,
            "focal_excluded_empirical_residual_q975": q975,
            "exploratory_prediction_interval_lower": expected + q025,
            "exploratory_prediction_interval_upper": expected + q975,
            "sensitivity_expected_plus_lagged_rainfall": sensitivity["expected"],
            "sensitivity_residual_observed_minus_expected": sensitivity["residual_observed_minus_expected"],
            "sensitivity_selected_penalty": sensitivity["selected_penalty"],
            "sensitivity_expected_minus_primary_expected": float(sensitivity["expected"]) - expected,
        })

    final_predictions.sort(key=lambda row: (TARGETS.index(row["target_id"]), row["geography_id"], int(row["target_year"])))
    support_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), row["geography_id"], int(row["target_year"]), PRIMARY_FEATURES.index(row["feature_id"])))
    coefficient_rows.sort(key=lambda row: (TARGETS.index(row["target_id"]), row["outer_holdout_geography_id"], row["parameter_type"], row["parameter_id"]))

    write_csv(
        PREDICTIONS_OUT,
        [
            "target_id",
            "target_direction",
            "geography_id",
            "geography_name",
            "target_year",
            "feature_year",
            "observed",
            "expected",
            "residual_observed_minus_expected",
            "naive_same_year_peer_mean",
            "naive_residual",
            "selected_penalty",
            "inner_cv_selected_rmse",
            "all_primary_features_inside_same_year_marginal_minmax",
            "support_warning",
            "benchmark_qualified",
            "substantive_interpretation_authorized",
            "focal_excluded_empirical_residual_q025",
            "focal_excluded_empirical_residual_q975",
            "exploratory_prediction_interval_lower",
            "exploratory_prediction_interval_upper",
            "sensitivity_expected_plus_lagged_rainfall",
            "sensitivity_residual_observed_minus_expected",
            "sensitivity_selected_penalty",
            "sensitivity_expected_minus_primary_expected",
        ],
        [{key: format_number(value) for key, value in row.items()} for row in final_predictions],
    )
    write_csv(
        TARGET_SUMMARY_OUT,
        [
            "target_id",
            "target_direction",
            "crossfit_prediction_count",
            "outer_geography_count",
            "target_year_count",
            "model_rmse",
            "model_mae",
            "naive_same_year_peer_mean_rmse",
            "naive_same_year_peer_mean_mae",
            "rmse_improvement_vs_naive_percent",
            "mae_improvement_vs_naive_percent",
            "benchmark_qualified",
            "substantive_expected_performance_interpretation_authorized",
            "support_warning_prediction_count",
            "outer_selected_penalty_counts_json",
        ],
        [{key: format_number(value) for key, value in row.items()} for row in target_summaries],
    )
    write_csv(
        SUPPORT_OUT,
        [
            "target_id",
            "geography_id",
            "target_year",
            "feature_year",
            "feature_id",
            "focal_value",
            "same_year_training_min",
            "same_year_training_max",
            "inside_same_year_marginal_minmax",
        ],
        [{key: format_number(value) for key, value in row.items()} for row in support_rows],
    )
    write_csv(
        COEFFICIENTS_OUT,
        [
            "target_id",
            "outer_holdout_geography_id",
            "model_variant",
            "selected_penalty",
            "parameter_type",
            "parameter_id",
            "coefficient",
        ],
        [{key: format_number(value) for key, value in row.items()} for row in coefficient_rows],
    )
    write_csv(
        SENSITIVITY_SUMMARY_OUT,
        [
            "target_id",
            "primary_rmse",
            "primary_mae",
            "primary_plus_lagged_rainfall_rmse",
            "primary_plus_lagged_rainfall_mae",
            "sensitivity_minus_primary_rmse",
            "sensitivity_minus_primary_mae",
            "sensitivity_better_rmse",
            "sensitivity_better_mae",
            "sensitivity_outer_selected_penalty_counts_json",
            "sensitivity_can_replace_primary",
            "rainfall_claim_type",
            "causal_rainfall_interpretation_authorized",
        ],
        [{key: format_number(value) for key, value in row.items()} for row in sensitivity_summaries],
    )

    qualified_targets = [target for target in TARGETS if qualification_by_target[target]]
    failed_targets = [target for target in TARGETS if not qualification_by_target[target]]
    manifest = {
        "schema": "ranah-observatory/milestone11-expected-performance-v2/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 11,
        "regime_id": REGIME_ID,
        "input_regime_id": m10_manifest.get("regime_id"),
        "geography_count": 19,
        "target_years": TARGET_YEARS,
        "target_year_count": 6,
        "model_frame_row_count": len(frame),
        "target_ids": TARGETS,
        "primary_feature_ids": PRIMARY_FEATURES,
        "sensitivity_feature_ids": SENSITIVITY_FEATURES,
        "feature_lag_years": 1,
        "penalty_grid": PENALTY_GRID,
        "outer_validation": "leave_one_geography_out_all_six_years",
        "inner_model_selection": "leave_one_geography_out_within_outer_training_universe",
        "crossfit_prediction_count": len(final_predictions),
        "expected_crossfit_prediction_count": 3 * 19 * 6,
        "support_diagnostic_row_count": len(support_rows),
        "outer_fold_coefficient_row_count": len(coefficient_rows),
        "benchmark_qualified_target_ids": qualified_targets,
        "benchmark_failed_target_ids": failed_targets,
        "benchmark_qualified_target_count": len(qualified_targets),
        "target_metrics": target_metrics,
        "benchmark_gate": "model_rmse_lt_naive_rmse_and_model_mae_lt_naive_mae",
        "target_year_selected_before_model_fit": design_gate.get("target_year_selected_before_model_fit") is True,
        "targets_selected_before_model_fit": design_gate.get("targets_selected_before_model_fit") is True,
        "features_selected_before_model_fit": design_gate.get("features_selected_before_model_fit") is True,
        "sensitivity_selected_before_model_fit": design_gate.get("sensitivity_selected_before_model_fit") is True,
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
        "source_inputs": {
            str(INPUT_WIDE.relative_to(ROOT)): sha256(INPUT_WIDE),
            str(INPUT_MANIFEST.relative_to(ROOT)): sha256(INPUT_MANIFEST),
            str(DESIGN_GATE.relative_to(ROOT)): sha256(DESIGN_GATE),
            str(SPEC.relative_to(ROOT)): sha256(SPEC),
        },
        "outputs": {
            "model_frame": {"path": str(MODEL_FRAME_OUT.relative_to(ROOT)), "sha256": sha256(MODEL_FRAME_OUT)},
            "crossfit_predictions": {"path": str(PREDICTIONS_OUT.relative_to(ROOT)), "sha256": sha256(PREDICTIONS_OUT)},
            "target_summary": {"path": str(TARGET_SUMMARY_OUT.relative_to(ROOT)), "sha256": sha256(TARGET_SUMMARY_OUT)},
            "support_diagnostics": {"path": str(SUPPORT_OUT.relative_to(ROOT)), "sha256": sha256(SUPPORT_OUT)},
            "outer_fold_coefficients": {"path": str(COEFFICIENTS_OUT.relative_to(ROOT)), "sha256": sha256(COEFFICIENTS_OUT)},
            "sensitivity_summary": {"path": str(SENSITIVITY_SUMMARY_OUT.relative_to(ROOT)), "sha256": sha256(SENSITIVITY_SUMMARY_OUT)},
        },
        "milestone11_complete": True,
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
