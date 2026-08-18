# Milestone 13 — Development Gap Decomposition Specification

## Phase 2 role

Milestone 13 turns the M11 conditional-expectation layer and M12 empirical favorable-peer layer into a transparent **multidimensional gap decomposition**.

It deliberately does **not** collapse all domains into one score.

M13 does not estimate causation, an intervention effect, a production inefficiency parameter, or a monetary value of "wasted potential".

## Locked scope

District/city analytical regime:

- exact 19 current West Sumatra kabupaten/kota;
- target years 2019–2024;
- three benchmark-qualified M11/M12 targets;
- 342 target-geography-year rows.

Dimensions:

1. `living_standards_inclusion` → `poverty_rate`;
2. `labor_market` → `unemployment_rate`;
3. `economic_dynamism` → `real_grdp_growth`.

The national 2024 `real_grdp_per_capita` favorable-peer reference from M12 is preserved as a separate `income_productivity_national_anchor`. It is not merged numerically with district/city outcomes.

## Two distinct gap concepts

### 1. Conditional expected-performance gap

This uses M11 expected performance.

All gaps are reoriented so:

> positive = observed outcome is less favorable than the reference.

For lower-is-favorable targets:

`expected_adverse_gap = observed - expected`

For higher-is-favorable targets:

`expected_adverse_gap = expected - observed`

A negative value means observed performance is more favorable than the M11 conditional expectation.

### 2. Favorable-peer gap

Primary favorable-peer gap comes directly from M12's signed primary distance:

`favorable_peer_gap = M12 primary_distance_to_favorable_reference`

M12 already orients this so positive = less favorable than the favorable peer reference.

The alternative structural-neighbor distance is retained separately:

`alternative_favorable_peer_gap`.

M13 never replaces the primary gap with whichever method produces the larger or smaller number.

## Expected-performance uncertainty classification

M11 provides an empirical focal-excluded prediction interval.

For each row classify observed performance relative to that interval:

### Lower-is-favorable targets

- `materially_less_favorable_than_expected` if `observed > interval_upper`;
- `materially_more_favorable_than_expected` if `observed < interval_lower`;
- `within_expected_interval` otherwise.

### Higher-is-favorable targets

- `materially_less_favorable_than_expected` if `observed < interval_lower`;
- `materially_more_favorable_than_expected` if `observed > interval_upper`;
- `within_expected_interval` otherwise.

This is a predictive interval classification, not a hypothesis test or causal significance test.

## Standardized gap diagnostics

Raw target units are not comparable across poverty, unemployment, and growth.

M13 therefore reports **RMSE-unit diagnostics** using the preregistered M11 cross-fitted model RMSE for each target:

`expected_gap_rmse_units = expected_adverse_gap / M11_model_RMSE`

`favorable_peer_gap_rmse_units = favorable_peer_gap / M11_model_RMSE`

`alternative_gap_rmse_units = alternative_favorable_peer_gap / M11_model_RMSE`

These diagnostics allow magnitude comparison on a common predictive-error scale, but they are not utilities, welfare weights, or ingredients for a hidden composite score.

No winsorization, clipping, or sign truncation is allowed.

## Method agreement

For each row report:

`frontier_gap_sign_agreement = sign(primary favorable-peer gap) == sign(alternative favorable-peer gap)`

Zero is treated as its own sign.

Method disagreement is an uncertainty signal and must remain visible.

## Interpretation eligibility

A district/city row is `gap_interpretation_authorized=true` only when M12 `primary_frontier_interpretation_authorized=true`.

This inherits:

- M11 target benchmark qualification;
- M12 target calibration;
- M11 same-year marginal support.

Rows that fail support remain in the decomposition but are blocked from substantive favorable-peer-gap interpretation.

The M11 expected-performance gap itself remains observable for all cross-fitted rows, but support warnings remain attached.

## Persistence decomposition

For each `geography × target`, summarize the six target years 2019–2024.

Report:

- total row count (must be 6);
- interpretation-authorized row count;
- support-warning row count;
- years with positive primary favorable-peer gap among authorized rows;
- years with zero/negative primary favorable-peer gap among authorized rows;
- positive-gap persistence rate among authorized rows;
- median raw expected gap;
- median raw primary favorable-peer gap;
- median RMSE-unit expected gap;
- median RMSE-unit primary favorable-peer gap;
- latest 2024 gap values;
- latest expected-interval classification;
- primary/alternative gap-sign agreement rate.

### Locked persistence labels

A label is assigned only when at least **4 of 6 rows** are interpretation-authorized.

Among authorized rows:

- `persistent_less_favorable_than_favorable_reference` if positive-gap rate >= `2/3`;
- `mostly_meets_or_exceeds_favorable_reference` if positive-gap rate <= `1/3`;
- `mixed_relative_to_favorable_reference` otherwise.

If fewer than four rows are authorized:

- `insufficient_supported_years`.

These thresholds are fixed before persistence outputs are inspected and are descriptive classifications only.

## Geography profile without composite score

For each geography, M13 produces one profile row with three parallel target columns rather than a weighted score.

For each target include:

- persistence label;
- authorized-year count;
- persistence rate;
- median RMSE-unit primary favorable-peer gap;
- 2024 RMSE-unit primary favorable-peer gap;
- 2024 expected-interval classification;
- 2024 support/interpretable flag.

Also report only **counts**, not weighted sums:

- number of targets with persistent less-favorable classification;
- number of targets mostly meeting/exceeding favorable reference;
- number of targets mixed;
- number with insufficient support.

No rank or league table is authorized from these counts in M13.

## National income/productivity anchor

Carry M12's 2024 West Sumatra national lane unchanged into a separate summary object:

- observed real GRDP/capita;
- M7 conditional expected level;
- M12 conditional favorable peer level;
- observed-minus-expected arithmetic difference;
- favorable-reference-minus-observed arithmetic difference;
- observed/reference ratios;
- M7 support context.

Important:

- the expected difference is not a causal loss;
- the favorable-reference difference is not inefficiency;
- neither difference may be multiplied by population;
- neither difference may be accumulated over time;
- neither difference is combined with district poverty/unemployment/growth gaps.

## Required outputs

1. `data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv`
2. `data/analysis/engine/gap_decomposition_v1/m13-persistence-by-geography-target.csv`
3. `data/analysis/engine/gap_decomposition_v1/m13-geography-profiles.csv`
4. `data/analysis/engine/gap_decomposition_v1/m13-national-income-anchor.json`
5. `data/manifests/milestone13_development_gap_decomposition.json`

## Completion gate

M13 completes when:

- exact 342 M11/M12 target-geography-year rows reconcile one-to-one;
- all raw expected and favorable-peer gaps reproduce their upstream arithmetic;
- all gap signs use the locked favorable orientation;
- RMSE-unit diagnostics reproduce M11 target RMSEs;
- no clipping/truncation/winsorization occurs;
- expected-interval classifications reproduce M11 intervals;
- M12 support/interpretation gates are inherited;
- primary/alternative disagreement remains visible;
- exact 57 geography-target persistence rows exist (`19 × 3`);
- exact 19 geography profiles exist;
- persistence thresholds remain fixed at >=4 supported years and 1/3 / 2/3 rates;
- no weighted composite score/rank is produced;
- the national income anchor remains a separate object;
- no causal/frontier-maximum/counterfactual/monetary-wasted-potential claim is emitted;
- focused tests pass;
- permanent read-only CI rebuilds all outputs byte-for-byte;
- M12, M11, M10, and Research Foundation 9/9 remain green.

## Claim taxonomy

- M11 expected gap: `model_estimate_difference`;
- M12 favorable-peer gap: `model_estimate_empirical_peer_reference_difference`;
- persistence label: `derived_descriptive_classification`;
- national income anchor: `model_estimate_context`.

All carry:

- `causal_claim=false`;
- `theoretical_maximum_claim=false`;
- `policy_counterfactual_claim=false`;
- `monetary_wasted_potential_claim=false`.

## Forbidden interpretations

M13 does not authorize statements such as:

- "this district is 40% inefficient";
- "education caused this gap";
- "the three gap dimensions sum to one development deficit";
- "a geography with two persistent dimensions ranks worse than one with one dimension";
- "Sumatera Barat lost the national income-anchor difference";
- "closing the statistical gap would automatically produce the reference outcome".

M13 answers only:

> Across separate development outcomes, where are observed results persistently less favorable than conditional expectations or empirical favorable-peer references, how large are those gaps on their native and predictive-error scales, and how robust are they to support and frontier-method diagnostics?
