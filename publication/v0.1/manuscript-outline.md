# Ranah Observatory v0.1 — Manuscript Outline

Working title: **Ranah Observatory: A Reproducible Evidence Framework for Development Gaps, Socioeconomic Trajectories, and Climate-Disaster Constraints in West Sumatra**

Frozen analytical base: `e1571e63fd19222c0f6112d340b61ed5d7996e58`

Publication rule: every substantive result below is bound to one or more IDs in `claim-ledger.csv`. Context-only evidence cannot be upgraded into explanation; blocked claims cannot appear as positive conclusions.

## Abstract

Claims: `C11_EXPECTED_PERFORMANCE`, `C13_GAP_DISTRIBUTION`, `C14_RAINFALL_ASSOCIATION`, `N19_FORECAST_FAILURE`, `N20_MONOTONIC_RAINFALL`, `N21_REGIME_SHIFT`, `C22_LFP_TRAJECTORY`, `C22_UNEMPLOYMENT_TRAJECTORY`, `C22_GRDP_GROWTH_TRAJECTORY`, `C22_RICE_YIELD_TRAJECTORY`, `B01_MONETARY_WASTED_POTENTIAL`, `B09_POLICY_RANKING`.

The abstract should position v0.1 as a reproducible evidence framework with bounded empirical results, not as a definitive monetary wasted-potential estimate or policy-ranking paper. It should include at least one positive bounded result and the central negative qualification results.

## 1. Introduction

Claims: `C11_EXPECTED_PERFORMANCE`, `C12_EMPIRICAL_REFERENCE`, `C13_GAP_DISTRIBUTION`, `B01_MONETARY_WASTED_POTENTIAL`, `B02_THEORETICAL_MAXIMUM`, `B03_CAUSAL_RESIDUAL`, `B04_GUARANTEED_POLICY_GAIN`, `B09_POLICY_RANKING`.

### 1.1 Research motivation

Explain the difference between measuring observed outcomes, estimating bounded expected performance, constructing empirical favorable references, identifying model-relative gaps, testing associations and identification, and ranking policies.

### 1.2 Contribution

Frame the contribution as a reproducible claim-gated evidence architecture for West Sumatra. Emphasize explicit missingness, negative-result retention, source and methodology provenance, and fail-closed claim boundaries.

### 1.3 What this paper does not claim

Make the nine blocked claim classes visible early, with the complete table later in the paper.

## 2. Evidence architecture and data regimes

Claims: `X24_NATIONAL_COMPARATOR`, `X25_PUBLIC_FINANCE`, `X26_DISASTER_COMPONENTS`, `X27_INVESTMENT_HISTORY`, `X28_BROADER_PANEL`.

### 2.1 Primary modern kabupaten/kota regime

Describe the current-boundary 19-geography, 2018-2025 regime and explicit missingness. Distinguish Panel v1 from the separate M28 Panel v2 expansion.

### 2.2 Historical climate regime

Claims: `N20_MONOTONIC_RAINFALL`, `N21_REGIME_SHIFT`.

Describe CHIRPS 1981-2025 as model-estimate evidence on fixed current boundaries. State that independent station validation remains pending and is non-blocking for v0.1.

### 2.3 National comparator regime

Claim: `X24_NATIONAL_COMPARATOR`.

Describe the stable-32 province panel and why six current Papua-region provinces are excluded rather than backcast.

### 2.4 Fiscal, disaster, investment, and broader outcome evidence

Claims: `X25_PUBLIC_FINANCE`, `X26_DISASTER_COMPONENTS`, `X27_INVESTMENT_HISTORY`, `X28_BROADER_PANEL`.

Treat these datasets as qualified context unless an upstream completed analysis explicitly authorizes a stronger statement.

## 3. Methods and claim gates

Claims: `C11_EXPECTED_PERFORMANCE`, `C12_EMPIRICAL_REFERENCE`, `C13_GAP_DISTRIBUTION`, `C13_METHOD_DISAGREEMENT`, `C14_RAINFALL_ASSOCIATION`, `C15_IDENTIFICATION_DISCIPLINE`, `C17_PREDICTIVE_SENSITIVITY`, `N19_FORECAST_FAILURE`, `N20_MONOTONIC_RAINFALL`, `N21_REGIME_SHIFT`, `N22_SCHOOLING_POVERTY_TRAJECTORY`.

### 3.1 Cross-fitted expected performance

Describe M11 geography-out cross-fitting and the preregistered peer-mean benchmark. Preserve predictive/non-causal semantics.

### 3.2 Empirical favorable references and support rules

Describe M12 reference construction and M13 support qualification. Explicitly distinguish empirical reference from theoretical frontier.

### 3.3 Stable association versus causal identification

Describe M14 screening and M15 identification library. Association magnitude or p-value cannot override identification status.

### 3.4 Predictive scenario sensitivity

Describe M17 standardized model-state perturbations and why they are neither treatment effects nor forecasts.

### 3.5 Negative-result qualification designs

Describe the M19 persistence benchmark, M20 robust monotonic-trend gate, M21 segmented-regime predictive/stability gates, and M22 hierarchical-vs-independent-trend benchmark.

## 4. Results

### 4.1 Expected performance and development gaps

Claims: `C11_EXPECTED_PERFORMANCE`, `C12_EMPIRICAL_REFERENCE`, `C13_GAP_DISTRIBUTION`, `C13_METHOD_DISAGREEMENT`.

Report the 342 prediction/gap rows, expected-interval categories, support-authorized versus blocked rows, and 50-row reference-method sign disagreement.

### 4.2 Associated bottleneck signal and identification status

Claims: `C14_RAINFALL_ASSOCIATION`, `C08_EARTHQUAKE_NULL`, `C15_IDENTIFICATION_DISCIPLINE`, `B05_CAUSAL_RAINFALL_UNEMPLOYMENT`.

Report the rainfall-unemployment-gap association as non-causal and retain the earthquake non-directional quasi-causal result and identification failures.

### 4.3 Modern socioeconomic trajectories

Claims: `N22_SCHOOLING_POVERTY_TRAJECTORY`, `C22_LFP_TRAJECTORY`, `C22_UNEMPLOYMENT_TRAJECTORY`, `C22_GRDP_GROWTH_TRAJECTORY`, `C22_RICE_YIELD_TRAJECTORY`.

All seven indicators must appear. Report failures and qualified trajectory counts together.

### 4.4 Forecast qualification failure

Claim: `N19_FORECAST_FAILURE`.

Report dynamic-ridge versus persistence RMSE and MAE for poverty, unemployment, and real-GRDP growth. No substantive 2026 forecast follows.

### 4.5 Historical rainfall: monotonic trend and regime-shift qualification failures

Claims: `N20_MONOTONIC_RAINFALL`, `N21_REGIME_SHIFT`.

Report zero geography-level robust monotonic trends and the candidate 1998 break only alongside the failed predictive and stability gates.

### 4.6 Expanded context evidence after M18

Claims: `X24_NATIONAL_COMPARATOR`, `X25_PUBLIC_FINANCE`, `X26_DISASTER_COMPONENTS`, `X27_INVESTMENT_HISTORY`, `X28_BROADER_PANEL`.

Summarize coverage gained and held states without asserting that these additions explain M13 gaps.

## 5. Discussion

### 5.1 What is currently defensible

Claims: all `publishable_bounded` and `publishable_negative_result` claims used in Results.

Discuss the value of bounded empirical references, explicit support rules, retained method disagreement, and preregistered failures.

### 5.2 Why negative results matter

Claims: `C08_EARTHQUAKE_NULL`, `N19_FORECAST_FAILURE`, `N20_MONOTONIC_RAINFALL`, `N21_REGIME_SHIFT`, `N22_SCHOOLING_POVERTY_TRAJECTORY`.

Explain that failed gates constrain interpretation and reduce researcher degrees of freedom.

### 5.3 Evidence expansion does not equal identification

Claims: `X24_NATIONAL_COMPARATOR`, `X25_PUBLIC_FINANCE`, `X26_DISASTER_COMPONENTS`, `X27_INVESTMENT_HISTORY`, `X28_BROADER_PANEL`, `C15_IDENTIFICATION_DISCIPLINE`.

State clearly that richer context is not automatically explanatory or causal evidence.

### 5.4 Action readiness remains incomplete

Claims: `C17_PREDICTIVE_SENSITIVITY`, `B04_GUARANTEED_POLICY_GAIN`, `B08_SENSITIVITY_AS_POLICY_EFFECT`, `B09_POLICY_RANKING`.

List the missing ingredients for intervention ranking: qualified treatment effects, feasible raw-unit changes, costs, horizons, implementation constraints, risks, and uncertainty.

## 6. Limitations

Claims: `B01_MONETARY_WASTED_POTENTIAL`, `B02_THEORETICAL_MAXIMUM`, `B03_CAUSAL_RESIDUAL`, `B04_GUARANTEED_POLICY_GAIN`, `B05_CAUSAL_RAINFALL_UNEMPLOYMENT`, `B06_EVENT_COUNTS_AS_IMPACT`, `B07_COMPOSITE_DISASTER_RISK`, `B08_SENSITIVITY_AS_POLICY_EFFECT`, `B09_POLICY_RANKING`, plus relevant negative-result claims.

Cover current-boundary dependence, limited historical boundary harmonization, short modern panels, pending station validation, missing disaster-impact components, held investment quarter, structured missingness, model instability, and identification limits.

## 7. Conclusion

Claims: `C11_EXPECTED_PERFORMANCE`, `C13_GAP_DISTRIBUTION`, `C15_IDENTIFICATION_DISCIPLINE`, `N19_FORECAST_FAILURE`, `N20_MONOTONIC_RAINFALL`, `N21_REGIME_SHIFT`, `C22_LFP_TRAJECTORY`, `C22_UNEMPLOYMENT_TRAJECTORY`, `C22_RICE_YIELD_TRAJECTORY`, `B01_MONETARY_WASTED_POTENTIAL`, `B09_POLICY_RANKING`.

Close on the publication's main contribution: an auditable evidence substrate that identifies what can be said now and what additional evidence is required before stronger wasted-potential or policy claims become defensible.

## Planned publication objects

- Table T01: evidence and claim architecture.
- Table T02: modern panel and M28 expansion.
- Table T03: expected performance, references, and gaps.
- Table T04: M22 trajectory qualification.
- Table T05: M19-M21 negative-result qualification.
- Table T06: M24-M28 context evidence inventory.
- Table T07: nine blocked claims.
- Figure F01: evidence chain.
- Figure F02: M13 gap/support/disagreement summary.
- Figure F03: M22 trajectory classification matrix.
- Figure F04: M19 forecast benchmark failure.
- Figure F05: M20-M21 rainfall qualification diagnostics.
- Figure F06: M24-M28 evidence coverage expansion.
