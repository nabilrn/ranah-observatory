# CHIRPS Rainfall Zonal-Aggregation Proof of Concept

## Purpose

This phase proves the mechanics required to combine the qualified CHIRPS v3 Final monthly rainfall lane with the qualified BIG June 2026 current kabupaten/kota polygons.

It is intentionally bounded. It does **not** create the production 1981-present rainfall panel and it does **not** write canonical observations.

## Scope

The live proof of concept runs only for calendar year 1981 and three deliberately different current geographies:

- `idn.13.1371` — Padang, representing a city;
- `idn.13.1307` — Agam, representing a mainland regency;
- `idn.13.1301` — Kepulauan Mentawai, representing an island/coastal regency.

The scope therefore contains exactly:

- 12 CHIRPS v3 Final monthly COGs;
- 3 BIG current-boundary polygons;
- 36 monthly estimates;
- 3 annual proof-of-concept estimates.

All outputs are workflow artifacts only.

## Evidence contract

Every rainfall value produced by this proof of concept is classified as:

`model_estimate`

The spatial frame is:

`fixed_current_boundary_june_2026`

A 1981 raster value summarized over a June 2026 BIG polygon is therefore a **current-boundary reconstruction of historical climate exposure**, not evidence that the June 2026 administrative boundary was the legally valid boundary in 1981.

The workflow explicitly keeps:

`historical_boundary_continuity_claimed = false`

## Monthly zonal statistic

CHIRPS v3 Final monthly precipitation is a gridded monthly total in millimetres. For each selected polygon and month, the proof of concept calculates a geodesic area-weighted mean over intersecting grid-cell portions.

For polygon `g`, the monthly statistic is conceptually:

`sum(rainfall_cell * geodesic_intersection_area) / sum(valid_geodesic_intersection_area)`

The intersection area is measured on the WGS84 ellipsoid rather than treating one degree of latitude-longitude as a constant planar area.

The pixel-overlap weights are calculated once from the first monthly grid and reused only if subsequent monthly files preserve the same CRS, 0.05-degree resolution, and read window.

Grid drift fails closed.

## Nodata and coastline rule

CHIRPS is a land precipitation product. Administrative polygons can include coastline or portions with no valid CHIRPS cell value.

The workflow therefore:

1. never converts nodata to rainfall zero;
2. removes nodata/non-finite cells from the monthly numerator;
3. removes the same cells from the valid-area denominator;
4. records `valid_area_fraction` for every geography-month;
5. fails if a polygon has no valid CHIRPS overlap.

For coastal regions like Kepulauan Mentawai, silently treating ocean/nodata cells as zero would bias the polygon mean downward.

The proof of concept does not yet define a production minimum coverage threshold. Its purpose is to expose the observed coverage fractions first so the threshold can be chosen from evidence rather than guessed in advance.

## Annual statistic

An annual estimate is emitted only when months 1 through 12 are present exactly once for the geography.

The annual value is:

`sum(monthly polygon mean precipitation totals)`

Missing or duplicate months fail annualization rather than being interpolated or silently ignored.

## Source provenance

### BIG geometry

The workflow fetches the already-qualified BIG Sumatera Barat GeoJSON query and uses the June 2026 `KDPKAB` Permendagri/PUM crosswalk in:

`data/registries/big_geography_map.csv`

The proof-of-concept manifest records:

- query URL;
- retrieval timestamp through the overall manifest timestamp;
- response byte count;
- response SHA-256;
- HTTP ETag/Last-Modified when exposed;
- source edition;
- selected canonical geography IDs and source names.

### CHIRPS monthly files

For each of the 12 COGs the manifest records:

- exact source URL;
- range-response status;
- Content-Range/Content-Length when exposed;
- ETag/Last-Modified when exposed;
- SHA-256 of the fetched TIFF prefix;
- TIFF signature check.

The prefix hash is transport provenance for the bounded proof of concept; it is not represented as a full-file cryptographic checksum.

A production materialization phase must decide whether stronger freezing is needed before canonical observations are committed.

## Runtime outputs

The workflow creates three artifacts under `artifacts/chirps-rainfall-poc/`:

- `chirps_rainfall_poc_monthly.csv`;
- `chirps_rainfall_poc_annual.csv`;
- `chirps_rainfall_poc_manifest.json`.

These files are uploaded by GitHub Actions and are deliberately not committed as the canonical climate panel.

## Exit gate

This proof of concept passes only when:

1. BIG resolves exactly the three intended current geometries through the qualified crosswalk;
2. all selected BIG geometries are valid non-empty Polygon/MultiPolygon objects;
3. all 12 CHIRPS 1981 monthly COGs are readable through the remote COG lane;
4. the CHIRPS grid is EPSG:4326 at 0.05-degree resolution;
5. the monthly grid contract does not drift across the year;
6. all 36 geography-month rows have positive valid CHIRPS overlap;
7. exactly three complete annual rows are produced;
8. all rainfall values remain `model_estimate`;
9. the June 2026 fixed-current-boundary label is retained;
10. no historical-boundary continuity claim is made.

## What this phase deliberately does not do

This phase does not:

- run all 19 kabupaten/kota;
- run 1981-2025;
- write canonical observations;
- define the final coastline coverage threshold;
- compare CHIRPS against BMKG stations;
- add ERA5-Land;
- calculate extreme-rainfall days;
- perform trend, causal, econometric, or machine-learning analysis.

## Next slice after this PoC

If the live proof of concept passes and the coverage diagnostics are sensible, the next bounded step is to expand the same method to all 19 current kabupaten/kota for a very small multi-year sample, inspect coverage and numerical stability, and only then authorize full 1981-2025 production materialization.
