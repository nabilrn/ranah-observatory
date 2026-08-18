# Milestone 14 — Bottleneck Association Engine v1

## Purpose

Milestone 14 screens a small preregistered set of lagged context variables for **stable non-causal associations** with M13 adverse expected-performance gaps.

The milestone name uses `bottleneck` as operational shorthand. Passing the stability gate does not make a variable a causal bottleneck, policy lever, or root cause.

## Why the primary outcome is the M11 expected gap

M14 uses M13 `expected_gap_rmse_units` as its primary association outcome.

This is deliberate. M12 favorable-peer references are calibrated around ambitious top/bottom-decile performance, so ordinary geographies are expected to fall short often. Using that frontier distance as the primary bottleneck signal would risk treating distance from an elite reference as evidence of failure.

M12 favorable-peer gaps remain a sensitivity only.

## Locked analysis window

- target years: 2021–2024;
- feature years: 2020–2023;
- one-year feature lag;
- 19 current West Sumatra kabupaten/kota;
- 76 geography-year rows per target;
- 228 target-geography-year association-frame rows.

## Preregistered candidates

Exactly four candidate variables were chosen before association results were inspected:

1. expected years of schooling;
2. life expectancy;
3. underemployment rate;
4. CHIRPS annual rainfall.

The five M11 primary predictors were intentionally excluded from M14 screening so the engine would not simply rediscover variables already used to construct the conditional expectation.

## Stability gate

A target-candidate pair is a `stable_association_candidate` only when all five rules pass:

1. absolute pooled year-demeaned Spearman >= 0.25;
2. at least 3 of 4 annual Spearman correlations preserve the pooled sign;
3. all 19 leave-one-geography-out estimates preserve the pooled sign;
4. support-safe sample contains at least 40 rows;
5. support-safe Spearman preserves the pooled sign.

No p-value threshold is used to select candidates.

## Results

Three of twelve target-candidate pairs pass the locked gate.

| Target gap | Candidate | Pooled year-demeaned Spearman | Annual sign consistency | LOO range | Support-safe Spearman | Stable |
|---|---|---:|---:|---:|---:|---|
| Unemployment adverse gap | Lagged CHIRPS annual rainfall | +0.386 | 4/4 | +0.315 to +0.443 | +0.529 | yes |
| Real-GRDP-growth adverse gap | Lagged expected years schooling | -0.273 | 4/4 | -0.372 to -0.226 | -0.267 | yes |
| Real-GRDP-growth adverse gap | Lagged life expectancy | -0.295 | 4/4 | -0.368 to -0.224 | -0.269 | yes |

All three also preserve the same broad direction in the favorable-peer-gap sensitivity:

- rainfall vs unemployment favorable-peer gap: Spearman about +0.542;
- expected years schooling vs growth favorable-peer gap: about -0.266;
- life expectancy vs growth favorable-peer gap: about -0.260.

### Poverty

No preregistered candidate passes the full stability gate for the poverty adverse gap.

Expected years schooling comes closest in directional stability, but its pooled Spearman is only about +0.210, below the locked absolute-0.25 threshold. M14 does not lower the threshold after seeing this result.

### Underemployment

Lagged underemployment does not pass the full gate for any of the three targets.

This matters because underemployment could easily have been narratively attractive as a labor-market "bottleneck". The preregistered diagnostics do not support elevating it to a stable M14 association candidate.

## Interpretation of the three stable candidates

### 1. Rainfall ↔ unemployment adverse gap

The positive association means that, within target years, geographies with higher lagged CHIRPS annual rainfall tend to have larger adverse unemployment gaps relative to M11 conditional expectation.

This does **not** establish that rainfall causes unemployment underperformance.

Plausible non-causal explanations include:

- geography and topography;
- agriculture dependence;
- urban/rural structure;
- infrastructure and accessibility;
- unmodelled local economic composition;
- persistent spatial differences correlated with rainfall;
- CHIRPS measurement/model characteristics.

CHIRPS remains `model_estimate` evidence with independent BMKG station validation pending. M14 does not claim station-observation equivalence, event-day rainfall effects, flood causation, or climate-change attribution.

### 2. Expected years schooling ↔ real-GRDP-growth adverse gap

The negative association means higher lagged HLS tends to coincide with a smaller adverse growth gap, or more favorable growth relative to M11 conditional expectation.

It is not a causal education elasticity.

HLS is closely related to broader human-development conditions and to mean years schooling, which M11 already uses. Residual confounding, common development trajectories, and model structure can all produce this pattern.

### 3. Life expectancy ↔ real-GRDP-growth adverse gap

The negative association likewise means higher lagged life expectancy tends to coincide with a smaller adverse growth gap.

Life expectancy is a broad accumulated human-development outcome. It may proxy health systems, historical income, urbanization, demography, public services, infrastructure, and other omitted factors. Reverse causality and long-run joint determination remain plausible.

## What did not pass

Nine of twelve target-candidate pairs fail at least one locked stability criterion.

M14 keeps these negative screening results. They are not deleted to make the engine appear more decisive.

Failure does not prove there is no relationship; it means the association is not sufficiently stable under the preregistered M14 diagnostics.

## Why no causal ranking is produced

M14 does not rank the three stable candidates by "importance".

A larger Spearman coefficient is not a larger policy effect, and candidates belong to different semantic domains. Association strength also does not account for intervention feasibility, cost, mechanism, confounding, or causal identification.

The stable-candidate output therefore explicitly sets:

- `causal_bottleneck_interpretation_authorized=false`;
- `policy_priority_interpretation_authorized=false`.

## Outputs

- `data/analysis/engine/bottleneck_association_v1/m14-association-frame.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-feature-associations.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-year-specific-correlations.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-leave-one-geography-out.csv`
- `data/analysis/engine/bottleneck_association_v1/m14-stable-association-candidates.csv`
- `data/manifests/milestone14_bottleneck_association.json`

## Downstream implication

M14 provides **hypothesis candidates**, not causal conclusions.

Milestone 15 — Causal Evidence Expansion — may use these and other substantively important mechanisms to search for genuine identification opportunities. A stable M14 association does not automatically earn an M15 causal study; identification quality, source availability, timing, and treatment variation remain the governing criteria.
