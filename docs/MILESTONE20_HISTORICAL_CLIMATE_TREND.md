# Milestone 20 — Historical Climate Trend Engine

Status: **complete analytical result; public monotonic-trend claims fail closed**.

M20 analyzes the qualified CHIRPS v3 annual-rainfall model estimates for 19 current West Sumatra kabupaten/kota over 1981–2025. It uses a robust Theil–Sen slope for trend magnitude, an autocorrelation-adjusted Mann–Kendall diagnostic for direction evidence, Holm family-wise correction across the 19 geography tests, and pre-specified split-period plus leave-one-year-out stability checks.

## Result

No geography passes the full preregistered public robust-monotonic-trend gate (`0/19`). The result is not interpreted as evidence that rainfall was constant. Instead, the full-period positive/negative tendency is generally not stable enough across the mechanically split early (1981–2002) and late (2003–2025) periods after multiplicity and uncertainty guardrails are applied.

Several geography-level full-period Theil–Sen slopes are positive and have 95% slope intervals above zero, but the early-period and late-period slopes commonly disagree in direction. Because split-direction consistency is mandatory, those apparent full-period trends remain blocked from public monotonic-trend claims.

The current-boundary regional unweighted mean has a full-period Theil–Sen slope of approximately **+9.45 mm/year (+94.53 mm/decade)** with a 95% slope interval above zero and adjusted Mann–Kendall p≈0.032. However, the early-period slope is approximately **−13.08 mm/year** while the late-period slope is approximately **+12.84 mm/year**. The regional series therefore also fails the stability gate and is classified `no_robust_monotonic_trend`.

This result motivates a separate, preregistered **change-point / regime-shift analysis** rather than relaxing the monotonic-trend gate post hoc.

## Claim boundary

This analysis remains CHIRPS `model_estimate` evidence on a fixed June 2026 current-boundary frame. It is not station-equivalent BMKG observation evidence, does not reconstruct historical administrative boundaries, and does not attribute any trend or regime change to anthropogenic climate change or downstream socioeconomic/disaster outcomes.

## Reproducible outputs

- `data/analysis/engine/historical_climate_trend_v1/m20-geography-trends.csv`
- `data/analysis/engine/historical_climate_trend_v1/m20-leave-one-year-out.csv`
- `data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv`
- `data/analysis/engine/historical_climate_trend_v1/m20-regional-trend.csv`
- `data/manifests/milestone20_historical_climate_trend.json`
