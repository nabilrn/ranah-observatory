# Data Foundation

## Purpose

This phase turns the research contract into machine-readable data contracts. It does not ingest analytical datasets yet. Its job is to make later BPS, BMKG, BNPB, BIG, archival, and derived data interoperable without erasing provenance, geography history, or claim type.

## Design principles

1. **Stable internal IDs, source-native codes retained.** `geography_id`, `indicator_id`, and `source_id` are project identifiers. Source codes such as BPS work-area codes remain explicit attributes and are never treated as timeless universal IDs.
2. **Source-era geography first.** Historical observations attach to the geography represented by the source. Harmonization is a separate, documented operation.
3. **Boundary history is versioned.** A changed boundary creates a new geography version or an explicit crosswalk; it never silently mutates old observations.
4. **Provenance is mandatory.** Every observation must trace to a source artifact and retrieval/transform context.
5. **Claim type is data.** Observed, derived, reconstructed, model-estimated, causal, qualitative, and scenario values must remain distinguishable.
6. **Raw inputs are immutable.** Later ingestion phases will place original source artifacts under snapshot/versioned storage and never overwrite them in place.
7. **Unknown is preferable to invented.** Missing historical validity dates, crosswalk weights, licenses, or methodology details stay null/blank until evidenced.

## Canonical entities

### Geography

A geography record represents a named spatial unit for a stated validity interval.

Required identity fields:

- `geography_id`: stable Ranah Observatory identifier;
- `geography_level`: country, province, regency, city, district, village, historical_region, watershed, station, grid, or other;
- `canonical_name`;
- optional source-native identifiers such as `bps_code`;
- `parent_geography_id` when hierarchical;
- `valid_from` / `valid_to` when evidenced;
- `status`: current, historical, provisional, or retired;
- `source_id` documenting the authority for the record.

The initial seed contains Indonesia, Sumatera Barat, and the 19 current regency/city statistical units. Their existence and BPS codes are seeded; historical formation dates are deliberately not inferred.

### Geography crosswalk

Crosswalk records describe a relationship between two geography versions or systems.

Important fields:

- `from_geography_id` and `to_geography_id`;
- relationship type such as rename, split, merge, boundary_adjustment, containment, or code_change;
- validity/effective date where known;
- optional weight and `weight_basis` for area/population/other allocations;
- `evidence_source_id`;
- confidence and notes.

No weighted harmonization is valid without an explicit weight basis. A split must not be represented as a simple rename.

### Indicator

The indicator registry is the analytical ontology. It records what a measure means before values are collected.

Minimum metadata:

- stable `indicator_id`;
- domain and human-readable name;
- operational definition;
- unit and expected frequency;
- preferred geography;
- source priority;
- allowed claim types;
- status and comparability notes.

The initial seed backlog started with 50 concepts across the twelve research domains. The registry may grow beyond 60 because it is the broader ontology and source-qualification backlog; `backlog` means conceptually approved for source qualification, not that comparable data already exists.

The Research Charter's separate **40–60 high-value indicators with provenance** criterion is measured from canonical observations whose provenance resolves, not from the number of rows in this registry. That completion state is maintained in `data/manifests/milestone4_indicator_inventory.json` and enforced by the Milestone 4 indicator audit.

### Source

`catalog/data-catalog.csv` remains the source-family discovery catalog. Dataset-specific ingestion phases should add records rather than collapsing multiple datasets under a single generic ministry/archive row.

A source identifier used by observations or geography records must resolve to a catalog entry once the relevant source is qualified.

### Provenance

A provenance record identifies the exact source artifact and transformation context behind a material value. It should retain:

- source ID and artifact locator;
- retrieval timestamp;
- source release/version when available;
- checksum for local snapshots when applicable;
- parser/transform revision;
- extraction method;
- notes on revisions, OCR, manual transcription, or other uncertainty.

### Observation

The canonical observation is long-form. At minimum it contains:

- `observation_id`;
- `indicator_id`;
- `geography_id`;
- reference period (`time_start`, optional `time_end`, and frequency);
- numeric or textual value as applicable;
- unit;
- `claim_type`;
- `provenance_id`;
- optional flags for missingness, suppression, reconstruction, comparability, and uncertainty.

An observation does not become comparable merely because its unit and indicator ID match. Boundary version, methodology, price basis, classification, and source breaks remain material.

## Claim types

Canonical values:

- `observed`
- `derived`
- `reconstructed`
- `model_estimate`
- `causal_estimate`
- `qualitative`
- `scenario`

Ingestion branches should normally emit `observed` values. Any transformation that changes the inferential status must set a stronger/different claim type explicitly rather than inheriting `observed` automatically.

## Time conventions

- Dates use ISO 8601.
- Annual observations use January 1 to December 31 only when the source represents a calendar year; otherwise preserve the source reference period.
- Census/reference-date values retain their actual reference date when known.
- Publication date and observation/reference date are separate concepts.
- Retrieval time belongs to provenance, not the observation period.

## Geography conventions

- BPS codes are stored as strings to preserve leading zeros at lower geography levels.
- BPS codes are source identifiers, not the Ranah Observatory primary key.
- Historical records keep source-era names and codes in provenance/crosswalk metadata.
- Aggregation across changed boundaries requires a documented crosswalk or a statement that the series is not harmonized.
- Raster, station, watershed, and network observations may use non-administrative geography IDs; they must not be forced into administrative units before an aggregation method is recorded.

## Directory contract

```text
catalog/
  data-catalog.csv

data/
  registries/
    geographies.csv
    geography_crosswalk.csv
    indicators.csv

schemas/
  data-foundation.schema.json

scripts/
  validate_data_foundation.py

tests/
  test_data_foundation.py
```

Later ingestion phases may add `data/raw`, `data/interim`, and `data/processed`, but large source artifacts should not be committed blindly to Git. Snapshot storage and manifest rules must be defined per source.

## Validation gates

Before this branch can be considered complete:

- registry IDs are unique and non-empty;
- geography parents resolve when present;
- current seed BPS codes are unique;
- every indicator uses a known domain and allowed claim-type vocabulary;
- the indicator ontology contains at least 40 registered definitions and covers all twelve research domains;
- the Milestone 4 audit separately enforces 40–60 canonical indicators with resolved provenance;
- crosswalk references resolve when rows exist;
- the JSON schema parses;
- the standard-library validator and unit tests pass;
- no historical validity dates or crosswalk weights are asserted without evidence.

## Deferred to ingestion and reconstruction phases

- full district/nagari registry;
- historical province/regency/city versions and formation dates;
- boundary geometries and area/population-weighted crosswalks;
- raw data snapshots;
- source-specific parsers;
- unit/price-basis harmonization;
- historical OCR/transcription workflow;
- analytical database or warehouse selection;
- ML feature tables.
