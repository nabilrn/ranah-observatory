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

The live service identifies the national administrative-boundary geodatabase as edition `Juni 2026`. The qualification probe pins that edition string so a future upstream replacement is a review event rather than an unnoticed geometry change.

## Layer contract and live field behavior

The area layer exposes:

- ArcGIS Feature Layer semantics;
- polygon geometry;
- EPSG:4326 output;
- JSON / GeoJSON query support;
- `KDBBPS` and `KDPBPS` fields;
- `KDPKAB` and `KDPPUM` PUM/Permendagri code fields;
- `WADMKK` and `WADMPR` administrative names;
- source geometry and metadata fields.

Schema presence is not the same as field usability. A national live diagnostic against the June 2026 layer returned 541 features and found:

- `KDBBPS`: 0 nonblank values;
- `KDPBPS`: 0 nonblank values;
- `KDPKAB`: 520 nonblank values;
- `KDPPUM`: 541 nonblank values;
- `WADMKK`: 520 nonblank values;
- `WADMPR`: 541 nonblank values.

Therefore `KDBBPS` and `KDPBPS` are **not usable live join keys** for this source snapshot even though they exist in the schema. Ranah Observatory must not infer a BPS-code join from the field names alone.

For Sumatera Barat, the usable kabupaten/kota identifier is `KDPKAB`. Values such as `13.01`, `13.09`, and `13.71` are treated as Permendagri/PUM codes, not BPS statistical-area codes.

## Source selection rule

The live query selects all source objects whose `WADMPR` is `Sumatera Barat`, requests geometry in EPSG:4326, and then filters client-side to records with both:

- nonblank `KDPKAB`;
- nonblank `WADMKK`.

The national diagnostic found 22 Sumatera Barat candidate objects. Nineteen are kabupaten/kota records with populated `KDPKAB` and `WADMKK`. Three additional source objects have `NAMOBJ=Sumatera Barat` but blank `KDPKAB`/`WADMKK`; their remarks describe province/island boundary administration. They are retained in raw-source provenance but excluded from the kabupaten/kota geometry set.

This distinction prevents province-level or special boundary artifacts from being silently interpreted as additional kabupaten/kota.

## Canonical mapping rule

BIG `KDPKAB` is mapped through the edition-specific registry:

`data/registries/big_geography_map.csv`

Mapping path:

`BIG KDPKAB` → normalized Permendagri/PUM code → explicit BIG June 2026 crosswalk → canonical `geography_id`

The crosswalk contains exactly 19 current Sumatera Barat mappings. It intentionally preserves cases where the Permendagri code is not the same as the canonical BPS code. Examples include:

- `13.01` → Pesisir Selatan → `idn.13.1302`;
- `13.09` → Kepulauan Mentawai → `idn.13.1301`;
- `13.10` → Dharmasraya → `idn.13.1311`;
- `13.11` → Solok Selatan → `idn.13.1310`.

The probe fails if it sees:

- fewer or more than 19 selected kabupaten/kota;
- a missing or unexpected Permendagri source code;
- a duplicate source code;
- a source-name mismatch against the crosswalk;
- an incomplete or non-bijective mapping to the 19 current canonical geographies;
- a selected feature outside Sumatera Barat;
- empty geometry;
- non-polygon geometry;
- missing required source fields.

The repository's current BPS codes remain attributes of the canonical geography registry. They are not read from blank BIG `KDBBPS`/`KDPBPS` fields.

## Snapshot and provenance

Repository probe:

`scripts/probe_big_sumbar_boundaries.py`

The probe records:

- service and layer transport metadata;
- source edition signal;
- source response SHA-256;
- raw Sumatera Barat source-object count;
- excluded non-kabupaten/kota artifact count and source metadata;
- exact `KDPKAB`/Permendagri footprint;
- explicit source-code → canonical-geography mapping;
- `KDBBPS`/`KDPBPS` nonblank diagnostics;
- feature count;
- geometry type/non-empty checks;
- coordinate-pair count;
- source names by Permendagri code.

The live workflow uploads the raw source GeoJSON response as an immutable run artifact together with the qualification manifest. The artifact preserves all source objects returned by the Sumatera Barat query, including excluded source artifacts; the qualification manifest records which objects are retained for the kabupaten/kota analytical layer.

## Current versus historical geography

This qualification establishes only a **current boundary snapshot** suitable for current-geometry zonal aggregation.

It does not establish that the same polygons are valid for 1981, 1950, 1961, or any other earlier year. Administrative splits, boundary changes, and source-era geography remain part of the historical reconstruction problem.

Therefore:

- current polygons may be used to calculate a clearly labelled `current-boundary reconstruction` of older gridded climate values when that analytical choice is intentional;
- they must not be presented as the actual historical administrative boundaries for all prior years;
- any historical-boundary panel requires separately versioned geometry and temporal validity evidence.

Feature-level `METADATA` strings are preserved as source provenance, but mixed internal dates within a June 2026 service are not interpreted as independent historical validity intervals without separate documentation.

## Climate implication

Once this source passes the live gate, CHIRPS v3 monthly COGs can be spatially aggregated to the **current 19-kabupaten/kota footprint** of Sumatera Barat.

A resulting 1981-present rainfall panel must still disclose that historical raster values are being summarized over current administrative polygons unless historical geometry is later reconstructed.

This distinction is important: a long climate series on fixed current polygons is analytically useful for comparing physical climate exposure over a constant spatial frame, but it is not the same object as a historical administrative-statistics panel whose boundaries change over time.

## Exit gate

This source is qualified for the next zonal-aggregation phase when:

1. the BIG service and polygon layer are reachable from GitHub-hosted runners;
2. the service edition matches the pinned June 2026 snapshot;
3. the Sumatera Barat GeoJSON query succeeds;
4. client-side kabupaten/kota selection yields exactly 19 features;
5. all 19 `KDPKAB` Permendagri codes match the edition-specific BIG crosswalk;
6. the crosswalk maps bijectively to exactly the 19 current canonical Sumatera Barat geographies;
7. all source names pass crosswalk validation;
8. all selected geometries are non-empty Polygon/MultiPolygon features;
9. the raw response and qualification manifest are retained as workflow artifacts;
10. `KDBBPS`/`KDPBPS` are not required as live join keys;
11. historical-boundary continuity remains explicitly false.
