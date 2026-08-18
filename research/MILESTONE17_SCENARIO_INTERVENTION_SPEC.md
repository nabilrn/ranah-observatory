# Milestone 17 — Scenario & Intervention Engine v1

## Criterion

Translate the qualified analytical evidence into transparent scenario contracts without presenting scenarios as observed causal truth.

M17 v1 separates:

1. **quantitative predictive sensitivity scenarios** — controlled perturbations of M11 model-state variables;
2. **blocked intervention scenarios** — policy-relevant ideas whose causal/risk mapping is not currently identified.

No scenario is a policy recommendation.

## Upstream contracts

M17 inherits these hard boundaries:

- M11 coefficients are descriptive predictive-model diagnostics, not causal effects;
- M14's rainfall/unemployment result is association only;
- M15 does not authorize a rainfall → unemployment causal model;
- M16 does not authorize disaster-risk synthesis because compatible exposure, vulnerability, capacity, and observed-impact components are incomplete.

M17 may not weaken any of those boundaries.

## Quantitative sensitivity family

M17 preregisters all five M11 primary structural features before inspecting M17 scenario results:

1. `mean_years_schooling`;
2. `labor_force_participation`;
3. `agriculture_share_grdp`;
4. `manufacturing_share_grdp`;
5. `rice_yield`.

Every feature is evaluated against all three M11 targets:

- `poverty_rate`;
- `unemployment_rate`;
- `real_grdp_growth`.

No feature/target mapping may be dropped because its sign is inconvenient.

## Symmetric perturbation

For every feature-target pair, M17 applies the same analytical perturbation:

`±0.5 training-fold standardized feature units`

Because M11 continuous coefficients are stored in training-fold standardized units, this perturbation can be mapped directly to each outer-fold coefficient.

For outer fold `g`:

`model_delta(+0.5 SD)_g = 0.5 × beta_g`

and

`model_delta(-0.5 SD)_g = -0.5 × beta_g`

The perturbation is symmetric so M17 does not select a preferred direction after inspecting coefficient signs.

## What the quantitative mapping means

The 19 outer-fold model deltas are summarized with:

- minimum;
- 10th percentile;
- median;
- 90th percentile;
- maximum;
- positive-sign fold share;
- negative-sign fold share;
- dominant-sign retention.

These summaries measure **predictive-model sensitivity and cross-fold coefficient dispersion**.

They do not estimate:

- a treatment effect;
- a policy elasticity;
- a structural causal parameter;
- a forecast after a real intervention;
- a welfare effect;
- a cost-benefit ratio.

A `+0.5 SD` scenario is an analytical model-state perturbation, not a promise that a government program can deliver a corresponding raw-unit change.

## Structural scenario contracts

Each of the five M11 feature scenarios must state:

- intervention/state variable;
- assumed change: symmetric `±0.5 SD`;
- empirical/model mapping: M11 outer-fold predictive coefficients;
- evidence strength: benchmark-qualified predictive, non-causal;
- uncertainty: outer-fold coefficient dispersion;
- implementation horizon: not estimated from current evidence;
- cost information: not qualified;
- omitted mechanisms: joint feature movement, general-equilibrium response, implementation feasibility, causal confounding, and raw-unit delivery mapping.

M17 must not rank the five scenarios by desirability or expected policy return.

## Blocked scenario 1 — rainfall/labor adaptation

M14 found one stable association between lagged CHIRPS annual rainfall and the unemployment adverse expected-performance gap.

M15 explicitly concluded that a new causal rainfall → unemployment model is not identification-ready because the discovery window would be largely reused and only 2025 is genuinely new annual unemployment evidence.

Therefore M17 may retain a `rainfall_labor_adaptation` scenario contract only as:

`blocked_causal_mapping`

No assumed policy effect, intervention size, job effect, or cost-benefit calculation is authorized.

## Blocked scenario 2 — disaster-risk reduction

M16 exposes qualified hazard/climate/recorded-occurrence objects but keeps compatible exposure, vulnerability, capacity, and observed impact incomplete for risk synthesis.

Therefore M17 may retain a `disaster_risk_reduction` scenario contract only as:

`blocked_risk_mapping`

No synthetic risk reduction, avoided-loss estimate, or investment-return calculation is authorized.

## Cost and implementation discipline

When cost evidence is absent, the scenario must say `cost_not_qualified`; it must not use placeholder rupiah values.

When implementation timing is not empirically identified, the scenario must say `implementation_horizon_not_estimated`; it must not invent a delivery schedule.

## Forbidden operations

M17 v1 must not:

- call M11 coefficients causal effects;
- convert standardized perturbations to raw intervention units without fold-specific raw-unit delivery evidence;
- choose only favorable coefficient signs;
- rank scenarios by policy attractiveness;
- convert M14 association into a rainfall intervention effect;
- override M15 identification blocks;
- override M16 risk-synthesis blocks;
- compute avoided disaster loss without observed-impact/exposure/risk mapping;
- create cost-benefit ratios without qualified cost data;
- estimate monetary wasted potential;
- claim that any scenario will occur.

## Required outputs

1. `data/analysis/engine/scenario_intervention_v1/m17-scenario-library.csv`
2. `data/analysis/engine/scenario_intervention_v1/m17-model-sensitivity-mappings.csv`
3. `data/manifests/milestone17_scenario_intervention.json`
4. `docs/MILESTONE17_SCENARIO_INTERVENTION.md`

## Completion gate

M17 v1 is complete only if:

- all five preregistered M11 features are retained;
- all three benchmark-qualified M11 targets are mapped for every structural feature;
- exactly 15 feature-target quantitative mappings are emitted;
- every mapping uses the same symmetric ±0.5 SD perturbation;
- all 19 outer-fold primary coefficients contribute to each mapping;
- rainfall/labor and disaster-risk candidate scenarios remain blocked;
- implementation horizon and costs are explicit even when unknown;
- no causal policy effect, ranking, forecast, cost-benefit, or monetary wasted-potential claim is emitted;
- permanent read-only CI rebuilds outputs byte-for-byte and upstream audits remain green.

M17 completion means the project has a reproducible **scenario semantics and sensitivity layer**. It does not mean the project has identified optimal policies.
