# Milestone 19 — Dynamic Forecast Engine v1 Specification

## Purpose

Milestone 19 adds a **retrospectively backtested one-year-ahead forecasting lane** to Ranah Observatory. It is deliberately separate from M11 expected-performance estimation, M14 association screening, M15 causal evidence, and M17 intervention sensitivity.

The question is:

> Given only information available through year `t-1`, can a simple pooled autoregressive structural model predict district/city outcome `t` better than carrying forward the district/city's own previous-year outcome?

This milestone is predictive, not causal. A coefficient is not a treatment effect and a forecast is not a policy counterfactual.

## Why this model family

The available modern panel is small in statistical terms: 19 current West Sumatra kabupaten/kota observed annually. This does not justify high-capacity tree ensembles or neural networks as the first forecasting model. M19 therefore uses a transparent **pooled autoregressive ridge regression** grounded in three considerations:

1. annual socioeconomic outcomes are persistent, so the target's own lag is a strong theory-consistent baseline predictor;
2. structural covariates may add predictive information beyond persistence;
3. ridge shrinkage is appropriate when the sample is small and predictors may be correlated.

No algorithm is added after inspecting M19 backtest results merely to obtain a favorable score.

## Input regime

Primary input:

`data/analysis/engine/panel_v1/m10-panel-wide.csv`

Required M10 regime:

`sumbar_current_kabkota_2018_2025_v1`

M19 model regime:

`sumbar_current_kabkota_dynamic_forecast_2019_2026_v1`

Geographies: exact 19 current West Sumatra kabupaten/kota.

## Outcomes

Exactly three targets are preregistered:

- `poverty_rate` — lower is favorable;
- `unemployment_rate` — lower is favorable;
- `real_grdp_growth` — higher is favorable.

## Predictor set

For target year `t`, use only values from `t-1`:

- the target's own lag, `lag1_target`;
- `mean_years_schooling`;
- `labor_force_participation`;
- `rice_yield`.

This deliberately narrower structural feature set is chosen because all three structural predictors remain qualified through 2025 in M10, allowing a genuine 2026 forecast without imputing 2024/2025 agriculture/manufacturing-share gaps.

Explicit exclusions from the primary forecasting model:

- contemporaneous/future information;
- agriculture/manufacturing share because the qualified current panel stops before the 2025 feature year needed for a 2026 forecast;
- population because district/city coverage is a census anchor rather than annual series;
- BNPB event counts because district/city coverage is sparse;
- CHIRPS rainfall because M19 is testing a minimal deployable socioeconomic forecaster and climate evidence has separate claim semantics;
- geography fixed effects, because M19 prioritizes a compact pooled predictive model and avoids treating fixed effects as structural explanation.

## Model

For each target separately:

`y(i,t) = intercept + phi * y(i,t-1) + beta' X(i,t-1) + error(i,t)`

where `X` contains the three preregistered structural predictors.

All four continuous predictors are standardized using training-only means and scales. The intercept is unpenalized; all standardized predictor coefficients are ridge-penalized.

Fixed ridge penalty grid:

`[0.01, 0.1, 1.0, 10.0, 100.0]`

No target-specific feature search is allowed.

## Temporal validation

### Outer rolling-origin backtest

Outer forecast years are exactly 2021–2025.

For outer year `T`:

1. fit/tune using target rows with year `< T` only;
2. never use target-year `T` outcomes, predictors from `T`, or later information in fitting;
3. predict all 19 geographies for `T` from their `T-1` information.

This yields `5 × 19 = 95` strictly out-of-time backtest predictions per target, `285` total.

### Inner rolling-origin penalty selection

Within each outer training window, choose the ridge penalty using only nested past-year validation:

- each inner validation year `v` is predicted from rows with target year `< v`;
- the first possible inner validation year is 2020;
- RMSE is pooled across all available inner validation rows;
- tie-break toward the larger penalty to prefer more shrinkage.

Thus hyperparameter selection never sees the outer forecast year.

## Benchmark

Primary benchmark: **district/city persistence**.

For geography `i` and forecast year `t`:

`persistence_prediction(i,t) = y(i,t-1)`

This is intentionally hard to beat for persistent annual indicators and is available without fitting a model.

## Qualification gate

A target is `forecast_qualified=true` only if, across all 95 outer backtest predictions:

- dynamic-ridge RMSE < persistence RMSE; and
- dynamic-ridge MAE < persistence MAE.

Failure is retained as evidence. It does not authorize trying additional algorithms post hoc until one wins.

## 2026 forecast

After backtesting, fit each target on all available 2019–2025 target rows, select the penalty using nested rolling-origin CV, and predict 2026 from 2025 values.

A 2026 point forecast may be materialized for every target/geography as a model diagnostic. **Substantive public forecast use is authorized only when that target passes the backtest qualification gate.**

Uncertainty is exploratory: use empirical 2.5% and 97.5% quantiles of the target's strictly out-of-time backtest residuals and add them to the 2026 point forecast. Intervals are not silently clipped to natural bounds.

## Required outputs

1. `data/analysis/engine/dynamic_forecast_v1/m19-model-frame.csv`
2. `data/analysis/engine/dynamic_forecast_v1/m19-backtest-predictions.csv`
3. `data/analysis/engine/dynamic_forecast_v1/m19-target-summary.csv`
4. `data/analysis/engine/dynamic_forecast_v1/m19-outer-fold-coefficients.csv`
5. `data/analysis/engine/dynamic_forecast_v1/m19-forecast-2026.csv`
6. `data/manifests/milestone19_dynamic_forecast_engine.json`

## Completion gate

M19 completes when:

- exact 19-geography input footprint is preserved;
- exact 2021–2025 outer forecast years are backtested;
- every outer prediction is strictly out-of-time;
- penalty tuning is nested inside each outer training window;
- persistence benchmark is present for every backtest row;
- target qualification is fail-closed and requires both RMSE and MAE improvement;
- 2026 predictions use only 2025 predictors and lagged target values;
- empirical forecast intervals derive only from out-of-time residuals;
- no causal, frontier, treatment-effect, policy-ranking, or guaranteed-future claim is emitted;
- focused tests pass;
- permanent CI can rebuild committed outputs byte-for-byte.

## Forbidden interpretations

M19 does not authorize statements such as:

- “schooling caused the forecast change”;
- “the coefficient is the effect of increasing a predictor”;
- “the 2026 value will definitely occur”;
- “a forecast that failed persistence benchmarking is decision-ready”;
- “the model is superior because a later algorithm was searched after seeing failures.”
