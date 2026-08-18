# Milestone 14 — Bottleneck Association Engine Specification

## Phase 2 role

Milestone 14 searches for **stable non-causal associations** between context variables and M13 development-gap signals.

The word `bottleneck` in the milestone name is operational shorthand. No candidate becomes a causal bottleneck merely because it correlates with a gap.

M14 does not estimate treatment effects, policy elasticities, mediation effects, or causal feature importance.

## Primary association outcome

Primary outcome for association screening:

`M13 expected_gap_rmse_units`

This is the M13 expected-performance gap oriented so:

> positive = observed outcome is less favorable than the M11 conditional expectation.

M14 deliberately does **not** use M12 favorable-peer distance as the primary screening outcome because the favorable reference is intentionally ambitious and most ordinary observations are expected to fall short.

Sensitivity outcome:

`M13 favorable_peer_gap_rmse_units`

The favorable-peer sensitivity is restricted to rows where M13 `gap_interpretation_authorized=true`.

## Locked analysis window

Target years:

`2021–2024`

Feature years:

`2020–2023` (`t-1`)

Reason selected before association results:

- M10 has exact 19-geography coverage for all four preregistered candidate variables in 2020–2023;
- life expectancy qualified coverage begins in 2020;
- using one-year lag keeps candidate context temporally prior to the target gap;
- no candidate window is selected from observed association strength.

Footprint:

- 19 geographies;
- 4 target years;
- 76 geography-year rows per target;
- 3 targets;
- 228 target-geography-year association rows.

## Candidate variables

Exactly four lagged candidate variables are preregistered:

1. `expected_years_schooling`
   - domain: education/human-capital aspiration;
   - reason: not included among M11's five primary predictors because M11 retained mean years schooling as the single human-capital stock proxy.

2. `life_expectancy`
   - domain: health/human development;
   - reason: omitted from M11 primary model because qualified coverage begins only in 2020.

3. `underemployment_rate`
   - domain: labor-market slack/quality;
   - reason: excluded from M11 primary features because it is itself a labor-market outcome-like measure.

4. `annual_rainfall`
   - domain: climate context;
   - reason: CHIRPS remained a pre-specified M11 sensitivity only and is not treated as BMKG station-observation equivalence.

No candidate is added or removed after seeing M13 gaps.

### Explicit exclusions

M14 primary screening excludes:

- the five M11 primary predictors, to avoid simply rediscovering the variables that already construct the conditional expectation;
- poverty/unemployment/growth lags themselves;
- population_total because M10 contains only the SP2020 anchor;
- BNPB flood/landslide counts because qualified district/city detail is 2024 only;
- feature values at or after the target year;
- any candidate chosen because its coefficient/correlation is large.

## Association frame

For every target-geography-year row, materialize:

- target/dimension;
- target year;
- feature year = target year − 1;
- M13 expected gap in RMSE units;
- M13 favorable-peer gap in RMSE units;
- M13 support/interpretation flags;
- the four lagged candidate values;
- source semantics for CHIRPS and other candidates.

No imputation is permitted.

## Primary association statistic

For each `target × candidate`:

1. within each target year, subtract the cross-geography mean from both candidate and expected-gap values;
2. pool the 76 year-demeaned rows;
3. compute Spearman correlation of the year-demeaned candidate and year-demeaned expected gap.

Also report pooled year-demeaned Pearson correlation.

Year demeaning removes common target-year level shifts but does not establish causal identification.

## Annual stability diagnostics

For each `target × candidate × target year`, compute:

- Spearman correlation across 19 geographies;
- Pearson correlation across 19 geographies.

Report how many of the four annual Spearman correlations have the same sign as the primary pooled year-demeaned Spearman correlation.

Zero annual correlation counts as neither positive nor negative.

## Leave-one-geography-out stability

For each `target × candidate`, repeat the pooled year-demeaned Spearman correlation 19 times, each time excluding one geography and all four of its rows.

Report:

- minimum LOO Spearman;
- maximum LOO Spearman;
- median LOO Spearman;
- whether every LOO estimate preserves the primary pooled sign.

No geography is deleted from the published association because it weakens a result.

## Support-safe sensitivity

Repeat pooled year-demeaned Spearman after excluding rows with M13/M11 support warnings.

Report:

- support-safe row count;
- support-safe Spearman;
- whether its sign agrees with the primary all-row association.

This sensitivity does not replace the primary statistic.

## Favorable-peer sensitivity

Using only M13 rows with `gap_interpretation_authorized=true`, repeat the year-demeaned Spearman correlation between each lagged candidate and `favorable_peer_gap_rmse_units`.

This sensitivity answers whether a candidate covaries with distance from the ambitious favorable-peer reference; it is not used to qualify a primary association.

## Stable-association candidate rule

A `target × candidate` is labelled `stable_association_candidate=true` only when **all** of the following preregistered rules hold:

1. `abs(primary_year_demeaned_spearman) >= 0.25`;
2. at least `3 of 4` annual Spearman correlations have the same sign as the primary pooled association;
3. all 19 leave-one-geography-out pooled Spearman estimates preserve the primary sign;
4. support-safe sample contains at least `40` rows;
5. support-safe Spearman has the same sign as the primary association.

The rule does not use p-values and does not authorize causal interpretation.

Failure to meet the rule is not evidence of no relationship; it means M14 does not classify the association as stable under these diagnostics.

## Association direction

M14 does not preregister a desired sign.

For a candidate that passes stability, report only:

- `positive_association_with_adverse_gap`; or
- `negative_association_with_adverse_gap`.

This wording is descriptive. For example, a positive association between underemployment and adverse unemployment gap does not prove underemployment caused the gap.

## Candidate-specific semantic guards

### Expected years schooling

HLS is adjacent to mean years schooling, which was already used by M11. Association may reflect broader human-capital differences or residual structure; it is not an independent causal education effect.

### Life expectancy

Life expectancy is a broad human-development outcome and may jointly reflect income, health systems, demography, and historical conditions. Reverse causality/confounding remain plausible.

### Underemployment

Underemployment is itself a labor-market outcome and is especially vulnerable to conceptual overlap with unemployment-gap diagnostics.

### CHIRPS rainfall

CHIRPS remains `model_estimate` evidence with independent BMKG station validation pending. M14 rainfall associations do not establish event-day rainfall, flood causation, climate-change attribution, or station-observation equivalence.

## Output products

1. `data/analysis/engine/bottleneck_association_v1/m14-association-frame.csv`
2. `data/analysis/engine/bottleneck_association_v1/m14-feature-associations.csv`
3. `data/analysis/engine/bottleneck_association_v1/m14-year-specific-correlations.csv`
4. `data/analysis/engine/bottleneck_association_v1/m14-leave-one-geography-out.csv`
5. `data/analysis/engine/bottleneck_association_v1/m14-stable-association-candidates.csv`
6. `data/manifests/milestone14_bottleneck_association.json`

## Completion gate

M14 completes when:

- exact 228-row association frame exists;
- four candidates are complete over feature years 2020–2023 for exact 19 geographies;
- no imputation occurs;
- primary year-demeaned Pearson/Spearman are reported for all 12 target-candidate pairs;
- exact 48 annual target-candidate-year correlations are reported;
- exact 228 LOO target-candidate-geography diagnostics are reported;
- support-safe and favorable-peer sensitivities are reported;
- stable-association candidate flags use only the locked five-rule gate;
- no candidate is dropped because its association is weak or contrary to expectations;
- no p-value significance hunting is used to select candidates;
- no causal/policy/counterfactual/monetary-wasted-potential claim is emitted;
- focused tests pass;
- permanent read-only CI rebuilds outputs byte-for-byte;
- M13, M12, M11, M10, and Research Foundation 9/9 remain green.

## Claim taxonomy

Association outputs use:

- `claim_type=derived_association_diagnostic`;
- `causal_claim=false`;
- `bottleneck_causal_claim=false`;
- `policy_effect_claim=false`;
- `monetary_wasted_potential_claim=false`.

A stable candidate means only:

> The candidate's lagged cross-geography association with the adverse expected-performance gap is directionally and numerically stable under the preregistered M14 diagnostics.

It does **not** mean:

- changing that candidate would close the gap;
- the candidate is the root cause;
- the candidate is a policy priority by itself;
- its correlation coefficient is an elasticity;
- it should be ranked above a candidate that fails the stability gate.
