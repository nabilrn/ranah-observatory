# Milestone 8 — Inference and Diagnostic Protocol

This protocol is locked **after source qualification and before any outcome-model fitting**. It does not change the case-study estimand in `MILESTONE8_QUASI_CAUSAL_SPEC.md`; it operationalizes the already-preregistered event-study diagnostics and small-cluster inference rules.

## Analysis frame

Primary outcome frame:

- exact 19 West Sumatra kabupaten/kota;
- annual 2005–2013 panel;
- 171 geography-year observations;
- 2005–2008 from qualified BPS Sumatera Barat Table 22;
- 2009–2013 from BPS comparative Table 13.1.2;
- 2009 overlap reconciled under the pre-fit 0.5% materiality rule;
- four source inconsistencies resolved only from independent local BPS publications, with original central values retained alongside the resolution record.

Primary exposure:

- `area_mean_pga_pct_g` from the frozen USGS ShakeMap event `usp000h237`;
- summarized over the declared BIG June-2026 fixed-current-boundary spatial frame;
- standardized across the fixed 19-unit analysis universe using population standard deviation (`ddof=0`):
  `exposure_z = (exposure - mean_19) / sd_19`.

No outcome values may be used to redefine exposure, the sample, the baseline year, or the diagnostic thresholds below.

## Primary event study

Fit OLS:

`log(real_grdp_it) = alpha_i + gamma_t + Σ[k != -1] beta_k * exposure_z_i * 1[event_time=k] + epsilon_it`

with:

- geography fixed effects;
- year fixed effects;
- event time `year - 2009`;
- 2008 (`k=-1`) omitted;
- coefficients for `k = -4,-3,-2,0,1,2,3,4`;
- 2009 (`k=0`) interpreted as partial-year exposure;
- 2010–2013 (`k=1..4`) interpreted as full-year post-event differential trajectories that can include disruption and reconstruction.

No covariate-selection search is allowed in the primary model.

## Conventional small-cluster covariance

Report geography-clustered CR1 covariance with 19 clusters and the finite-sample multiplier:

`(G/(G-1)) * ((N-1)/(N-K))`.

CR1 inference is retained for transparency but is not the sole inferential basis because 19 clusters are small.

## Wild-cluster bootstrap

Primary small-cluster-aware inference uses a Rademacher wild-cluster bootstrap-t:

- geography is the bootstrap cluster;
- Rademacher weights `{-1,+1}` with equal probability;
- `B = 1,999` bootstrap draws;
- deterministic RNG seed `20090930`;
- coefficient-specific tests impose the null coefficient equal to zero before generating bootstrap outcomes;
- the joint pre-trend test imposes all three pre-event coefficients equal to zero together;
- add-one p-value correction: `(extreme + 1) / (B + 1)`.

The bootstrap configuration may not be changed because another configuration gives a more favorable p-value.

## Parallel-trend diagnostic gate

Pre-event coefficients are `k=-4,-3,-2`; 2008 is baseline.

The identification screen passes only if:

1. the wild-cluster-bootstrap joint pre-trend p-value is **>= 0.10**; and
2. no pre-event coefficient has absolute magnitude greater than **0.10 log points per one-SD PGA exposure**.

The 0.10 p-value rule is a conservative screening convention, not proof of parallel trends. Passing it does not establish causality by itself, especially with only 19 clusters and three non-baseline pre years.

## Pre-period placebo

Use only 2005–2008 and define a pseudo event in 2007. Fit geography and year fixed effects plus:

`exposure_z_i * 1[year >= 2007]`.

The placebo screen passes if:

- wild-cluster-bootstrap p-value is **>= 0.10**; and
- absolute placebo coefficient is **<= 0.10 log points per one-SD exposure**.

This specification and threshold are fixed before the primary outcome model is fit.

## Influence diagnostics

Re-fit the primary event study after excluding, one at a time:

- Kota Padang;
- Kabupaten Padang Pariaman;
- Kota Pariaman.

Also calculate leave-one-geography-out point-estimate diagnostics for all 19 units when computationally practical.

The named-geography influence screen passes if every 2010–2013 (`k=1..4`) coefficient changes by no more than **0.10 log points per one-SD exposure** relative to the full-sample estimate under each named exclusion.

This threshold is a stability screen, not a significance criterion.

## Exposure-definition sensitivity

Repeat the event-study point estimates using the pre-specified physical exposure summaries, each standardized across the same 19 units:

- area-median PGA;
- area-90th-percentile PGA;
- area-maximum PGA;
- area-mean MMI.

Do not select a preferred result from this set based on significance. Report all of them. Material sign/magnitude instability weakens interpretation and must be disclosed even if the primary model is significant.

## Housing-damage validation

Housing-damage shares remain secondary validation only among geographies actually reported in the qualified government DLNA table. Unreported geographies must never be filled with zero.

The validation is used to compare physical hazard with realized damage/vulnerability, not to replace the pre-fit primary exposure.

## GRDP-growth robustness

Where official annual real-GRDP growth can be qualified consistently across the event window, report it as a robustness outcome. If a source-period/revision inconsistency prevents a comparable official-growth panel, document that limitation rather than reconstructing an "official" series silently from the level panel.

Derived log growth from the resolved level panel may be reported separately but must remain labelled `derived statistic`.

## Claim authorization

A statistically significant post-event coefficient is **not** enough for causal wording.

`quasi-causal estimate` may be authorized only if all required source, geography, exposure, pre-trend, placebo, influence, and small-cluster-inference gates pass and the result is not dominated by an unresolved source/revision issue.

If an identification gate fails, Milestone 8 may still document the completed design and estimates, but the public classification must fall back to `association` or `failed identification attempt`.

No result from this case study is automatically a total disaster loss, welfare loss, production frontier, policy counterfactual, or "wasted potential" estimate.
