# Milestone 14 — Bottleneck Association Engine v1

## Purpose

Milestone 14 screens for **stable associations** between lagged candidate variables and the adverse expected-performance gap produced by M13/M11.

It is deliberately not a causal-bottleneck model. A stable association is a reason to investigate a mechanism later, not evidence that changing the candidate would change the outcome.

## Primary gap object

Primary outcome per target/geography/year:

`M13 expected_gap_rmse_units`

Its orientation is fixed:

> positive = observed outcome is less favorable than the M11 conditional expectation.

Targets remain separate:

- poverty rate;
- unemployment rate;
- real GRDP growth.

No cross-target score or ranking is produced.

## Circularity guard

M14 does not reuse the five lagged structural predictors that built M11 expected performance:

- mean years schooling;
- labor-force participation;
- agriculture share of GRDP;
- manufacturing share of GRDP;
- rice yield.

This prevents a mechanically residualized exercise from being presented as a new bottleneck test.

Primary M14 candidates are instead:

- expected years of schooling;
- underemployment rate, except in the primary unemployment screen;
- CHIRPS annual rainfall;
- life expectancy as a shorter health-extension screen.

All candidate values are lagged one year.

## Locked diagnostics

For each preregistered target-candidate pair M14 reports:

- within-year Pearson association;
- within-year rank association;
- 4,999 geography-block permutations with seed `140014`;
- leave-one-geography-out stability;
- leave-one-year-out stability;
- all-benchmark-row support sensitivity;
- M12 favorable-peer-gap sensitivity.

A stable signal required all pre-locked gates:

- |within-year rank association| >= 0.20;
- permutation p <= 0.10;
- geography-LOO sign retention >= 0.90;
- year-LOO sign retention >= 0.80;
- >= 4 target years;
- >= 60 support-clean geography-year rows.

## Primary result

Exactly **one of 11** preregistered screens passes every stability gate:

### Lagged annual rainfall → unemployment adverse-gap association

- candidate: `annual_rainfall`;
- evidence type: CHIRPS `model_estimate`;
- target: `unemployment_rate` adverse expected gap;
- support-clean rows: 81;
- six target years: 2019–2024;
- 15 geographies survive the M11 support-clean filter at least once;
- within-year Pearson: about **+0.420**;
- within-year rank association: about **+0.458**;
- geography-block permutation p: about **0.0056**;
- geography leave-one-out sign retention: **100%**;
- year leave-one-out sign retention: **100%**;
- all-benchmark-row rank association, including M11 support-warning rows: about **+0.333**.

Under M13 orientation, the positive sign means:

> within the screened period, higher lagged annual CHIRPS rainfall tended to align with a larger adverse unemployment gap relative to M11 conditional expectation.

This is **not** evidence that rainfall causes unemployment.

Plausible non-causal explanations include omitted geography, accessibility, sector mix, climate-sensitive livelihoods, disaster exposure, infrastructure, or other persistent spatial characteristics. Annual rainfall also cannot resolve event timing or extreme-rainfall mechanisms.

## Important near-signal that remains rejected

The health-extension screen for life expectancy versus the real-GRDP-growth adverse gap produced:

- within-year rank association around **−0.360**;
- permutation p around **0.074**;
- geography/year LOO signs stable.

However the support-clean health-extension frame contains only **55 rows**, below the preregistered minimum of 60.

Therefore:

`stable_association_signal = false`

M14 does not relax the row threshold after seeing this result.

## Other primary screens

The other preregistered core screens do not satisfy the combined magnitude/permutation/stability gates.

Examples:

- expected years schooling vs poverty gap: rank association about +0.128, p≈0.638;
- underemployment vs poverty gap: about +0.094, p≈0.698;
- expected years schooling vs growth gap: about −0.223, p≈0.147;
- rainfall vs growth gap: about −0.083, p≈0.575;
- expected years schooling vs unemployment gap: about −0.078, p≈0.679.

Null or weak results are retained rather than removed from the output.

## Outcome-adjacent sensitivity

Underemployment is intentionally excluded from the primary unemployment-gap screen because it is another closely related labor-market outcome.

Its separate sensitivity output can describe numerical association but has:

`stable_association_signal_authorized = false`

regardless of the result.

## Why no SHAP or black-box model

The usable sample is small and clustered. The primary support-clean core screens contain 81 geography-year rows, and the health extension only 55.

M14 therefore prefers transparent association/stability diagnostics to training a flexible model solely to manufacture a feature-importance ranking.

## Interpretation boundary

M14 supports statements of the form:

> Candidate X shows / does not show a stable association with adverse gap Y under the locked screening design.

It does not support:

- X causes Y;
- X is the policy bottleneck to fix first;
- a one-unit intervention in X closes a quantified share of Y;
- feature importance identifies a mechanism;
- the associated gap is monetary wasted potential.

The one stable rainfall/unemployment association is therefore a **candidate mechanism for M15 causal-evidence prioritization**, not a policy conclusion.

## Outputs

- `data/analysis/engine/bottleneck_association_v1/m14-association-screen.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-geography-loo.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-year-loo.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-favorable-peer-sensitivity.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-outcome-adjacent-sensitivity.csv`
- `data/manifests/milestone14_bottleneck_association.json`
