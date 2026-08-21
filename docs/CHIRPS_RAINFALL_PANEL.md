# CHIRPS v3 Annual Rainfall Panel

## Purpose

This materialization produces the first long climate indicator panel in Ranah Observatory:

- indicator: `annual_rainfall`;
- source: CHIRPS v3 Final monthly precipitation;
- period: 1981–2025 for the qualified full run;
- geography: the 19 current Sumatera Barat kabupaten/kota;
- spatial frame: fixed June 2026 BIG current boundaries;
- claim type: `model_estimate`.

The panel is intended for longitudinal climate-exposure analysis on a constant current spatial frame. It is not a reconstruction of historical administrative boundaries and it is not a direct BMKG station-observation series.

## Source products

### CHIRPS v3 Final monthly

Producer: Climate Hazards Center, University of California Santa Barbara.

Qualified source family:

`https://www.chc.ucsb.edu/data/chirps3`

Monthly global COG repository:

`https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/`

Ranah Observatory previously qualified the Final monthly product as a credential-free gridded rainfall `model_estimate` candidate and verified continuous monthly availability from January 1981 through December 2025.

CHIRPS combines satellite-based precipitation estimates with in-situ station information to create a gridded rainfall field over land. The gridded value is therefore not equivalent to a direct rain-gauge observation, even though station observations contribute to the product.

### BIG June 2026 boundaries

Producer: Badan Informasi Geospasial.

Qualified service:

`https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_KABKOTA_AR/MapServer`

The June 2026 Sumatera Barat geometry is mapped through source-native `KDPKAB` Permendagri/PUM codes and the explicit repository crosswalk:

`data/registries/big_geography_map.csv`

The live BIG `KDBBPS` and `KDPBPS` fields are blank in this service snapshot and are intentionally not used as join keys.

## Why monthly COGs are used

CHIRPS also distributes annual GeoTIFF products. The annual files are useful for independent inspection, but the reviewed annual TIFF is strip-organized rather than cloud optimized. The qualified monthly files are tiled Cloud Optimized GeoTIFF-style objects and the GitHub-hosted probe confirmed HTTP range-read support.

The production lane therefore reads the monthly COGs and transfers only the raster window covering Sumatera Barat rather than downloading complete global rasters for every period.

Using monthly inputs also provides a stronger completeness contract: an annual observation is emitted only when all 12 months are successfully processed.

## Spatial aggregation method

Materializer:

`scripts/build_chirps_rainfall_panel.py`

### 1. Geometry qualification

When no geometry snapshot is supplied explicitly, the materializer re-runs the official BIG live probe and writes the returned Sumatera Barat GeoJSON into the output directory.

Only the 19 source objects with qualified `KDPKAB` → canonical geography mappings are retained for calculation. Province/island source artifacts with blank kabupaten/kota identifiers remain in the raw GeoJSON for provenance but are excluded from the analytical geometry set.

### 2. Grid contract

Every monthly CHIRPS raster must retain the qualified grid signature:

- CRS: EPSG:4326;
- nominal grid size: 0.05° × 0.05°;
- stable width, height, transform, and resolution across months.

A grid change is a hard failure rather than an implicit resampling event.

### 3. Fractional polygon-pixel weights

Ranah Observatory does not use a simple pixel-center inclusion rule.

For each current BIG polygon, the materializer intersects the polygon with every CHIRPS grid cell touched by the polygon. Intersection areas are calculated after projection to equal-area CRS `EPSG:6933`.

The polygon-specific weight for pixel `i` is therefore proportional to:

`area(polygon ∩ pixel_i)`

This matters for:

- coastlines;
- small cities;
- fragmented island geometry such as Kepulauan Mentawai;
- boundary cells that would otherwise be fully included or excluded based only on their center point.

Weights are computed once because the CHIRPS grid is fixed, then reused for all monthly rasters.

The sum of the intersection areas must reconstruct each polygon area to within a narrow numerical tolerance before processing continues.

### 4. Nodata and ocean handling

CHIRPS raster samples use a large negative sentinel for missing/non-land values. The materializer treats the following as invalid:

- non-finite values;
- negative precipitation values;
- values at or below the configured nodata guard.

For each polygon-month, fractional weights are renormalized across valid CHIRPS cells. At least 98% of polygon intersection area must have valid data or the run fails.

The valid-area fraction is written to the monthly diagnostics so coastal/island coverage is auditable rather than hidden.

### 5. Monthly statistic

For geography `g` and month `m`:

`P_g,m = Σ(P_i,m × A_i,g) / Σ(A_i,g)`

where:

- `P_i,m` is CHIRPS monthly precipitation at pixel `i`;
- `A_i,g` is the valid equal-area intersection between pixel `i` and geography `g`.

The result is a spatial mean monthly precipitation depth in millimetres over the current polygon frame.

### 6. Annual statistic

An annual row is generated only when months 1 through 12 are all present:

`P_g,y = Σ_m=1^12 P_g,y,m`

Because precipitation depth is additive through time, the twelve monthly spatial means are summed to obtain the annual spatial mean rainfall depth for the same fixed geography.

The annual calculation does not average monthly precipitation values.

## Output contract

Default directory:

`data/processed/climate/chirps/`

### Annual canonical-style observations

`chirps-v3-annual-rainfall-current-boundaries.csv`

Key semantics:

- `indicator_id = annual_rainfall`;
- `frequency = annual`;
- `unit = millimetres`;
- `claim_type = model_estimate`;
- `methodology_version = chirps-v3-final-monthly_fractional-area-v1`;
- one row per current geography per complete year.

For the full 1981–2025 materialization the required cardinality is:

- 45 years;
- 19 geographies;
- 855 annual observations.

### Monthly diagnostics

`chirps-v3-monthly-zonal-diagnostics.csv`

The full materialization requires 10,260 rows:

`45 years × 12 months × 19 geographies`.

The diagnostics retain:

- monthly weighted precipitation;
- valid-area fraction;
- valid and total weighted areas;
- valid/total intersecting pixel counts;
- exact remote source URL.

These rows are calculation diagnostics, not a separate canonical monthly indicator release.

### Provenance

`chirps-v3-rainfall-provenance.csv`

The provenance row records the CHIRPS source family, retrieval timestamp, transform revision, spatial-boundary edition, and remote monthly-object pattern.

The production lane uses HTTP range reads, so it does not pretend to possess whole-file SHA-256 checksums for remote COGs that were never fully downloaded. Instead, exact URLs, source release, grid signature, transformation revision, raw BIG snapshot checksum, diagnostics, and checksums of materialized outputs are retained.

### Manifest

`chirps-v3-rainfall-panel.manifest.json`

The manifest captures:

- panel year range;
- geography and source-edition contract;
- raw BIG GeoJSON SHA-256;
- CHIRPS grid signature;
- weighting and annual-aggregation method;
- minimum and maximum data coverage;
- output checksums and byte sizes;
- rainfall range diagnostics;
- negative semantic guards.

## Semantic guardrails

The materialized value is a `model_estimate`.

It must not be relabelled as:

- a BMKG station observation;
- a gauge-only precipitation series;
- a historical administrative-boundary observation;
- an estimate using historical kabupaten/kota polygons.

The geometry statement is intentionally specific:

> Historical CHIRPS raster values are summarized over the fixed June 2026 current kabupaten/kota polygons.

This fixed spatial frame is useful for comparing physical climate exposure through time while avoiding artificial time-series breaks caused only by administrative splits. It answers a different question from a historical administrative-statistics panel.

## Comparability

Within the CHIRPS v3 Final 1981–2025 materialization, annual rows share:

- one CHIRPS product family;
- one grid contract;
- one aggregation algorithm;
- one fixed current-boundary geography frame.

They are therefore marked internally comparable within this panel.

That flag does **not** imply direct comparability with:

- BMKG station measurements;
- ERA5-Land reanalysis;
- future CHIRPS product versions;
- climate values aggregated using historical administrative geometry.

Cross-source comparisons require an explicit validation and harmonization phase.

## Validation

Output validator:

`scripts/validate_chirps_rainfall_panel.py`

The validator enforces:

- exact current geography coverage;
- unique geography-year and geography-year-month keys;
- exactly 12 monthly inputs per annual observation;
- `model_estimate` claim type;
- exact method revision;
- valid calendar-year bounds;
- broad physical plausibility guards;
- ≥98% valid weighted area for every geography-month;
- exact source URL pattern;
- provenance resolution;
- materialized output checksums;
- raw BIG snapshot checksum;
- negative semantic guards.

For a full 1981–2025 run it additionally pins the cardinalities of 855 annual observations and 10,260 monthly diagnostics.

## Release sequence

The pipeline should be promoted in two stages:

1. **smoke materialization** — one complete recent year to verify remote raster access, geometry mapping, fractional weights, monthly completeness, output schema, and runtime behavior on a GitHub-hosted runner;
2. **full materialization** — 1981–2025 only after the smoke run passes unchanged methodology and validation contracts.

The smoke output is a technical validation artifact. The full 1981–2025 output is the intended first long rainfall research panel.

## Next analytical dependency

After the full panel is reproducibly materialized, the next climate task is validation rather than more source acquisition:

1. compare overlapping CHIRPS estimates with available BMKG daily/monthly station observations where obtainable;
2. characterize level and trend differences;
3. document station representativeness versus polygon-average gridded rainfall;
4. only then use the climate panel together with BNPB disaster observations or economic indicators in inferential or machine-learning models.
