#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
INPUT_WIDE = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"
M10_MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
DESIGN_GATE = ROOT / "data/manifests/milestone22_design_gate.json"
SPEC = ROOT / "research/MILESTONE22_HIERARCHICAL_SOCIOECONOMIC_TRAJECTORY_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/hierarchical_trajectory_v1"
MODEL_FRAME_OUT = OUT_DIR / "m22-model-frame.csv"
OUTER_PREDICTIONS_OUT = OUT_DIR / "m22-outer-predictions.csv"
INDICATOR_SUMMARY_OUT = OUT_DIR / "m22-indicator-summary.csv"
TRAJECTORIES_OUT = OUT_DIR / "m22-geography-trajectories.csv"
LOO_SLOPES_OUT = OUT_DIR / "m22-loo-slopes.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone22_hierarchical_socioeconomic_trajectory.json"

REGIME_ID = "sumbar_current_kabkota_hierarchical_trajectory_2018_2025_v1"
SOURCE_REGIME_ID = "sumbar_current_kabkota_2018_2025_v1"
YEARS = list(range(2018, 2026))
TIME_CENTER = 2021.5
TIME_SCALE = 2.5
INDICATORS = [
    "expected_years_schooling",
    "mean_years_schooling",
    "labor_force_participation",
    "unemployment_rate",
    "poverty_rate",
    "real_grdp_growth",
    "rice_yield",
]
FAVORABLE_DIRECTION = {
    "expected_years_schooling": "higher_is_generally_favorable",
    "mean_years_schooling": "higher_is_generally_favorable",
    "labor_force_participation": "higher_is_generally_favorable_with_context",
    "unemployment_rate": "lower_is_generally_favorable",
    "poverty_rate": "lower_is_generally_favorable",
    "real_grdp_growth": "higher_rate_is_generally_favorable_but_slope_is_not_structural_acceleration",
    "rice_yield": "higher_is_generally_favorable_with_context",
}
PENALTY_GRID = [0.01, 0.1, 1.0, 10.0, 100.0]
DIRECTION_RETENTION_THRESHOLD = 0.875


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
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def rmse(errors: list[float]) -> float:
    return math.sqrt(mean([error * error for error in errors]))


def mae(errors: list[float]) -> float:
    return mean([abs(error) for error in errors])


def sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def z_year(year: int) -> float:
    return (year - TIME_CENTER) / TIME_SCALE


def inv2(a00: float, a01: float, a11: float) -> tuple[float, float, float]:
    determinant = a00 * a11 - a01 * a01
    if abs(determinant) < 1e-14:
        raise ValueError("singular 2x2 system")
    return a11 / determinant, -a01 / determinant, a00 / determinant


def mat2_vec(m00: float, m01: float, m11: float, v0: float, v1: float) -> tuple[float, float]:
    return m00 * v0 + m01 * v1, m01 * v0 + m11 * v1


def fit_hierarchy(rows: list[dict[str, Any]], geographies: list[str], penalty: float) -> dict[str, Any]:
    if penalty <= 0.0:
        raise ValueError("hierarchical penalty must be positive")
    by_geo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_geo[str(row["geography_id"])].append(row)
    if sorted(by_geo) != geographies:
        raise ValueError("hierarchical fit requires every geography")

    stats: dict[str, dict[str, float]] = {}
    global_a00 = 0.0
    global_a01 = 0.0
    global_a11 = 0.0
    global_c0 = 0.0
    global_c1 = 0.0
    schur00 = 0.0
    schur01 = 0.0
    schur11 = 0.0
    rhs0 = 0.0
    rhs1 = 0.0

    for geography_id in geographies:
        group = by_geo[geography_id]
        a00 = float(len(group))
        a01 = sum(float(row["z_time"]) for row in group)
        a11 = sum(float(row["z_time"]) ** 2 for row in group)
        c0 = sum(float(row["value"]) for row in group)
        c1 = sum(float(row["z_time"]) * float(row["value"]) for row in group)
        b00, b01, b11 = inv2(a00 + penalty, a01, a11 + penalty)

        # A * B where A=[[a00,a01],[a01,a11]], B symmetric.
        ab00 = a00 * b00 + a01 * b01
        ab01 = a00 * b01 + a01 * b11
        ab10 = a01 * b00 + a11 * b01
        ab11 = a01 * b01 + a11 * b11
        # A*B*A
        aba00 = ab00 * a00 + ab01 * a01
        aba01 = ab00 * a01 + ab01 * a11
        aba11 = ab10 * a01 + ab11 * a11
        # A*B*c
        bc0, bc1 = mat2_vec(b00, b01, b11, c0, c1)
        abc0 = a00 * bc0 + a01 * bc1
        abc1 = a01 * bc0 + a11 * bc1

        global_a00 += a00
        global_a01 += a01
        global_a11 += a11
        global_c0 += c0
        global_c1 += c1
        schur00 += a00 - aba00
        schur01 += a01 - aba01
        schur11 += a11 - aba11
        rhs0 += c0 - abc0
        rhs1 += c1 - abc1
        stats[geography_id] = {
            "a00": a00,
            "a01": a01,
            "a11": a11,
            "c0": c0,
            "c1": c1,
            "b00": b00,
            "b01": b01,
            "b11": b11,
        }

    q00, q01, q11 = inv2(schur00, schur01, schur11)
    beta0, beta1 = mat2_vec(q00, q01, q11, rhs0, rhs1)

    effects: dict[str, dict[str, float]] = {}
    for geography_id in geographies:
        s = stats[geography_id]
        residual_c0 = s["c0"] - (s["a00"] * beta0 + s["a01"] * beta1)
        residual_c1 = s["c1"] - (s["a01"] * beta0 + s["a11"] * beta1)
        a_dev, b_dev = mat2_vec(s["b00"], s["b01"], s["b11"], residual_c0, residual_c1)
        effects[geography_id] = {
            "intercept_deviation": a_dev,
            "slope_deviation_z": b_dev,
            "intercept": beta0 + a_dev,
            "slope_z": beta1 + b_dev,
            "slope_per_year": (beta1 + b_dev) / TIME_SCALE,
        }
    return {
        "penalty": penalty,
        "fixed_intercept": beta0,
        "fixed_slope_z": beta1,
        "fixed_slope_per_year": beta1 / TIME_SCALE,
        "effects": effects,
    }


def predict_hierarchy(model: dict[str, Any], geography_id: str, year: int) -> float:
    effect = model["effects"][geography_id]
    return float(effect["intercept"]) + float(effect["slope_z"]) * z_year(year)


def fit_independent_ols(rows: list[dict[str, Any]], geographies: list[str]) -> dict[str, dict[str, float]]:
    by_geo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_geo[str(row["geography_id"])].append(row)
    models: dict[str, dict[str, float]] = {}
    for geography_id in geographies:
        group = by_geo[geography_id]
        a00 = float(len(group))
        a01 = sum(float(row["z_time"]) for row in group)
        a11 = sum(float(row["z_time"]) ** 2 for row in group)
        c0 = sum(float(row["value"]) for row in group)
        c1 = sum(float(row["z_time"]) * float(row["value"]) for row in group)
        q00, q01, q11 = inv2(a00, a01, a11)
        intercept, slope_z = mat2_vec(q00, q01, q11, c0, c1)
        models[geography_id] = {
            "intercept": intercept,
            "slope_z": slope_z,
            "slope_per_year": slope_z / TIME_SCALE,
        }
    return models


def predict_ols(models: dict[str, dict[str, float]], geography_id: str, year: int) -> float:
    model = models[geography_id]
    return model["intercept"] + model["slope_z"] * z_year(year)


def select_penalty(rows: list[dict[str, Any]], geographies: list[str], validation_years: list[int]) -> tuple[float, list[dict[str, float]]]:
    diagnostics: list[dict[str, float]] = []
    for penalty in PENALTY_GRID:
        errors: list[float] = []
        for held_year in validation_years:
            training = [row for row in rows if int(row["analysis_year"]) != held_year]
            validation = [row for row in rows if int(row["analysis_year"]) == held_year]
            model = fit_hierarchy(training, geographies, penalty)
            for row in validation:
                prediction = predict_hierarchy(model, str(row["geography_id"]), held_year)
                errors.append(prediction - float(row["value"]))
        diagnostics.append({"penalty": penalty, "rmse": rmse(errors), "mae": mae(errors)})
    selected = min(diagnostics, key=lambda row: (row["rmse"], -row["penalty"]))
    return float(selected["penalty"]), diagnostics


def validate_inputs() -> tuple[list[dict[str, str]], list[str], dict[str, Any], dict[str, Any]]:
    m10 = json.loads(M10_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    if m10.get("schema") != "ranah-observatory/milestone10-analytical-panel/v1" or m10.get("milestone10_complete") is not True:
        raise ValueError("M22 requires completed M10")
    if m10.get("regime_id") != SOURCE_REGIME_ID:
        raise ValueError("M22 M10 regime drift")
    if m10.get("geography_count") != 19 or m10.get("wide_row_count") != 152:
        raise ValueError("M22 M10 footprint drift")
    complete = set(m10.get("complete_2018_2025_indicator_ids", []))
    if not set(INDICATORS).issubset(complete):
        raise ValueError("M22 selected indicator lost complete M10 coverage")
    if "annual_rainfall" not in complete:
        raise ValueError("M22 expects annual_rainfall to be the only complete indicator intentionally routed to M20-M21")

    locked = {
        "schema": "ranah-observatory/milestone22-design-gate/v1",
        "design_locked_before_model_fit": True,
        "input_regime_id": SOURCE_REGIME_ID,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "geography_count": 19,
        "indicator_ids": INDICATORS,
        "indicator_count": 7,
        "rows_per_indicator": 152,
        "model_family": "hierarchical_random_intercept_random_slope_penalized_least_squares",
        "time_center": TIME_CENTER,
        "time_scale_years": TIME_SCALE,
        "random_effect_penalty_grid": PENALTY_GRID,
        "outer_validation": "leave_one_calendar_year_out",
        "inner_validation": "leave_one_calendar_year_out_within_outer_training",
        "penalty_selection_metric": "rmse",
        "benchmark_model": "independent_geography_ols_linear_trend",
        "qualification_requires_rmse_and_mae_improvement": True,
        "loo_direction_retention_threshold": DIRECTION_RETENTION_THRESHOLD,
        "posthoc_indicator_selection_authorized": False,
        "posthoc_model_search_authorized": False,
    }
    for key, expected in locked.items():
        if gate.get(key) != expected:
            raise ValueError(f"M22 design gate drift: {key}")

    wide = read_csv(INPUT_WIDE)
    if len(wide) != 152:
        raise ValueError(f"M22 requires 152 M10 wide rows, got {len(wide)}")
    keys: set[tuple[str, int]] = set()
    names: dict[str, str] = {}
    for row in wide:
        geography_id = row["geography_id"]
        year = int(row["analysis_year"])
        if row["regime_id"] != SOURCE_REGIME_ID:
            raise ValueError("M22 source regime drift in wide panel")
        if year not in YEARS:
            raise ValueError("M22 source year drift")
        key = (geography_id, year)
        if key in keys:
            raise ValueError(f"duplicate M22 source key {key}")
        keys.add(key)
        names[geography_id] = row["geography_name"]
        for indicator in INDICATORS:
            raw = row.get(indicator, "")
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(f"missing/non-numeric {indicator} for {key}") from exc
            if not math.isfinite(value):
                raise ValueError(f"non-finite {indicator} for {key}")
    geographies = sorted(names)
    if len(geographies) != 19:
        raise ValueError("M22 requires exact 19 geographies")
    for geography_id in geographies:
        if {year for geo, year in keys if geo == geography_id} != set(YEARS):
            raise ValueError(f"M22 incomplete years for {geography_id}")
    return wide, geographies, m10, gate


def build_model_frame(wide: list[dict[str, str]]) -> list[dict[str, Any]]:
    frame: list[dict[str, Any]] = []
    for source in sorted(wide, key=lambda row: (row["geography_id"], int(row["analysis_year"]))):
        year = int(source["analysis_year"])
        for indicator in INDICATORS:
            frame.append({
                "regime_id": REGIME_ID,
                "indicator_id": indicator,
                "geography_id": source["geography_id"],
                "geography_name": source["geography_name"],
                "analysis_year": year,
                "z_time": z_year(year),
                "value": float(source[indicator]),
                "favorable_direction_semantics": FAVORABLE_DIRECTION[indicator],
            })
    if len(frame) != 7 * 19 * 8:
        raise ValueError("M22 model-frame footprint drift")
    return frame


def build_outputs() -> dict[str, Any]:
    wide, geographies, m10, gate = validate_inputs()
    frame = build_model_frame(wide)
    by_indicator: dict[str, list[dict[str, Any]]] = {
        indicator: [row for row in frame if row["indicator_id"] == indicator]
        for indicator in INDICATORS
    }

    outer_predictions: list[dict[str, Any]] = []
    outer_slopes: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []

    for indicator in INDICATORS:
        rows = by_indicator[indicator]
        hierarchical_errors: list[float] = []
        benchmark_errors: list[float] = []
        slope_by_geo: dict[str, list[float]] = {geo: [] for geo in geographies}

        for outer_year in YEARS:
            outer_training = [row for row in rows if int(row["analysis_year"]) != outer_year]
            outer_test = [row for row in rows if int(row["analysis_year"]) == outer_year]
            inner_years = [year for year in YEARS if year != outer_year]
            selected_penalty, _ = select_penalty(outer_training, geographies, inner_years)
            hierarchical = fit_hierarchy(outer_training, geographies, selected_penalty)
            benchmark = fit_independent_ols(outer_training, geographies)

            for geography_id in geographies:
                slope = float(hierarchical["effects"][geography_id]["slope_per_year"])
                slope_by_geo[geography_id].append(slope)
                outer_slopes.append({
                    "indicator_id": indicator,
                    "geography_id": geography_id,
                    "outer_held_year": outer_year,
                    "selected_penalty": selected_penalty,
                    "hierarchical_slope_per_year": slope,
                })

            for row in sorted(outer_test, key=lambda item: item["geography_id"]):
                geography_id = str(row["geography_id"])
                observed = float(row["value"])
                hp = predict_hierarchy(hierarchical, geography_id, outer_year)
                bp = predict_ols(benchmark, geography_id, outer_year)
                h_error = hp - observed
                b_error = bp - observed
                hierarchical_errors.append(h_error)
                benchmark_errors.append(b_error)
                outer_predictions.append({
                    "indicator_id": indicator,
                    "geography_id": geography_id,
                    "geography_name": row["geography_name"],
                    "outer_held_year": outer_year,
                    "training_year_count": 7,
                    "selected_penalty": selected_penalty,
                    "observed_value": observed,
                    "hierarchical_prediction": hp,
                    "hierarchical_error": h_error,
                    "independent_ols_prediction": bp,
                    "independent_ols_error": b_error,
                })

        hierarchical_rmse = rmse(hierarchical_errors)
        hierarchical_mae = mae(hierarchical_errors)
        benchmark_rmse = rmse(benchmark_errors)
        benchmark_mae = mae(benchmark_errors)
        qualified = hierarchical_rmse < benchmark_rmse and hierarchical_mae < benchmark_mae

        final_penalty, final_penalty_diagnostics = select_penalty(rows, geographies, YEARS)
        full_model = fit_hierarchy(rows, geographies, final_penalty)
        final_penalty_diagnostic = next(row for row in final_penalty_diagnostics if row["penalty"] == final_penalty)

        persistent_increase_count = 0
        persistent_decrease_count = 0
        robust_count = 0
        by_geo_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_geo_source[str(row["geography_id"])].append(row)

        for geography_id in geographies:
            group = sorted(by_geo_source[geography_id], key=lambda row: int(row["analysis_year"]))
            full_slope = float(full_model["effects"][geography_id]["slope_per_year"])
            loo = slope_by_geo[geography_id]
            full_sign = sign(full_slope)
            same_direction = sum(full_sign != 0 and sign(value) == full_sign for value in loo) / len(loo)
            loo_min = min(loo)
            loo_max = max(loo)
            if qualified and full_slope > 0.0 and same_direction >= DIRECTION_RETENTION_THRESHOLD and loo_min > 0.0:
                classification = "persistent_increase"
                persistent_increase_count += 1
                robust_count += 1
            elif qualified and full_slope < 0.0 and same_direction >= DIRECTION_RETENTION_THRESHOLD and loo_max < 0.0:
                classification = "persistent_decrease"
                persistent_decrease_count += 1
                robust_count += 1
            else:
                classification = "trajectory_not_robust"

            observed_2018 = float(next(row["value"] for row in group if int(row["analysis_year"]) == 2018))
            observed_2025 = float(next(row["value"] for row in group if int(row["analysis_year"]) == 2025))
            fitted = [
                predict_hierarchy(full_model, geography_id, int(row["analysis_year"]))
                for row in group
            ]
            observed = [float(row["value"]) for row in group]
            geo_errors = [pred - actual for pred, actual in zip(fitted, observed)]
            trajectory_rows.append({
                "indicator_id": indicator,
                "geography_id": geography_id,
                "geography_name": group[0]["geography_name"],
                "favorable_direction_semantics": FAVORABLE_DIRECTION[indicator],
                "indicator_hierarchical_trajectory_qualified": qualified,
                "selected_final_penalty": final_penalty,
                "observed_2018": observed_2018,
                "observed_2025": observed_2025,
                "observed_change_2018_2025": observed_2025 - observed_2018,
                "shared_slope_per_year": full_model["fixed_slope_per_year"],
                "geography_slope_deviation_per_year": full_slope - float(full_model["fixed_slope_per_year"]),
                "hierarchical_slope_per_year": full_slope,
                "fitted_2018": predict_hierarchy(full_model, geography_id, 2018),
                "fitted_2025": predict_hierarchy(full_model, geography_id, 2025),
                "geography_full_fit_rmse": rmse(geo_errors),
                "loo_min_slope_per_year": loo_min,
                "loo_max_slope_per_year": loo_max,
                "loo_same_direction_retention": same_direction,
                "stability_envelope_excludes_zero": loo_min > 0.0 or loo_max < 0.0,
                "trajectory_classification": classification,
                "stability_envelope_is_confidence_interval": False,
                "causal_claim_authorized": False,
                "guaranteed_future_trajectory_authorized": False,
                "historical_boundary_continuity_claimed": False,
            })

        summary_rows.append({
            "indicator_id": indicator,
            "favorable_direction_semantics": FAVORABLE_DIRECTION[indicator],
            "outer_prediction_count": len([row for row in outer_predictions if row["indicator_id"] == indicator]),
            "hierarchical_rmse": hierarchical_rmse,
            "hierarchical_mae": hierarchical_mae,
            "independent_ols_rmse": benchmark_rmse,
            "independent_ols_mae": benchmark_mae,
            "rmse_improvement_vs_independent_ols": benchmark_rmse - hierarchical_rmse,
            "mae_improvement_vs_independent_ols": benchmark_mae - hierarchical_mae,
            "hierarchical_trajectory_qualified": qualified,
            "selected_final_penalty": final_penalty,
            "final_penalty_loo_rmse": final_penalty_diagnostic["rmse"],
            "final_penalty_loo_mae": final_penalty_diagnostic["mae"],
            "shared_slope_per_year": full_model["fixed_slope_per_year"],
            "persistent_increase_count": persistent_increase_count,
            "persistent_decrease_count": persistent_decrease_count,
            "robust_trajectory_count": robust_count,
        })

    model_frame_fields = [
        "regime_id", "indicator_id", "geography_id", "geography_name", "analysis_year",
        "z_time", "value", "favorable_direction_semantics",
    ]
    prediction_fields = [
        "indicator_id", "geography_id", "geography_name", "outer_held_year", "training_year_count",
        "selected_penalty", "observed_value", "hierarchical_prediction", "hierarchical_error",
        "independent_ols_prediction", "independent_ols_error",
    ]
    summary_fields = list(summary_rows[0].keys())
    trajectory_fields = list(trajectory_rows[0].keys())
    loo_fields = ["indicator_id", "geography_id", "outer_held_year", "selected_penalty", "hierarchical_slope_per_year"]

    write_csv(MODEL_FRAME_OUT, model_frame_fields, frame)
    write_csv(OUTER_PREDICTIONS_OUT, prediction_fields, outer_predictions)
    write_csv(INDICATOR_SUMMARY_OUT, summary_fields, summary_rows)
    write_csv(TRAJECTORIES_OUT, trajectory_fields, trajectory_rows)
    write_csv(LOO_SLOPES_OUT, loo_fields, outer_slopes)

    qualified_ids = [row["indicator_id"] for row in summary_rows if row["hierarchical_trajectory_qualified"]]
    classification_counts: dict[str, int] = defaultdict(int)
    for row in trajectory_rows:
        classification_counts[str(row["trajectory_classification"])] += 1

    manifest = {
        "schema": "ranah-observatory/milestone22-hierarchical-socioeconomic-trajectory/v1",
        "milestone": 22,
        "phase": "post_phase2_socioeconomic_trajectory_expansion",
        "criterion": "partial-pooled modern socioeconomic trajectories validated out of calendar year against independent geography trends",
        "milestone22_complete": True,
        "regime_id": REGIME_ID,
        "source_regime_id": SOURCE_REGIME_ID,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "geography_count": 19,
        "indicator_count": 7,
        "indicator_ids": INDICATORS,
        "model_frame_row_count": len(frame),
        "outer_prediction_count": len(outer_predictions),
        "loo_slope_row_count": len(outer_slopes),
        "geography_trajectory_row_count": len(trajectory_rows),
        "hierarchical_trajectory_qualified_indicator_count": len(qualified_ids),
        "hierarchical_trajectory_qualified_indicator_ids": qualified_ids,
        "trajectory_classification_counts": dict(sorted(classification_counts.items())),
        "model_family": "hierarchical_random_intercept_random_slope_penalized_least_squares",
        "random_effect_penalty_grid": PENALTY_GRID,
        "outer_validation": "leave_one_calendar_year_out",
        "inner_validation": "leave_one_calendar_year_out_within_outer_training",
        "benchmark_model": "independent_geography_ols_linear_trend",
        "qualification_requires_rmse_and_mae_improvement": True,
        "loo_direction_retention_threshold": DIRECTION_RETENTION_THRESHOLD,
        "stability_envelope_is_confidence_interval": False,
        "posthoc_indicator_selection_performed": False,
        "posthoc_model_search_performed": False,
        "causal_analysis_performed": False,
        "policy_effect_estimated": False,
        "historical_boundary_continuity_claimed": False,
        "guaranteed_future_trajectory_authorized": False,
        "indicator_results": summary_rows,
        "inputs": {
            "m10_wide_panel": {"path": str(INPUT_WIDE.relative_to(ROOT)), "sha256": sha256(INPUT_WIDE)},
            "m10_manifest": {"path": str(M10_MANIFEST.relative_to(ROOT)), "sha256": sha256(M10_MANIFEST)},
            "design_gate": {"path": str(DESIGN_GATE.relative_to(ROOT)), "sha256": sha256(DESIGN_GATE)},
            "spec": {"path": str(SPEC.relative_to(ROOT)), "sha256": sha256(SPEC)},
        },
        "outputs": {
            "model_frame": {"path": str(MODEL_FRAME_OUT.relative_to(ROOT)), "sha256": sha256(MODEL_FRAME_OUT)},
            "outer_predictions": {"path": str(OUTER_PREDICTIONS_OUT.relative_to(ROOT)), "sha256": sha256(OUTER_PREDICTIONS_OUT)},
            "indicator_summary": {"path": str(INDICATOR_SUMMARY_OUT.relative_to(ROOT)), "sha256": sha256(INDICATOR_SUMMARY_OUT)},
            "geography_trajectories": {"path": str(TRAJECTORIES_OUT.relative_to(ROOT)), "sha256": sha256(TRAJECTORIES_OUT)},
            "loo_slopes": {"path": str(LOO_SLOPES_OUT.relative_to(ROOT)), "sha256": sha256(LOO_SLOPES_OUT)},
        },
        "upstream_m10_complete": m10["milestone10_complete"],
        "design_gate_schema": gate["schema"],
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = build_outputs()
    print(json.dumps({
        "milestone22_complete": manifest["milestone22_complete"],
        "qualified_indicator_count": manifest["hierarchical_trajectory_qualified_indicator_count"],
        "trajectory_classification_counts": manifest["trajectory_classification_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
