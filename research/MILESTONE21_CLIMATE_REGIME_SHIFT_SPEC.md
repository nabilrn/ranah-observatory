# Milestone 21 — Climate Regime-Shift Engine Specification

## Purpose

M21 tests whether the non-monotonic rainfall pattern exposed by M20 is better represented by a **single-break, two-regime robust trend model** than by a single long-run trend.

The milestone is predictive/descriptive. It does **not** perform anthropogenic climate-change attribution, causal inference, disaster attribution, or station-equivalent observation analysis.

## Locked input regime

Primary input:

`data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv`

Required upstream state:

- M20 complete;
- 45 annual current-boundary regional mean rainfall values, 1981–2025;
- each annual value is the unweighted mean of the 19 current West Sumatra kabupaten/kota CHIRPS model estimates;
- M20 regional monotonic-trend claim is fail-closed;
- source semantics remain CHIRPS `model_estimate_spatial_mean`, not BMKG station observations.

M21 uses the regional series first because the 19 geography series share spatial climate structure and are not treated as 19 independent replications.

## Primary candidate model

### Single-trend benchmark

Fit one Theil–Sen line to all training years and extrapolate one year ahead.

### Single-break segmented trend

For each training set, consider every breakpoint that leaves at least **10 annual observations in both segments**.

For a candidate breakpoint `b`:

- segment 1 contains years `<= b`;
- segment 2 contains years `> b`;
- fit a separate Theil–Sen slope in each segment;
- define each segment intercept as `median(y - slope*x)`;
- compute pooled in-training mean absolute error across both segments.

Select the breakpoint with the lowest pooled training MAE. Ties are resolved by the earliest breakpoint year. Breakpoint selection uses training data only.

The segmented one-year-ahead forecast is produced by extrapolating the **post-break** Theil–Sen line.

No breakpoint is selected by looking at future held-out rainfall.

## Primary validation: rolling-origin out-of-time forecast

Outer forecast years are fixed at **2006–2025**.

For each forecast year `t`:

1. train only on 1981 through `t-1`;
2. fit the single-trend benchmark;
3. select the segmented-model breakpoint using only that training window;
4. predict rainfall for year `t` with both models;
5. store errors and the selected breakpoint.

This yields 20 genuinely out-of-time forecast comparisons.

The segmented model passes the predictive qualification gate only if:

- segmented RMSE < single-trend RMSE; **and**
- segmented MAE < single-trend MAE.

Negative results are retained. No alternative breakpoint algorithm may be searched post hoc to manufacture a win.

## Breakpoint stability gate

Across the 20 rolling-origin fits:

- compute the median selected breakpoint year;
- report the interquartile range;
- compute the fraction of selected breakpoints within ±3 years of the median.

The preregistered stability threshold is **>= 0.75**.

A full-series 1981–2025 segmented fit is also computed. Its selected breakpoint must lie within ±3 years of the rolling-origin median breakpoint to pass the stability gate.

## Regime-shape gate

For the full-series selected breakpoint, the pre-break and post-break Theil–Sen slopes must have **opposite non-zero signs** before M21 may describe the evidence as a trend-regime reversal.

If predictive performance improves but slope signs are not opposite, the result remains a useful segmented forecast result but is not authorized as a trend-regime reversal claim.

## Pettitt diagnostic

M21 additionally reports a restricted-edge Pettitt nonparametric change-point diagnostic on the full regional series, using the same minimum 10-observation segment rule.

The Pettitt approximate p-value is **secondary diagnostic evidence only**. It does not authorize the M21 public claim by itself because serial dependence and finite-sample behavior can affect classical change-point inference.

## Public authorization

`predictively_supported_trend_regime_shift` is authorized only when all hold:

1. segmented RMSE is strictly lower than single-trend RMSE;
2. segmented MAE is strictly lower than single-trend MAE;
3. rolling breakpoint stability fraction within ±3 years is >= 0.75;
4. full-series breakpoint lies within ±3 years of the rolling median breakpoint;
5. full-series pre/post Theil–Sen slopes have opposite non-zero signs.

Otherwise classification is `regime_shift_not_qualified`.

## Required outputs

1. `data/analysis/engine/climate_regime_shift_v1/m21-rolling-backtest.csv`
2. `data/analysis/engine/climate_regime_shift_v1/m21-breakpoint-candidates.csv`
3. `data/analysis/engine/climate_regime_shift_v1/m21-full-series-regime.csv`
4. `data/manifests/milestone21_climate_regime_shift.json`

## Completion gate

M21 completes when:

- exact 1981–2025 regional series is validated against M20;
- all 20 outer years are forecast strictly out of time;
- every segmented breakpoint is selected from training data only;
- single and segmented Theil–Sen forecasts are compared using both RMSE and MAE;
- breakpoint stability and regime-shape gates are materialized;
- Pettitt remains secondary diagnostic evidence;
- no climate attribution, station equivalence, disaster causality, or socioeconomic causality is emitted;
- focused tests pass;
- permanent read-only CI reproduces committed artifacts byte-for-byte.

## Forbidden interpretations

M21 does not authorize claims that:

- a detected regime change was caused by anthropogenic climate change;
- a breakpoint is a physical climate mechanism date;
- CHIRPS regional means are equivalent to observed station rainfall;
- a rainfall regime shift caused floods, landslides, poverty, unemployment, or growth changes;
- a predictive breakpoint is guaranteed to persist in future climate.
