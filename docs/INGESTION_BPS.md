# BPS Ingestion

## Purpose

This phase exercises the canonical observation/provenance contracts against BPS before adding other source families. It is intentionally conservative: discovery metadata can be harvested broadly, but no BPS variable is mapped to a Ranah Observatory indicator until its definition, unit, geography, period semantics, and methodology notes have been inspected.

## Official interfaces

Primary programmatic interface:

- BPS WebAPI documentation: `https://webapi.bps.go.id/documentation/`
- API base used by this repository: `https://webapi.bps.go.id/v1`

The official documentation states that WebAPI requests are identified by a key token. Keep the token in `BPS_API_KEY`; never commit it or write it into snapshots.

The first target website domain is BPS Provinsi Sumatera Barat (`1300`). Domain identifiers are source-native metadata, not Ranah Observatory geography IDs.

## Acquisition lanes

### 1. Dynamic-table discovery

Use the WebAPI variable and data endpoints to discover machine-readable series. Candidate mappings must preserve:

- BPS variable ID (`var_id`);
- subject and definition;
- BPS unit;
- vertical-variable semantics;
- period-data ID and displayed period label;
- derived-variable and derived-period selections;
- source notes and metadata returned by BPS.

Important: the WebAPI `th` parameter is a **period-data ID selection**. It must not be treated as a calendar year merely because the displayed label may be a year.

### 2. Static tables

Static-table metadata can be searched by keyword/year and may expose an Excel artifact. Static tables are useful when a target indicator is not represented cleanly in dynamic data, but table structure and metadata must be qualified before automatic parsing.

### 3. Publications

Publication metadata and PDFs are first-class evidence, especially for:

- technical notes;
- methodology and classification changes;
- regional tables not exposed consistently through the API;
- historical reconstruction.

Initial qualified publications include:

- *Provinsi Sumatera Barat Dalam Angka 2026* — release 2026-02-27, revised 2026-05-21, catalog `1102001.13`, publication `13000.26007`;
- *Indikator Strategis Provinsi Sumatera Barat 2026* — release 2026-04-30, catalog `1103019.13`, publication `13000.26027`;
- *Master Wilayah Administrasi Provinsi Sumatera Barat 2025* — release 2026-05-29, catalog `1301002.13`, publication `13000.26029`.

Publication metadata is not itself an observation. Tables extracted from publications must retain page/table provenance and extraction method.

## Repository components

```text
scripts/
  bps_client.py          # small stdlib WebAPI client
  harvest_bps.py         # snapshot CLI

data/registries/
  bps_indicator_coverage.csv
  bps_publications_seed.csv

tests/
  test_bps_client.py

.github/workflows/
  ingestion-bps.yml
```

## Snapshot contract

`harvest_bps.py` writes an immutable JSON envelope and adjacent SHA-256 file. A snapshot includes:

- snapshot schema version;
- `source_id`;
- UTC retrieval timestamp;
- BPS domain;
- language;
- acquisition command;
- non-secret query filters;
- raw normalized API result.

Raw snapshots belong under local/versioned data storage and are ignored by Git by default. A later ingestion PR may commit small fixtures or manifests, but should not commit large API/PDF artifacts merely for convenience.

## Example commands

```bash
export BPS_API_KEY='...'

python scripts/harvest_bps.py \
  --domain 1300 \
  --output data/raw/bps/publications-2026.json \
  publications --year 2026

python scripts/harvest_bps.py \
  --domain 1300 \
  --output data/raw/bps/variables.json \
  variables --max-pages 5

python scripts/harvest_bps.py \
  --domain 1300 \
  --output data/raw/bps/population-selection.json \
  dynamic --var <BPS_VAR_ID> --th <BPS_PERIOD_ID>
```

Do not put literal keys in shell history when avoidable; environment variables or repository secrets are preferred.

## Indicator qualification workflow

For each candidate indicator:

1. Search variables/static tables/publications using terms in `bps_indicator_coverage.csv`.
2. Record candidate BPS identifiers; do not immediately ingest values.
3. Inspect definition, unit, geography, period labels, notes, and methodological breaks.
4. Decide whether the BPS artifact maps directly to the canonical indicator or requires a derived indicator/version.
5. Freeze the selected source mapping in a registry before routine harvesting.
6. Harvest raw source data with checksum/provenance.
7. Normalize into canonical long-form observations.
8. Validate duplicates, nulls, units, geography, temporal coverage, and source breaks.

## What this phase does not assume

- that the newest table is historically comparable;
- that one BPS variable ID is stable across every website/domain/version;
- that publication year equals observation year;
- that matching indicator names imply matching methodology;
- that rebased GRDP series can be concatenated without a linking decision;
- that census, projection, Susenas, Sakernas, and administrative data are interchangeable.

## Live validation gate

Unit tests and schema/registry checks run without network access or credentials.

If repository secret `BPS_API_KEY` is configured, the BPS workflow additionally runs a one-page live publication smoke test against domain `1300`. Live harvesting is deliberately optional so contributors and forks can validate the code without possessing a key.

## Exit criteria for this branch

- WebAPI client and snapshot CLI pass offline tests;
- coverage matrix covers all canonical indicators;
- high-value BPS publications are explicitly registered;
- source catalog distinguishes API and qualified publication artifacts;
- CI is green without a key;
- live smoke test is green once `BPS_API_KEY` is supplied;
- no canonical indicator/value mapping is asserted solely from a title match.

The next BPS sub-phase after a live key is available is dataset discovery and mapping: harvest variable/static/publication inventories, inspect high-priority candidates, then add the first validated observations (population, HDI components, labor, poverty, and GRDP are likely starting families, subject to actual source qualification).
