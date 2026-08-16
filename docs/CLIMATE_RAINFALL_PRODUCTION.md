# CHIRPS Rainfall Production Dry-Run

## Objective

This phase executes the complete qualified CHIRPS v3 Final rainfall transformation for all current Sumatera Barat kabupaten/kota and all complete final years from 1981 through 2025.

It is deliberately a **production dry-run**, not yet canonical materialization.

The dry-run exists to inspect complete-series coverage, runtime, annual distributions, and temporal discontinuity diagnostics before 855 annual rainfall estimates are permanently committed into the Ranah Observatory canonical observation layer.

## Scope

The live run contains exactly:

- 45 complete calendar years: 1981–2025;
- 19 current BIG June 2026 kabupaten/kota polygons;
- 540 CHIRPS v3 Final monthly COGs;
- 10,260 geography-month estimates;
- 855 geography-year annual estimates.

All output remains a GitHub Actions artifact during this phase.

## Evidence semantics

Every output is classified as:

`claim_type = model_estimate`

The spatial frame is:

`fixed_current_boundary_june_2026`

Historical CHIRPS rasters are summarized over one fixed modern geography so long-run climate exposure is spatially comparable. This does not imply that the June 2026 polygons were legally valid historical administrative boundaries.

Therefore:

`historical_boundary_continuity_claimed = false`

## Spatial statistic

For each geography-month, rainfall is the geodesic area-weighted mean of all CHIRPS-valid grid-cell portions intersecting the BIG polygon.

The monthly statistic is:

`sum(rainfall_cell_mm * geodesic_intersection_area) / sum(valid_geodesic_intersection_area)`

Grid-cell overlap areas are measured on the WGS84 ellipsoid.

Area weights are computed once from the first COG and reused only if every subsequent COG preserves the same CRS, spatial resolution, and regional read-window contract.

Any grid drift fails closed.

## Missing-value and coastline policy

The pipeline excludes:

- GDAL-declared nodata;
- CHIRPS `-9999` missing sentinel;
- non-finite raster values.

Missing values are never converted to rainfall zero.

### Production coverage threshold

The bounded 1981/2000/2025 sample observed:

- minimum monthly valid-area fraction: `0.99877921`;
- 5th percentile: `0.99877921`;
- median: `1.0`.

The production dry-run therefore sets:

`minimum valid_area_fraction = 0.995`

This threshold is intentionally below the observed sample minimum, retaining operational margin while still failing a material loss of CHIRPS-valid polygon coverage.

The threshold is a processing-quality guard. It is not a statement that 99.5% coverage makes CHIRPS equivalent to station observations.

## Annualization

An annual estimate is emitted only when months 1 through 12 are present exactly once for a geography-year.

Annual rainfall is the sum of the 12 monthly polygon-mean rainfall totals.

No monthly interpolation or imputation is allowed in this phase.

## Full-series diagnostics

The production dry-run records diagnostics without automatically deleting scientifically plausible extremes.

### Coverage diagnostics

The manifest records:

- minimum valid-area fraction;
- 1st percentile coverage;
- 5th percentile coverage;
- median coverage;
- exact geography-month producing minimum coverage.

### Annual spatial-distribution diagnostics

For every year, the pipeline calculates Tukey 1.5×IQR fences across the 19 current geographies and records any geography-year values outside those fences.

These flags are descriptive only.

### Temporal diagnostics

For every geography, the manifest records:

- minimum annual rainfall;
- median annual rainfall;
- maximum annual rainfall;
- largest absolute year-over-year fractional change and its year pair.

Year-over-year changes of at least 50% are listed as review flags. They are not automatically classified as errors because legitimate hydroclimatic variability may be large.

A flagged value requires source and independent-evidence review before rejection.

## Provenance

For BIG, the run retains:

- query URL;
- full response SHA-256;
- ETag/Last-Modified where available;
- source edition;
- exact 19 canonical geography IDs and source names.

For every one of the 540 CHIRPS COGs, the manifest retains:

- exact URL;
- range-response metadata;
- ETag/Last-Modified where available;
- prefix SHA-256;
- TIFF signature result.

The prefix hash remains transport provenance, not a full-file cryptographic freeze.

Before canonical materialization, the project must explicitly decide whether this provenance level is sufficient or whether a stronger frozen source manifest is required.

## Outputs

The workflow creates:

- `chirps_rainfall_production_monthly.csv` — 10,260 intermediate monthly estimates;
- `chirps_rainfall_production_annual.csv` — 855 candidate annual estimates;
- `chirps_rainfall_production_manifest.json` — method, source, coverage, runtime, and diagnostic evidence.

These files remain workflow artifacts until a later materialization gate.

## Exit gate

The dry-run passes only when:

1. exactly 19 current BIG geographies are resolved;
2. all 540 CHIRPS Final COGs are readable;
3. all COGs preserve the expected EPSG:4326 0.05-degree grid contract;
4. exactly 10,260 monthly rows are generated;
5. exactly 855 annual rows are generated;
6. every monthly row has at least 99.5% CHIRPS-valid polygon coverage;
7. no non-missing negative rainfall value is accepted;
8. all annual values are positive;
9. all rows retain `model_estimate` claim type;
10. all rows retain the June 2026 fixed-current-boundary label;
11. historical boundary continuity remains explicitly false.

## Still not canonical

A successful dry-run does **not** automatically mean the annual values enter the canonical panel.

Before canonical materialization, Ranah Observatory should inspect:

- full-series coverage diagnostics;
- spatial IQR flags;
- large year-over-year change flags;
- runtime and reproducibility;
- provenance sufficiency;
- compatibility with the canonical observation/provenance schemas;
- a future independent comparison against BMKG station rainfall where obtainable.

Only after those checks should a dedicated materialization branch convert the 855 annual estimates into canonical `annual_rainfall` observations.
