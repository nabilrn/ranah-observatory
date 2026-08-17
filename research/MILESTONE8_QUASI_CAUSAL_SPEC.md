# Milestone 8 — 2009 West Sumatra Earthquake Quasi-Causal Design

## Charter criterion

Milestone 8 targets exactly one initial-success criterion from `research/RESEARCH_CHARTER.md`:

> one focused causal or quasi-causal case study

This document preregisters the design before any effect estimate is interpreted.

## Amendment 1 — physical shaking exposure, before outcome-model fitting

The original preregistration named `heavy_housing_damage_share` as the primary treatment intensity. During source qualification, **before any outcome model was fit**, the government-led DLNA housing table was found to report only 12 named West Sumatra kabupaten/kota rather than the intended 19-unit universe. The original stop rule therefore blocks that measure from serving as the full-sample primary exposure; absent areas are not coded as zero.

Housing damage also combines physical ground motion with building vulnerability, construction quality, settlement patterns, and reporting/assessment processes. Those characteristics may themselves correlate with local economic trajectories.

Before inspecting any fitted outcome effect, the project independently froze the USGS event `usp000h237` and its preferred ShakeMap Atlas `grid.xml` for the 30 September 2009 earthquake. The grid was then summarized over the already-qualified 19 BIG June-2026 Sumatera Barat kabupaten/kota polygons. All 19 geographies have positive grid support.

Amendment 1 therefore supersedes the original primary-exposure clause as follows:

- **Primary exposure:** `area_mean_pga_pct_g`, the arithmetic mean USGS ShakeMap PGA (%g) across ShakeMap grid-cell centers contained by each fixed-current-boundary BIG polygon.
- For regression interpretation the primary exposure may be standardized across the 19 analysis units as `z(area_mean_pga_pct_g)`. Standardization is a fixed linear transformation and must use the full pre-specified 19-unit exposure frame, not an outcome-selected subset.
- **Pre-specified physical-exposure sensitivities:** area-median PGA, area-90th-percentile PGA, area-maximum PGA, and area-mean MMI.
- **Housing-damage role after Amendment 1:** secondary validation / vulnerability diagnostic among the 12 geographies actually reported in the qualified DLNA table. It may not be completed by assigning unreported geographies zero damage.
- Spatial frame: BIG June 2026 fixed-current-boundary polygons. This is an explicit zonal-summary frame for the 2009 physical field; it is **not** a claim that 2026 polygons reconstruct every historical 2009 boundary detail.

Reason for amendment: source-completeness failure plus reduced exposure endogeneity. The amendment is recorded while `outcome_model_fit=false`, `quasi_causal_effect_estimated=false`, and `causal_claim_authorized=false`.

## Research question

What was the differential effect of exposure to the 30 September 2009 West Sumatra earthquake on the subsequent real economic trajectory of West Sumatra regencies/cities?

The primary estimand is a **quasi-causal differential effect by pre-specified physical shaking intensity**, not the total macroeconomic cost of the earthquake and not a monetary estimate of long-run "wasted potential".

## Why this case

The earthquake is a sharply timed, externally generated physical shock with highly heterogeneous local exposure. Official post-disaster assessments identify materially different damage across West Sumatra regencies/cities, USGS ShakeMap supplies a continuous physical ground-motion field, and BPS publications provide district/city real-GRDP evidence around the event.

Physical shaking is preferable to realized damage as the primary exposure because it is upstream of local building vulnerability and post-event damage assessment. This does **not** make the design automatically causal: geography, terrain, coastal proximity, market access, urban structure, sector mix, and reconstruction flows can still correlate with both shaking and economic outcomes. The design therefore remains quasi-experimental and must pass explicit diagnostics before causal language is permitted.

## Unit, geography, and period

- Unit: West Sumatra kabupaten/kota.
- Intended universe: 19 kabupaten/kota.
- Analysis window target: 2005–2013.
- Event date: 2009-09-30.
- Baseline year for event-study interactions: 2008.
- 2009 is a **partial-treatment year** because the earthquake occurred at the end of Q3; annual 2009 outcomes contain roughly nine pre-event months and three post-event months.

### Geography gate

The M8-specific geography contract qualifies the intended 19-unit analytical footprint for 2005–2013. This qualification is intentionally narrow and does not backfill the repository's general historical formation-date registry.

For physical-exposure aggregation, the USGS 2009 shaking grid is summarized over fixed BIG June-2026 polygons with an explicit `historical_boundary_continuity_claimed=false` flag. Modern polygon geometry is used as a stable zonal frame, not silently represented as a historical reconstruction.

## Outcome

Primary outcome:

- total real GRDP at constant 2000 prices;
- transformed as natural log of positive GRDP level;
- annual frequency.

Primary source target:

1. BPS/Bappeda publication covering district/city GRDP for 2005–2009 at constant 2000 prices;
2. BPS comparative table covering district/city GRDP for 2009–2013 at constant prices.

The overlapping 2009 values must reconcile under a rule documented **before** the combined analytical panel is used for estimation. If one source is explicitly later/revised, the bridge may use the later source for the overlap and post-period while preserving the earlier source as a cross-check; any material disagreement must remain visible.

Robustness outcome:

- official annual real-GRDP growth rate, when source definitions and revisions are consistent with the level series.

## Treatment / exposure

### Primary exposure after Amendment 1

`area_mean_pga_pct_g`

Source contract:

- event: USGS `usp000h237`, M7.6, 30 km WSW of Pariaman, 2009-09-30;
- product: preferred non-deleted USGS ShakeMap Atlas product;
- field: PGA, source unit `%g` / `pctg`;
- aggregation: arithmetic mean over ShakeMap grid-cell centers contained by each qualified BIG polygon;
- required coverage: exact 19/19 geographies with positive grid support.

The primary interaction variable may be expressed in raw `%g` or a pre-specified z-score. Published coefficients must state the scale explicitly.

### Pre-specified physical sensitivities

- `area_median_pga_pct_g`;
- `area_p90_pga_pct_g`;
- `area_max_pga_pct_g`;
- `area_mean_mmi`.

These are sensitivity specifications, not a menu for selecting the most significant result.

### Secondary damage validation

The original government DLNA housing measures are retained only where directly reported:

`heavy_housing_damage_share = heavily_damaged_houses / pre_disaster_housing_stock`

`any_housing_damage_share = (heavy + moderate + light damaged houses) / pre_disaster_housing_stock`

They may be used to check whether greater physical shaking broadly corresponds to greater realized damage among the 12 reported geographies and to illustrate the distinction between physical hazard and vulnerability. Missing districts may not be silently assigned zero damage.

## Primary design

Primary specification is a continuous-intensity two-way fixed-effects event study:

`log(real_grdp_it) = alpha_i + gamma_t + sum_{k != -1} beta_k * exposure_i * 1[event_time=k] + epsilon_it`

where:

- `alpha_i` = geography fixed effects;
- `gamma_t` = year fixed effects;
- `event_time = year - 2009`;
- 2008 (`k=-1`) is the omitted baseline;
- `exposure_i` = pre-specified physical shaking intensity from Amendment 1;
- pre-event coefficients diagnose differential trends by eventual shaking intensity;
- post-event coefficients estimate differential trajectories associated with earthquake exposure.

Because treatment occurs on 30 September, the 2009 coefficient is interpreted as a **partial-year immediate effect**. 2010 onward measures full-year post-event differential trajectories that may include both disruption and reconstruction responses.

## Identification assumptions

A quasi-causal interpretation requires all of the following to remain reasonably defensible:

1. **Parallel differential trends:** absent the earthquake, areas with stronger and weaker eventual shaking would have followed similar conditional log-GRDP trends.
2. **No anticipation:** economic outcomes before 30 September 2009 were not affected by anticipation of this specific earthquake.
3. **No simultaneous exposure-correlated shock:** another 2009 shock did not differentially hit the same areas in proportion to shaking intensity.
4. **Stable measurement:** GRDP definitions, price basis, revision status, and geography are sufficiently comparable across the analysis window.
5. **Exposure validity:** the frozen USGS ShakeMap field is a sufficiently credible ordering of local physical ground motion for the event.
6. **No outcome-driven treatment coding:** exposure transformations, thresholds, spatial summaries, and sample exclusions are set without using post-event GRDP results.
7. **Spatial-frame transparency:** fixed-current-boundary zonal aggregation does not create a false historical-boundary claim.

## Major confounders / threats

At minimum the analysis must discuss and, where feasible, diagnose:

- 2008–2009 global financial-crisis exposure and local sector composition;
- terrain/coastal geography and market access correlated with shaking intensity;
- urbanization and construction quality;
- trade, tourism, transport, and government-service concentration;
- Minangkabau International Airport / Padang Pariaman transport structure;
- differential reconstruction transfers and private rebuilding;
- geographic market access and remoteness;
- contemporaneous local disasters;
- measurement revisions in historical GRDP publications;
- spillovers from severely damaged economic centers to nominal controls;
- measurement error from summarizing a continuous shaking field over administrative polygons.

Reconstruction spending is especially important: a positive later coefficient would not mean the earthquake was beneficial. It may reflect replacement investment after destruction.

## Required diagnostics and falsification

Before upgrading any result to `quasi-causal estimate`, require:

1. at least three pre-event years with complete outcome coverage;
2. at least three full post-event years after 2009;
3. exact or explicitly reconciled 2009 source overlap;
4. qualified 19-unit geography for 2005–2013;
5. complete qualified primary physical exposure for all 19 modeled units;
6. event-study pre-trend coefficients reported, not hidden;
7. joint pre-trend diagnostic;
8. placebo event timing in pre-period years where estimable;
9. leave-one-out sensitivity for Padang, Padang Pariaman, and Pariaman;
10. primary area-mean PGA versus the pre-specified physical-exposure sensitivities;
11. housing-damage validation among reported DLNA geographies without zero-filling absent units;
12. sensitivity to excluding materially exposed donor/control units where a binary diagnostic is used;
13. sensitivity using official real-GRDP growth rather than log level where comparable;
14. influence diagnostics for the largest economy, Kota Padang;
15. uncertainty appropriate to the small number of geography clusters, with small-sample limitations stated explicitly.

## Inference rule

With only 19 geographic units, conventional cluster-robust standard errors may be unstable. The implementation must report this limitation and use a small-cluster-aware procedure where technically feasible, such as a wild cluster bootstrap, alongside conventional estimates for transparency.

Inference method may not be selected post hoc solely because it produces statistical significance.

## Claim taxonomy

Possible final classifications:

- `observed data`: source GRDP and DLNA housing-damage counts;
- `model-derived physical exposure`: USGS ShakeMap zonal summaries over the declared fixed polygon frame;
- `derived statistic`: damage shares, exposure standardization, and growth transformations;
- `quasi-causal estimate`: event-study differential effect **only if identification gates pass**;
- `association`: mandatory fallback if identification gates fail.

The study does not estimate:

- total welfare loss;
- total disaster damage/loss (the official assessment already has its own accounting framework);
- a production frontier;
- a policy counterfactual;
- long-run "wasted potential" in rupiah.

## Stop rules

Milestone 8 remains incomplete if any of the following hold:

- the 2005–2013 19-unit analytical geography cannot be qualified;
- fewer than three pre-event or three full post-event years survive qualification;
- the pre/post GRDP blocks use irreconcilable price bases or overlapping 2009 values conflict materially;
- the primary USGS physical exposure cannot be reproduced for exact 19-unit coverage;
- the design amendment is not demonstrably recorded before any outcome-model fitting;
- pre-trends show material exposure-correlated divergence that cannot be credibly addressed;
- the result depends on an outcome-driven exposure threshold, donor exclusion, or specification search;
- the sign or substantive conclusion is dominated by a single geography without a defensible reason;
- source snapshots, hashes, spatial aggregation, and transformations cannot be reproduced.

If these gates fail, the correct output is a documented association or failed identification attempt, not a forced causal estimate.

## Current status

Design status: **preregistered + Amendment 1 locked / outcome-data qualification in progress**.

Primary physical exposure candidate has exact 19/19 grid support. No outcome model has been fit, and no causal or quasi-causal effect has yet been estimated.
