# Long Historical Climate Baseline Qualification

## Objective

Ranah Observatory needs a reproducible climate baseline long enough to study structural change rather than only current weather. This qualification evaluates two complementary gridded source families:

1. CHIRPS v3 for credential-free rainfall estimates from 1981 onward;
2. ERA5-Land for a longer 1950-present reanalysis extension including near-surface temperature and precipitation.

Neither source is allowed to masquerade as a BMKG station observation.

## Evidence classes

The project distinguishes the following climate evidence:

- `observed`: direct source observations such as qualified BMKG station measurements;
- `derived`: deterministic transformations of compatible observations;
- `model_estimate`: gridded estimates or reanalysis products whose values are not direct station measurements.

CHIRPS v3 and ERA5-Land enter this phase as `model_estimate` evidence. A source can be high quality and still require a non-observed claim type.

## CHIRPS v3 Final

Primary producer documentation:

`https://www.chc.ucsb.edu/data/chirps3`

Primary data repository:

`https://data.chc.ucsb.edu/products/CHIRPS/v3.0/`

### Product contract

The Climate Hazards Center documents CHIRPS v3 as a 40+ year quasi-global rainfall dataset from 1981 to near-present at 0.05 degree resolution. It combines satellite-based thermal-infrared precipitation estimates with in-situ station observations to produce a gridded rainfall time series over land.

Two product states exist:

- preliminary: rapid update using quickly available station inputs;
- final: produced monthly using the best available station inputs.

For longitudinal research the final product is preferred because the project values stable retrospective comparability above minimum latency.

CHIRPS v3 is fundamentally a pentad and monthly product. Annual values can be derived from compatible monthly or pentadal totals. Daily products are derived through an additional temporal-disaggregation step and therefore have different semantics.

### Qualified access lane

Preferred machine-readable lane:

`https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/`

The repository exposes one global Cloud Optimized GeoTIFF-style object per month. The project probe verifies:

- directory accessibility without credentials;
- presence of January 1981;
- presence of December 2025;
- complete monthly coverage from 1981 through 2025;
- TIFF signatures for an early and recent stable file;
- HTTP range-read behavior suitable for future spatial subsetting.

Repository probe:

`scripts/probe_chirps_v3.py`

### Canonical role

CHIRPS v3 Final is qualified as:

`rainfall_model_estimate_candidate`

It is suitable to support a future `annual_rainfall` series when all of the following are implemented:

1. canonical or historically appropriate polygon geometry is available;
2. grid-to-polygon aggregation is explicit and reproducible;
3. nodata and coastline handling are documented;
4. monthly completeness is enforced before annual aggregation;
5. the resulting observation rows use claim type `model_estimate`;
6. source version and retrieval provenance are retained.

This phase qualifies the source and transport. It does **not** yet create canonical kabupaten/kota rainfall observations because the repository currently lacks the required versioned polygon geometry pipeline.

## CHIRPS daily and extreme-rainfall days

Primary daily-product documentation:

`https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/readme.txt`

CHIRPS v3 daily values are not simply direct daily gauge observations. The producer documents two temporal-disaggregation products:

- `rnl`: ERA5 daily precipitation ratios partition CHIRPS pentadal totals;
- `sat`: NASA IMERG daily precipitation ratios partition CHIRPS pentadal totals.

For the full CHIRPS historical period, the reanalysis-based `rnl` path is the relevant long-span candidate because ERA5 covers the full period while IMERG does not.

The project therefore classifies CHIRPS daily `rnl` as:

`derived_reanalysis_disaggregated_estimate`

and its current canonical role as:

`held_extreme_day_candidate`

No `extreme_rainfall_days` observations are promoted in this phase. Before promotion the project must define:

- the threshold in mm/day;
- day/time-zone semantics;
- treatment of missing days;
- whether a threshold count derived from temporally disaggregated pentadal rainfall is scientifically acceptable for the intended analysis;
- validation against available BMKG daily rainfall stations over an overlapping period.

## ERA5-Land

Primary dataset page:

`https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land`

Primary ECMWF product description:

`https://www.ecmwf.int/en/forecasts/datasets/era5-land-hourly-data-1950-present`

### Product contract

ERA5-Land is a global land reanalysis from January 1950 to present with hourly temporal resolution. The Climate Data Store distributes it on a regular 0.1 degree latitude-longitude grid; the native model resolution is approximately 9 km.

The product includes variables relevant to this project such as:

- 2 metre temperature;
- total precipitation;
- land-surface and hydrological variables.

ERA5-Land is generated by replaying the land component of ERA5. Observations are not directly assimilated into ERA5-Land itself; they influence the product indirectly through ERA5 atmospheric forcing. ECMWF also states that model-estimate uncertainty generally increases backward in time as the atmospheric observing system becomes sparser.

The project therefore classifies ERA5-Land as:

`reanalysis_model_estimate`

with current canonical role:

`long_baseline_extension_candidate`

### Access constraint

The Climate Data Store data are open under the dataset licence, but programmatic retrieval requires:

- a CDS account;
- a personal access token;
- manual acceptance of the dataset licence/terms before API download.

This makes ERA5-Land a reproducible authenticated lane rather than a credential-free lane.

The access constraint does not disqualify the source. It means ERA5-Land acquisition should not block the credential-free CHIRPS work and must not embed a user token in the repository.

## Proposed climate coverage architecture

### Rainfall 1981-present

Primary gridded candidate:

CHIRPS v3 Final monthly → polygon aggregation → annual rainfall `model_estimate`.

BMKG station rainfall remains the preferred observed validation source wherever obtainable.

### Rainfall 1950-1980

Candidate extension:

ERA5-Land total precipitation → polygon aggregation → annual rainfall `model_estimate`.

The CHIRPS/ERA5 overlap from 1981 onward must be used to quantify level differences, variance differences, trend agreement, and spatial bias before any stitched long-run series is considered.

A stitched series must never silently treat a change of source in 1981 as a continuous homogeneous measurement system.

### Temperature 1950-present

Candidate:

ERA5-Land 2 metre temperature → temporal aggregation → polygon aggregation → mean temperature `model_estimate`.

BMKG station temperature remains the preferred observed validation source where available.

## Validation hierarchy

Before climate estimates enter downstream statistical or machine-learning models, validation should proceed in this order:

1. source transport and coverage checks;
2. raster metadata and unit validation;
3. versioned geography/polygon acquisition;
4. grid-to-polygon aggregation tests;
5. overlap comparison among CHIRPS, ERA5-Land, and BMKG stations where available;
6. temporal completeness and discontinuity diagnostics;
7. canonical observation generation with explicit claim type and provenance.

## Why CHIRPS is not called observed

CHIRPS uses real station observations, but the published value at a grid cell is a blended gridded rainfall estimate that also uses satellite-derived information and a climatological framework. Calling each grid value an `observed` rainfall measurement would erase the distinction between direct gauge data and a spatially modelled/blended product.

The correct Ranah Observatory claim type is therefore `model_estimate`.

## Why ERA5-Land is not called observed

ERA5-Land is explicitly a reanalysis/model product. Its atmospheric forcing is influenced by global observations, but the land fields are simulated estimates. It is valuable precisely because it provides a globally complete physically consistent record where direct observations are sparse, but that advantage must not be converted into an observational claim.

## Current decision

Qualified now:

- CHIRPS v3 Final monthly as a credential-free rainfall model-estimate source candidate;
- CHIRPS monthly COG transport for efficient future Sumatera Barat subsetting;
- ERA5-Land as a 1950-present reanalysis extension candidate whose acquisition requires CDS credentials;
- explicit `model_estimate` support for the core climate indicators.

Held now:

- canonical rainfall observations until versioned polygon geometry and zonal aggregation are implemented;
- CHIRPS-derived extreme-rainfall-day counts until daily-disaggregation and threshold validation are complete;
- ERA5-Land downloads until a CDS token and licence acceptance are available;
- any stitched CHIRPS/ERA5 long series until overlap diagnostics are performed.

## Immediate next dependency

The highest-leverage dependency is a reproducible authoritative Sumatera Barat polygon layer with stable identifiers and provenance. Once polygon geometry is qualified, the credential-free CHIRPS monthly COG lane can produce the first 1981-present gridded rainfall panel without waiting for BMKG Data Online or CDS credentials.
