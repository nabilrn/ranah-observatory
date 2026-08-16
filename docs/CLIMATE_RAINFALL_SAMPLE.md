# CHIRPS Multi-Year Rainfall Sample Gate

## Purpose

This phase is the second bounded validation step after the 1981 three-geography proof of concept.

It expands the exact same evidence and zonal-aggregation contract to all 19 current Sumatera Barat kabupaten/kota, but only for three sample years:

- 1981 — beginning of the qualified CHIRPS v3 Final record;
- 2000 — interior historical checkpoint;
- 2025 — recent complete year already qualified by the CHIRPS source probe.

The purpose is not to publish the full climate panel. The purpose is to test whether the method remains stable when geography coverage and temporal distance are expanded before authorizing 1981–2025 production materialization.

## Scope

The live sample contains exactly:

- 19 qualified current BIG June 2026 kabupaten/kota polygons;
- 3 complete calendar years;
- 36 CHIRPS v3 Final monthly COGs;
- 684 geography-month estimates;
- 57 geography-year annual estimates.

Outputs remain GitHub Actions artifacts only and are not canonical observations.

## Evidence contract

Every output remains:

`claim_type = model_estimate`

with spatial frame:

`fixed_current_boundary_june_2026`

The 1981, 2000, and 2025 rainfall rasters are summarized over the same June 2026 BIG polygons to create a fixed-area climate-exposure comparison. This does not establish that those polygons were the legally valid administrative boundaries in earlier years.

Therefore:

`historical_boundary_continuity_claimed = false`

## Spatial aggregation

For each geography and month, the script calculates a geodesic area-weighted mean of CHIRPS grid-cell portions intersecting the BIG polygon.

Conceptually:

`sum(monthly_rainfall_mm * geodesic_intersection_area) / sum(valid_geodesic_intersection_area)`

The WGS84 ellipsoid is used for intersection-area weighting.

Grid weights are created from the first sample COG and reused only if every later sample COG has the same CRS, resolution, and read-window contract. Any grid drift fails the workflow.

## Missing values and coastline

CHIRPS is a land precipitation product. The workflow therefore excludes:

- GDAL-declared nodata;
- the explicit CHIRPS `-9999` missing sentinel;
- non-finite raster values.

Missing values are never interpreted as rainfall zero.

Every monthly row records `valid_area_fraction`, allowing island and coastal geographies to be inspected separately from inland polygons. The phase intentionally does not invent a final production coverage threshold before the 19-geography sample is observed.

## Annualization

A geography-year annual estimate is produced only when months 1 through 12 are present exactly once.

Annual rainfall is the sum of the 12 monthly polygon-mean rainfall totals.

No interpolation is performed for missing months.

## Diagnostics

The sample produces two diagnostic families.

### Coverage

The manifest records:

- minimum monthly valid-area fraction;
- 5th percentile valid-area fraction;
- median valid-area fraction;
- the geography, year, and month with the lowest observed coverage.

These diagnostics are used to decide whether a production minimum coverage rule is needed.

### Annual rainfall distribution

For each sample year, the manifest records:

- minimum annual rainfall;
- median annual rainfall;
- maximum annual rainfall;
- Tukey 1.5×IQR diagnostic fences;
- geography-year values outside those fences.

IQR flags are **diagnostic only**. They are not auto-rejections because a spatial rainfall extreme can be physically real. Any flagged value must be investigated through source consistency and, later, comparison with BMKG or another independent climate product before being treated as erroneous.

## Provenance

The manifest retains:

- BIG query URL, response SHA-256, response metadata, source edition, and all 19 canonical IDs;
- exact URL for each of the 36 CHIRPS COGs;
- HTTP range-response metadata;
- ETag/Last-Modified when available;
- prefix SHA-256 used as bounded transport provenance;
- CHIRPS grid metadata;
- execution runtime.

The prefix hash is not represented as a full-file cryptographic checksum. A production-freeze decision remains a later gate.

## Exit gate

This sample passes only when:

1. exactly 19 qualified current BIG geometries are resolved;
2. all 36 sample monthly COGs are readable;
3. the CHIRPS grid remains EPSG:4326 at 0.05-degree resolution across the sample;
4. exactly 684 monthly rows are emitted;
5. exactly 57 complete annual rows are emitted;
6. every monthly geography has positive valid CHIRPS overlap;
7. no non-missing negative rainfall value is accepted;
8. all output rows remain `model_estimate`;
9. all output rows retain the June 2026 fixed-current-boundary label;
10. no historical-boundary continuity claim is introduced.

## What this phase does not do

This phase does not:

- materialize all years 1981–2025;
- commit rainfall observations to the canonical panel;
- claim BMKG station validation;
- define a causal relationship between rainfall and disaster or economic outcomes;
- calculate extreme-rainfall days;
- add ERA5-Land;
- reconstruct historical kabupaten/kota boundaries.

## Next decision

If the sample is green and the artifact diagnostics are numerically sensible, the next phase can define a production rainfall-panel contract for all 19 current geographies and all complete CHIRPS Final years 1981–2025.

Before that production phase is merged, the project should explicitly decide:

1. whether the observed sample coverage supports a formal minimum coverage threshold;
2. whether source-file provenance needs stronger freezing than prefix hashes;
3. how the final canonical observation schema records current-boundary reconstruction semantics;
4. whether a small independent validation sample against BMKG stations is required before downstream modelling.
