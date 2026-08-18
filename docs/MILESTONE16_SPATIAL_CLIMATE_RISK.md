# Milestone 16 — Spatial & Climate Risk Engine v1

M16 integrates the spatial/climate evidence currently qualified for West Sumatra without manufacturing a disaster-risk score from incompatible or incomplete components.

## What is substantively available

The 19-geography frame retains three distinct evidence classes:

1. **Earthquake hazard intensity** — area-mean PGA and area-mean MMI from the 30 September 2009 USGS ShakeMap, summarized over the qualified BIG June 2026 fixed-current-boundary polygons.
2. **Climate context** — CHIRPS 2024 annual rainfall anomaly relative to each geography's 1981–2023 baseline.
3. **Recorded disaster occurrence** — BNPB 2024 flood and landslide event counts.

These objects are deliberately not normalized into one scale or combined into a ranking.

## Descriptive footprint

Across the 19 fixed-current-boundary geographies:

- area-mean 2009 earthquake PGA ranges from about 10.73%g to 52.29%g;
- 2024 CHIRPS rainfall z-scores range from about +0.861 to +1.708 relative to the 1981–2023 local baselines;
- all 19 geographies are wetter in 2024 than their own CHIRPS baseline;
- the canonical BNPB frame records 64 flood events and 10 landslide events in 2024.

These figures belong to different evidence objects and time regimes. The earthquake and hydroclimate columns sharing one row is a spatial alignment convenience, not authorization to add, average, correlate, or interpret them as contemporaneous risk components.

## Why PGA is not called exposure here

M8 originally built a physical-shaking exposure candidate for a quasi-causal design. In M16 taxonomy the PGA/MMI values are classified as `hazard_intensity` because they measure physical shaking over area, not people, buildings, assets, or livelihoods exposed to that shaking.

This avoids overloading the word exposure across disaster-risk frameworks.

## Why BNPB event counts are not impact

The M9 BNPB object counts recorded flood and landslide events. It does not by itself measure:

- affected population;
- fatalities or injuries;
- damaged buildings or infrastructure;
- disrupted livelihoods;
- hectares damaged;
- monetary loss.

M16 therefore classifies these rows as `recorded_event_occurrence` and keeps `observed_impact` as a qualified evidence gap.

## InaRISK readiness finding

Official BNPB InaRISK infrastructure exposes anonymous ArcGIS ImageServer services for at least:

- flood hazard;
- landslide hazard;
- flood vulnerability;
- landslide vulnerability.

The inspected services expose machine-readable floating-point rasters and standard image-service operations. Official InaRISK methodology also distinguishes hazard, vulnerability, capacity, and modeled risk.

However, the individual ImageServer metadata inspected for M16 does not itself provide a sufficient exact vintage/methodology binding. The public WebGIS exposes a KRB 2021 data group, but M16 does not infer that every similarly named ImageServer is exactly that release solely from visual/service naming.

Therefore the four endpoints are retained as:

`endpoint_verified_version_binding_unresolved`

No InaRISK raster pixels are ingested in M16 v1.

## Current risk-synthesis state

A defensible full disaster-risk synthesis would require compatible, qualified objects for at least hazard, exposure, vulnerability, and capacity, with observed impact retained as an independent validation/impact object rather than conflated with modeled risk.

M16 currently lacks qualified compatible objects for:

- exposure;
- vulnerability in the substantive frame;
- capacity;
- observed impact.

Accordingly:

- `risk_synthesis_authorized = false`;
- no composite risk score is produced;
- no kabupaten/kota risk ranking is produced;
- no cross-event temporal aggregation is performed;
- no causal or climate-change attribution is performed;
- no monetary wasted-potential estimate is produced.

## Why this is still a completed M16 v1

The milestone's purpose is to create a trustworthy spatial/climate risk evidence layer, not to force every risk component into existence.

The completed engine now makes it machine-readable which spatial evidence is qualified, which component it represents, which evidence is blocked, and exactly what additional qualification is required before a fuller risk model is allowed.

That fail-closed state is the input contract for later scenario work.

## Outputs

- `data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv`
- `data/analysis/engine/spatial_climate_risk_v1/m16-evidence-component-registry.csv`
- `data/manifests/milestone16_spatial_climate_risk.json`
