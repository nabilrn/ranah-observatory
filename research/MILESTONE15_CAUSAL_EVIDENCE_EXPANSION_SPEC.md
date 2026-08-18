# Milestone 15 — Causal Evidence Expansion v1 Specification

## Phase 2 role

Milestone 15 expands the project from one completed quasi-causal case study into a **causal evidence library** that records both successful designs and failed identification attempts.

The core rule is:

> A candidate mechanism is not upgraded to a causal study merely because an association looked interesting in Milestone 14.

Failed identification attempts are first-class research outputs. M15 may complete without fitting a new causal model when the newly reviewed candidates fail preregistered identification-readiness gates.

## Library entry states

Every candidate must receive exactly one state:

- `completed_quasi_causal_study` — an estimate exists and its identification diagnostics are documented;
- `identification_ready_model_not_yet_fit` — the design has enough evidence to authorize fitting;
- `not_identification_ready` — one or more hard gates fail, therefore no causal model may be fit;
- `abandoned_invalid_design` — the proposed estimand/design is conceptually invalid under available evidence.

No entry can be promoted because its expected sign would support a preferred narrative.

## Entry 1 — 2009 West Sumatra earthquake

Source: completed Milestone 8.

Question:

> Did stronger local physical shaking from the 30 September 2009 earthquake produce a differential real-GRDP trajectory across West Sumatra kabupaten/kota?

Status is inherited from the authoritative M8 completion audit:

`completed_quasi_causal_study`

M8 remains the only completed causal/quasi-causal estimate at M15 start.

M15 must not rewrite its result. The M8 conclusion remains that internal identification screens passed but no statistically robust differential real-GRDP effect by shaking intensity was detected over 2009–2013.

## Entry 2 — lagged rainfall and unemployment

### Why this candidate exists

M14 preregistered an association screen and found one stable signal:

- candidate: lagged CHIRPS annual rainfall;
- target: unemployment adverse expected-performance gap;
- within-year rank association about +0.458;
- geography-block permutation p about 0.0056;
- geography/year leave-one-out sign retention 100%.

This makes rainfall/unemployment a mechanism worth investigating. It does **not** make the M14 result causal.

### Readiness gates

A new causal weather-shock model is authorized only if all of the following hold:

1. **independent confirmation window** — the causal estimation/evaluation window must not substantially reuse the same target-year outcome sample that generated the M14 discovery signal;
2. **treatment measurement** — the climate treatment must have a qualified interpretation for the intended causal estimand; CHIRPS may remain model-estimate evidence, but station-equivalence may not be claimed without validation;
3. **temporal resolution** — annual rainfall must be sufficient for the proposed mechanism, or a higher-frequency extreme-rainfall measure must be qualified;
4. **spatial inference** — inference must address correlated weather shocks across neighboring geographies rather than relying only on naive independent-row assumptions;
5. **pre-specified estimand** — the causal estimand and lag structure must be fixed before the independent outcome window is inspected.

### Current decision rule

M14 uses target years 2019–2024. M10 currently extends unemployment only through 2025. A proposed 2019–2025 panel would reuse six of seven target years from the discovery sample and leave only one genuinely new annual outcome year.

Therefore the independent-confirmation gate fails.

Additional limitations remain visible:

- CHIRPS district rainfall is `model_estimate` evidence with independent BMKG station validation pending;
- annual rainfall is temporally coarse for flood/extreme-weather mechanisms;
- rainfall shocks are spatially correlated.

M15 therefore preregisters:

`not_identification_ready`

and **forbids fitting a new causal rainfall-unemployment model in v1**.

This is a selection-bias guard, not a claim that rainfall has no labor-market effect.

## Entry 3 — COVID-19 structural exposure and local economic outcomes

### Candidate design

A plausible design would interact a pre-pandemic district structural exposure with post-2020 years and study unemployment, poverty, or real-GRDP growth.

Candidate exposure classes available in M10 include pre-pandemic agriculture/manufacturing structure.

### Readiness gate

For an event-study / differential-trend design, M15 requires at least **three complete pre-event annual outcome years** before 2020 for the selected outcome and analytical geography regime.

M10 current-boundary analytical coverage begins in 2018. It therefore supplies only 2018 and 2019 before the 2020 shock.

Two annual pre-period points provide only one pre-event transition and are insufficient for the M15 minimum trend-diagnostic rule.

M15 therefore preregisters:

`not_identification_ready`

and forbids fitting a COVID structural-exposure event study from the current M10 window.

Historical extension of compatible district outcomes may reopen this candidate later.

## M15 completion concept

M15 v1 completes when the repository has a machine-readable causal evidence library with at least:

1. the completed M8 earthquake study;
2. the M14-generated rainfall/unemployment candidate audited against independent-confirmation, measurement, temporal-resolution, and spatial-inference gates;
3. a COVID structural-exposure candidate audited against a pretrend-data sufficiency gate;
4. explicit `model_fit_authorized` fields for every candidate;
5. no causal model fit for a candidate whose hard gate fails;
6. no causal claim created from an M14 association result;
7. permanent read-only CI proving the library is consistent with M8/M10/M14 evidence.

M15 v1 is a **causal-evidence governance and expansion milestone**, not a requirement to manufacture a second causal coefficient.

## Reopening rules

### Rainfall/unemployment can be reopened if, for example:

- several genuinely new post-M14 annual outcome years become available; or
- a qualified higher-frequency unemployment/labor outcome creates an independent validation window; and
- climate measurement/inference design is qualified for the chosen estimand.

### COVID structural exposure can be reopened if:

- compatible current-boundary district outcomes are extended backward to at least 2017, preferably earlier; and
- exposure is fixed from pre-pandemic evidence before post-shock outcomes are inspected.

## Forbidden interpretations

M15 v1 does not authorize:

- "rainfall causes unemployment";
- "COVID exposure caused the observed district gaps";
- fitting the same-data M14 signal as a new confirmatory causal study;
- relaxing pretrend requirements to obtain an estimate;
- calling `not_identification_ready` evidence of no effect;
- monetary wasted-potential aggregation.
