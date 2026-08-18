# Milestone 19 — Dynamic Forecast Engine v1

## What was tested

M19 asks a narrow predictive question: can a pooled autoregressive ridge model, using only prior-year information, beat the district/city's own previous-year outcome as a one-year-ahead forecast?

Targets:

- poverty rate;
- unemployment rate;
- real GRDP growth.

Predictors for year `t` are measured at `t-1`:

- target's own lag;
- mean years of schooling;
- labor-force participation;
- rice yield.

The model is evaluated with strict rolling-origin backtests for 2021–2025. Every outer forecast year is predicted using only earlier target years. The baseline is own-lag persistence.

## Result

None of the three targets passed the preregistered qualification rule requiring both lower RMSE and lower MAE than persistence.

| Target | Dynamic ridge RMSE | Persistence RMSE | Dynamic ridge MAE | Persistence MAE | Qualified |
|---|---:|---:|---:|---:|---|
| Poverty rate | 0.4945 | 0.4649 | 0.4051 | 0.3636 | No |
| Unemployment rate | 0.9016 | 0.8308 | 0.6599 | 0.5688 | No |
| Real GRDP growth | 12.7623 | 2.5763 | 6.5968 | 1.5713 | No |

The poverty and unemployment models are modestly worse than persistence. The pooled growth model is much worse, indicating that this simple dynamic-linear specification is not adequate for annual growth over the tested period.

## Interpretation

This is a useful negative benchmark result.

For poverty and unemployment, the previous-year district/city value is already a strong short-horizon predictor. The three structural covariates do not add enough stable out-of-time predictive information in this sample to justify replacing persistence.

For real GRDP growth, the modern window contains large common shocks and regime changes. M19 does not infer the cause of the poor performance, but the result is consistent with the limitation of fitting a single pooled linear dynamic relationship across a short, shock-heavy period.

No alternative algorithm is searched post hoc in M19 merely to obtain a winning score.

## 2026 output boundary

M19 materializes 2026 model point forecasts and empirical residual intervals as diagnostics so that the pipeline is reproducible. However, because all three targets failed the backtest qualification gate:

- `public_substantive_use_authorized=false` for every 2026 forecast row;
- no M19 2026 forecast should be presented to the public as a decision-ready prediction;
- the outputs are retained for model research and comparison only.

## What M19 establishes

M19 establishes a reusable time-respecting forecasting harness:

1. lag construction from canonical panel data;
2. nested rolling-origin hyperparameter selection;
3. strict out-of-time outer backtesting;
4. hard persistence benchmark;
5. fail-closed forecast authorization;
6. empirical residual uncertainty;
7. deterministic artifact materialization.

Future forecasting work should use this harness or an equally strict temporal evaluation design. New model families must have a theory/data justification and must not be introduced simply because M19 failed.
