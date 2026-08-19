# Milestone 22 — Hierarchical Socioeconomic Trajectory Engine Specification

## Purpose

M22 estimates **modern-period district/city trajectories** for every non-climate indicator that has complete 2018–2025 coverage in M10. It is designed for the short repeated-measures panel: 19 current West Sumatra kabupaten/kota observed annually for eight years.

The engine uses a hierarchical random-intercept/random-slope model implemented as deterministic penalized least squares. Geography-specific trajectories are partially pooled toward a shared trajectory rather than estimated as 19 unrelated eight-point regressions.

M22 is descriptive/predictive trajectory evidence. It does **not** estimate causal effects, policy treatment effects, structural production functions, theoretical frontiers, or long-run historical trends before 2018.

## Locked analytical regime

Input:

`data/analysis/engine/panel_v1/m10-panel-wide.csv`

Required M10 regime:

`sumbar_current_kabkota_2018_2025_v1`

- exact 19 current West Sumatra kabupaten/kota;
- years 2018–2025 inclusive;
- eight observations per geography for every selected indicator;
- no imputation;
- no historical-boundary continuity claim.

## Indicator universe

M22 includes **all seven non-climate indicators** that M10 marks complete for every geography-year in 2018–2025:

1. `expected_years_schooling`;
2. `mean_years_schooling`;
3. `labor_force_participation`;
4. `unemployment_rate`;
5. `poverty_rate`;
6. `real_grdp_growth`;
7. `rice_yield`.

`annual_rainfall` is excluded only because M20–M21 already provide the dedicated 1981–2025 climate trajectory regime. No socioeconomic indicator is dropped after inspecting M22 model performance.

## Model

For indicator `k`, geography `i`, and year `t`:

`y_it = beta0 + beta1*z_t + a_i + b_i*z_t + error_it`

where:

- `z_t = (t - 2021.5) / 2.5`, a fixed centered/scaled time covariate;
- `beta0`, `beta1` are unpenalized shared intercept/slope terms;
- `a_i`, `b_i` are geography-specific intercept/slope deviations;
- geography-specific trajectory slope is `(beta1 + b_i) / 2.5` in original outcome units per year.

The fitting criterion is:

`SSE + lambda * sum_i(a_i^2 + b_i^2)`.

This is a Gaussian hierarchical/random-coefficient model expressed through penalized least squares. The random deviations are partially pooled toward zero, while the shared fixed effects are not penalized.

### Penalty grid

Exactly one common random-effect penalty is selected per fit from:

`[0.01, 0.1, 1.0, 10.0, 100.0]`

No continuous hyperparameter search and no alternative model family may be introduced after observing results.

## Primary validation: nested leave-one-year-out

The central question is whether partial pooling improves reconstruction/prediction of unseen annual observations compared with independent geography-specific linear trends.

For each indicator and each of the eight outer held-out years:

1. remove that year for all 19 geographies;
2. use only the remaining seven years as the outer training set;
3. select `lambda` using inner leave-one-year-out validation across the remaining seven training years;
4. inner selection minimizes RMSE across all held-out geography-year rows; ties use the larger penalty to prefer stronger pooling;
5. fit the hierarchical model to all seven outer-training years;
6. predict all 19 observations in the outer held-out year.

No value from the outer held-out year participates in penalty selection or fitting.

### Benchmark

For the same outer fold and indicator, independently fit an ordinary least-squares line to each geography using its seven training observations and predict the held-out year.

The benchmark therefore asks whether partial pooling improves on 19 separate short-panel trend regressions.

## Indicator qualification

An indicator is `hierarchical_trajectory_qualified=true` only when, over all `8 × 19 = 152` outer predictions:

- hierarchical RMSE < independent-geography OLS RMSE; **and**
- hierarchical MAE < independent-geography OLS MAE.

Failure is retained as evidence that partial pooling did not improve that indicator. The engine remains complete even when one or all indicators fail.

## Full-period trajectory fit

For each indicator, choose its final penalty using leave-one-year-out validation on the complete 2018–2025 panel, then fit the hierarchy to all 152 rows.

Report for every geography:

- 2018 observed value;
- 2025 observed value;
- raw 2018→2025 change;
- hierarchical geography slope in outcome units/year;
- shared slope;
- geography slope deviation;
- selected final penalty;
- fitted 2018 and 2025 values;
- full-period residual RMSE for that geography.

## Trajectory stability

For each indicator-geography pair, retain the geography-specific slope from each of the eight outer models, each of which excludes one complete calendar year.

Report:

- minimum leave-one-year-out slope;
- maximum leave-one-year-out slope;
- fraction of outer slopes with the same non-zero direction as the full-period hierarchical slope.

The preregistered direction-retention threshold is `7/8 = 0.875`.

## Public trajectory classification

A geography-indicator pair is classified:

- `persistent_increase` only if:
  - the indicator is hierarchical-trajectory-qualified;
  - full-period slope > 0;
  - leave-one-year-out same-direction retention >= 0.875;
  - minimum leave-one-year-out slope > 0;

- `persistent_decrease` only if the symmetric negative conditions hold;

- otherwise `trajectory_not_robust`.

The leave-one-year-out slope range is a **stability envelope**, not a formal confidence interval.

No minimum effect-size threshold is introduced post hoc. Magnitudes remain visible even when classification is blocked.

## Public-language direction semantics

A direction classification describes only the numerical indicator trajectory. It does not automatically mean development improved or worsened.

For example:

- decreasing poverty is generally favorable;
- increasing mean years of schooling is generally favorable;
- increasing unemployment is generally unfavorable;
- real GRDP growth is a rate whose linear slope over this shock-heavy short period must not be described as structural acceleration without additional evidence.

M22 outputs direction and evidence strength separately from normative interpretation.

## Required outputs

1. `data/analysis/engine/hierarchical_trajectory_v1/m22-model-frame.csv`
2. `data/analysis/engine/hierarchical_trajectory_v1/m22-outer-predictions.csv`
3. `data/analysis/engine/hierarchical_trajectory_v1/m22-indicator-summary.csv`
4. `data/analysis/engine/hierarchical_trajectory_v1/m22-geography-trajectories.csv`
5. `data/analysis/engine/hierarchical_trajectory_v1/m22-loo-slopes.csv`
6. `data/manifests/milestone22_hierarchical_socioeconomic_trajectory.json`

## Completion gate

M22 completes when:

- all seven preregistered indicators have exact 19×8 source coverage;
- every indicator has 152 strict outer leave-one-year-out predictions;
- penalty selection is nested inside each outer fold;
- independent-geography OLS benchmark predictions are present;
- indicator qualification is fail-closed on both RMSE and MAE;
- all 133 geography-indicator trajectories are materialized;
- all `7 × 19 × 8 = 1064` leave-one-year-out slope diagnostics are materialized;
- public trajectory classification cannot bypass indicator qualification or slope-stability gates;
- no causal, policy, frontier, monetary-wasted-potential, pre-2018 historical continuity, or guaranteed-future claim is emitted;
- focused tests pass;
- permanent read-only CI reproduces committed artifacts byte-for-byte.

## Forbidden interpretations

M22 does not authorize statements that:

- time caused an outcome change;
- a geography-specific slope is a policy effect;
- a 2018–2025 slope describes the entire post-independence history;
- a robust trajectory guarantees continuation after 2025;
- partial pooling proves geographies are exchangeable in every substantive sense;
- a `trajectory_not_robust` classification means the indicator did not change.
