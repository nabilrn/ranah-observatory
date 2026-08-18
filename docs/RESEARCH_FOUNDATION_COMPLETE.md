# Ranah Observatory — Initial Research Foundation Complete

## Scope

This document closes the **initial research foundation** defined in `research/RESEARCH_CHARTER.md`.

It does **not** claim that the final Ranah Observatory research program, final analytical engine, policy product, or public dashboard is complete.

The charter defines nine initial-success criteria. The authoritative closure manifest is:

`data/manifests/research_foundation_complete.json`

Current closure state:

- criteria: **9 / 9 complete**;
- closure errors: **0**;
- `initial_research_foundation_complete = true`;
- `final_ranah_observatory_product_complete = false`.

## The nine completed criteria

### 1. Canonical geography registry

Evidence: `data/registries/geographies.csv`

- 59 registry rows at closure;
- canonical Indonesia and West Sumatra anchors;
- exact 19 current West Sumatra kabupaten/kota child geographies;
- historical source-era geographies remain distinct rather than being silently projected into modern boundaries.

### 2. Source catalog

Evidence: `catalog/data-catalog.csv`

- 26 source-family records at closure;
- official/statistical, disaster, climate and geospatial lanes are catalogued separately;
- required core source families include BPS, BNPB, CHIRPS and BIG;
- discovery, qualification and access constraints remain explicit.

### 3. Indicator framework

Evidence: `data/registries/indicators.csv`

- 67 indicator definitions;
- 12 development domains;
- definitions, units, frequency, claim types and comparability notes are explicit.

### 4. 40–60 high-value indicators with provenance

Evidence: `data/manifests/milestone4_indicator_inventory.json`

- exactly 40 indicators count toward the initial milestone;
- provenance resolution and observation-ID integrity are enforced;
- missingness and held/unqualified candidates are not hidden merely to increase coverage.

### 5. Comparative Indonesian panel where feasible

Evidence: `data/manifests/milestone5_comparative_panel_audit.json`

- 38 current provinces;
- 2024–2025;
- six qualified BPS series;
- 456 long-form observations / 76 wide rows;
- current-boundary comparison is separated from historical geography reconstruction.

### 6. Exploratory historical analysis

Evidence: `data/manifests/milestone6_historical_eda_audit.json`

The analysis intentionally uses segmented evidence regimes rather than inventing one continuous West Sumatra time series:

- legal/statistical chronology and explicit gaps;
- 1971 source-era population anchor;
- 1981–2025 CHIRPS fixed-current-boundary climate diagnostics;
- modern BPS trajectories with trend qualification rules.

No causal or frontier model is falsely attributed to this milestone.

### 7. Baseline expected-performance/frontier model

Evidence: `data/manifests/milestone7_expected_performance_audit.json`

- transparent ridge expected-performance baseline;
- 38 provinces, West Sumatra as a full focal holdout;
- four qualified structural/capability predictors;
- leave-one-province-out validation;
- model must beat a naive benchmark;
- prediction residual is not relabelled as causal or monetary wasted potential.

### 8. Focused causal/quasi-causal case study

Evidence: `data/manifests/milestone8_complete_audit.json`

Case: 30 September 2009 West Sumatra earthquake.

- 19 kabupaten/kota × 2005–2013 = 171 observations;
- real GRDP outcome, physical USGS ShakeMap exposure;
- design and inference protocol locked before outcome fitting;
- geography/year fixed-effects event study;
- small-cluster-aware wild bootstrap;
- pretrend, placebo, influence and exposure-sensitivity diagnostics;
- final conclusion: no statistically robust differential real-GRDP effect detected by local shaking intensity over the study window.

That conclusion is not a claim that the earthquake had no economic impact and is not a total-loss estimate.

### 9. Climate/disaster case study relevant to West Sumatra

Evidence: `data/manifests/milestone9_hydroclimate_case_study.json`

Case: 2024 spatial alignment between long-baseline CHIRPS rainfall and official BNPB flood/landslide event counts.

- exact 19-geography overlap;
- CHIRPS 2024 annual rainfall compared with each geography's 1981–2023 baseline;
- all 19 geographies are wetter than their historical annual mean in 2024;
- flood-count association with relative annual wetness is weak-negative;
- landslide-count association is weak-positive;
- leave-one-out sensitivity does not turn annual rainfall into a simple disaster-burden proxy.

The case study therefore demonstrates an important evidence boundary: annual rainfall totals and annual recorded disaster counts are different layers and cannot be substituted for one another.

## What is now complete

The project now has the minimum trustworthy substrate required by the charter:

```text
source catalog
    ↓
qualified evidence + provenance
    ↓
canonical geography + indicator semantics
    ↓
qualified observations
    ↓
historical + comparative analysis
    ↓
baseline expected-performance model
    ↓
focused quasi-causal case study
    ↓
climate/disaster case study
```

The initial phase no longer depends on creating a polished dashboard or a spectacular single "wasted potential" number. Those were explicitly non-goals of the initial charter.

## What remains after the foundation

Foundation completion unlocks, but does not complete, the larger research program. Future work can expand:

- longer and richer historical quantitative reconstruction;
- stronger national regency/city comparator panels;
- additional structural predictors and endowment controls;
- frontier/efficiency models beyond the current expected-performance baseline;
- event-window rainfall and BMKG station validation;
- additional quasi-experimental case studies;
- spatial accessibility, land-use and remote-sensing indicators;
- multi-dimensional development-gap synthesis;
- intervention ranking and scenario analysis;
- uncertainty propagation from source → transformation → model → recommendation;
- eventually, a public research interface/dashboard.

Those are **post-foundation research phases**. They must not retroactively weaken the evidence rules established here.

## Reproduction

The closure is machine-audited. The permanent research-foundation workflow rebuilds the closure manifest from current evidence and fails if any criterion drops below its contract.

Core commands:

```bash
python scripts/validate_data_foundation.py
python -m scripts.audit_milestone9_hydroclimate_case_study --require-complete
python -m scripts.build_research_foundation_closure
python -m scripts.audit_research_foundation_complete --require-complete
PYTHONPATH=. python -m unittest tests.test_milestone9_hydroclimate_case_study tests.test_research_foundation_complete -v
```

A change that invalidates an underlying criterion must cause the final closure to fail rather than leaving a stale `9/9` badge.
