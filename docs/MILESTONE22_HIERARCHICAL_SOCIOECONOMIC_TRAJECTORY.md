# Milestone 22 — Hierarchical Socioeconomic Trajectory Engine

Status: **complete analytical result; 4/7 indicators qualify for hierarchical trajectory interpretation**.

M22 estimates modern 2018–2025 kabupaten/kota trajectories with a partially pooled random-intercept/random-slope model implemented as deterministic penalized least squares. Pooling strength is selected inside nested leave-one-calendar-year-out validation and is benchmarked against 19 independent geography-specific OLS trends.

## Indicator qualification

An indicator qualifies only when the hierarchical model beats the independent-geography benchmark on **both RMSE and MAE** across 152 strict held-out-year predictions.

Qualified:

- `labor_force_participation`: RMSE 2.1746 vs 2.2225; MAE 1.7344 vs 1.7640; final penalty 1.0.
- `unemployment_rate`: RMSE 0.9134 vs 0.9434; MAE 0.6517 vs 0.6694; final penalty 1.0.
- `real_grdp_growth`: RMSE 2.8915 vs 2.9187; MAE 1.9637 vs 1.9662; final penalty 100.0.
- `rice_yield`: RMSE 0.3434 vs 0.3530; MAE 0.2665 vs 0.2707; final penalty 0.1.

Not qualified:

- `expected_years_schooling`: tiny RMSE improvement but tiny MAE deterioration.
- `mean_years_schooling`: RMSE improves but MAE deteriorates.
- `poverty_rate`: both RMSE and MAE are slightly worse than independent geography trends.

A failed model qualification does **not** mean the underlying indicator did not improve or worsen. It means this hierarchical partial-pooling representation did not improve sufficiently over the preregistered benchmark to authorize hierarchy-based public trajectory classifications.

## Geography-level robust trajectories

Across 133 geography-indicator pairs:

- **32** are `persistent_increase`;
- **14** are `persistent_decrease`;
- **87** are `trajectory_not_robust`.

A persistent classification requires the indicator-level benchmark gate to pass and all eight leave-one-year-out slope diagnostics to retain a stable direction under the preregistered envelope rule.

### Labor-force participation

The qualified model has a shared slope of approximately **+0.489 percentage points/year**.

- 17/19 geographies are classified persistent increase.
- Pesisir Selatan and Padang Panjang remain `trajectory_not_robust` under the slope-stability gate.

This describes the numerical labor-force-participation trajectory only. It does not establish why participation changed or whether every increase represents an unambiguously favorable labor-market outcome.

### Unemployment

The qualified model has a shared slope of approximately **−0.077 percentage points/year**, but district/city heterogeneity is material:

- 11 geographies are persistent decreases;
- 5 are persistent increases;
- 3 are not robust.

The persistent-increase group is Sijunjung, Tanah Datar, Lima Puluh Kota, Dharmasraya, and Pasaman Barat. The result therefore does not support a single province-wide statement that unemployment uniformly improved across all districts/cities.

### Real GRDP growth

The hierarchical model narrowly beats the independent-trend benchmark, but its final penalty is **100**, implying strong pooling toward the shared trajectory. Despite indicator-level qualification, **0/19 geographies** pass the slope-stability gate.

The 2018–2025 period contains major macroeconomic shocks, so M22 does not interpret the small positive shared slope as structural economic acceleration. Growth remains `trajectory_not_robust` for every geography.

### Rice yield

The qualified model has a shared slope of approximately **+0.034 raw yield units/year**.

- 10 geographies are persistent increases;
- 3 are persistent decreases;
- 6 are not robust.

The persistent-decrease group is Tanah Datar, Agam, and Pariaman. These are descriptive yield trajectories, not causal diagnoses of agricultural productivity policy.

## Why schooling and poverty are blocked

Observed schooling values generally rise and the fitted shared poverty slope is negative, but M22 deliberately separates **observed change** from **model-qualified trajectory evidence**.

Because schooling fails the MAE benchmark and poverty fails both benchmark metrics, M22 does not promote geography-level hierarchical slope classifications for those indicators. Their observed 2018–2025 changes remain available in the underlying panel and can be communicated descriptively with the appropriate evidence label.

## Claim boundary

M22 covers only the current-boundary **2018–2025** regime. Its hierarchical slopes are not causal effects, policy treatment effects, theoretical frontiers, historical trajectories back to independence, or forecasts guaranteed to continue after 2025. The leave-one-year-out slope envelope is a stability diagnostic, **not a confidence interval**.

## Reproducible outputs

- `data/analysis/engine/hierarchical_trajectory_v1/m22-model-frame.csv`
- `data/analysis/engine/hierarchical_trajectory_v1/m22-outer-predictions.csv`
- `data/analysis/engine/hierarchical_trajectory_v1/m22-indicator-summary.csv`
- `data/analysis/engine/hierarchical_trajectory_v1/m22-geography-trajectories.csv`
- `data/analysis/engine/hierarchical_trajectory_v1/m22-loo-slopes.csv`
- `data/manifests/milestone22_hierarchical_socioeconomic_trajectory.json`
