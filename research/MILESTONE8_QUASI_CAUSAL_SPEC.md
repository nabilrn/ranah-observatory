# Milestone 8 — 2009 West Sumatra Earthquake Quasi-Causal Design

## Charter criterion

Milestone 8 targets exactly one initial-success criterion from `research/RESEARCH_CHARTER.md`:

> one focused causal or quasi-causal case study

This document preregisters the design before any effect estimate is interpreted.

## Research question

What was the differential effect of exposure to the 30 September 2009 West Sumatra earthquake on the subsequent real economic trajectory of West Sumatra regencies/cities?

The primary estimand is a **quasi-causal differential effect by pre-specified disaster intensity**, not the total macroeconomic cost of the earthquake and not a monetary estimate of long-run "wasted potential".

## Why this case

The earthquake is a sharply timed, externally generated physical shock with highly heterogeneous local exposure. Official post-disaster assessments identify materially different damage across West Sumatra regencies/cities, while BPS publications provide district/city real-GRDP evidence around the event.

This does **not** make damage intensity random. Building vulnerability, urban structure, sector mix, terrain, reconstruction flows, and market access may be correlated with both damage and economic outcomes. The design therefore remains quasi-experimental and must pass explicit diagnostics before causal language is permitted.

## Unit, geography, and period

- Unit: West Sumatra kabupaten/kota.
- Intended universe: 19 kabupaten/kota.
- Analysis window target: 2005–2013.
- Event date: 2009-09-30.
- Baseline year for event-study interactions: 2008.
- 2009 is a **partial-treatment year** because the earthquake occurred at the end of Q3; annual 2009 outcomes contain roughly nine pre-event months and three post-event months.

### Geography gate

Current registry rows still state that historical formation dates are deferred. Before model fitting, the project must independently qualify that the intended 19-unit geography is boundary-consistent for 2005–2013, or version any exceptions explicitly. Modern codes must not be projected backward merely because names match.

## Outcome

Primary outcome:

- total real GRDP at constant 2000 prices;
- transformed as natural log of positive GRDP level;
- annual frequency.

Primary source target:

1. BPS/Bappeda publication covering district/city GRDP for 2005–2009 at constant 2000 prices;
2. BPS comparative table covering district/city GRDP for 2009–2013 at constant prices.

The overlapping 2009 values must reconcile within a documented tolerance before the two source blocks are combined.

Robustness outcome:

- official annual real-GRDP growth rate, when source definitions and revisions are consistent with the level series.

## Treatment / exposure

Primary exposure is continuous and fixed from the official 2009 post-disaster assessment:

`heavy_housing_damage_share = heavily_damaged_houses / pre_disaster_housing_stock`

Secondary exposure for robustness:

`any_housing_damage_share = (heavy + moderate + light damaged houses) / pre_disaster_housing_stock`

No severity weights may be invented after seeing the economic outcome.

Exposure must be frozen for the full 19-unit universe from one qualified assessment contract. Missing districts may not be silently assigned zero damage merely because they are absent from a table.

## Primary design

Primary specification is a continuous-intensity two-way fixed-effects event study:

`log(real_grdp_it) = alpha_i + gamma_t + sum_{k != -1} beta_k * exposure_i * 1[event_time=k] + epsilon_it`

where:

- `alpha_i` = geography fixed effects;
- `gamma_t` = year fixed effects;
- `event_time = year - 2009`;
- 2008 (`k=-1`) is the omitted baseline;
- pre-event coefficients diagnose differential trends by eventual damage intensity;
- post-event coefficients estimate differential trajectories associated with earthquake exposure.

Because treatment occurs on 30 September, the 2009 coefficient is interpreted as a **partial-year immediate effect**. 2010 onward measures full-year post-event differential trajectories that may include both disruption and reconstruction responses.

## Identification assumptions

A quasi-causal interpretation requires all of the following to remain reasonably defensible:

1. **Parallel differential trends:** absent the earthquake, high- and low-damage areas would have followed similar conditional log-GRDP trends.
2. **No anticipation:** economic outcomes before 30 September 2009 were not affected by anticipation of this specific earthquake.
3. **No simultaneous exposure-correlated shock:** another 2009 shock did not differentially hit the same areas in proportion to earthquake damage.
4. **Stable measurement:** GRDP definitions, price basis, revision status, and geography are sufficiently comparable across the analysis window.
5. **Exposure validity:** housing-damage shares measure local earthquake severity/vulnerability consistently enough to order treatment intensity.
6. **No outcome-driven treatment coding:** exposure thresholds, transformations, and sample exclusions are set without using post-event GRDP results.

## Major confounders / threats

At minimum the analysis must discuss and, where feasible, diagnose:

- 2008–2009 global financial-crisis exposure and local sector composition;
- urbanization and construction quality;
- trade, tourism, transport, and government-service concentration;
- Minangkabau International Airport / Padang Pariaman transport structure;
- differential reconstruction transfers and private rebuilding;
- geographic market access and remoteness;
- contemporaneous local disasters;
- measurement revisions in historical GRDP publications;
- spillovers from severely damaged economic centers to nominal controls.

Reconstruction spending is especially important: a positive later coefficient would not mean the earthquake was beneficial. It may reflect replacement investment after destruction.

## Required diagnostics and falsification

Before upgrading any result to `quasi-causal estimate`, require:

1. at least three pre-event years with complete outcome coverage;
2. at least three full post-event years after 2009;
3. exact or explicitly reconciled 2009 source overlap;
4. qualified 19-unit geography for 2005–2013;
5. complete qualified exposure for all modeled units;
6. event-study pre-trend coefficients reported, not hidden;
7. joint pre-trend diagnostic;
8. placebo event timing in pre-period years where estimable;
9. leave-one-out sensitivity for Padang, Padang Pariaman, and Pariaman;
10. primary heavy-damage exposure versus any-damage exposure sensitivity;
11. sensitivity to excluding materially exposed donor/control units;
12. sensitivity using official real-GRDP growth rather than log level where comparable;
13. influence diagnostics for the largest economy, Kota Padang;
14. uncertainty appropriate to the small number of geography clusters, with small-sample limitations stated explicitly.

## Inference rule

With only 19 geographic units, conventional cluster-robust standard errors may be unstable. The implementation must report this limitation and use a small-cluster-aware procedure where technically feasible, such as a wild cluster bootstrap, alongside conventional estimates for transparency.

Inference method may not be selected post hoc solely because it produces statistical significance.

## Claim taxonomy

Possible final classifications:

- `observed data`: source GRDP and housing-damage counts;
- `derived statistic`: damage shares and growth transformations;
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

- the 2005–2013 19-unit boundary regime cannot be qualified;
- fewer than three pre-event or three full post-event years survive qualification;
- the pre/post GRDP blocks use irreconcilable price bases or overlapping 2009 values conflict materially;
- treatment exposure is incomplete or mixes incompatible assessment revisions;
- pre-trends show material exposure-correlated divergence that cannot be credibly addressed;
- the result depends on an outcome-driven exposure threshold, donor exclusion, or specification search;
- the sign or substantive conclusion is dominated by a single geography without a defensible reason;
- source snapshots and transformations cannot be reproduced.

If these gates fail, the correct output is a documented association or failed identification attempt, not a forced causal estimate.

## Current status

Design status: **preregistered / data qualification in progress**.

No causal or quasi-causal effect has yet been estimated.
