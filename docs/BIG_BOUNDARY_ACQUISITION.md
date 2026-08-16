# BIG Current Boundary Acquisition

## Objective

Ranah Observatory needs authoritative polygon geometry before gridded climate products such as CHIRPS can be aggregated to the current Sumatera Barat kabupaten/kota geography.

This phase qualifies a current BIG boundary snapshot only. It does not reconstruct historical administrative boundaries.

## Source

Authority: Badan Informasi Geospasial (BIG)

ArcGIS service:

`https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_KABKOTA_AR/MapServer`

Layer:

`0` — `Area Batas Wilayah Administrasi Kabupaten/Kota`

The reviewed BIG boundary-service family identifies the national administrative-boundary geodatabase as edition `Juni 2026`. The qualification probe pins that edition string so a future upstream replacement is a review event rather than an unnoticed geometry change.

## Layer contract

The area layer is expected to expose:

- ArcGIS Feature Layer semantics;
- polygon geometry;
- EPSG:4326 output;
- JSON / GeoJSON query support;
- `KDBBPS` — BPS kabupaten/kota code;
- `KDPBPS` — BPS province code;
- `WADMKK` — kabupaten/kota name;
- `WADMPR` — province name;
- source geometry and metadata fields.

For Sumatera Barat the query is restricted to BPS province code `13` and requests geometry in EPSG:4326.

## Canonical mapping rule

The geometry source is joined to Ranah Observatory by normalized `KDBBPS` only after the live source reproduces exactly the 19 current BPS kabupaten/kota codes already registered under canonical province `idn.13`.

The probe fails if it sees:

- fewer or more than 19 features;
- a missing canonical BPS code;
- an unexpected BPS code;
- a duplicate BPS code;
- a feature outside Sumatera Barat;
- empty geometry;
- non-polygon geometry;
- missing required source fields.

Names remain provenance and a diagnostic signal. Code identity is the primary current-snapshot join key because the repository's canonical geography registry is already anchored to current BPS statistical codes.

## Snapshot and provenance

Repository probe:

`scripts/probe_big_sumbar_boundaries.py`

The probe records:

- service and layer transport metadata;
- source edition signal;
- source response SHA-256;
- exact returned BPS-code footprint;
- feature count;
- geometry type/non-empty checks;
- coordinate-pair count;
- source names by BPS code.

The live workflow also uploads the raw source GeoJSON response as an immutable run artifact together with the qualification manifest. Large or upstream-owned geometry does not need to be silently rewritten into the canonical registry.

## Current versus historical geography

This qualification establishes only a **current boundary snapshot** suitable for current-geometry zonal aggregation.

It does not establish that the same polygons are valid for 1981, 1950, 1961, or any other earlier year. Administrative splits, boundary changes, and source-era geography remain part of the historical reconstruction problem.

Therefore:

- current polygons may be used to calculate a clearly labelled `current-boundary reconstruction` of older gridded climate values when that analytical choice is intentional;
- they must not be presented as the actual historical administrative boundaries for all prior years;
- any historical-boundary panel requires separately versioned geometry and temporal validity evidence.

## Climate implication

Once this source passes the live gate, CHIRPS v3 monthly COGs can be spatially aggregated to the **current 19-kabupaten/kota footprint** of Sumatera Barat.

A resulting 1981-present rainfall panel must still disclose that historical raster values are being summarized over current administrative polygons unless historical geometry is later reconstructed.

This distinction is important: a long climate series on fixed current polygons is analytically useful for comparing physical climate exposure over a constant spatial frame, but it is not the same object as a historical administrative-statistics panel whose boundaries change over time.

## Exit gate

This source is qualified for the next zonal-aggregation phase when:

1. the BIG service and polygon layer are reachable from GitHub-hosted runners;
2. the service edition matches the pinned June 2026 snapshot;
3. GeoJSON query succeeds;
4. exactly 19 current Sumatera Barat BPS codes are returned;
5. all 19 match the canonical geography registry exactly after code normalization;
6. all geometries are non-empty Polygon/MultiPolygon features;
7. the raw response and qualification manifest are retained as workflow artifacts;
8. historical-boundary continuity remains explicitly false.
