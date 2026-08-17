# Milestone 7 — Baseline Expected-Performance Model Specification

## Charter criterion

Milestone 7 satisfies exactly one initial-success criterion from `research/RESEARCH_CHARTER.md`:

> one baseline expected-performance/frontier model

This milestone chooses an **expected-performance baseline**, not an efficiency frontier. A frontier/maximal-attainable model may be evaluated later, but it is not required to close Milestone 7.

## Research interpretation

The baseline asks a narrow question:

> Given a small set of qualified, current-boundary structural/capability characteristics observed for Indonesian provinces, what real GRDP per capita would a transparent cross-province model predict for West Sumatra?

The prediction is a **model estimate**, not a causal estimate, not a production frontier, and not a monetary estimate of “wasted potential.”

## Geography and reference period

- Unit of analysis: current Indonesian provinces.
- Geography regime: the 38-province current-boundary regime already established in Milestone 5.
- Preferred reference year: **2024**, because the current 38-province regime is explicitly qualified from 2024 onward and 2024 avoids using a future year as a feature source for the initial baseline.
- West Sumatra (`idn.13`) is the focal holdout and must not contribute its target value to final model fitting.

If the required structural features are not available with exact 38-province coverage for one common qualified year, the model must stop rather than silently mix years or boundary regimes.

## Target

Primary target:

- `real_grdp_per_capita`
- unit: million rupiah per person at constant 2010 prices
- model scale: natural logarithm of the positive target value.

The log scale is preregistered because provincial real GRDP per capita is strongly right-skewed and includes resource- and capital-intensive outliers.

## Predictor eligibility

The primary model may use at most **six** predictors because the current cross-section contains only 38 provinces.

Eligible predictor classes, in priority order:

1. human capital / schooling;
2. health capability;
3. population density or urbanization;
4. digital or physical connectivity;
5. sector structure, including resource/mining exposure where qualified;
6. other clearly structural/endowment proxies with national 38-province coverage.

Every selected feature must:

- come from a qualified source contract;
- cover exactly the same current 38 provinces for the model year;
- have explicit unit, period, selector, and geography semantics;
- contain finite values for all 38 provinces;
- be defensibly interpretable as a capability, structural characteristic, or endowment proxy rather than a direct restatement of the target.

### Primary-model exclusions

The following Milestone 5 outcomes are **not eligible as primary predictors** for the first baseline:

- `poverty_rate`;
- `gini_ratio`;
- `unemployment_rate`;
- `underemployment_rate`;
- `neet_rate`.

They are excluded to reduce outcome leakage and circular interpretation. They may be used later as diagnostics or alternative outcomes, but not to make the primary real-GRDP-per-capita prediction look artificially accurate.

No feature may be selected merely because it improves West Sumatra’s residual or supports an underperformance narrative.

## Model family

Primary estimator: **ridge linear regression** on `log(real_grdp_per_capita)`.

Rationale:

- transparent;
- appropriate for a small cross-section;
- stable under correlated capability predictors;
- deterministic;
- coefficients remain inspectable;
- substantially lower overfitting risk than a flexible tree ensemble at n=38.

Predictors are standardized using training-fold means and standard deviations only. Constant features are rejected.

Fixed ridge penalty grid:

`[0.0, 0.01, 0.1, 1.0, 10.0, 100.0]`

`0.0` is the unregularized linear baseline. No post-hoc expansion of the grid is allowed merely to improve the West Sumatra estimate.

## Holdout and validation protocol

### West Sumatra focal holdout

West Sumatra is removed before model selection and final fitting.

The final expected-performance estimate for West Sumatra must therefore be genuinely out-of-sample with respect to its target value.

### Hyperparameter selection

On the remaining 37 provinces:

1. run leave-one-province-out cross-validation for every preregistered ridge penalty;
2. standardize predictors within each training fold;
3. calculate prediction error on the held-out province;
4. select the penalty with the lowest mean squared error on the log-target scale;
5. ties choose the **larger** penalty to prefer the more regularized model.

### Naive benchmark

For each validation fold, compare against a training-fold mean-log-target predictor.

The model is not qualified as a useful expected-performance baseline unless its cross-validated RMSE on the 37 non-West-Sumatra provinces is lower than the naive benchmark RMSE.

## Final fit and West Sumatra estimate

After penalty selection:

1. standardize on all 37 non-West-Sumatra provinces;
2. fit the selected ridge model;
3. predict West Sumatra log real GRDP per capita;
4. report the log residual;
5. report the actual-to-predicted ratio and percentage residual;
6. back-transform the expected level with an explicitly documented retransformation rule.

### Locked level retransformation rule

Before fitting the model, Milestone 7 locks the level retransformation rule to a **Duan smearing correction**. On the final 37-province training fit, compute the arithmetic mean of `exp(observed_log_target - fitted_log_target)` and multiply `exp(predicted_log_target)` by that factor for the reported level-scale expected value. The uncorrected log prediction and `exp(predicted_log_target)` remain in the output so the correction is auditable.

## Uncertainty and support

The model must report:

- leave-one-province-out RMSE and MAE;
- naive-benchmark RMSE;
- selected penalty;
- coefficient table on standardized predictors;
- empirical cross-validation residual distribution;
- an exploratory prediction interval for West Sumatra derived from held-out residuals;
- whether each West Sumatra feature lies inside the min/max support of the 37-province training set;
- the maximum absolute training-standardized z-score of West Sumatra’s feature vector.

### Locked exploratory interval rule

Before fitting the model, Milestone 7 locks the exploratory interval to the empirical **2.5th and 97.5th percentiles** of selected-model leave-one-province-out log residuals, using linear interpolation between adjacent ordered residuals. The two residual quantiles are added to the West Sumatra predicted log target and exponentiated. This interval is explicitly descriptive/predictive; it is not a parametric confidence interval and not a causal uncertainty interval.

If West Sumatra is materially outside training support, the estimate must be labelled extrapolative rather than silently presented as comparable.

## Required sensitivity output

At minimum, produce one transparent sensitivity comparison:

- unregularized linear model (`lambda = 0`) versus the selected ridge model using the **same preregistered features and same 37-province training universe**.

This is diagnostic only. It does not permit feature shopping.

## Claim taxonomy

Primary model outputs are:

- `predictive/model estimate` for expected performance;
- `derived statistic` for residuals and ratios.

They are **not**:

- observed outcomes other than the actual source value;
- causal estimates;
- frontier efficiency scores;
- counterfactual policy effects;
- estimates of money “lost” by West Sumatra.

## Stop rules

Milestone 7 must remain incomplete if any of the following occur:

- fewer than four qualified structural predictors remain after semantic review;
- any selected predictor lacks exact 38-province coverage in the common reference year;
- West Sumatra target leaks into model selection/fitting;
- the model fails to beat the naive cross-validated benchmark;
- source/provenance contracts cannot be frozen and reproduced;
- model outputs cannot be regenerated deterministically from committed evidence.

If the baseline fails these gates, the correct result is a documented failed/insufficient baseline, followed by additional data work—not a weaker standard or a more flexible model chosen to force a positive result.
