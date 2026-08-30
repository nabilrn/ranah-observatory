# Ranah Observatory — Final Model Validation

**Audit date:** 30 August 2026  
**Release role:** required evidence for the clean-main reproducibility sweep

Ranah Observatory has two different predictive model contracts that must not be conflated.

## M11 — conditional expected performance

M11 is a cross-fitted conditional expected-performance engine, not a future forecasting engine.

- 19 current Sumatera Barat kabupaten/kota.
- Three targets: poverty rate, unemployment rate, and real GRDP growth.
- Six target years, 2019–2024.
- 342 leave-one-geography-out cross-fitted predictions.
- Nested inner geography CV for ridge penalty selection.
- The held-out geography is excluded from its own model fit and uncertainty calibration.
- All three targets beat the preregistered same-year peer-mean benchmark on both RMSE and MAE.

This result authorizes bounded expected-performance comparisons only. It does not authorize causal interpretation, theoretical maxima, guaranteed policy gains, or future forecasts.

## M19 — strict one-year-ahead forecast backtest

M19 is the actual temporal forecast test.

- 19 current Sumatera Barat kabupaten/kota.
- Three targets: poverty rate, unemployment rate, and real GRDP growth.
- Rolling-origin outer forecast years 2021–2025.
- 95 strictly out-of-time predictions per target, 285 total.
- Nested rolling-origin ridge tuning using only earlier years.
- Benchmark: each district/city's own previous-year outcome (persistence).
- Qualification requires the dynamic ridge model to beat persistence on both RMSE and MAE.

### Result

**0 / 3 targets qualify for substantive 2026 forecasting.**

| Target | Dynamic ridge RMSE | Persistence RMSE | Dynamic ridge MAE | Persistence MAE | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| Poverty rate | 0.4945 | 0.4649 | 0.4051 | 0.3636 | blocked |
| Unemployment rate | 0.9016 | 0.8308 | 0.6599 | 0.5688 | blocked |
| Real GRDP growth | 12.7623 | 2.5763 | 6.5968 | 1.5713 | blocked |

The model-generated 2026 rows remain diagnostics only. They are not qualified substantive forecasts.

## Why failure is retained

The failure is a valid research result. The preregistered model family is not replaced post hoc merely to obtain a winning score. A future model family may be evaluated only as a separately specified research lane with its own validation contract.

## Reproducibility contract

Permanent CI exists for both lanes:

- `.github/workflows/milestone11-expected-performance-repro.yml` rebuilds M11, audits it, runs focused tests, and requires committed outputs to remain byte-identical.
- `.github/workflows/milestone19-dynamic-forecast-repro.yml` rebuilds M19, audits it, runs focused tests, and requires committed outputs to remain byte-identical.

The final release validator additionally runs `scripts/validate_final_model_testing.py` so release readiness cannot silently drop, invert, or blur these model results.

## Release interpretation

The public product may say that M11 supports bounded conditional expected-performance comparisons and that M19 failed the stricter future-forecast benchmark. It must not describe M11 as proof of forecasting accuracy, and it must not publish the blocked M19 2026 rows as qualified forecasts.
