# Milestone 18 — Final Analytical Synthesis v1

## Criterion

Produce a coherent, reproducible evidence graph linking:

`observed trajectory -> expected performance -> attainable frontier -> development gaps -> associated bottlenecks -> causal evidence -> spatial/climate constraints -> intervention scenarios -> uncertainty/evidence strength`

M18 is a synthesis milestone. It does **not** introduce a new statistical model, retune an upstream result, or convert unresolved evidence into stronger claims.

## Closure semantics

M18 distinguishes two concepts:

1. **Phase 2 analytical engine complete** — the planned M10–M18 analytical architecture is reproducible and exposes evidence strength, uncertainty, and blocked claims;
2. **research question fully resolved** — the empirical evidence is sufficient to answer a Research Charter question without important unresolved scope/identification gaps.

Phase 2 may complete while individual Research Charter questions remain `bounded_partial` or `not_action_ready`.

## Research Charter questions

The synthesis must evaluate all five questions from `research/RESEARCH_CHARTER.md`:

- RQ1 — historical trajectory;
- RQ2 — attainable development;
- RQ3 — divergence;
- RQ4 — explanatory factors;
- RQ5 — action.

No question may be marked fully resolved merely because an upstream milestone is complete.

## Evidence graph nodes

M18 preregisters these synthesis nodes:

1. `observed_trajectory_foundation`
   - primary upstream: M6 + M10;
   - claim class: observed/derived evidence foundation;
   - limitation: historical coverage remains incomplete and historical boundary harmonization is not generally performed.

2. `expected_performance`
   - upstream: M11;
   - claim class: cross-fitted predictive/model estimate;
   - all three target models are benchmark-qualified;
   - residuals are not causal effects.

3. `attainable_reference`
   - upstream: M12;
   - claim class: empirical favorable-peer reference;
   - not a theoretical maximum or policy counterfactual.

4. `development_gaps`
   - upstream: M13;
   - claim class: derived differences relative to expected/favorable references;
   - dimensions remain separate;
   - no weighted composite or monetary aggregation.

5. `associated_bottlenecks`
   - upstream: M14;
   - claim class: stable association screening;
   - stable signals remain non-causal.

6. `causal_evidence`
   - upstream: M8 + M15;
   - claim class: quasi-causal evidence plus explicit failed identification attempts;
   - negative/null or identification-blocked findings remain valid evidence.

7. `spatial_climate_constraints`
   - upstream: M9 + M16;
   - claim class: hazard/climate/recorded-occurrence component evidence;
   - full disaster-risk synthesis remains unauthorized.

8. `intervention_scenarios`
   - upstream: M17;
   - claim class: predictive model sensitivity plus blocked intervention mappings;
   - no policy effect, forecast, ranking, cost-benefit, or recommendation.

9. `uncertainty_evidence_strength`
   - upstream: M10–M17 claim boundaries and diagnostics;
   - claim class: synthesis metadata;
   - disagreements and blocked claims must remain visible.

## Evidence graph edges

Edges must encode the logical dependency rather than a causal interpretation.

Required dependency edges:

- observed trajectory foundation -> expected performance;
- expected performance -> attainable reference;
- expected performance -> development gaps;
- attainable reference -> development gaps;
- development gaps -> associated bottlenecks;
- associated bottlenecks -> causal evidence;
- causal evidence -> intervention scenarios;
- spatial/climate constraints -> associated bottlenecks where used as candidates/context;
- spatial/climate constraints -> intervention scenarios as a readiness constraint;
- expected performance -> intervention scenarios for M17 model sensitivity;
- every analytical node -> uncertainty/evidence strength.

Edge type must be one of:

- `analytical_dependency`;
- `evidence_extension`;
- `readiness_constraint`;
- `uncertainty_annotation`.

No edge type may imply causality unless the underlying study itself authorizes a causal estimate.

## Research-question readiness states

Allowed readiness states:

- `bounded_answer` — a defensible answer exists within an explicitly limited analytical scope;
- `bounded_partial` — meaningful evidence exists but important scope/data gaps remain;
- `not_action_ready` — evidence is insufficient for ranking/choosing real interventions with expected impact, cost, and horizon.

M18 v1 preregisters the following expected interpretation logic, but the builder must derive the final state from upstream contracts rather than from desired narrative:

### RQ1 — Historical trajectory

Must remain `bounded_partial` while:

- historical boundary harmonization is not generally performed; and/or
- historical series coverage is sparse relative to the 1945-onward ambition.

### RQ2 — Attainable development

May be `bounded_answer` only for the explicitly modeled outcomes/time/geography regime when:

- M11 targets are benchmark-qualified; and
- M12 favorable-reference methods are calibrated.

It must explicitly exclude claims of theoretical maximum or universal attainable development across all dimensions.

### RQ3 — Divergence

Must remain `bounded_partial` unless the evidence identifies long-run divergence timing and comparable-region divergence across the Research Charter's broad dimensions.

M13 current-boundary 2019–2024 gap decomposition alone is insufficient for a fully resolved long-run divergence claim.

### RQ4 — Explanatory factors

May be `bounded_answer` only in the sense that the engine can distinguish stable association, quasi-causal evidence, and failed identification attempts.

It must not claim that the one stable M14 association is a causal explanation.

### RQ5 — Action

Must be `not_action_ready` while M17 has no causal policy counterfactual, no qualified costs, no implementation horizon, and blocked rainfall/disaster-risk intervention mappings.

## Required synthesis facts

M18 must preserve at least these upstream facts without recomputing or relabeling them:

- M10: 19 current kabupaten/kota, 2018–2025, 15 indicators, explicit missingness, no imputation;
- M11: 3/3 targets benchmark-qualified, predictive not causal;
- M12: 3 calibrated district target frontiers, empirical favorable references, not theoretical maxima;
- M13: 342 gap rows; expected-interval classifications 15 less favorable, 313 within, 14 more favorable; 50 primary-vs-alternative frontier sign disagreements remain visible;
- M14: exactly 1 stable association signal and zero causal analysis;
- M15: 1 completed quasi-causal study inherited, 2 not-identification-ready entries, 0 new causal models;
- M16: risk synthesis unauthorized; exposure/vulnerability/capacity/observed-impact gaps remain explicit;
- M17: 5 model-sensitivity scenarios, 2 blocked interventions, 15 mappings, no policy recommendation.

## Claim-boundary ledger

M18 must publish an explicit ledger for claims that remain forbidden or unsupported, including at minimum:

- definitive monetary wasted potential;
- theoretical maximum development;
- M11 residual = causal underperformance;
- M12 favorable reference = target that should be attained;
- M14 rainfall association = causal unemployment effect;
- M16 recorded event count = observed disaster impact;
- M16 component frame = composite disaster risk;
- M17 model sensitivity = policy treatment effect;
- policy ranking based on unqualified costs/horizons.

Each blocked claim must identify the evidence needed to upgrade it.

## Method disagreement preservation

M18 must not average away disagreement.

At minimum it must retain:

- M13 primary-vs-structural-neighbor frontier gap sign disagreement count;
- M17 feature-target mappings with low dominant-sign retention;
- M15 failed identification attempts;
- M16 blocked/missing risk components.

No post-hoc threshold may be introduced to hide an inconvenient result.

## Required outputs

1. `data/analysis/engine/final_synthesis_v1/m18-evidence-nodes.csv`
2. `data/analysis/engine/final_synthesis_v1/m18-evidence-edges.csv`
3. `data/analysis/engine/final_synthesis_v1/m18-research-question-readiness.csv`
4. `data/analysis/engine/final_synthesis_v1/m18-claim-boundary-ledger.csv`
5. `data/manifests/milestone18_final_analytical_synthesis.json`
6. `docs/MILESTONE18_FINAL_ANALYTICAL_SYNTHESIS.md`

## Completion gate

M18 v1 is complete only if:

- all M10–M17 completion manifests/audits remain green;
- all nine evidence nodes exist;
- all required evidence-graph dependency/constraint edges exist;
- RQ1–RQ5 each have exactly one readiness row with explicit limitation and next-evidence requirement;
- RQ1 remains historically bounded;
- RQ2 remains scope-bounded to modeled outcomes/regime;
- RQ3 does not become a long-run divergence claim;
- RQ4 distinguishes association from causal evidence;
- RQ5 remains not action-ready under current cost/horizon/causal constraints;
- blocked claims and method disagreements remain visible;
- no new model is fitted;
- no policy ranking or cost-benefit analysis is performed;
- no definitive monetary wasted-potential estimate is produced;
- permanent read-only CI rebuilds outputs byte-for-byte.

M18 completion closes **Phase 2 analytical-engine construction**. It does not mean the scientific research agenda, historical data collection, causal identification program, or future public product is finished.
