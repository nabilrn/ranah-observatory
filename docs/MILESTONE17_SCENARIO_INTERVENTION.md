# Milestone 17 — Scenario & Intervention Engine v1

M17 converts the current evidence base into explicit scenario contracts without turning predictive coefficients or associations into policy effects.

## Scenario library

The library contains seven scenarios:

- five quantitative **model-state sensitivity** scenarios inherited from the five preregistered M11 structural features;
- one rainfall/labor adaptation scenario blocked by the M15 identification gate;
- one disaster-risk-reduction scenario blocked by the M16 component-readiness gate.

Every scenario explicitly records evidence strength, uncertainty, implementation-horizon status, cost status, omitted mechanisms, and authorization flags.

## Quantitative sensitivity design

For each of the five M11 features and each of the three benchmark-qualified M11 targets, M17 applies the same symmetric perturbation:

`±0.5 training-fold standardized feature units`

The mapping uses all 19 outer-fold primary M11 coefficients. This produces 15 feature-target mappings.

The output is in target percentage points because M11 target transformations are identity while continuous features were standardized within training folds.

These are **predictive model deltas**, not treatment effects.

## What the results show

The fold-level coefficient dispersion is informative precisely because M17 does not suppress inconvenient mappings.

Examples for the `+0.5 SD` model perturbation:

- `mean_years_schooling` has a median modeled delta of about **-0.172 pp** for poverty, **+0.109 pp** for unemployment, and **+0.062 pp** for real-GRDP growth;
- `labor_force_participation` has median modeled deltas of about **+0.169 pp** for poverty, **-0.218 pp** for unemployment, and **+0.038 pp** for growth;
- `agriculture_share_grdp` has median modeled deltas of about **+0.249 pp** for poverty, **-0.122 pp** for unemployment, and approximately **0 pp** for growth;
- `manufacturing_share_grdp` has median modeled deltas of about **-0.111 pp** for poverty, **+0.173 pp** for unemployment, and **-0.010 pp** for growth;
- `rice_yield` has median modeled deltas of about **-0.260 pp** for poverty, **-0.012 pp** for unemployment, and **+0.015 pp** for growth.

These patterns are not a policy scorecard. Several state changes point in different directions across targets, and the coefficients are not causal.

## Cross-fold stability is retained, not hidden

M17 publishes sign retention rather than filtering mappings after seeing results.

Some mappings are highly sign-consistent across all 19 outer folds. Others are not. The clearest instability is `agriculture_share_grdp → real_grdp_growth`, where the `+0.5 SD` modeled delta is positive in 9 folds and negative in 10, giving dominant-sign retention of only about 0.526.

This disagreement is evidence about model sensitivity. M17 does not invent a stability threshold after seeing it and does not remove the row.

## Why these are not intervention effects

A structural feature can be associated with several mechanisms that the M11 linear predictive model does not identify.

For example, changing mean years of schooling in reality requires cohorts, education quality, migration, labor demand, and time. A standardized coefficient cannot tell us which policy delivers the state change, how long delivery takes, how much it costs, or whether the predictive relationship would remain invariant under intervention.

The same problem applies to labor-force participation, sector shares, and rice yield.

Therefore all five structural scenarios remain:

`quantitative_model_sensitivity_only`

with:

- `causal_effect_authorized = false`;
- `forecast_authorized = false`;
- `policy_recommendation_authorized = false`;
- `cost_benefit_authorized = false`.

## Rainfall/labor adaptation remains blocked

M14 found a stable lagged-rainfall association with the unemployment adverse expected-performance gap, but M15 did not authorize a causal rainfall → unemployment model.

M17 therefore retains the issue as a scenario-research target rather than assigning an adaptation effect size:

`blocked_causal_mapping`

No job effect, intervention magnitude, implementation horizon, or cost-benefit result is estimated.

## Disaster-risk reduction remains blocked

M16 integrated qualified hazard/climate/recorded-occurrence evidence but did not authorize a full disaster-risk synthesis because compatible exposure, vulnerability, capacity, and observed-impact components are incomplete.

M17 therefore retains disaster-risk reduction as:

`blocked_risk_mapping`

No avoided-loss or return-on-resilience-investment estimate is produced.

## Cost and implementation horizon

Current evidence does not identify program costs or implementation timing for these state changes.

Every scenario therefore reports:

- `cost_not_qualified`;
- `implementation_horizon_not_estimated`.

This is deliberate. Placeholder rupiah values or invented timelines would create more apparent precision than the evidence supports.

## Interpretation

M17 answers:

> If a preregistered M11 structural state variable is perturbed symmetrically inside the fitted predictive representation, how do the benchmark-qualified conditional expectations move across the 19 outer-fold models, and how stable is that mapping?

It does **not** answer:

> What policy should West Sumatra implement, and what causal outcome will that policy produce?

That stronger question remains dependent on future causal identification, implementation evidence, cost data, and—for disaster scenarios—a completed risk-component chain.

## Outputs

- `data/analysis/engine/scenario_intervention_v1/m17-scenario-library.csv`
- `data/analysis/engine/scenario_intervention_v1/m17-model-sensitivity-mappings.csv`
- `data/manifests/milestone17_scenario_intervention.json`
