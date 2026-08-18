# Phase 2 — Final Analytical Research Engine Roadmap

## Status

The initial Research Charter foundation is complete (`9/9`). Phase 2 begins only after that closure and is explicitly **not** the public-dashboard phase.

The goal of Phase 2 is to turn the qualified evidence foundation into a reproducible analytical system that can answer the project's harder questions about expected performance, attainable performance, development gaps, bottlenecks, causal mechanisms, climate/spatial constraints, and intervention scenarios.

## Core discipline

Phase 2 inherits all Research Charter rules:

- evidence before narrative;
- provenance before visualization;
- reproducibility before scale;
- comparison before underperformance claims;
- prediction is not causation;
- uncertainty remains visible;
- policy recommendations distinguish evidence from assumptions.

Additional Phase 2 rule:

> **No analytical convenience may silently erase source, geography, temporal, methodology, price-basis, or claim-type regimes.**

A wide modelling matrix is a derived analytical view, not a replacement for the underlying evidence lineage.

## Planned milestones

### Milestone 10 — Analytical Panel v1

Build the first analysis-ready, current-boundary West Sumatra kabupaten/kota substrate from already-qualified canonical observations.

Outputs must preserve:

- exact 19 current kabupaten/kota;
- 2018–2025 analysis window;
- source observation and provenance lineage;
- claim type;
- source reference period;
- methodology/version and price basis;
- explicit missingness;
- indicator coverage diagnostics.

No imputation, temporal backfill, historical-boundary reconstruction, or model fitting is allowed in M10.

### Milestone 11 — Expected Performance Engine v2

Expand M7 from a single 2024 province-level proof-of-concept into a benchmarked expected-performance system with multiple outcomes and transparent validation.

Requirements include:

- preregistered outcome/feature families;
- geography-aware validation;
- simple baseline models before complex models;
- support/extrapolation diagnostics;
- uncertainty;
- no causal interpretation of predictive residuals.

### Milestone 12 — Attainable Frontier Engine

Estimate realistic upper-performance envelopes using multiple defensible frontier approaches where data support them.

Candidate methods may include:

- stochastic frontier analysis;
- DEA where input/output semantics are defensible;
- high-quantile regression/frontier models;
- constrained or distributional ML only when sample size and validation justify it.

Expected performance and attainable frontier must remain conceptually distinct.

### Milestone 13 — Development Gap Decomposition

Construct multidimensional development-gap outputs rather than one opaque score.

Candidate dimensions include:

- income/productivity;
- human capital;
- labor and livelihoods;
- structural transformation;
- infrastructure/connectivity;
- fiscal/institutional capacity;
- resilience/climate vulnerability.

No monetary "wasted potential" aggregation is permitted unless an explicit defensible accounting/counterfactual model is later qualified.

### Milestone 14 — Bottleneck Association Engine

Identify variables consistently associated with development gaps while preserving the distinction between association and causation.

Possible tools include:

- panel econometrics;
- partial dependence / accumulated local effects;
- permutation importance / SHAP where technically justified;
- spatial diagnostics;
- stability analysis across specifications and time windows.

Feature importance is not a causal bottleneck claim.

### Milestone 15 — Causal Evidence Expansion

Build a library of focused natural-experiment or quasi-experimental studies for mechanisms that matter to West Sumatra.

Candidate methods depend on identification opportunity, not preference:

- event study / DiD;
- synthetic control;
- interrupted time series;
- IV;
- RDD;
- spatial discontinuity.

Failed identification attempts remain valid outputs.

### Milestone 16 — Spatial & Climate Risk Engine

Integrate qualified spatial and environmental evidence, potentially including:

- rainfall/extreme rainfall;
- floods/landslides;
- topography and slope;
- land cover/use;
- night lights;
- urban expansion;
- transport accessibility;
- market access;
- watershed/catchment context.

Hazard, exposure, vulnerability, and observed disaster impact must remain separate objects.

### Milestone 17 — Scenario & Intervention Engine

Translate empirical evidence into transparent scenarios without pretending scenarios are observed causal truth.

Each scenario must state:

- intervention variable;
- assumed change;
- empirical/model mapping;
- evidence strength;
- uncertainty;
- implementation horizon;
- cost information when qualified;
- important omitted mechanisms and risks.

### Milestone 18 — Final Analytical Synthesis

Produce a coherent evidence graph linking:

`observed trajectory -> expected performance -> attainable frontier -> development gaps -> associated bottlenecks -> causal evidence -> spatial/climate constraints -> intervention scenarios -> uncertainty/evidence strength`

The synthesis must expose disagreements among methods instead of averaging them into false certainty.

## Phase 2 completion concept

Phase 2 is complete when the analytical engine can reproducibly answer the Research Charter's core questions with explicit evidence strength and uncertainty.

It does **not** require a polished public web application. The public product/dashboard is a later delivery layer over stable analytical outputs.
