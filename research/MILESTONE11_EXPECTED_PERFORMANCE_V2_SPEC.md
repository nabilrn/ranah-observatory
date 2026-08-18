# Milestone 11 — Expected Performance Engine v2 Specification

## Phase 2 role

Milestone 11 upgrades the single-year province-level M7 proof-of-concept into a **multi-outcome, cross-fitted expected-performance engine** for the modern West Sumatra kabupaten/kota analytical regime created in M10.

The engine estimates conditional expected outcomes. It does **not** estimate a production frontier, causal treatment effect, policy counterfactual, or monetary value of unrealized potential.

## Locked analytical regime

Input substrate:

`data/analysis/engine/panel_v1/m10-panel-wide.csv`

M10 regime:

`sumbar_current_kabkota_2018_2025_v1`

M11 model regime:

`sumbar_current_kabkota_lagged_structural_2019_2024_v1`

- geographies: exact 19 current West Sumatra kabupaten/kota;
- target years: 2019–2024 inclusive;
- target rows per outcome: `19 × 6 = 114`;
- predictor year: `target_year - 1`, therefore 2018–2023;
- no historical-boundary continuity claim;
- no imputation.

The target window is chosen **before model fitting** because the preregistered structural feature set has exact 19-geography coverage for 2018–2023 in M10. It is not chosen from target residuals or model performance.

## Primary outcomes

M11 preregisters exactly three annual outcomes:

1. `poverty_rate`
   - unit: percent;
   - direction for later interpretation: lower is favorable;
   - target transformation: identity.

2. `unemployment_rate`
   - unit: percent;
   - direction for later interpretation: lower is favorable;
   - target transformation: identity.

3. `real_grdp_growth`
   - unit: percent;
   - direction for later interpretation: higher is favorable;
   - target transformation: identity.

All three targets have exact 19-geography annual coverage in M10 for 2019–2024.

M11 does not select outcomes based on which residual makes any geography look unusually good or bad.

## Primary lagged structural feature set

Every target uses the same five predictors, measured at `t-1`:

1. `mean_years_schooling` — human-capital stock proxy;
2. `labor_force_participation` — labor-market participation/capability;
3. `agriculture_share_grdp` — economic structure;
4. `manufacturing_share_grdp` — economic structure;
5. `rice_yield` — agricultural productivity proxy.

These features have exact 19-geography coverage for 2018–2023 in M10.

### Explicit feature exclusions

Primary models exclude:

- the target's own lagged value;
- contemporaneous target-year predictors;
- `expected_years_schooling`, because it is highly adjacent to `mean_years_schooling` and would duplicate the human-capital dimension in this small sample;
- `life_expectancy`, because its qualified M10 coverage begins only in 2020 and would materially shorten the primary window;
- `underemployment_rate`, because it is another labor-market outcome and stops at 2024;
- `population_total`, because the qualified district/city series is only the SP2020 census anchor;
- `annual_rainfall` from the primary model because CHIRPS station-equivalence remains unvalidated; it may be used only in a labelled sensitivity model;
- BNPB flood/landslide counts because qualified district/city coverage is 2024 only;
- any post-target or future information.

No feature may be added after seeing residual signs or benchmark results.

## Pre-specified sensitivity feature set

Exactly one sensitivity is allowed:

- primary five lagged features **plus lagged `annual_rainfall`**.

CHIRPS remains `model_estimate` evidence. A better sensitivity-model score does not promote rainfall into the primary model or imply causal rainfall effects.

## Model family

Primary candidate family: linear ridge regression with target-year fixed effects.

For observation `(geography i, target year t)`:

`y_it = year_effect_t + beta' X_i,t-1 + error_it`

where `X` contains the five preregistered lagged predictors.

Implementation rules:

- continuous predictors are standardized using **training-fold means/scales only**;
- target-year dummy effects are learned from training geographies in the same target years;
- continuous predictor coefficients are ridge-penalized;
- year effects are not ridge-penalized;
- no geography fixed effect is used because the engine must predict a geography held entirely out of fitting;
- no target-specific feature search is allowed.

Fixed ridge penalty grid:

`[0.0, 0.01, 0.1, 1.0, 10.0, 100.0]`

`0.0` is the unpenalized linear-model candidate.

## Validation design

### Primary evaluation: nested leave-one-geography-out cross-fitting

The primary estimate is always out-of-geography.

For each of the 19 outer folds:

1. hold out one kabupaten/kota and all six of its target-year rows;
2. use the remaining 18 geographies as the outer training universe;
3. select the ridge penalty using **inner leave-one-geography-out CV** among those 18 training geographies;
4. inner-fold model selection minimizes RMSE across all inner held-out rows;
5. fit the selected penalty on all 18 outer-training geographies;
6. predict all six target-year rows for the held-out geography.

Thus no geography contributes any target or predictor row to the model that produces its own primary M11 expected-performance predictions.

### Naive benchmark

For each outer held-out geography-year row, the benchmark prediction is the **mean target value among the 18 training geographies in that same target year**.

This benchmark absorbs the common target-year level but uses no structural predictors.

## Target qualification gate

Benchmark qualification is evaluated separately for each target using all 114 outer-fold cross-fitted predictions.

A target is `benchmark_qualified=true` only if:

- structural model RMSE < same-year peer-mean RMSE; **and**
- structural model MAE < same-year peer-mean MAE.

If either metric fails, the target remains a valid negative benchmark result but its residuals are **not authorized for substantive expected-performance interpretation** in downstream gap/decomposition work.

M11 as an engine may still complete when a target fails. Failure is evidence about model adequacy, not a reason to search alternative features after the fact.

## Cross-fitted expected performance and residuals

For each of the 342 target observations (`3 targets × 114 rows`) report:

- observed target;
- cross-fitted expected target;
- residual = `observed - expected`;
- same-year peer-mean benchmark prediction;
- benchmark residual;
- outer held-out geography;
- selected ridge penalty;
- feature-support diagnostics;
- benchmark-qualification flag for the target.

Residuals are **predictive/model residuals**. They are not causal effects and not a frontier distance.

## Empirical uncertainty

For each focal geography and target, prediction uncertainty is calibrated from cross-fitted residuals belonging to the **other 18 geographies only**.

Report empirical residual quantiles:

- 2.5th percentile;
- 97.5th percentile.

For each focal expected outcome:

`interval = expected + [q0.025, q0.975]`

The interval is finite-sample exploratory and may extend outside a target's natural support. It must not be silently clipped.

## Support diagnostics

For every outer-fold held-out geography-year prediction and each predictor:

- compare the focal lagged feature against the min/max of the 18 training geographies **in the same lagged feature year**;
- record per-feature inside/outside support;
- record whether all five primary predictors are inside same-year marginal support.

Predictions outside marginal support remain visible but must carry `support_warning=true`.

Support is not proof of multivariate overlap.

## Sensitivity model

Run the same nested leave-one-geography-out procedure with the five primary features plus lagged CHIRPS annual rainfall.

Report sensitivity RMSE/MAE and prediction differences.

The sensitivity model is not used to replace a primary result based on whichever version performs better.

## Coefficient diagnostics

For each target and outer fold, retain:

- selected penalty;
- standardized continuous-feature coefficients from the final outer-training model;
- year effects.

Coefficient signs/magnitudes are descriptive model diagnostics only. They are **not causal bottleneck estimates** and must not be ranked as policy effects.

## Required outputs

1. `data/analysis/engine/expected_performance_v2/m11-model-frame.csv`
2. `data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv`
3. `data/analysis/engine/expected_performance_v2/m11-target-summary.csv`
4. `data/analysis/engine/expected_performance_v2/m11-support-diagnostics.csv`
5. `data/analysis/engine/expected_performance_v2/m11-outer-fold-coefficients.csv`
6. `data/analysis/engine/expected_performance_v2/m11-sensitivity-summary.csv`
7. `data/manifests/milestone11_expected_performance_v2.json`

## Completion gate

M11 completes when:

- exact 19 geographies × 6 target years × 3 targets are cross-fitted;
- the primary model frame has no missing values in the preregistered target/feature fields;
- every primary prediction is produced by a model that excluded the focal geography entirely;
- nested inner geography CV selects penalties without outer-fold leakage;
- same-year peer-mean benchmarks are present;
- benchmark qualification is target-specific and fail-closed;
- empirical uncertainty excludes the focal geography's own residuals;
- same-year support diagnostics are present;
- the one preregistered rainfall sensitivity is reported;
- no causal/frontier/counterfactual/monetary-wasted-potential claim is emitted;
- focused tests pass;
- permanent read-only CI rebuilds committed artifacts byte-for-byte;
- M10 and the 9/9 Research Foundation remain green.

## Forbidden interpretations

M11 does not authorize statements such as:

- “this factor caused poverty/unemployment/growth”;
- “this is the maximum attainable outcome”;
- “the residual is wasted potential”;
- “changing feature X by one unit would cause Y to change by the coefficient”;
- “a target that failed the benchmark still reveals underperformance.”

A benchmark-qualified residual answers only:

> Given the preregistered lagged structural profile and peer-year context, how different was the observed outcome from this transparent cross-fitted conditional expectation?
