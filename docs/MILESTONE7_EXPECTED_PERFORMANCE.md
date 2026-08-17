# Milestone 7 — Baseline Expected-Performance Model

## Status

Milestone 7 implements the charter criterion:

> one baseline expected-performance/frontier model

The implemented object is a **baseline expected-performance model**, not a production frontier.

The model is deliberately narrow. It asks whether West Sumatra's 2024 real GRDP per capita differs from the level predicted by a transparent cross-province relationship using four prequalified capability indicators. It does **not** estimate causality, policy effects, efficiency, or monetary "wasted potential".

## Why this model is intentionally simple

The qualified current-boundary comparative cross-section contains only 38 provinces. West Sumatra is held out completely, leaving 37 provinces for model selection and fitting. A flexible tree ensemble or deep neural network would be difficult to justify at this sample size and would add model-selection degrees of freedom without solving the main evidence problem.

Milestone 7 therefore preregisters ridge linear regression on the natural logarithm of real GRDP per capita. Ridge regression provides a transparent small-sample baseline, remains stable under correlated predictors, and can be validated with leave-one-province-out cross-validation.

The model specification was locked in `research/MILESTONE7_MODEL_SPEC.md` before the first model result was inspected. The penalty grid, West Sumatra holdout rule, validation benchmark, Duan retransformation, and empirical interval rule were all fixed before interpreting the estimate.

## Geography and target

- Reference year: **2024**.
- Geography regime: `bps_current_38_province_2024plus`.
- Target: `real_grdp_per_capita`.
- Target unit: million rupiah per person at constant 2010 prices.
- Model scale: `log(real_grdp_per_capita)`.
- Focal holdout: current-boundary West Sumatra, `idn.13`.

The 2024 target comes from the Milestone 5 comparative panel. West Sumatra's target is present in the frozen model frame for final evaluation only; the model code removes it before hyperparameter selection and fitting.

## Predictor qualification

Milestone 7 initially explored national BPS WebAPI metadata rather than reusing variable IDs from the West Sumatra domain. This was necessary because BPS dynamic-data variable IDs are domain-local: the same numeric ID can represent unrelated indicators in different domains.

The final primary model uses exactly four predictors:

| Feature | BPS var | Selector | Meaning |
|---|---:|---|---|
| `m7_rls_age15_plus` | 1429 | no turvar | Mean years of schooling, population age 15+ |
| `m7_hls_method_new` | 417 | no turvar | Expected years of schooling, new method |
| `m7_household_internet_access` | 398 | `Perkotaan+Perdesaan` (`191`) | Households that accessed the internet in the previous three months |
| `m7_household_pln_lighting` | 856 | `Perkotaan+Perdesaan` (`191`) | Households whose main lighting source is PLN electricity |

Important semantic limits are retained in `data/registries/milestone7_expected_performance_features.csv`:

- RLS var 1429 refers to population age 15+ and must not be relabelled as a differently defined IPM schooling component.
- HLS is an expected-years measure, not observed completed schooling.
- Internet is a household access measure, not individual internet use.
- PLN lighting is a household main-lighting-source measure, not a measure of grid reliability or electricity quality.

Poverty, Gini, unemployment, underemployment, and NEET were explicitly excluded from the primary predictor set to avoid turning correlated development outcomes into circular explanatory variables.

### Mixed geography source for HLS

BPS var 417 exposes a combined `Provinsi/Kabupaten/Kota/Indonesia` vertical. Milestone 7 does not treat all of those rows as provinces. The extraction contract retains only current BPS province vertical IDs represented by four digits ending in `00`, excludes the Indonesia aggregate `9999`, and then requires the result to match the canonical current 38-province registry exactly.

The resulting HLS feature has exactly 38 current provinces for 2024. The mixed source is preserved rather than silently rewritten as a province-only source.

## Frozen evidence and model frame

Live BPS responses were frozen under `data/snapshots/bps/milestone7/` for variables 1429, 417, 398, and 856. Each series has the raw dynamic-data snapshot, SHA-256 checksum, normalized source-native long table, period metadata, and series manifest.

`scripts/build_milestone7_feature_frame.py` rebuilds the exact model frame from those frozen sources. It fails if any registered feature is missing, a selector changes, a selected value is non-finite, a feature does not resolve to exactly the current 38 provinces, or the target geography footprint differs from the predictor footprint.

The frozen feature frame contains 4 predictors, 38 provinces, 152 predictor observations, and 38 model rows.

West Sumatra's 2024 frozen values are:

| Variable | Value |
|---|---:|
| RLS age 15+ | 9.72 years |
| HLS | 14.30 years |
| Household internet access | 91.89% |
| PLN main lighting source | 98.95% |
| Actual real GRDP per capita | 34.16975 million rupiah/person |

## Model selection

Penalty grid, fixed before fitting:

`[0.0, 0.01, 0.1, 1.0, 10.0, 100.0]`

West Sumatra is removed first. For each penalty, the remaining 37 provinces undergo leave-one-province-out cross-validation. Predictor standardization is recomputed inside each training fold. The naive comparator predicts the training-fold mean log target.

The selected penalty is **0.1**.

Validation results for the selected model:

- LOPO RMSE on log target: **0.49616**.
- LOPO MAE on log target: **0.37843**.
- Naive LOPO RMSE: **0.60931**.
- RMSE reduction relative to the naive benchmark: approximately **18.6%**.

The model therefore passes the preregistered benchmark gate.

The unregularized model is retained as the required sensitivity case. It produces a very similar West Sumatra expected level, so the focal result is not an artifact of choosing a particular small ridge penalty.

## West Sumatra estimate

The frozen 2024 observed real GRDP per capita is **34.16975 million rupiah/person**.

The selected ridge model predicts a log target of approximately `3.51079`. The raw exponentiated prediction is approximately **33.47 million rupiah/person**. Because the model was preregistered to use a Duan smearing correction for the reported level estimate, the reported expected level is **36.33643 million rupiah/person**.

This gives an actual / expected ratio of **0.94037** and a percentage residual relative to the smearing-corrected expected level of **-5.96%**.

The OLS sensitivity expected level is approximately **36.45168 million rupiah/person**, close to the selected ridge estimate.

### Why the log residual and level residual have different signs

The uncorrected log-scale prediction is slightly below the observed log target, so `observed_log - predicted_log` is positive. The preregistered Duan correction raises the back-transformed expected level to account for retransformation bias. The smearing-corrected expected level is therefore above the observed level, giving a negative percentage residual on the reported level scale.

Both quantities are retained because they answer different mathematical questions. The project must not quietly substitute one for the other.

## Uncertainty and support

The exploratory interval is derived from the empirical 2.5th and 97.5th percentiles of selected-model LOPO log residuals, using the rule locked before fitting.

For West Sumatra, the resulting level interval is approximately **14.11 to 92.49 million rupiah/person**.

This interval is extremely wide. That is material evidence about the limitations of a 37-province cross-sectional baseline and is a reason not to overstate the focal residual.

All four West Sumatra feature values lie inside the univariate min/max range of the 37-province training set. The largest absolute training-standardized feature z-score is about **1.11**, so the focal prediction is not flagged as marginal feature extrapolation under this limited support diagnostic.

## Coefficients are not causal effects

Some fitted conditional coefficient signs are counterintuitive. In the selected standardized ridge model, for example, HLS and PLN lighting carry negative conditional weights while RLS and household internet access carry positive weights.

Those signs must **not** be interpreted as claims that increasing schooling expectancy or electricity access lowers economic output. With only 37 training provinces, correlated capability indicators, omitted structural variables, and large resource/capital-city heterogeneity, the coefficients are predictive conditional weights. They are not identified causal effects.

This is precisely why Milestone 7 stops at an expected-performance baseline. Causal interpretation belongs to a later explicitly designed causal study.

## What Milestone 7 establishes

Milestone 7 establishes that a small, preregistered, evidence-traceable capability model contains more out-of-sample signal than a naive mean benchmark and produces a reproducible West Sumatra expected-performance estimate.

It does **not** establish that West Sumatra has a 5.96% causal productivity shortfall, that 5.96% of GRDP is "wasted", that the gap can be converted into rupiah lost, that any of the four predictors causes the residual, that the prediction is a maximum attainable frontier, or that changing one predictor would move GRDP by its fitted coefficient.

The wide prediction interval makes these restrictions especially important.

## Reproduction

From frozen repository evidence, no live BPS call is required:

```bash
python scripts/build_milestone7_feature_frame.py
python scripts/build_milestone7_expected_performance_model.py
python scripts/audit_milestone7_expected_performance.py --require-complete
python -m unittest tests.test_milestone7_expected_performance -v
```

The permanent Milestone 7 workflow also requires a clean `git diff` after regeneration so committed artifacts must remain byte-identical to a fresh deterministic rebuild.
