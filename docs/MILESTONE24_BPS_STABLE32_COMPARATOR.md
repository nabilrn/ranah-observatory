# Milestone 24 — BPS Stable-32 Province Comparator Panel

Status: **complete; national comparison universe materially expanded**.

M24 establishes a nationally comparable BPS province-level panel for **32 current Indonesian provinces over 2018–2025**. It deliberately excludes the six current Papua-region provinces from this longitudinal regime rather than silently backcasting across the 2022 provincial division.

## Result

All six locked BPS selector contracts qualify across the full eight-year window:

1. poverty rate — March total;
2. Gini ratio — March urban+rural;
3. unemployment rate — August;
4. underemployment rate — source annual period;
5. real GRDP per capita — constant 2010 price component;
6. NEET rate — source annual period.

The credentialed probe covers **48 candidate-year cells (6 series × 8 years)**. Every cell preserves the exact pre-existing selector contract and contains one finite selected value for each of the 32 stable provinces.

The frozen canonical panel contains:

- **1,536 observations** (`6 × 32 × 8`);
- **48 provenance records** (`6 × 8`);
- **48 frozen BPS dynamic-data snapshots** plus checksums;
- a probe-to-freeze semantic-identity verification covering all 48 snapshots.

No selector was changed after the probe, no values were imputed, and no Papua geography was backcast to current boundaries.

## Why 32 provinces instead of 38

The goal is a defensible longitudinal comparison regime, not maximum row count. The current Papua-region province codes 91, 92, 94, 95, 96, and 97 are excluded because treating all six current units as if they had comparable current-boundary histories throughout 2018–2025 would require a separate historical boundary reconstruction.

The resulting panel therefore represents a deliberately restricted **stable-32 comparison universe**. It must not be described as full-territory Indonesia without mentioning the exclusion.

## What this unlocks

M24 materially improves the evidence substrate for:

- national province-level comparison of West Sumatra against peers;
- RQ3 comparative divergence analysis over 2018–2025;
- future province-level attainable-performance and external-validation experiments when an estimand has sufficient features/outcomes within this exact regime.

It does **not** directly enlarge the 19-kabupaten/kota training sample used by M10/M11/M22. Province and district/city levels remain separate analytical regimes unless a future design explicitly justifies cross-level modeling.

## Source and provenance

The data were retrieved from the official BPS WebAPI national domain using the repository `BPS_API_KEY` GitHub Secret. The secret is not persisted in repository outputs. The repository stores credential-free source snapshots, SHA-256 checksums, normalized source rows, exact selector metadata, source update metadata, and canonical provenance.

The Stage 1 probe and Stage 2 freeze were run separately. Stage 2 was allowed to proceed only after all six candidates passed the locked probe. A dedicated verifier then confirmed that every frozen payload had the same semantic digest as the payload that passed the probe.

## Claim boundary

M24 is an evidence-acquisition and harmonization milestone, not a statistical model. It does not establish causal relationships, development rankings, a theoretical frontier, or a monetary value of unrealized potential. Stable administrative treatment also does not prove that every BPS statistical methodology was unchanged across all years; each downstream analysis must retain the series-specific methodology and reference-period semantics.

## Reproducible outputs

- `data/manifests/milestone24_bps_stable32_probe.json`
- `data/analysis/engine/bps_stable32_v1/m24-probe-coverage.csv`
- `data/processed/bps/comparative_stable32/source/`
- `data/processed/bps/comparative_stable32/bps-stable32-canonical-observations.csv`
- `data/processed/bps/comparative_stable32/bps-stable32-provenance.csv`
- `data/processed/bps/comparative_stable32/bps-stable32.manifest.json`
- `data/processed/bps/comparative_stable32/m24-probe-freeze-verification.json`
- `data/manifests/milestone24_bps_stable32_complete.json`
