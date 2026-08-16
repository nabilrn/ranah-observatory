# CHIRPS Annual Rainfall Repository Freeze

## Objective

This phase turns the validated CHIRPS annual-rainfall canonical candidate into a durable repository baseline under:

`data/processed/climate/rainfall/`

The freeze does not change rainfall values, evidence class, geometry semantics, or station-validation status. It changes only the storage state from a CI candidate artifact to a version-controlled baseline and rewrites provenance locators accordingly.

## Frozen files

The baseline consists of:

- `chirps-annual-rainfall-observations.csv` — 855 annual `model_estimate` observations;
- `chirps-annual-rainfall-provenance.csv` — 45 year-level provenance rows;
- `chirps-source-contract.csv` — 541 source-identity items;
- `chirps-rainfall-materialization.manifest.json` — evidence, hash, methodology, and freeze metadata.

## Generation rule

The files are not hand-edited.

The freeze workflow executes the full chain on the PR branch:

1. re-run the hardened materialization unit tests;
2. rebuild all 540 CHIRPS monthly source reads for 1981–2025;
3. rebuild all 10,260 monthly and 855 annual rainfall candidates;
4. rebuild the 855 canonical-format candidates and 541-item source contract;
5. rewrite candidate artifact provenance locators to durable repository locators;
6. validate the frozen files against the canonical geography and indicator registries;
7. commit the generated baseline to the PR branch only.

The workflow never writes directly to `main`. The generated commit remains subject to PR review and merge gates.

## Repository provenance locator

Candidate provenance uses an artifact locator while the source contract exists only in a CI artifact.

At freeze time this becomes:

`repo://data/processed/climate/rainfall/chirps-source-contract.csv#year=YYYY`

The provenance checksum remains the SHA-256 of the complete source-contract CSV. The source contract itself preserves the more precise upstream digest scopes:

- CHIRPS COG identity: `sha256_first_16384_bytes_not_full_file_checksum`;
- BIG geometry identity: `sha256_full_geojson_query_response`.

The freeze must not relabel the CHIRPS prefix digest as a full raster checksum.

## Immutable evidence semantics

Every frozen observation remains:

- `indicator_id = annual_rainfall`;
- `unit = millimetres`;
- `frequency = annual`;
- `claim_type = model_estimate`;
- `spatial_frame = fixed_current_boundary_june_2026`;
- `historical_boundary_continuity = false`;
- `observed_station_equivalence = false`;
- `independent_station_validation = pending`.

The June 2026 BIG polygons are a constant spatial frame for backcasting climate exposure. They are not asserted as the actual legal kabupaten/kota boundaries in every historical year.

## Frozen validation contract

`scripts/validate_chirps_rainfall_freeze.py` requires:

- exactly 19 current Sumatera Barat kabupaten/kota IDs from the canonical geography registry;
- exactly 45 years, 1981–2025;
- exactly 855 unique geography-year observations;
- exactly 45 unique provenance IDs;
- exactly 540 CHIRPS source identities plus one BIG geometry identity;
- exact annual period bounds;
- finite positive rainfall values;
- canonical annual-rainfall unit and claim-type compatibility;
- repository-scoped provenance locators;
- matching observation, provenance, and source-contract hashes;
- no loss of the fixed-boundary, non-station, or validation-pending disclosures.

## Upstream drift behavior

The frozen baseline represents a specific qualified source snapshot.

A future rebuild that sees a changed CHIRPS ETag, Last-Modified value, prefix digest, object length, BIG full-response digest, transformation result, or source contract should be treated as a review event rather than silently replacing the baseline.

A later dedicated drift validator may automate that comparison. This freeze establishes the durable baseline required for such a validator.

## What remains after freeze

This baseline is sufficient for reproducible descriptive and exploratory climate analysis as a CHIRPS `model_estimate` series.

Before treating it as independently validated West Sumatra rainfall evidence in downstream causal or predictive modelling, the project still needs an overlap comparison against qualified BMKG station rainfall where available.
