# Milestone 20 — Historical Climate Trend Engine

Status: **implementation under validation**.

M20 analyzes the qualified CHIRPS v3 annual-rainfall model estimates for 19 current West Sumatra kabupaten/kota over 1981–2025. It uses a robust Theil–Sen slope for trend magnitude, an autocorrelation-adjusted Mann–Kendall diagnostic for direction evidence, Holm family-wise correction across the 19 geography tests, and pre-specified split-period plus leave-one-year-out stability checks.

The public-facing interpretation is intentionally conservative. A geography is only authorized as a robust monotonic increase/decrease if every prefit gate passes. Otherwise it remains `no_robust_monotonic_trend` even when a raw slope is positive or negative.

This analysis remains CHIRPS `model_estimate` evidence on a fixed June 2026 current-boundary frame. It is not station-equivalent BMKG observation evidence, does not reconstruct historical administrative boundaries, and does not attribute any trend to anthropogenic climate change or downstream socioeconomic/disaster outcomes.

Final result counts are populated from the committed M20 manifest after validation/materialization.
