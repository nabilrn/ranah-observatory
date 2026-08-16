# CHIRPS Annual Rainfall Canonical Materialization Contract

## Objective

The full CHIRPS v3 Final dry-run established that Ranah Observatory can reproducibly transform 1981–2025 monthly rainfall rasters into 855 complete annual estimates across the 19 current Sumatera Barat kabupaten/kota polygons.

This phase defines how those annual estimates become **canonical-format evidence** without erasing their model-estimate or current-boundary semantics.

The phase generates a canonical candidate artifact. It does not yet commit the 855 rows as the repository's frozen baseline; that final freeze remains a separate reviewable step.

## Canonical observation schema

The materializer uses the same observation fields already used by the existing BPS canonical panel:

- `observation_id`
- `indicator_id`
- `geography_id`
- `time_start`
- `time_end`
- `frequency`
- `value_numeric`
- `unit`
- `claim_type`
- `provenance_id`
- `suppressed`
- `comparable`
- `methodology_version`
- `price_basis`
- `notes`

For CHIRPS annual rainfall:

- `indicator_id = annual_rainfall`
- `frequency = annual`
- `unit = millimetres`
- `claim_type = model_estimate`
- `suppressed = false`
- `comparable = true` only within the explicitly stated CHIRPS v3 Final fixed-current-boundary frame
- `price_basis` is empty
- `time_start` and `time_end` are January 1 and December 31 of the stated year.

`comparable = true` does **not** mean that CHIRPS grid estimates are directly interchangeable with BMKG station observations, ERA5-Land, or a historical-boundary administrative series. That limitation remains in the observation notes.

## Stable observation identity

Observation IDs are deterministic hashes of:

- source: `chirps_v3`;
- indicator: `annual_rainfall`;
- canonical geography ID;
- year;
- spatial frame;
- methodology version.

This makes an annual observation identity stable for the same evidence contract while allowing a future methodology or boundary revision to generate a distinct identity rather than silently overwrite the old one.

## Spatial semantics

Every canonical candidate retains:

`spatial_frame = fixed_current_boundary_june_2026`

and:

`historical_boundary_continuity = false`

The 1981–2025 raster values are summarized over the same June 2026 BIG kabupaten/kota polygons. The resulting series is a constant-spatial-frame climate reconstruction, not a claim that those polygons were the legally valid administrative boundaries in every historical year.

## Evidence semantics

Every observation retains:

`claim_type = model_estimate`

The notes explicitly state:

- `observed_station_equivalence=false`;
- `independent_station_validation=pending`.

CHIRPS incorporates station and satellite information, but the published grid cell value is not a direct BMKG gauge observation.

This distinction is mandatory for later statistical or machine-learning use.

## Source contract

The canonical candidate includes a separate source-contract artifact containing 541 items:

- 540 CHIRPS v3 Final monthly COG identities for January 1981 through December 2025;
- one BIG June 2026 Sumatera Barat geometry-response identity.

### CHIRPS identity scope

For each monthly COG, the contract records:

- exact URL;
- year and month;
- HTTP ETag where available;
- Last-Modified value where available;
- reported full object length from Content-Range;
- SHA-256 of the first 16,384 bytes used by the qualified range-read probe.

The identity is labelled:

`sha256_first_16384_bytes_not_full_file_checksum`

The prefix digest must never be represented as a cryptographic digest of the entire upstream raster.

### BIG identity scope

For the BIG query response used to build the polygon set, the source contract records the full response SHA-256 and labels it:

`sha256_full_geojson_query_response`

The source edition remains `Juni 2026`.

## Canonical provenance checksum

The canonical provenance schema has a `checksum_sha256` field. For this materialization, that field is defined as the SHA-256 of the **committed/generated source-contract CSV artifact**, not the full bytes of any upstream global CHIRPS raster.

This is deliberately explicit.

The source-contract checksum verifies the exact provenance bundle used by the materialization: URLs, transport identities, prefix digests, reported object lengths, and the full BIG geometry response digest.

It does not convert a prefix digest into a full-file digest.

## Provenance granularity

The materializer creates one provenance row per year, for 45 total provenance rows.

Each annual provenance row represents:

- the twelve CHIRPS monthly source files for that year;
- the common BIG June 2026 geometry snapshot;
- the raster parser revision;
- the production zonal transform revision;
- the canonical materializer revision.

All 19 geography observations in the same year reference the same year-level provenance row because they use the same twelve rainfall rasters and the same qualified geometry response. Geography-specific transformation semantics remain encoded in the deterministic observation identity and fixed geometry contract.

## Methodology version

The canonical candidate uses:

`chirps_v3_final_monthly_big_june_2026_fixed_boundary_v1`

A future change to any material transformation rule should use a new methodology version rather than altering old observation identities in place.

Examples requiring a new methodology version include:

- a different polygon vintage;
- a different zonal weighting rule;
- a different coastline/nodata rule;
- historical-boundary harmonization;
- a different CHIRPS product generation;
- an explicit station-bias correction.

## Promotion gates

The materializer fails unless the upstream production manifest has already passed all dry-run gates and contains:

- 1981–2025 complete coverage;
- 19 geographies;
- 855 annual candidates;
- all production quality gates true.

It additionally requires each annual candidate to have:

- exactly 12 complete months;
- positive rainfall;
- minimum valid-area coverage of at least 0.995;
- `claim_type = model_estimate`;
- `spatial_frame = fixed_current_boundary_june_2026`.

The canonical candidate must then contain exactly:

- 855 unique observations;
- 45 provenance rows;
- 541 source-contract items.

## Independent validation remains pending

Canonical-format materialization means the evidence has passed the repository's source, transformation, completeness, geography, and provenance contracts.

It does **not** mean that CHIRPS has been independently validated against West Sumatra BMKG stations for this project.

The existing full-series diagnostic findings therefore remain review targets, including:

- spatial high-rainfall flags concentrated around Pariaman / Padang Pariaman / Padang in multiple years;
- the synchronized 1997→1998 rainfall increase across most current geographies;
- the 1997 minimum candidate and 2022 maximum candidate.

Those values are retained unless independent evidence supports rejection or correction.

## Outputs

The workflow generates:

- `chirps-annual-rainfall-observations.csv` — 855 canonical-format observations;
- `chirps-annual-rainfall-provenance.csv` — 45 year-level provenance rows;
- `chirps-source-contract.csv` — 541 frozen source-identity contract items;
- `chirps-rainfall-materialization.manifest.json` — counts, hashes, methodology, and evidence status.

## Next freeze step

If the live materialization workflow is green and the candidate artifact is internally consistent, the next bounded phase may freeze these canonical-format outputs into `data/processed/climate/rainfall/` and add a live drift validator.

That freeze must preserve the source-contract checksum semantics described above and must not change `independent_station_validation=pending` until an actual BMKG overlap comparison has been performed.
