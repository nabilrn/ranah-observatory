# Milestone 21 — Climate Regime-Shift Engine

Status: **complete analytical result; regime-shift claim not qualified**.

M21 tests whether the non-monotonic regional rainfall pattern exposed by M20 is better represented by a single-break, two-regime robust trend than by one Theil–Sen trend across the whole history.

## Full-series fit

The full 1981–2025 regional current-boundary CHIRPS mean selects **1998** as the minimum-training-MAE breakpoint.

- pre-break Theil–Sen slope: approximately **−43.70 mm/year**;
- post-break Theil–Sen slope: approximately **+9.95 mm/year**;
- the pre/post slopes therefore have opposite non-zero signs.

The secondary restricted Pettitt diagnostic independently selects **1998**, with approximate p≈**0.084**. Pettitt is not the authorization gate.

## Out-of-time validation

Across 20 rolling one-year-ahead forecasts (2006–2025):

- single-trend RMSE: approximately **402.65 mm**;
- segmented RMSE: approximately **420.14 mm**;
- single-trend MAE: approximately **343.12 mm**;
- segmented MAE: approximately **333.38 mm**.

The segmented model improves MAE but worsens RMSE. Because the preregistered predictive gate requires both metrics to improve, predictive qualification fails.

The rolling median selected breakpoint is 1998, but only **55%** of rolling breakpoints fall within ±3 years of that median, below the preregistered 75% stability threshold. The breakpoint is therefore not sufficiently stable across expanding historical windows.

## Interpretation

M21 does **not** establish a defensible 1998 climate-regime shift. It establishes that a two-regime representation is plausible enough to investigate, but not stable and predictively superior enough to authorize a public regime-shift claim under the locked design.

This is stronger evidence than fitting a breakpoint to the full series and reporting the best-looking year: the same candidate must survive rolling out-of-time prediction and stability checks, and it did not.

## Claim boundary

The input remains an unweighted mean of 19 current-boundary CHIRPS model-estimate series. M21 does not claim station equivalence, historical-boundary continuity, anthropogenic climate-change attribution, physical mechanism identification, disaster causality, or socioeconomic causality.

## Reproducible outputs

- `data/analysis/engine/climate_regime_shift_v1/m21-rolling-backtest.csv`
- `data/analysis/engine/climate_regime_shift_v1/m21-breakpoint-candidates.csv`
- `data/analysis/engine/climate_regime_shift_v1/m21-full-series-regime.csv`
- `data/manifests/milestone21_climate_regime_shift.json`
