# Milestone 12 — Attainable Frontier Engine Specification

## Phase 2 role

Milestone 12 separates **conditional expected performance** from a more favorable empirical peer reference.

It does not estimate a physical maximum, a causal counterfactual, or a guaranteed policy-achievable outcome.

M12 uses the term **frontier** only for a finite-sample empirical favorable-performance reference. Public/machine-readable outputs must preserve labels that distinguish this from a theoretical production frontier.

## Two analytical lanes

### Lane A — current West Sumatra kabupaten/kota favorable references

Input:

- M11 cross-fitted expected-performance predictions;
- M11 model frame and preregistered lagged structural features.

Scope:

- exact 19 current West Sumatra kabupaten/kota;
- target years 2019–2024;
- targets:
  - `poverty_rate` — lower is favorable;
  - `unemployment_rate` — lower is favorable;
  - `real_grdp_growth` — higher is favorable.

Only M11 targets with `benchmark_qualified=true` are eligible for substantive M12 frontier-distance interpretation. Failed M11 targets must remain visible but blocked.

### Lane B — national 2024 West Sumatra province anchor

Input:

- M7 selected cross-fitted non-West-Sumatra province residuals;
- M7 West Sumatra full-holdout expected-performance estimate.

Target:

- `real_grdp_per_capita`, constant 2010 prices, 2024.

Purpose:

- provide one national conditional favorable-performance anchor for the province;
- do not aggregate the level difference into total or cumulative rupiah loss.

## Method qualification

The method registry is locked before frontier results are inspected:

`data/registries/milestone12_frontier_method_qualification.csv`

M12 v1 qualifies:

1. **conditional favorable residual quantile** — primary district/city method;
2. **structural-neighbor favorable envelope** — alternative district/city method;
3. **M7 national favorable residual quantile** — national province anchor.

Classic DEA is rejected for M12 v1 because the current predictors are not defensible monotonic production inputs and two primary outcomes are undesirable rates.

Classic half-normal SFA is deferred because one common one-sided inefficiency process is not justified for this short mixed-outcome panel.

Linear quantile regression is deferred rather than introduced post hoc after seeing M11 residuals.

## Primary district/city method — conditional favorable residual quantile

For each M11 target, geography, and target year:

1. take the focal row's M11 cross-fitted expected value;
2. collect primary M11 residuals for the **same target from the other 18 geographies only**, pooling the six target years;
3. compute a favorable residual quantile;
4. shift the focal expected value by that quantile.

Locked favorable quantiles:

- lower-is-favorable targets (`poverty_rate`, `unemployment_rate`): **10th percentile residual**;
- higher-is-favorable target (`real_grdp_growth`): **90th percentile residual**.

Thus:

`favorable_reference = expected + favorable_residual_quantile`

The focal geography's own residuals are excluded from its frontier calibration.

### Unified signed distance

For lower-is-favorable targets:

`distance_to_favorable_reference = observed - favorable_reference`

For higher-is-favorable targets:

`distance_to_favorable_reference = favorable_reference - observed`

Interpretation:

- positive: observed outcome is less favorable than the empirical favorable reference;
- zero: observed equals the reference;
- negative: observed outcome exceeds the favorable reference.

Distances are **not truncated at zero**. A quantile frontier is not a hard maximum/minimum.

## Primary calibration diagnostic

The favorable quantile is intended to represent approximately a top/bottom decile conditional peer reference.

For each target, report the fraction of 114 focal observations that **meet or exceed the favorable reference**:

- lower-is-favorable: `observed <= favorable_reference`;
- higher-is-favorable: `observed >= favorable_reference`.

Pre-fit calibration band:

`0.04 <= favorable_exceedance_rate <= 0.20`

This broad band is a diagnostic tolerance around the nominal 10% reference in a finite 114-row cross-fitted sample.

If a target lies outside the band, M12 still reports the result but sets `primary_frontier_calibrated=false`, blocking substantive frontier-distance interpretation for that target. M12 must not retune the quantile after seeing calibration.

## Alternative district/city method — structural-neighbor favorable envelope

For each focal geography-year:

1. use the same five lagged structural features preregistered in M11;
2. restrict peers to the other 18 geographies in the **same target year**;
3. standardize each feature using those 18 peers only;
4. compute Euclidean distance in the standardized feature space;
5. select the **6 nearest peers**;
6. among those six, take the mean outcome of the **2 most favorable peers**.

Favorable means:

- lowest outcome for poverty/unemployment;
- highest outcome for real GRDP growth.

Locked parameters:

- `k_neighbors = 6`;
- `favorable_neighbor_count = 2`.

This is an observed structural-peer envelope, not a production-function estimate.

### Pre-specified neighbor-count sensitivity

Repeat the alternative method with:

- `k=5`, favorable count 2;
- `k=7`, favorable count 2.

These sensitivities are reported only for stability. They cannot replace the locked k=6 method based on whichever gives a more dramatic distance.

## Method-agreement diagnostics

For each target compare primary and k=6 alternative methods using all 114 rows:

- Pearson correlation of favorable-reference levels;
- Spearman rank correlation of favorable-reference levels;
- Pearson correlation of unified signed distances;
- Spearman rank correlation of unified signed distances;
- sign agreement rate for whether `distance_to_favorable_reference > 0`;
- median absolute difference between method reference levels.

No agreement threshold is used to select one method over another. Disagreement is itself an uncertainty signal.

## Support and M11 qualification inheritance

Every district/city frontier row must carry forward:

- M11 `benchmark_qualified`;
- M11 `support_warning`;
- M11 cross-fitted expected value;
- M11 prediction interval.

Substantive primary frontier interpretation is authorized for a row only when:

1. target is M11 benchmark-qualified;
2. primary frontier calibration passes for that target;
3. row has `support_warning=false`.

Rows failing any condition remain in the output with explicit blocking flags.

## National province favorable anchor

M7 provides:

- a West Sumatra full-holdout predicted log real GRDP per capita;
- selected LOPO residuals for the 37 non-West-Sumatra provinces.

Locked national favorable residual quantile:

- 90th percentile of the 37 M7 selected LOPO log residuals.

National conditional favorable log reference:

`frontier_log = west_sumatra_predicted_log + q90_non_sumbar_crossfit_residual`

National conditional favorable level:

`frontier_level = exp(frontier_log)`

Distance:

`frontier_level - observed_real_grdp_per_capita`

Also report:

- observed/frontier ratio;
- percent distance relative to frontier;
- M7 expected level for context;
- M7 support diagnostics.

This is a **2024 conditional favorable peer reference**, not maximum GDP, a causal counterfactual, or money "lost" by West Sumatra.

The level difference may be expressed in the target unit (`million rupiah/person constant 2010`) but must not be multiplied by population or accumulated over years in M12.

## Output products

1. `data/analysis/engine/frontier_v1/m12-district-frontier.csv`
2. `data/analysis/engine/frontier_v1/m12-district-method-summary.csv`
3. `data/analysis/engine/frontier_v1/m12-neighbor-sensitivity.csv`
4. `data/analysis/engine/frontier_v1/m12-national-west-sumatra-frontier.json`
5. `data/manifests/milestone12_attainable_frontier.json`

## Completion gate

M12 completes when:

- all three M11 target × 19 geography × 6 year rows are represented;
- focal geography residuals are excluded from primary favorable-quantile calibration;
- favorable quantiles remain fixed at 0.10/0.90;
- primary calibration rates and pass/fail flags are reported without retuning;
- k=6 neighbor references and k=5/k=7 sensitivities are complete;
- method-agreement diagnostics are complete;
- M11 benchmark/support flags are inherited;
- the national M7 West Sumatra favorable anchor is reproduced from frozen M7 outputs;
- no DEA/SFA/quantile-regression result is introduced outside the locked method registry;
- no distance is truncated to manufacture non-negative "inefficiency";
- no causal/counterfactual/maximum-attainable/monetary-loss claim is emitted;
- focused tests pass;
- permanent read-only CI rebuilds all committed outputs byte-for-byte;
- M11, M10, and the 9/9 Research Foundation remain green.

## Claim taxonomy

District/city and national frontier outputs use:

- `claim_type=model_estimate` for conditional favorable references;
- `frontier_scope=empirical_favorable_peer_reference`;
- `theoretical_maximum_claim=false`;
- `causal_claim=false`;
- `policy_counterfactual_claim=false`;
- `monetary_wasted_potential_claim=false`.

## Forbidden interpretations

M12 does not authorize:

- “this is the maximum West Sumatra can achieve”;
- “the distance is inefficiency caused by feature X”;
- “West Sumatra lost Rp X because actual is below frontier”;
- “moving predictors to the frontier would cause the outcome to reach it”;
- “neighbor/frontier differences prove a policy intervention.”

M12 answers only:

> What favorable conditional performance levels are empirically represented by high-performing peers under transparent finite-sample reference rules, and how far are observed outcomes from those references?
