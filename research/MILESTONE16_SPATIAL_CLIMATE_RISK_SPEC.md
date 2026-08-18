# Milestone 16 — Spatial & Climate Risk Engine v1

## Criterion

Build a reproducible spatial/climate evidence layer for West Sumatra that preserves the distinction among **hazard**, **climate context**, **exposure**, **vulnerability**, **capacity**, **recorded event occurrence**, and **observed impact**.

M16 v1 is allowed to finish with `risk_synthesis_authorized=false`. A fail-closed component ledger is preferable to manufacturing a composite disaster-risk score from incomplete evidence.

## Spatial regime

- exact 19 current West Sumatra kabupaten/kota;
- canonical geography IDs inherited from the qualified BIG June 2026 fixed-current-boundary frame;
- no historical-boundary continuity claim;
- event-specific 2009 earthquake evidence and 2024 hydroclimate evidence remain temporally distinct;
- no cross-event or cross-year risk aggregation.

## Qualified inherited evidence

### 1. Earthquake physical hazard intensity

Source object: M8 USGS ShakeMap aggregated over the qualified BIG June 2026 polygon frame.

Primary metric:

- `area_mean_pga_pct_g`.

Interpretation:

- physical shaking intensity over a fixed current-boundary spatial frame;
- not population exposure;
- not asset exposure;
- not observed damage;
- not historical-boundary reconstruction.

### 2. Hydroclimate context

Source object: M9 CHIRPS annual rainfall for 2024 relative to each geography's 1981–2023 baseline.

Primary metric:

- `rainfall_z_2024`.

Interpretation:

- annual gridded rainfall model estimate;
- not a BMKG station observation;
- not event-day rainfall;
- not flood or landslide attribution;
- independent station validation remains pending.

### 3. Recorded disaster occurrence

Source object: M9/BNPB canonical 2024 event counts.

Metrics:

- `flood_events`;
- `landslide_events`.

Interpretation:

- observed recorded-event occurrence counts;
- not affected population;
- not fatalities/injuries;
- not damaged buildings;
- not monetary losses;
- not a hazard probability surface.

## External spatial-source readiness

BNPB InaRISK exposes anonymous ArcGIS ImageServer services for flood/landslide hazard and vulnerability. Official InaRISK methodology preserves hazard, vulnerability, capacity, and risk as distinct concepts, and the public WebGIS exposes KRB 2021 data.

However, the ImageServer metadata inspected for M16 does not itself expose a sufficiently explicit vintage/methodology binding. Therefore M16 v1 records those services as:

`endpoint_verified_version_binding_unresolved`

and does **not** ingest their pixel values into the substantive 19-geography frame.

This status may be upgraded only after the exact raster/service vintage can be bound to an official methodology/data release without inference from visual layer grouping alone.

## Component taxonomy

Every evidence object must have one of these component classes:

- `hazard_intensity`;
- `climate_context`;
- `exposure`;
- `vulnerability`;
- `capacity`;
- `recorded_event_occurrence`;
- `observed_impact`;
- `modeled_risk`.

An object may not silently migrate between classes.

## M16 v1 substantive frame

The 19-geography frame may contain only:

- M8 `area_mean_pga_pct_g`;
- M8 `area_mean_mmi` as a secondary shaking descriptor;
- M9 `rainfall_z_2024`;
- M9 `rainfall_baseline_percentile`;
- M9 `flood_events`;
- M9 `landslide_events`.

The frame must also expose explicit authorization flags showing that qualified exposure, vulnerability, capacity, and observed-impact objects are not yet present.

## Forbidden operations

M16 v1 must not:

- sum or average earthquake, rainfall, flood, or landslide metrics into one score;
- rank kabupaten/kota by an invented disaster-risk score;
- interpret PGA/MMI as population or asset exposure;
- interpret annual CHIRPS rainfall as event-day flood/landslide rainfall;
- interpret BNPB event counts as disaster impact or loss;
- ingest InaRISK raster pixels while the exact service-vintage binding is unresolved;
- treat 2009 earthquake and 2024 hydroclimate evidence as contemporaneous;
- claim climate-change attribution;
- claim causal disaster mechanisms;
- estimate monetary wasted potential.

## Required outputs

1. `data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv`
2. `data/analysis/engine/spatial_climate_risk_v1/m16-evidence-component-registry.csv`
3. `data/manifests/milestone16_spatial_climate_risk.json`
4. `docs/MILESTONE16_SPATIAL_CLIMATE_RISK.md`

## Completion gate

M16 v1 is complete only if:

- exact 19-geography alignment holds between M8 and M9;
- upstream M8 and M9 manifests retain their claim boundaries;
- all component classes and readiness states are explicit;
- unqualified InaRISK services remain blocked from substantive aggregation;
- no composite risk score/ranking exists;
- no causal or monetary claim is created;
- deterministic rebuild produces byte-identical outputs;
- canonical and historical foundation audits remain green.

The completion claim is **spatial/climate evidence integration with explicit risk-synthesis limits**, not completion of a fully parameterized disaster-risk model.
