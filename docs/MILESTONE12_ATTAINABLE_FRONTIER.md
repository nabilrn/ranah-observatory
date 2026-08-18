# Milestone 12 — Attainable Frontier Engine v1

## Purpose

Milestone 12 separates two concepts that must not be collapsed:

- **expected performance** — what M11 predicts conditionally from a preregistered structural profile and peer-year context;
- **empirical favorable reference** — a transparent finite-sample performance level represented by favorable peers.

M12 uses `frontier` as shorthand for the second concept. It does **not** estimate a theoretical physical maximum, guaranteed attainable outcome, causal policy counterfactual, or monetary value lost.

## Method selection before results

The method registry was frozen before M12 outputs were inspected.

Qualified:

1. conditional favorable residual quantile — primary district/city reference;
2. structural-neighbor favorable envelope — alternative district/city reference;
3. M7 national favorable residual quantile — national 2024 Sumatera Barat anchor.

Not used:

- classic DEA — rejected because current predictors are not defensible monotonic controllable production inputs and poverty/unemployment are undesirable rates;
- classic half-normal SFA — deferred because the short mixed-outcome panel does not justify a common one-sided inefficiency distribution;
- linear quantile regression — deferred rather than introduced after seeing M11 residuals.

## District/city primary frontier

For each M11 geography-year prediction, the focal geography is excluded from frontier calibration.

The reference is:

`M11 expected outcome + favorable quantile of other-geography cross-fitted residuals`

Locked quantiles:

- poverty: residual q10;
- unemployment: residual q10;
- real GRDP growth: residual q90.

These are designed as approximately favorable-decile conditional peer references, not hard maxima/minima.

### Calibration

The pre-specified acceptable exceedance band is 4%–20% of the 114 rows per target.

Observed calibration:

| Target | Nominal favorable quantile | Rows meeting/exceeding reference | Rate | Calibrated |
|---|---:|---:|---:|---|
| Poverty rate | q10 | 13 / 114 | 11.40% | yes |
| Unemployment rate | q10 | 13 / 114 | 11.40% | yes |
| Real GRDP growth | q90 | 11 / 114 | 9.65% | yes |

All three pass without changing the locked q10/q90 rules.

## Alternative structural-neighbor envelope

For every focal geography-year:

- use the other 18 geographies in the same target year;
- standardize the five lagged M11 structural predictors among those 18 peers;
- find six nearest peers in standardized Euclidean feature space;
- average the outcomes of the two most favorable among those six.

Pre-specified sensitivities use k=5 and k=7, still averaging the two most favorable peers. Sensitivities cannot replace locked k=6 because they look more dramatic or convenient.

## Method agreement

The two district/city methods are not identical, which is useful uncertainty information.

| Target | Reference Pearson | Reference Spearman | Distance Pearson | Distance Spearman | Distance-sign agreement | Median abs. reference difference |
|---|---:|---:|---:|---:|---:|---:|
| Poverty | 0.875 | 0.898 | 0.939 | 0.875 | 86.0% | 0.544 pp |
| Unemployment | 0.732 | 0.712 | 0.920 | 0.900 | 90.4% | 0.751 pp |
| Real GRDP growth | 0.988 | 0.886 | 0.927 | 0.520 | 79.8% | 0.444 pp |

The growth result deserves the most caution. M11's growth model only narrowly beat the naive benchmark, and although the two M12 reference levels correlate strongly, rank agreement of the resulting distances is much weaker than for poverty/unemployment.

M12 therefore preserves both methods rather than declaring one the truth.

## Signed frontier distance

M12 does not truncate distances at zero.

For poverty/unemployment:

`distance = observed - favorable_reference`

For growth:

`distance = favorable_reference - observed`

Positive values indicate a less-favorable observed outcome than the empirical reference. Negative values mean the observed outcome exceeded the favorable-quantile/envelope reference.

A negative distance is not an error: the reference is a quantile/envelope, not a theoretical hard boundary.

## M11 support inheritance

Every row carries M11 benchmark qualification and same-year marginal support diagnostics.

Although all three targets are benchmark-qualified and all three M12 quantile calibrations pass, only rows without an M11 support warning are authorized for substantive primary-frontier interpretation.

Each target has:

- 114 rows total;
- 33 support-warning rows;
- 81 rows authorized for primary frontier interpretation.

This retains extrapolation risk instead of deleting difficult rows.

## National Sumatera Barat anchor

The separate national lane uses M7's 37 non-Sumatera-Barat province cross-fitted log residuals and the existing M7 Sumatera Barat full holdout.

The locked national favorable reference uses the 90th percentile non-Sumatera-Barat residual.

Results for 2024:

- observed real GRDP per capita: **Rp34.17 million/person**, constant 2010 prices;
- M7 conditional expected level for context: **Rp36.34 million/person**;
- q90 conditional favorable peer reference: **Rp66.74 million/person**;
- arithmetic level difference relative to that reference: **Rp32.57 million/person**;
- observed/reference ratio: **0.512**;
- relative distance to the reference: **48.8%**.

### What Rp66.74 million does NOT mean

It does **not** mean:

- Sumatera Barat “should” produce Rp66.74 million per person;
- Rp66.74 million is the maximum attainable GRDP per capita;
- the Rp32.57 million arithmetic difference is economic value that was lost;
- multiplying Rp32.57 million by population produces a defensible wasted-potential estimate;
- the difference was caused by any feature in M7;
- moving a policy variable would cause Sumatera Barat to reach the reference.

The number is deliberately labelled a **2024 top-decile conditional empirical peer reference**. M7 itself has a broad prediction interval, so this national anchor should be read as an ambitious peer-performance reference with substantial model uncertainty, not a precise potential estimate.

M12 performs neither population aggregation nor multi-year accumulation.

## Why M12 does not use DEA/SFA just for appearance

A mathematically sophisticated efficiency score is only useful if the underlying production semantics are defensible.

The current M11 structural predictors include schooling, labor participation, sector shares, and rice yield. They are not a clean vector of controllable production inputs consumed to produce poverty, unemployment, and GRDP growth outputs. Treating them as DEA inputs would create a strong efficiency interpretation that the evidence does not justify.

Likewise, imposing a one-sided SFA inefficiency distribution across these mixed outcomes would add assumptions stronger than the current research question warrants.

M12 therefore prefers transparent empirical favorable-peer rules that can be directly audited from cross-fitted evidence.

## Outputs

- `data/analysis/engine/frontier_v1/m12-district-frontier.csv`
- `data/analysis/engine/frontier_v1/m12-district-method-summary.csv`
- `data/analysis/engine/frontier_v1/m12-neighbor-sensitivity.csv`
- `data/analysis/engine/frontier_v1/m12-national-west-sumatra-frontier.json`
- `data/manifests/milestone12_attainable_frontier.json`

## Downstream implication

M12 gives Phase 2 two different objects for later gap work:

1. a conditional expectation from M11;
2. an empirical favorable-peer reference from M12.

Milestone 13 may use those objects to build a multidimensional development-gap decomposition, but it may not simply relabel every positive frontier distance as inefficiency or monetary wasted potential.
