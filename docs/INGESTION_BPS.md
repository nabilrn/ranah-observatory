# BPS Ingestion

## Purpose

This phase exercises the canonical observation/provenance contracts against BPS before adding other source families. It is intentionally conservative: discovery metadata can be harvested broadly, but no BPS table or publication value is mapped to a Ranah Observatory indicator until its definition, unit, geography, period semantics, and methodology notes have been inspected.

BPS WebAPI access is useful, but it is **not a hard dependency**. Official BPS publication pages and their downloadable PDF artifacts form a credential-free acquisition lane and are the primary route for historical reconstruction.

## Official interfaces

### Public publication website — no credential required

BPS publication pages under `*.bps.go.id/.../publication/...` expose publication metadata and a public `Unduh Publikasi` link. The current website resolves that link through `web-api.bps.go.id/download.php` without requiring a developer API token.

Ranah Observatory records the stable official publication-page URL and downloaded artifact checksum. The resolved download URL is treated as ephemeral transport metadata and is not used as a stable identifier.

### WebAPI — optional accelerator

- BPS WebAPI documentation: `https://webapi.bps.go.id/documentation/`
- API base used by this repository: `https://webapi.bps.go.id/v1`

The official documentation states that WebAPI requests are identified by a key token. If available, keep the token in `BPS_API_KEY`; never commit it or write it into snapshots.

The first target website domain is BPS Provinsi Sumatera Barat (`1300`). Domain identifiers are source-native metadata, not Ranah Observatory geography IDs.

## Acquisition lanes

### 1. Public publication pages and PDFs — default historical lane

Use `scripts/harvest_bps_publication.py` with an official BPS publication page. The downloader:

- accepts only HTTPS `*.bps.go.id` publication pages;
- resolves the current official download link;
- accepts downloads only from the expected BPS artifact hosts;
- rejects non-PDF responses such as access-denied HTML;
- writes the PDF atomically;
- writes an adjacent SHA-256 checksum;
- writes a provenance manifest containing the stable official page URL, retrieval timestamp, artifact size, and checksum;
- never requires or persists a BPS developer key.

Publication metadata is not itself an observation. Tables extracted from PDFs must retain page/table provenance and extraction method.

### 2. Dynamic-table discovery — optional WebAPI lane

When a developer key is available, use WebAPI variable and data endpoints to discover machine-readable series. Candidate mappings must preserve:

- BPS variable ID (`var_id`);
- subject and definition;
- BPS unit;
- vertical-variable semantics;
- period-data ID and displayed period label;
- derived-variable and derived-period selections;
- source notes and metadata returned by BPS.

The WebAPI `th` parameter is a **period-data ID selection**. It must not be treated as a calendar year merely because the displayed label may be a year.

### 3. Static tables

Static-table metadata may expose an Excel artifact. Static tables are useful when a target indicator is not represented cleanly in dynamic data, but table structure and metadata must be qualified before automatic parsing.

## Verified Sumatera Barat publication anchors

Current high-value seeds include:

- *Provinsi Sumatera Barat Dalam Angka 2026* — release 2026-02-27, revised 2026-05-21;
- *Indikator Strategis Provinsi Sumatera Barat 2026* — release 2026-04-30;
- *Master Wilayah Administrasi Provinsi Sumatera Barat 2025* — release 2026-05-29.

A separate historical anchor registry verifies public BPS publication pages for reference years 1970, 1971, 1975, 1989, 1990, 1999, 2000, 2010, 2015, 2019, 2024, 2025, and 2026.

Documented timeline:

- the official abstract for the 1971 edition describes it as the **second** book in the series;
- the official 1970 publication page is therefore the earliest currently verified digital anchor for this series in this repository.

This does **not** establish that no earlier statistical source exists. The 1945–1969 period is explicitly deferred to archival reconstruction, including source-era administrative concepts such as Sumatera Tengah where relevant.

## Repository components

```text
scripts/
  bps_client.py                  # small stdlib WebAPI client
  harvest_bps.py                 # credentialed WebAPI snapshot CLI
  bps_publication.py             # keyless official publication acquisition
  harvest_bps_publication.py     # keyless publication CLI

data/registries/
  bps_indicator_coverage.csv
  bps_publications_seed.csv
  bps_historical_anchors.csv

tests/
  test_bps_client.py
  test_bps_publication.py

.github/workflows/
  ingestion-bps.yml
```

## Snapshot and artifact contract

### WebAPI JSON

`harvest_bps.py` writes an immutable JSON envelope and adjacent SHA-256 file containing source, UTC retrieval timestamp, domain, language, acquisition command, non-secret filters, and normalized raw API result.

### Publication PDF

`harvest_bps_publication.py` writes:

```text
book.pdf
book.pdf.sha256
book.pdf.manifest.json
```

The manifest uses `bps_publication_web` as its source family and preserves the stable official page URL. The ephemeral `download.php` URL is intentionally excluded from the persisted provenance record.

Raw snapshots and PDFs belong under local/versioned data storage and are ignored by Git by default. Small fixtures or manifests may be committed deliberately; large source artifacts should not be committed merely for convenience.

## Example commands

### No-key publication acquisition

```bash
python scripts/harvest_bps_publication.py \
  'https://sumbar.bps.go.id/id/publication/2026/02/27/2c7cc5c693ff125fc6751f7a/provinsi-sumatera-barat-dalam-angka-2026.html' \
  --inspect

python scripts/harvest_bps_publication.py \
  'https://sumbar.bps.go.id/id/publication/2026/02/27/2c7cc5c693ff125fc6751f7a/provinsi-sumatera-barat-dalam-angka-2026.html' \
  --output data/raw/bps/publications/sumbar-dalam-angka-2026.pdf
```

### Optional WebAPI acquisition

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
```

Do not put literal keys in shell history when avoidable; environment variables or repository secrets are preferred.

## Indicator qualification workflow

For each candidate indicator:

1. Search the coverage registry and qualified publications first.
2. Acquire the relevant official artifact with immutable checksum/provenance.
3. Inspect definition, unit, geography, reference period, table notes, and methodological breaks.
4. Record page/table coordinates and extraction method.
5. Decide whether the artifact maps directly to the canonical indicator or requires a derived/versioned indicator.
6. Freeze the selected source mapping before routine extraction.
7. Normalize into canonical long-form observations.
8. Validate duplicates, nulls, units, geography, temporal coverage, and source breaks.
9. Use WebAPI machine-readable series as an accelerator/cross-check when credentials and comparable variables are available.

## What this phase does not assume

- that the newest table is historically comparable;
- that one BPS variable ID is stable across every website/domain/version;
- that publication year equals observation year;
- that matching indicator names imply matching methodology;
- that rebased GRDP series can be concatenated without a linking decision;
- that census, projection, Susenas, Sakernas, and administrative data are interchangeable;
- that a publication number is globally unique — archived BPS pages demonstrate collisions;
- that current Sumatera Barat boundaries can be projected backward to early-independence data.

## Validation gates

All merge-blocking checks are credential-free:

- canonical data-foundation validation;
- BPS registry validation;
- unit tests for WebAPI request construction/normalization;
- unit tests for publication-page parsing, host allow-listing, PDF validation, checksum, and manifest generation.

If repository secret `BPS_API_KEY` is later configured, the workflow may additionally run a live WebAPI smoke test. Lack of a key does not block the research pipeline.

## Exit criteria for this branch

- WebAPI client and snapshot CLI pass offline tests;
- keyless publication acquisition passes offline tests;
- coverage matrix covers all canonical indicators;
- high-value current and historical BPS publications are explicitly registered;
- source catalog distinguishes WebAPI from credential-free publication artifacts;
- CI is green without a key;
- no canonical indicator/value mapping is asserted solely from a title match.

After this branch, the next work is **historical reconstruction and first observation extraction**, not waiting for a WebAPI account: acquire selected publications, inventory table structures and definition breaks, then extract a small validated panel starting with population, education/HDI components, labor, poverty/inequality, and GRDP where the evidence permits.
