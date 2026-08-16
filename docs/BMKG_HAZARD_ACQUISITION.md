# BMKG Hazard Acquisition Qualification

## Question

Can the official BMKG `Peta Curah Hujan dan hari Hujan` service be used as a reproducible historical rainfall panel for Ranah Observatory?

## Official discovery source

BMKG Satu Peta MKG lists `Peta Curah Hujan dan hari Hujan` as a public WMS in its official Data API registry:

`https://gis.bmkg.go.id/portal/dataapi`

The reviewed ArcGIS service is:

`Peta_Curah_Hujan_dan_Hari_Hujan_`

## Hosted-runner access test

The service is operational from a GitHub-hosted runner.

Reviewed probe run: `31898690617`  
Reviewed artifact: `9250489861`  
Artifact SHA-256: `a261b5e91778d2ae89293d8a87c15ce65d1f7d6320be5369f88b61e485a9dc55`

Results:

- ArcGIS MapServer JSON: HTTP 200;
- standard ArcGIS WMS `GetCapabilities`: HTTP 200;
- WMS capabilities parsed successfully;
- the `/arcgis/rest/.../WMSServer` variant is invalid and returned HTTP 400, so it must not be used as the WMS endpoint.

The preferred WMS endpoint shape is:

`https://gis.bmkg.go.id/arcgis/services/Peta_Curah_Hujan_dan_Hari_Hujan_/MapServer/WMSServer`

## Layer semantics

ArcGIS REST exposes a group layer with two data layers:

### Layer 0 — Peta Hari Hujan

- type: Feature Layer;
- geometry: point;
- relevant source field: `TTALHH`;
- ArcGIS `timeInfo`: absent.

### Layer 1 — Peta Curah Hujan

- type: Feature Layer;
- geometry: polygon;
- relevant source field: `CRHHJN`;
- ArcGIS `timeInfo`: absent.

WMS capabilities expose two named layers:

- WMS layer `1` — `Peta Hari Hujan`;
- WMS layer `2` — `Peta Curah Hujan`.

Neither WMS layer exposes a `TIME` dimension. The ArcGIS map service itself also has no `timeInfo`.

## Qualification decision

Classification:

`accessible_no_time_dimension_static_or_current_map`

Canonical suitability:

`not_suitable_as_historical_panel_without_separate_vintage_metadata`

This does **not** mean the BMKG map is invalid. It means the service endpoint does not expose the temporal dimension required to reconstruct a reproducible annual or monthly historical rainfall series.

Ranah Observatory therefore must not transform this WMS directly into:

- `annual_rainfall_mm`;
- `extreme_rainfall_days`;
- `mean_temperature_c`;
- or another longitudinal observed-climate indicator.

A separate official source carrying explicit observation dates/vintages is required.

## Next climate lane

The preferred next source family remains BMKG observed station/climate data rather than a forecast product. BMKG Data Online is retained as the primary candidate because it exposes observed climate parameters, but its authenticated acquisition workflow must be handled separately.

Other official BMKG map products may be useful as climatological context or spatial covariates if their reference period is explicit. For example, a 30-year rainfall normal is a climatological normal, not an annual observation, and must remain a separate indicator/concept.

## Research rule

Map accessibility is not evidence of temporal comparability.

Before a BMKG source can enter the canonical longitudinal panel, it must expose or be paired with:

1. an explicit observation/reference period;
2. a stable variable definition and unit;
3. station/grid geography metadata;
4. acquisition provenance;
5. a documented aggregation rule from the source grain to the canonical geography/time grain.
