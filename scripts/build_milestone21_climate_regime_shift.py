#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv"
M20_MANIFEST = ROOT / "data/manifests/milestone20_historical_climate_trend.json"
DESIGN = ROOT / "data/manifests/milestone21_design_gate.json"
SPEC = ROOT / "research/MILESTONE21_CLIMATE_REGIME_SHIFT_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/climate_regime_shift_v1"
BACKTEST_OUT = OUT_DIR / "m21-rolling-backtest.csv"
CANDIDATES_OUT = OUT_DIR / "m21-breakpoint-candidates.csv"
FULL_OUT = OUT_DIR / "m21-full-series-regime.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone21_climate_regime_shift.json"

START_YEAR = 1981
END_YEAR = 2025
OUTER_START = 2006
OUTER_END = 2025
MIN_SEGMENT = 10
STABILITY_WINDOW = 3
STABILITY_THRESHOLD = 0.75


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


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


def sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires values")
    return float(statistics.median(values))


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def quantile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if not ordered or not 0.0 <= p <= 1.0:
        raise ValueError("invalid quantile")
    if len(ordered) == 1:
        return ordered[0]
    pos = p * (len(ordered) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    w = pos - lo
    return ordered[lo] * (1.0 - w) + ordered[hi] * w


def rmse(errors: list[float]) -> float:
    return math.sqrt(mean([error * error for error in errors]))


def mae(errors: list[float]) -> float:
    return mean([abs(error) for error in errors])


def fit_theil_sen(years: list[int], values: list[float]) -> dict[str, float]:
    if len(years) != len(values) or len(years) < 2:
        raise ValueError("invalid Theil-Sen input")
    slopes: list[float] = []
    for i in range(len(years) - 1):
        for j in range(i + 1, len(years)):
            dx = years[j] - years[i]
            if dx <= 0:
                raise ValueError("years must be strictly increasing")
            slopes.append((values[j] - values[i]) / dx)
    slope = median(slopes)
    intercept = median([value - slope * year for year, value in zip(years, values)])
    predictions = [intercept + slope * year for year in years]
    errors = [pred - actual for pred, actual in zip(predictions, values)]
    return {
        "slope": slope,
        "intercept": intercept,
        "training_mae": mae(errors),
        "training_rmse": rmse(errors),
    }


def predict(model: dict[str, float], year: int) -> float:
    return model["intercept"] + model["slope"] * year


def fit_segmented(years: list[int], values: list[float], break_year: int) -> dict[str, Any]:
    pre = [(year, value) for year, value in zip(years, values) if year <= break_year]
    post = [(year, value) for year, value in zip(years, values) if year > break_year]
    if len(pre) < MIN_SEGMENT or len(post) < MIN_SEGMENT:
        raise ValueError("segment shorter than preregistered minimum")
    pre_model = fit_theil_sen([y for y, _ in pre], [v for _, v in pre])
    post_model = fit_theil_sen([y for y, _ in post], [v for _, v in post])
    errors: list[float] = []
    for year, actual in zip(years, values):
        model = pre_model if year <= break_year else post_model
        errors.append(predict(model, year) - actual)
    return {
        "break_year": break_year,
        "pre_n": len(pre),
        "post_n": len(post),
        "pre_slope": pre_model["slope"],
        "pre_intercept": pre_model["intercept"],
        "post_slope": post_model["slope"],
        "post_intercept": post_model["intercept"],
        "training_mae": mae(errors),
        "training_rmse": rmse(errors),
    }


def candidate_break_years(years: list[int]) -> list[int]:
    n = len(years)
    if n < 2 * MIN_SEGMENT:
        raise ValueError("insufficient years for segmented model")
    # split index t means first segment has t observations and break is years[t-1].
    return [years[t - 1] for t in range(MIN_SEGMENT, n - MIN_SEGMENT + 1)]


def select_segmented(years: list[int], values: list[float]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidates = [fit_segmented(years, values, break_year) for break_year in candidate_break_years(years)]
    selected = min(candidates, key=lambda row: (row["training_mae"], row["break_year"]))
    return selected, candidates


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: (item[1], item[0]))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def pettitt_restricted(years: list[int], values: list[float]) -> dict[str, float | int]:
    n = len(values)
    ranks = average_ranks(values)
    choices: list[tuple[float, int, float]] = []
    for t in range(MIN_SEGMENT, n - MIN_SEGMENT + 1):
        u_t = 2.0 * sum(ranks[:t]) - t * (n + 1.0)
        choices.append((abs(u_t), years[t - 1], u_t))
    k, break_year, signed_u = max(choices, key=lambda item: (item[0], -item[1]))
    approx_p = min(1.0, 2.0 * math.exp((-6.0 * k * k) / (n**3 + n**2)))
    return {
        "pettitt_k": k,
        "pettitt_break_year": break_year,
        "pettitt_signed_u": signed_u,
        "pettitt_approx_p": approx_p,
    }


def validate_inputs() -> tuple[list[int], list[float], dict[str, Any], dict[str, Any]]:
    manifest = json.loads(M20_MANIFEST.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone20-historical-climate-trend/v1":
        raise ValueError("M21 requires M20 manifest v1")
    if manifest.get("milestone20_complete") is not True:
        raise ValueError("M21 requires complete M20")
    if manifest.get("regional_public_claim_authorized") is not False:
        raise ValueError("M21 is preregistered for the M20 non-monotonic regional result")
    if manifest.get("source_contract", {}).get("claim_type") != "model_estimate":
        raise ValueError("M21 source semantics drift")
    locked = {
        "schema": "ranah-observatory/milestone21-design-gate/v1",
        "design_locked_before_model_fit": True,
        "input_start_year": START_YEAR,
        "input_end_year": END_YEAR,
        "input_year_count": 45,
        "outer_forecast_start_year": OUTER_START,
        "outer_forecast_end_year": OUTER_END,
        "outer_forecast_count": 20,
        "minimum_segment_years": MIN_SEGMENT,
        "breakpoint_selection_loss": "training_mae",
        "breakpoint_stability_window_years": STABILITY_WINDOW,
        "breakpoint_stability_fraction_threshold": STABILITY_THRESHOLD,
        "posthoc_algorithm_search_authorized": False,
    }
    for key, expected in locked.items():
        if design.get(key) != expected:
            raise ValueError(f"M21 design drift: {key}")

    rows = read_csv(INPUT)
    if len(rows) != 45:
        raise ValueError(f"M21 expects 45 regional annual rows, got {len(rows)}")
    years: list[int] = []
    values: list[float] = []
    for row in rows:
        year = int(row["analysis_year"])
        value = float(row["unweighted_mean_rainfall_mm"])
        if int(row["geography_count"]) != 19:
            raise ValueError("M21 regional geography count drift")
        if row["claim_type"] != "model_estimate_spatial_mean":
            raise ValueError("M21 claim type drift")
        if row["spatial_frame"] != "fixed_current_boundary_june_2026":
            raise ValueError("M21 spatial frame drift")
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("invalid regional rainfall value")
        years.append(year)
        values.append(value)
    if years != list(range(START_YEAR, END_YEAR + 1)):
        raise ValueError("M21 annual sequence drift")
    return years, values, manifest, design


def build_outputs() -> dict[str, Any]:
    years, values, m20, design = validate_inputs()

    backtest_rows: list[dict[str, Any]] = []
    selected_breaks: list[int] = []
    for forecast_year in range(OUTER_START, OUTER_END + 1):
        train = [(year, value) for year, value in zip(years, values) if year < forecast_year]
        actual = dict(zip(years, values))[forecast_year]
        train_years = [y for y, _ in train]
        train_values = [v for _, v in train]
        single = fit_theil_sen(train_years, train_values)
        segmented, _ = select_segmented(train_years, train_values)
        single_pred = predict(single, forecast_year)
        segmented_pred = segmented["post_intercept"] + segmented["post_slope"] * forecast_year
        selected_breaks.append(int(segmented["break_year"]))
        backtest_rows.append({
            "forecast_year": forecast_year,
            "training_start_year": train_years[0],
            "training_end_year": train_years[-1],
            "training_year_count": len(train_years),
            "selected_break_year": segmented["break_year"],
            "pre_segment_year_count": segmented["pre_n"],
            "post_segment_year_count": segmented["post_n"],
            "pre_slope_mm_per_year": segmented["pre_slope"],
            "post_slope_mm_per_year": segmented["post_slope"],
            "single_slope_mm_per_year": single["slope"],
            "observed_rainfall_mm": actual,
            "single_trend_prediction_mm": single_pred,
            "segmented_prediction_mm": segmented_pred,
            "single_error_mm": single_pred - actual,
            "segmented_error_mm": segmented_pred - actual,
        })

    single_errors = [float(row["single_error_mm"]) for row in backtest_rows]
    segmented_errors = [float(row["segmented_error_mm"]) for row in backtest_rows]
    single_rmse = rmse(single_errors)
    single_mae = mae(single_errors)
    segmented_rmse = rmse(segmented_errors)
    segmented_mae = mae(segmented_errors)
    predictive_qualified = segmented_rmse < single_rmse and segmented_mae < single_mae

    median_break = median([float(year) for year in selected_breaks])
    q25 = quantile([float(year) for year in selected_breaks], 0.25)
    q75 = quantile([float(year) for year in selected_breaks], 0.75)
    stability_fraction = sum(abs(year - median_break) <= STABILITY_WINDOW for year in selected_breaks) / len(selected_breaks)
    rolling_stability_pass = stability_fraction >= STABILITY_THRESHOLD

    full_segmented, full_candidates = select_segmented(years, values)
    full_single = fit_theil_sen(years, values)
    full_break = int(full_segmented["break_year"])
    full_break_close = abs(full_break - median_break) <= STABILITY_WINDOW
    opposite_slopes = sign(float(full_segmented["pre_slope"])) != 0 and sign(float(full_segmented["post_slope"])) == -sign(float(full_segmented["pre_slope"]))
    pettitt = pettitt_restricted(years, values)

    public_authorized = predictive_qualified and rolling_stability_pass and full_break_close and opposite_slopes
    classification = "predictively_supported_trend_regime_shift" if public_authorized else "regime_shift_not_qualified"

    candidate_rows: list[dict[str, Any]] = []
    for row in full_candidates:
        candidate_rows.append({
            "break_year": row["break_year"],
            "pre_segment_year_count": row["pre_n"],
            "post_segment_year_count": row["post_n"],
            "pre_slope_mm_per_year": row["pre_slope"],
            "post_slope_mm_per_year": row["post_slope"],
            "training_mae_mm": row["training_mae"],
            "training_rmse_mm": row["training_rmse"],
            "selected_full_series_break": int(row["break_year"]) == full_break,
        })

    full_rows = [{
        "series_id": "sumbar_current_boundary_unweighted_mean_rainfall",
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "year_count": len(years),
        "single_slope_mm_per_year": full_single["slope"],
        "single_training_mae_mm": full_single["training_mae"],
        "single_training_rmse_mm": full_single["training_rmse"],
        "selected_break_year": full_break,
        "pre_segment_year_count": full_segmented["pre_n"],
        "post_segment_year_count": full_segmented["post_n"],
        "pre_slope_mm_per_year": full_segmented["pre_slope"],
        "post_slope_mm_per_year": full_segmented["post_slope"],
        "segmented_training_mae_mm": full_segmented["training_mae"],
        "segmented_training_rmse_mm": full_segmented["training_rmse"],
        "outer_forecast_count": len(backtest_rows),
        "single_backtest_rmse_mm": single_rmse,
        "single_backtest_mae_mm": single_mae,
        "segmented_backtest_rmse_mm": segmented_rmse,
        "segmented_backtest_mae_mm": segmented_mae,
        "predictive_qualification_pass": predictive_qualified,
        "rolling_median_break_year": median_break,
        "rolling_break_q25_year": q25,
        "rolling_break_q75_year": q75,
        "rolling_break_within_3y_fraction": stability_fraction,
        "rolling_break_stability_pass": rolling_stability_pass,
        "full_break_within_3y_of_rolling_median": full_break_close,
        "pre_post_slopes_opposite_nonzero": opposite_slopes,
        "pettitt_break_year": pettitt["pettitt_break_year"],
        "pettitt_k": pettitt["pettitt_k"],
        "pettitt_approx_p": pettitt["pettitt_approx_p"],
        "pettitt_role": "secondary_diagnostic_only",
        "classification": classification,
        "public_claim_authorized": public_authorized,
        "claim_type": "model_estimate_spatial_mean",
        "station_observation_equivalence": False,
        "climate_change_attribution_performed": False,
        "causal_analysis_performed": False,
        "historical_boundary_continuity_claimed": False,
        "spatial_frame": "fixed_current_boundary_june_2026",
    }]

    backtest_fields = list(backtest_rows[0].keys())
    candidate_fields = list(candidate_rows[0].keys())
    full_fields = list(full_rows[0].keys())
    write_csv(BACKTEST_OUT, backtest_fields, backtest_rows)
    write_csv(CANDIDATES_OUT, candidate_fields, candidate_rows)
    write_csv(FULL_OUT, full_fields, full_rows)

    manifest = {
        "schema": "ranah-observatory/milestone21-climate-regime-shift/v1",
        "milestone": 21,
        "phase": "post_phase2_historical_climate_evidence_expansion",
        "criterion": "single-break robust trend regime evaluated by strict rolling-origin out-of-time performance and breakpoint stability",
        "milestone21_complete": True,
        "input_year_count": 45,
        "outer_forecast_count": len(backtest_rows),
        "minimum_segment_years": MIN_SEGMENT,
        "single_trend_model": "theil_sen",
        "segmented_model": "single_break_two_theil_sen_lines",
        "breakpoint_selection_loss": "training_mae",
        "single_backtest_rmse_mm": single_rmse,
        "single_backtest_mae_mm": single_mae,
        "segmented_backtest_rmse_mm": segmented_rmse,
        "segmented_backtest_mae_mm": segmented_mae,
        "predictive_qualification_pass": predictive_qualified,
        "rolling_median_break_year": median_break,
        "rolling_break_q25_year": q25,
        "rolling_break_q75_year": q75,
        "rolling_break_within_3y_fraction": stability_fraction,
        "rolling_break_stability_pass": rolling_stability_pass,
        "full_series_selected_break_year": full_break,
        "full_break_within_3y_of_rolling_median": full_break_close,
        "full_pre_slope_mm_per_year": full_segmented["pre_slope"],
        "full_post_slope_mm_per_year": full_segmented["post_slope"],
        "pre_post_slopes_opposite_nonzero": opposite_slopes,
        "pettitt_break_year": pettitt["pettitt_break_year"],
        "pettitt_approx_p": pettitt["pettitt_approx_p"],
        "pettitt_role": "secondary_diagnostic_only",
        "classification": classification,
        "public_claim_authorized": public_authorized,
        "posthoc_algorithm_search_performed": False,
        "climate_change_attribution_performed": False,
        "causal_analysis_performed": False,
        "station_observation_equivalence": False,
        "historical_boundary_continuity_claimed": False,
        "inputs": {
            "m20_regional_annual_mean": {"path": str(INPUT.relative_to(ROOT)), "sha256": sha256(INPUT)},
            "m20_manifest": {"path": str(M20_MANIFEST.relative_to(ROOT)), "sha256": sha256(M20_MANIFEST)},
            "design_gate": {"path": str(DESIGN.relative_to(ROOT)), "sha256": sha256(DESIGN)},
            "spec": {"path": str(SPEC.relative_to(ROOT)), "sha256": sha256(SPEC)},
        },
        "outputs": {
            "rolling_backtest": {"path": str(BACKTEST_OUT.relative_to(ROOT)), "sha256": sha256(BACKTEST_OUT)},
            "breakpoint_candidates": {"path": str(CANDIDATES_OUT.relative_to(ROOT)), "sha256": sha256(CANDIDATES_OUT)},
            "full_series_regime": {"path": str(FULL_OUT.relative_to(ROOT)), "sha256": sha256(FULL_OUT)},
        },
        "upstream_m20_regional_public_claim_authorized": m20["regional_public_claim_authorized"],
        "design_gate_schema": design["schema"],
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = build_outputs()
    print(json.dumps({
        "milestone21_complete": manifest["milestone21_complete"],
        "classification": manifest["classification"],
        "selected_break_year": manifest["full_series_selected_break_year"],
        "predictive_qualification_pass": manifest["predictive_qualification_pass"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
