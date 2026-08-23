# Milestone 31 — Submission Package Integration

## Purpose

Turn the certified v0.1 manuscript and M30 canonical tables/figures into a portable submission-facing package without changing the frozen scientific evidence, model results, claim states, or interpretation boundaries.

M31 is publication integration, not research expansion.

## Required outputs

Under `publication/v0.1/submission/`:

- `manuscript-with-assets.md` — the M29 manuscript with deterministic references to canonical M30 tables and figures;
- `asset-index.csv` — one row for every T01–T07 and F01–F06 asset with its canonical path and claim bindings;
- `metadata.json` — title, release, research scope, keywords, frozen evidence identity, and explicit pending submission metadata;
- `submission-manifest.json` — SHA-256 identities for all submission inputs and generated outputs;
- `README.md` — portable package notes and the remaining human-confirmation checklist.

## Integration rules

- The canonical M29 manuscript remains the scientific source text.
- M31 may insert figure/table callouts and submission metadata only.
- No substantive sentence may be rewritten to strengthen or weaken a scientific claim.
- Every callout must point to an existing canonical M30 rendered asset.
- All 7 tables and all 6 figures must appear in the asset index.
- Negative-result figures/tables must remain explicitly labeled as failed qualification where applicable.
- Blocked claims remain blocked.

## Metadata rules

M31 may prefill stable project metadata such as the working title, release, scope, keywords, repository identity, and frozen analytical base. Venue, DOI, publication license, ORCID, final corresponding-author details, and journal-specific formatting must remain explicitly pending unless independently confirmed.

## Prohibited operations

M31 does not authorize new source acquisition, data modification, model fitting/refitting, imputation, composite scoring, monetary aggregation, causal claim upgrades, forecast upgrades, policy-effect interpretation, or cost-benefit ranking.

## Completion rule

M31 is complete when the submission package is generated deterministically from the committed M29/M30 package, all 13 canonical assets are indexed and referenced as planned, M29 claim/completeness audit still passes, M30 rendered assets rebuild byte-identically, and a read-only CI rebuild leaves all committed M31 outputs byte-identical.
