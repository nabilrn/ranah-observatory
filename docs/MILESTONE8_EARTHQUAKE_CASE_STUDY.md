# Milestone 8 — 2009 West Sumatra Earthquake Quasi-Causal Case Study

## Status

Milestone 8 satisfies the research-charter criterion:

> one focused causal or quasi-causal case study

Authoritative completion manifest:

`data/manifests/milestone8_case_study.json`

Authoritative completion audit:

`data/manifests/milestone8_complete_audit.json`

The study is complete **without claiming a statistically established nonzero earthquake effect**. Its final classification is:

`quasi_causal_estimate_no_statistically_robust_differential_effect_detected`

That distinction is central to the result.

## Research question

What was the differential effect of exposure to the 30 September 2009 West Sumatra earthquake on the subsequent real-GRDP trajectory of West Sumatra kabupaten/kota?

The study estimates whether areas experiencing stronger physical shaking followed different real-GRDP trajectories than areas experiencing weaker shaking, conditional on geography and year fixed effects.

It does not estimate total disaster loss, welfare loss, reconstruction cost, a production frontier, or long-run “wasted potential.”

## Analysis frame

- Geography: 19 West Sumatra kabupaten/kota.
- Years: 2005–2013.
- Observations: 171 geography-year rows.
- Outcome: total real GRDP at constant 2000 prices, natural-log transformed.
- Event date: 30 September 2009.
- Omitted event-study baseline: 2008.
- 2009: partial-treatment year because the earthquake occurred near the end of Q3.

The M8-specific geography contract qualifies the 19-unit analytical footprint for 2005–2013 without converting modern registry rows into a general historical backcast.

## Outcome-source reconstruction

### 2005–2008 block

The primary pre-period source is BPS Sumatera Barat / Bappeda:

`Perkembangan Ekonomi Sumatera Barat ... Tahun 2005-2009`

Its Table 22 contains all 19 kabupaten/kota and all five 2005–2009 constant-2000-price GRDP levels in million rupiah. The model panel uses 2005–2008 from this source.

### 2009–2013 block

The later comparative BPS source provides Table 13.1.2 with all 19 kabupaten/kota for 2009–2013 at constant prices.

The overlapping 2009 values were reconciled under a rule fixed before model fitting:

- materiality threshold: 0.5%;
- all 19 overlap differences passed;
- maximum absolute relative difference: about 0.162%, in Kota Payakumbuh;
- the later post-period source supplies the bridge value for 2009.

### Source inconsistencies

The post-period source contained internal level-versus-growth inconsistencies for Bukittinggi and Solok Selatan. These were not corrected by reverse-engineering levels from reported growth.

Independent local BPS publications were frozen and used instead. The resolution ledger records five decisions:

- four official-local-source overrides;
- one confirmation that the central value was already correct;
- original central values remain preserved alongside the resolved values.

The resolved panel therefore retains a complete provenance path rather than silently replacing inconvenient observations.

## Exposure

### Original preregistration

The first preregistration named heavy housing-damage share as treatment intensity.

During source qualification, before any outcome model was fit, the government-led DLNA housing table was found to report only 12 named West Sumatra geographies. Missing geographies were not coded as zero.

Housing damage also mixes physical hazard with vulnerability, construction quality, settlement patterns, and damage-assessment processes.

### Amendment 1

Before outcome-model fitting, the primary exposure was amended to physical shaking from the USGS ShakeMap for event:

`usp000h237` — M7.6, 30 km WSW of Pariaman.

Primary measure:

`area_mean_pga_pct_g`

The frozen USGS ShakeMap grid is summarized over the qualified BIG June-2026 19-kabupaten/kota polygon frame. This is explicitly a fixed-current-boundary zonal-summary frame; historical-boundary continuity is not claimed.

All 19 geographies have positive grid support.

Housing damage remains secondary validation only among the 12 geographies actually reported in DLNA Table 3.19.

## Model

The preregistered primary specification is:

`log(real_grdp_it) = alpha_i + gamma_t + Σ beta_k * exposure_z_i * 1[event_time=k] + epsilon_it`

where:

- `alpha_i` = geography fixed effects;
- `gamma_t` = year fixed effects;
- `exposure_z` = one-SD standardized area-mean PGA across the fixed 19-unit universe;
- 2008 (`k=-1`) is omitted;
- estimated event times are `-4,-3,-2,0,1,2,3,4`.

No covariate-selection search was performed in the primary model.

## Small-cluster inference

There are only 19 geography clusters. Conventional cluster-robust inference alone is therefore not treated as sufficient.

Before model fitting, the inference protocol locked:

- CR1 geography-clustered covariance with finite-sample correction;
- Rademacher wild-cluster-bootstrap-t;
- 1,999 draws;
- deterministic seed `20090930`;
- null-imposed coefficient tests;
- joint null-imposed pre-trend test;
- add-one bootstrap p-value correction.

## Identification diagnostics

### Pre-trends

The locked pre-trend screen passes:

- joint wild-cluster-bootstrap p-value: approximately 0.7245;
- maximum absolute pre-event coefficient: approximately 0.0103 log units per one-SD PGA;
- preregistered thresholds: joint p-value at least 0.10 and max absolute pre coefficient no greater than 0.10.

Passing this screen does not prove parallel trends.

### Placebo

The pre-period pseudo event in 2007 passes the locked placebo screen:

- wild-cluster-bootstrap p-value: approximately 0.4545;
- coefficient magnitude remains below the preregistered 0.10-log-unit screen.

### Influence

Named leave-one-out checks exclude separately:

- Kota Padang;
- Kabupaten Padang Pariaman;
- Kota Pariaman.

The maximum absolute change among the 2010–2013 primary coefficients is only about 0.00226 log units, below the pre-fit 0.10 threshold.

## Primary estimates

All primary 2009–2013 point estimates are negative, but none has a wild-cluster-bootstrap p-value at or below 0.10.

Approximate interpretation per one-SD higher area-mean PGA:

| Year | Event time | Log coefficient | Approx. percent transform | WCB p-value |
|---|---:|---:|---:|---:|
| 2009 | 0 | about -0.0037 | about -0.37% | about 0.103 |
| 2010 | 1 | about -0.0050 | about -0.50% | about 0.146 |
| 2011 | 2 | about -0.0051 | about -0.51% | about 0.279 |
| 2012 | 3 | about -0.0047 | about -0.47% | about 0.406 |
| 2013 | 4 | about -0.0043 | about -0.43% | about 0.472 |

Exact coefficients, CR1 standard errors, test statistics, bootstrap p-values, and bootstrap counts are preserved in:

`data/analysis/quasi_causal/m8-event-study-primary.csv`

The defensible interpretation is therefore:

> Under the preregistered design, stronger local shaking is estimated to have small negative differential real-GRDP coefficients during 2009–2013, but the study does not detect a statistically robust nonzero differential effect with the locked small-cluster inference procedure.

This is not equivalent to saying that the earthquake had no economic impact. The design estimates cross-area differential trajectories by shaking intensity, not the total destruction, welfare loss, asset loss, reconstruction cost, or province-wide macroeconomic effect common to all areas.

## Exposure-definition sensitivity

The pre-specified physical-exposure sensitivity models use:

- area-median PGA;
- area-90th-percentile PGA;
- area-maximum PGA;
- area-mean MMI.

All 2009–2013 sensitivity point estimates remain negative and small. No exposure definition was selected because it produced a more favorable significance result.

## Housing-damage validation

DLNA Table 3.19 provides 12 named West Sumatra geographies. The project parses those rows exactly and never fills the seven unreported geographies with zero.

Among the 12 reported units, physical shaking is positively correlated with realized housing damage. For area-mean PGA versus heavy-damage share, Pearson correlation is approximately 0.759 and Spearman correlation approximately 0.727.

This is descriptive validation that the physical-hazard measure broadly tracks realized damage. It is not a proof that the exposure is exogenous to every economic confounder.

## GRDP-growth robustness

A uniform official tabular 19-geography growth series for the full 2005–2013 event-study window could not be qualified from the frozen sources.

The project therefore does not fabricate one.

Instead it preserves:

- 95 directly tabulated official growth observations for 2009–2013;
- 152 level-to-level growth transitions derived from the resolved GRDP panel for 2006–2013, explicitly labelled `derived_statistic`.

The derived growth series is not substituted as an unpreregistered causal outcome.

## Final claim boundary

Allowed:

- the study is a completed quasi-causal case study;
- the identification screens required by the preregistered protocol pass;
- the model produces quasi-causal differential-effect estimates;
- no statistically robust nonzero differential real-GRDP effect is detected by the locked WCB procedure over 2009–2013.

Not allowed:

- “the earthquake had no economic impact”;
- “the earthquake reduced Sumbar GDP by X%” from these coefficients;
- treating the coefficients as total disaster loss;
- converting them directly into welfare loss or “wasted potential”;
- interpreting later recovery as evidence that the earthquake was beneficial;
- treating DLNA-unreported geographies as zero-damage controls.

## Reproduction

The permanent Milestone 8 audit rebuilds deterministic derived artifacts from committed evidence and then verifies that the repository remains byte-identical.

Core commands are implemented in the corresponding repository workflows and scripts:

- `build_milestone8_preperiod_grdp.py`
- `build_milestone8_postperiod_grdp.py`
- `reconcile_milestone8_grdp_overlap.py`
- `build_milestone8_grdp_panel.py`
- `resolve_milestone8_grdp_source_anomalies.py`
- `build_milestone8_event_study.py`
- `build_milestone8_housing_damage_validation.py`
- `build_milestone8_growth_robustness.py`
- `build_milestone8_case_study.py`
- `audit_milestone8_complete.py`

The pre-fit design gate is intentionally preserved rather than rewritten after model fitting. This keeps the timing of the preregistration, exposure amendment, source rules, and inference protocol auditable.
