#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
INPUT_WIDE = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
INPUT_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
DESIGN_GATE = ROOT / "data/manifests/milestone19_design_gate.json"
SPEC = ROOT / "research/MILESTONE19_DYNAMIC_FORECAST_ENGINE_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/dynamic_forecast_v1"
MODEL_FRAME_OUT = OUT_DIR / "m19-model-frame.csv"
BACKTEST_OUT = OUT_DIR / "m19-backtest-predictions.csv"
SUMMARY_OUT = OUT_DIR / "m19-target-summary.csv"
COEFFICIENTS_OUT = OUT_DIR / "m19-outer-fold-coefficients.csv"
FORECAST_OUT = OUT_DIR / "m19-forecast-2026.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone19_dynamic_forecast_engine.json"

REGIME_ID = "sumbar_current_kabkota_dynamic_forecast_2019_2026_v1"
TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
TARGET_DIRECTIONS = {
    "poverty_rate": "lower_is_favorable",
    "unemployment_rate": "lower_is_favorable",
    "real_grdp_growth": "higher_is_favorable",
}
STRUCTURAL_FEATURES = [
    "mean_years_schooling",
    "labor_force_participation",
    "rice_yield",
]
MODEL_TARGET_YEARS = list(range(2019, 2026))
OUTER_FORECAST_YEARS = list(range(2021, 2026))
FINAL_FORECAST_YEAR = 2026
PENALTY_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


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


def float_value(row: dict[str, str], key: str, context: str) -> float:
    raw = row.get(key, "")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"missing/non-numeric {key} in {context}: {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite {key} in {context}")
    return value


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


def validate_prefit_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    m10 = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    if m10.get("schema") != "ranah-observatory/milestone10-analytical-panel/v1":
        raise ValueError("M19 requires M10 Analytical Panel v1")
    if m10.get("milestone10_complete") is not True:
        raise ValueError("M19 requires completed M10")
    if m10.get("regime_id") != "sumbar_current_kabkota_2018_2025_v1":
        raise ValueError("unexpected M10 regime")
    if m10.get("geography_count") != 19 or m10.get("wide_row_count") != 152:
        raise ValueError("M10 footprint drift before M19")
    required_complete = {
        "mean_years_schooling",
        "labor_force_participation",
        "rice_yield",
        *TARGETS,
    }
    complete = set(m10.get("complete_2018_2025_indicator_ids", []))
    if not required_complete.issubset(complete):
        raise ValueError("M19 required annual indicators are not complete through 2025")

    expected_gate = {
        "schema": "ranah-observatory/milestone19-design-gate/v1",
        "milestone": 19,
        "regime_id": REGIME_ID,
        "geography_count": 19,
        "target_ids": TARGETS,
        "structural_feature_ids": STRUCTURAL_FEATURES,
        "include_target_lag": True,
        "feature_lag_years": 1,
        "outer_forecast_years": OUTER_FORECAST_YEARS,
        "final_forecast_year": FINAL_FORECAST_YEAR,
        "penalty_grid": PENALTY_GRID,
        "benchmark": "own_previous_year_persistence",
        "qualification_requires_rmse_and_mae_improvement": True,
        "model_family": "pooled_autoregressive_ridge",
        "model_fit": False,
        "backtest_results_known": False,
        "forecast_results_known": False,
        "targets_selected_before_model_fit": True,
        "features_selected_before_model_fit": True,
        "outer_years_selected_before_model_fit": True,
        "algorithm_selected_before_model_fit": True,
        "posthoc_algorithm_search_authorized": False,
        "causal_claim_authorized": False,
        "policy_counterfactual_authorized": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            raise ValueError(f"M19 prefit design gate drift: {key}")
    return m10, gate


def load_wide() -> tuple[dict[tuple[str, int], dict[str, str]], dict[str, str], list[str]]:
    rows = read_csv(INPUT_WIDE)
    if len(rows) != 152:
        raise ValueError(f"M10 wide frame must have 152 rows, got {len(rows)}")
    by_key: dict[tuple[str, int], dict[str, str]] = {}
    names: dict[str, str] = {}
    for row in rows:
        geography_id = row.get("geography_id", "")
        year = int(row["analysis_year"])
        key = (geography_id, year)
        if key in by_key:
            raise ValueError(f"duplicate M10 wide key: {key}")
        by_key[key] = row
        names[geography_id] = row.get("geography_name", "")
    geographies = sorted(names)
    if len(geographies) != 19:
        raise ValueError(f"M19 expects exact 19 geographies, got {len(geographies)}")
    return by_key, names, geographies


def build_model_frame(
    by_key: dict[tuple[str, int], dict[str, str]],
    names: dict[str, str],
    geographies: list[str],
) -> list[dict[str, Any]]:
    frame: list[dict[str, Any]] = []
    for geography_id in geographies:
        for target_year in MODEL_TARGET_YEARS:
            feature_year = target_year - 1
            target_row = by_key[(geography_id, target_year)]
            lag_row = by_key[(geography_id, feature_year)]
            record: dict[str, Any] = {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "geography_name": names[geography_id],
                "target_year": target_year,
                "feature_year": feature_year,
            }
            for target in TARGETS:
                record[target] = float_value(target_row, target, f"{geography_id}/{target_year}")
                record[f"lag1_{target}"] = float_value(lag_row, target, f"{geography_id}/{feature_year}")
            for feature in STRUCTURAL_FEATURES:
                record[f"lag1_{feature}"] = float_value(lag_row, feature, f"{geography_id}/{feature_year}")
            frame.append(record)
    expected = 19 * len(MODEL_TARGET_YEARS)
    if len(frame) != expected:
        raise ValueError(f"M19 model frame must have {expected} rows, got {len(frame)}")
    return frame


def feature_columns_for(target: str) -> list[str]:
    return [
        f"lag1_{target}",
        *[f"lag1_{feature}" for feature in STRUCTURAL_FEATURES],
    ]


def fit_ridge(rows: list[dict[str, Any]], target: str, penalty: float) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot fit empty model")
    if penalty <= 0:
        raise ValueError("M19 ridge penalty must be positive")
    columns = feature_columns_for(target)
    means = [mean([float(row[column]) for row in rows]) for column in columns]
    scales: list[float] = []
    for j, column in enumerate(columns):
        variance = mean([(float(row[column]) - means[j]) ** 2 for row in rows])
        scale = math.sqrt(variance)
        if scale <= 1e-12:
            raise ValueError(f"constant/near-constant predictor {column}")
        scales.append(scale)

    p = len(columns)
    parameter_count = 1 + p
    gram = [[0.0 for _ in range(parameter_count)] for _ in range(parameter_count)]
    rhs = [0.0 for _ in range(parameter_count)]
    for row in rows:
        x = [1.0] + [
            (float(row[column]) - means[j]) / scales[j]
            for j, column in enumerate(columns)
        ]
        y = float(row[target])
        for j in range(parameter_count):
            rhs[j] += x[j] * y
            for k in range(parameter_count):
                gram[j][k] += x[j] * x[k]
    for j in range(1, parameter_count):
        gram[j][j] += penalty
    beta = solve_linear(gram, rhs)
    return {
        "target": target,
        "penalty": penalty,
        "columns": columns,
        "means": means,
        "scales": scales,
        "beta": beta,
        "training_row_count": len(rows),
        "training_start_year": min(int(row["target_year"]) for row in rows),
        "training_end_year": max(int(row["target_year"]) for row in rows),
    }


def predict(model: dict[str, Any], row: dict[str, Any]) -> float:
    x = [1.0] + [
        (float(row[column]) - model["means"][j]) / model["scales"][j]
        for j, column in enumerate(model["columns"])
    ]
    return sum(float(coef) * value for coef, value in zip(model["beta"], x))


def select_penalty(rows: list[dict[str, Any]], target: str) -> tuple[float, list[dict[str, Any]]]:
    years = sorted({int(row["target_year"]) for row in rows})
    validation_years = [year for year in years if year >= 2020]
    if not validation_years:
        raise ValueError("M19 penalty selection requires at least one inner validation year")

    scores: list[dict[str, Any]] = []
    for penalty in PENALTY_GRID:
        residuals: list[float] = []
        validation_rows = 0
        for validation_year in validation_years:
            inner_train = [row for row in rows if int(row["target_year"]) < validation_year]
            inner_test = [row for row in rows if int(row["target_year"]) == validation_year]
            if not inner_train or not inner_test:
                continue
            model = fit_ridge(inner_train, target, penalty)
            for row in inner_test:
                residuals.append(float(row[target]) - predict(model, row))
                validation_rows += 1
        if not residuals:
            raise ValueError("empty inner rolling-origin validation")
        scores.append(
            {
                "penalty": penalty,
                "rmse": rmse(residuals),
                "mae": mae(residuals),
                "validation_row_count": validation_rows,
            }
        )
    # Primary selection metric is RMSE. Exact/near ties prefer stronger shrinkage.
    scores.sort(key=lambda item: (round(float(item["rmse"]), 12), -float(item["penalty"])))
    return float(scores[0]["penalty"]), scores


def coefficient_rows(model: dict[str, Any], target: str, forecast_year: int, scope: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for column, coefficient in zip(model["columns"], model["beta"][1:]):
        rows.append(
            {
                "regime_id": REGIME_ID,
                "target_id": target,
                "forecast_year": forecast_year,
                "fit_scope": scope,
                "selected_penalty": model["penalty"],
                "training_start_year": model["training_start_year"],
                "training_end_year": model["training_end_year"],
                "training_row_count": model["training_row_count"],
                "predictor": column,
                "standardized_coefficient": coefficient,
                "interpretation": "predictive_diagnostic_not_causal_effect",
            }
        )
    return rows


def run_backtest(frame: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, bool]]:
    predictions: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    qualified: dict[str, bool] = {}

    for target in TARGETS:
        for forecast_year in OUTER_FORECAST_YEARS:
            train = [row for row in frame if int(row["target_year"]) < forecast_year]
            test = [row for row in frame if int(row["target_year"]) == forecast_year]
            if len(test) != 19:
                raise ValueError(f"M19 outer year {forecast_year} must have 19 rows")
            selected_penalty, _ = select_penalty(train, target)
            model = fit_ridge(train, target, selected_penalty)
            coefficients.extend(coefficient_rows(model, target, forecast_year, "outer_backtest"))
            for row in test:
                observed = float(row[target])
                model_prediction = predict(model, row)
                persistence_prediction = float(row[f"lag1_{target}"])
                predictions.append(
                    {
                        "regime_id": REGIME_ID,
                        "target_id": target,
                        "target_direction": TARGET_DIRECTIONS[target],
                        "geography_id": row["geography_id"],
                        "geography_name": row["geography_name"],
                        "forecast_year": forecast_year,
                        "information_cutoff_year": forecast_year - 1,
                        "observed": observed,
                        "dynamic_ridge_prediction": model_prediction,
                        "dynamic_ridge_residual": observed - model_prediction,
                        "persistence_prediction": persistence_prediction,
                        "persistence_residual": observed - persistence_prediction,
                        "selected_penalty": selected_penalty,
                        "training_start_year": model["training_start_year"],
                        "training_end_year": model["training_end_year"],
                        "training_row_count": model["training_row_count"],
                        "strictly_out_of_time": True,
                    }
                )

        target_rows = [row for row in predictions if row["target_id"] == target]
        if len(target_rows) != 95:
            raise ValueError(f"M19 target {target} must have 95 backtest rows")
        model_residuals = [float(row["dynamic_ridge_residual"]) for row in target_rows]
        persistence_residuals = [float(row["persistence_residual"]) for row in target_rows]
        model_rmse = rmse(model_residuals)
        model_mae = mae(model_residuals)
        persistence_rmse = rmse(persistence_residuals)
        persistence_mae = mae(persistence_residuals)
        is_qualified = model_rmse < persistence_rmse and model_mae < persistence_mae
        qualified[target] = is_qualified
        summaries.append(
            {
                "regime_id": REGIME_ID,
                "target_id": target,
                "target_direction": TARGET_DIRECTIONS[target],
                "backtest_prediction_count": len(target_rows),
                "outer_forecast_start_year": min(OUTER_FORECAST_YEARS),
                "outer_forecast_end_year": max(OUTER_FORECAST_YEARS),
                "dynamic_ridge_rmse": model_rmse,
                "dynamic_ridge_mae": model_mae,
                "persistence_rmse": persistence_rmse,
                "persistence_mae": persistence_mae,
                "rmse_improvement_vs_persistence": persistence_rmse - model_rmse,
                "mae_improvement_vs_persistence": persistence_mae - model_mae,
                "forecast_qualified": is_qualified,
                "qualification_rule": "dynamic_ridge_rmse_and_mae_both_strictly_lower_than_persistence",
            }
        )
    return predictions, summaries, coefficients, qualified


def build_2026_forecasts(
    frame: list[dict[str, Any]],
    by_key: dict[tuple[str, int], dict[str, str]],
    names: dict[str, str],
    geographies: list[str],
    backtest: list[dict[str, Any]],
    qualified: dict[str, bool],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    forecasts: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    for target in TARGETS:
        selected_penalty, _ = select_penalty(frame, target)
        model = fit_ridge(frame, target, selected_penalty)
        coefficients.extend(coefficient_rows(model, target, FINAL_FORECAST_YEAR, "final_2026_fit"))
        residuals = [
            float(row["dynamic_ridge_residual"])
            for row in backtest
            if row["target_id"] == target
        ]
        q025 = quantile(residuals, 0.025)
        q975 = quantile(residuals, 0.975)
        for geography_id in geographies:
            source = by_key[(geography_id, 2025)]
            forecast_row: dict[str, Any] = {
                "regime_id": REGIME_ID,
                "geography_id": geography_id,
                "geography_name": names[geography_id],
                "target_id": target,
                "target_direction": TARGET_DIRECTIONS[target],
                "forecast_year": FINAL_FORECAST_YEAR,
                "information_cutoff_year": 2025,
                f"lag1_{target}": float_value(source, target, f"{geography_id}/2025"),
            }
            for feature in STRUCTURAL_FEATURES:
                forecast_row[f"lag1_{feature}"] = float_value(source, feature, f"{geography_id}/2025")
            point = predict(model, forecast_row)
            forecasts.append(
                {
                    "regime_id": REGIME_ID,
                    "target_id": target,
                    "target_direction": TARGET_DIRECTIONS[target],
                    "geography_id": geography_id,
                    "geography_name": names[geography_id],
                    "forecast_year": FINAL_FORECAST_YEAR,
                    "information_cutoff_year": 2025,
                    "lag1_observed_target_2025": forecast_row[f"lag1_{target}"],
                    "forecast_point": point,
                    "forecast_interval_low_empirical": point + q025,
                    "forecast_interval_high_empirical": point + q975,
                    "empirical_residual_q025": q025,
                    "empirical_residual_q975": q975,
                    "selected_penalty": selected_penalty,
                    "forecast_qualified": qualified[target],
                    "public_substantive_use_authorized": qualified[target],
                    "claim_type": "one_year_ahead_model_forecast_not_causal",
                }
            )
    if len(forecasts) != 57:
        raise ValueError(f"M19 must create 57 2026 forecast rows, got {len(forecasts)}")
    return forecasts, coefficients


def write_outputs(
    frame: list[dict[str, Any]],
    backtest: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    coefficients: list[dict[str, Any]],
    forecasts: list[dict[str, Any]],
) -> None:
    write_csv(
        MODEL_FRAME_OUT,
        [
            "regime_id",
            "geography_id",
            "geography_name",
            "target_year",
            "feature_year",
            *TARGETS,
            *[f"lag1_{target}" for target in TARGETS],
            *[f"lag1_{feature}" for feature in STRUCTURAL_FEATURES],
        ],
        frame,
    )
    write_csv(
        BACKTEST_OUT,
        [
            "regime_id",
            "target_id",
            "target_direction",
            "geography_id",
            "geography_name",
            "forecast_year",
            "information_cutoff_year",
            "observed",
            "dynamic_ridge_prediction",
            "dynamic_ridge_residual",
            "persistence_prediction",
            "persistence_residual",
            "selected_penalty",
            "training_start_year",
            "training_end_year",
            "training_row_count",
            "strictly_out_of_time",
        ],
        backtest,
    )
    write_csv(
        SUMMARY_OUT,
        [
            "regime_id",
            "target_id",
            "target_direction",
            "backtest_prediction_count",
            "outer_forecast_start_year",
            "outer_forecast_end_year",
            "dynamic_ridge_rmse",
            "dynamic_ridge_mae",
            "persistence_rmse",
            "persistence_mae",
            "rmse_improvement_vs_persistence",
            "mae_improvement_vs_persistence",
            "forecast_qualified",
            "qualification_rule",
        ],
        summaries,
    )
    write_csv(
        COEFFICIENTS_OUT,
        [
            "regime_id",
            "target_id",
            "forecast_year",
            "fit_scope",
            "selected_penalty",
            "training_start_year",
            "training_end_year",
            "training_row_count",
            "predictor",
            "standardized_coefficient",
            "interpretation",
        ],
        coefficients,
    )
    write_csv(
        FORECAST_OUT,
        [
            "regime_id",
            "target_id",
            "target_direction",
            "geography_id",
            "geography_name",
            "forecast_year",
            "information_cutoff_year",
            "lag1_observed_target_2025",
            "forecast_point",
            "forecast_interval_low_empirical",
            "forecast_interval_high_empirical",
            "empirical_residual_q025",
            "empirical_residual_q975",
            "selected_penalty",
            "forecast_qualified",
            "public_substantive_use_authorized",
            "claim_type",
        ],
        forecasts,
    )


def build_manifest(
    m10: dict[str, Any],
    gate: dict[str, Any],
    frame: list[dict[str, Any]],
    backtest: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    coefficients: list[dict[str, Any]],
    forecasts: list[dict[str, Any]],
) -> dict[str, Any]:
    qualified_targets = [row["target_id"] for row in summaries if row["forecast_qualified"]]
    blocked_targets = [row["target_id"] for row in summaries if not row["forecast_qualified"]]
    return {
        "schema": "ranah-observatory/milestone19-dynamic-forecast-engine/v1",
        "milestone": 19,
        "phase": "post_phase2_predictive_evidence_expansion",
        "criterion": "strict one-year-ahead temporal forecasting benchmarked against own-lag persistence",
        "regime_id": REGIME_ID,
        "model_family": "pooled_autoregressive_ridge",
        "geography_count": 19,
        "target_ids": TARGETS,
        "structural_feature_ids": STRUCTURAL_FEATURES,
        "include_target_lag": True,
        "model_target_years": MODEL_TARGET_YEARS,
        "outer_forecast_years": OUTER_FORECAST_YEARS,
        "final_forecast_year": FINAL_FORECAST_YEAR,
        "penalty_grid": PENALTY_GRID,
        "model_frame_row_count": len(frame),
        "backtest_prediction_count": len(backtest),
        "backtest_prediction_count_per_target": 95,
        "coefficient_diagnostic_row_count": len(coefficients),
        "forecast_2026_row_count": len(forecasts),
        "forecast_qualified_target_count": len(qualified_targets),
        "forecast_qualified_target_ids": qualified_targets,
        "forecast_blocked_target_count": len(blocked_targets),
        "forecast_blocked_target_ids": blocked_targets,
        "strictly_out_of_time_backtest": all(row["strictly_out_of_time"] for row in backtest),
        "persistence_benchmark_used": True,
        "qualification_requires_rmse_and_mae_improvement": True,
        "forecast_intervals_from_out_of_time_residuals": True,
        "posthoc_algorithm_search_performed": False,
        "causal_analysis_performed": False,
        "causal_claim_authorized": False,
        "policy_counterfactual_authorized": False,
        "forecast_is_guaranteed_future": False,
        "milestone19_complete": True,
        "inputs": {
            "m10_panel_manifest": {
                "path": str(INPUT_MANIFEST.relative_to(ROOT)),
                "sha256": sha256(INPUT_MANIFEST),
                "schema": m10.get("schema"),
            },
            "m10_wide_panel": {
                "path": str(INPUT_WIDE.relative_to(ROOT)),
                "sha256": sha256(INPUT_WIDE),
            },
            "design_gate": {
                "path": str(DESIGN_GATE.relative_to(ROOT)),
                "sha256": sha256(DESIGN_GATE),
                "schema": gate.get("schema"),
            },
            "spec": {
                "path": str(SPEC.relative_to(ROOT)),
                "sha256": sha256(SPEC),
            },
        },
        "outputs": {
            "model_frame": {"path": str(MODEL_FRAME_OUT.relative_to(ROOT)), "sha256": sha256(MODEL_FRAME_OUT)},
            "backtest_predictions": {"path": str(BACKTEST_OUT.relative_to(ROOT)), "sha256": sha256(BACKTEST_OUT)},
            "target_summary": {"path": str(SUMMARY_OUT.relative_to(ROOT)), "sha256": sha256(SUMMARY_OUT)},
            "coefficients": {"path": str(COEFFICIENTS_OUT.relative_to(ROOT)), "sha256": sha256(COEFFICIENTS_OUT)},
            "forecast_2026": {"path": str(FORECAST_OUT.relative_to(ROOT)), "sha256": sha256(FORECAST_OUT)},
        },
        "target_results": summaries,
    }


def main() -> None:
    m10, gate = validate_prefit_contract()
    by_key, names, geographies = load_wide()
    frame = build_model_frame(by_key, names, geographies)
    backtest, summaries, outer_coefficients, qualified = run_backtest(frame)
    forecasts, final_coefficients = build_2026_forecasts(
        frame,
        by_key,
        names,
        geographies,
        backtest,
        qualified,
    )
    coefficients = [*outer_coefficients, *final_coefficients]
    write_outputs(frame, backtest, summaries, coefficients, forecasts)
    manifest = build_manifest(m10, gate, frame, backtest, summaries, coefficients, forecasts)
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "milestone19_complete": manifest["milestone19_complete"],
        "forecast_qualified_target_ids": manifest["forecast_qualified_target_ids"],
        "forecast_blocked_target_ids": manifest["forecast_blocked_target_ids"],
        "backtest_prediction_count": manifest["backtest_prediction_count"],
        "forecast_2026_row_count": manifest["forecast_2026_row_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
