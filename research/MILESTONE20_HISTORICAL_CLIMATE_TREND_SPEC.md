# Milestone 20 — Historical Climate Trend Engine Specification

## Purpose

M20 converts the qualified CHIRPS annual-rainfall history into a reproducible long-run trend evidence layer for public-facing historical interpretation.

It does **not** perform climate-change attribution, station-equivalent observation analysis, disaster-impact attribution, policy evaluation, or causal inference.

## Locked source regime

Input:

- `data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv`
- `data/processed/climate/rainfall/chirps-rainfall-materialization.manifest.json`

Required source contract:

- source: CHIRPS v3 Final monthly materialized to annual rainfall;
- indicator: `annual_rainfall`;
- claim type: `model_estimate`;
- unit: millimetres;
- 19 current West Sumatra kabupaten/kota;
- years 1981–2025 inclusive;
- exactly 45 annual observations per geography, 855 total;
- fixed current BIG June 2026 boundary frame;
- no historical-boundary continuity claim;
- independent station validation remains pending.

No imputation, smoothing, forward fill, backward fill, or source substitution is allowed.

## Primary estimand

For each of the 19 current-boundary geographies, estimate the monotonic long-run tendency of annual rainfall over 1981–2025.

The magnitude estimand is the **Theil–Sen median pairwise slope**, reported in:

- mm/year;
- mm/decade.

A 95% rank-based Sen slope confidence interval is reported. The estimator is robust to individual extreme annual values and does not require normally distributed rainfall residuals.

## Trend-direction test

M20 reports two Mann–Kendall diagnostics:

1. classical Mann–Kendall statistic and p-value, retained for transparency only;
2. an autocorrelation-adjusted Hamed–Rao-style variance correction applied to ranks of the Theil–Sen-detrended series.

The adjusted test is the primary direction-evidence diagnostic because serial dependence can invalidate the classical independent-sample variance assumption.

Implementation rules:

- ties are handled in the classical Mann–Kendall variance;
- the series is detrended using the full-period Theil–Sen slope before rank autocorrelation estimation;
- only rank autocorrelations whose absolute value exceeds `1.96 / sqrt(n)` enter the Hamed–Rao variance inflation/deflation term;
- the corrected variance factor is bounded below at a small positive numerical floor to prevent invalid negative variance from finite-sample estimation artifacts;
- all calculations are deterministic and dependency-free Python.

## Multiple testing

The 19 geography-level adjusted p-values are corrected with the **Holm step-down family-wise error procedure** at alpha `0.05`.

Unadjusted p-values must never be used by themselves to authorize a public geography-level trend claim.

## Stability diagnostics

A geography may only receive a public-facing robust directional trend classification when the full-period result is stable under pre-specified perturbations.

### Midpoint split

The 45-year period is split mechanically, not data-adaptively:

- early period: 1981–2002 (22 years);
- late period: 2003–2025 (23 years).

Theil–Sen slopes are estimated separately for both halves.

### Leave-one-year-out slope stability

For every geography, recompute the Theil–Sen slope 45 times, each time removing one year.

Report:

- minimum leave-one-year-out slope;
- maximum leave-one-year-out slope;
- fraction of leave-one-year-out slopes with the same non-zero direction as the full-period slope.

The preregistered stability threshold is `>= 0.90` same-direction retention.

## Public trend authorization gate

A geography is `robust_monotonic_increase` or `robust_monotonic_decrease` only when **all** of the following hold:

1. Holm-adjusted Hamed–Rao p-value `< 0.05`;
2. 95% Theil–Sen slope interval excludes zero in the same direction;
3. early-period and late-period Theil–Sen slopes have the same non-zero direction as the full-period slope;
4. leave-one-year-out direction retention is at least `0.90`.

Otherwise the geography is classified `no_robust_monotonic_trend`.

This is intentionally conservative. A blocked classification does not mean rainfall was constant; it means the available evidence does not pass the preregistered robust monotonic-trend gate.

## Regional aggregate diagnostic

M20 also computes a **current-boundary regional mean rainfall series** by taking the unweighted mean of the 19 geography-level CHIRPS values within each year, then applying the same trend calculations.

This regional aggregate is a descriptive spatial mean of current-boundary model estimates. It is not a historical province-boundary reconstruction and is not included in the 19-geography Holm correction family.

## Required outputs

1. `data/analysis/engine/historical_climate_trend_v1/m20-geography-trends.csv`
2. `data/analysis/engine/historical_climate_trend_v1/m20-leave-one-year-out.csv`
3. `data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv`
4. `data/analysis/engine/historical_climate_trend_v1/m20-regional-trend.csv`
5. `data/manifests/milestone20_historical_climate_trend.json`

## Completion gate

M20 completes when:

- all 855 source observations pass source-contract checks;
- all 19 geographies have exact 1981–2025 coverage;
- Theil–Sen, classical Mann–Kendall, adjusted Mann–Kendall, Holm correction, split-period slopes, and leave-one-year-out diagnostics are materialized;
- every public trend classification is fail-closed under the four-part authorization gate;
- no climate-change attribution, causal, disaster-impact, or station-equivalence claim is emitted;
- focused tests pass;
- a permanent read-only CI workflow reproduces committed artifacts byte-for-byte.

## Forbidden interpretations

M20 does not authorize claims that:

- anthropogenic climate change caused an estimated trend;
- CHIRPS model estimates are equivalent to BMKG station observations;
- rainfall trends caused floods, landslides, unemployment, poverty, or growth outcomes;
- current administrative boundaries represent historical administrative units throughout 1981–2025;
- failure of the robust trend gate proves there was no meaningful climate variability or change.
