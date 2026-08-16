# CHIRPS Rainfall Sanity Review

## Objective

This phase performs a bounded sanity review of the frozen CHIRPS v3 Final annual-rainfall baseline under:

`data/processed/climate/rainfall/`

It does **not** regenerate, replace, or reclassify the 855 frozen observations. The baseline remains:

- `claim_type=model_estimate`;
- `spatial_frame=fixed_current_boundary_june_2026`;
- `independent_station_validation=pending`;
- not equivalent to BMKG station observations.

The review addresses two specific questions exposed by the full 1981–2025 dry-run:

1. is the large 1997→1998 rainfall rebound internally coherent enough to treat as a plausible regional climate signal rather than an obvious processing failure?
2. how should repeated spatial Tukey-IQR flags in Pariaman, Padang Pariaman, and Padang be classified before station validation exists?

## Inputs

The checker reads only frozen repository data:

- `chirps-annual-rainfall-observations.csv`;
- `data/registries/geographies.csv`.

The workflow first runs `scripts.validate_chirps_rainfall_freeze`, so sanity diagnostics cannot proceed on a corrupted or structurally invalid frozen baseline.

The previously merged read-only drift validator remains a separate upstream-identity safeguard. This phase does not silently substitute transport stability for physical validation.

## Diagnostic 1: 1997→1998 transition

For every one of the 19 current kabupaten/kota polygons, the checker calculates:

`(rainfall_1998 / rainfall_1997 - 1) * 100`

The transition is classified as:

`plausible_regional_climate_signal_pending_independent_station_validation`

only when:

- at least 18 of 19 geographies move in the same positive direction; and
- minimum valid-area coverage across 1997 and 1998 remains at least `0.995`.

This is a **sanity classification**, not causal attribution and not validation of rainfall magnitude.

### Independent large-scale climate context

The directional classification has independent large-scale context from NOAA Climate Prediction Center assessments:

- NOAA's 1997 annual ENSO assessment describes one of the strongest Pacific warm episodes on record developing during 1997 and persisting into 1998:  
  https://www.cpc.ncep.noaa.gov/products/assessments/assess_97/enso.html
- NOAA's September 1997 diagnostic advisory reported tropical rainfall suppressed over Indonesia during the strong El Niño:  
  https://www.cpc.ncep.noaa.gov/products/predictions/experimental/bulletin/Sep97/art01.html
- NOAA's 1998 annual assessment states that monsoonal precipitation was suppressed across Indonesia during the 1997–98 El Niño, followed by development of cold-episode conditions and enhanced convective activity across portions of Indonesia during JJA 1998:  
  https://www.cpc.ncep.noaa.gov/products/assessments/assess_98/enso.html
- NOAA's 1999 assessment records La Niña becoming established by July 1998, accompanied by enhanced tropical convection throughout Indonesia and the western Pacific:  
  https://www.cpc.ncep.noaa.gov/products/assessments/assess_99/enso.html
- NOAA CPC's historical ONI table independently records the strong 1997 warm episode and transition to negative ONI values during 1998:  
  https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php

These sources support the **directional plausibility** of a dry-1997 / wetter-late-1998 regional transition in Indonesia. They do not validate a specific CHIRPS annual total for any Sumatera Barat kabupaten/kota.

## Diagnostic 2: spatial Tukey-IQR flags

For each year independently, the checker calculates Q1 and Q3 across the 19 geography-level annual estimates and flags values outside:

`[Q1 - 1.5 × IQR, Q3 + 1.5 × IQR]`

The calculation uses linear percentile interpolation, matching the diagnostic intent of the production dry-run.

An IQR flag is **descriptive review metadata only**. It is never an automatic rejection rule.

The frozen series has a concentrated review pattern in:

- Pariaman;
- Padang Pariaman;
- Padang;
- with isolated flags in Bukittinggi and Payakumbuh.

The three coastal focus geographies remain classified:

`unresolved_local_magnitude_pending_independent_station_validation`

because a spatial outlier can be physically real, a gridded-estimate artefact, or a local representativeness problem. Internal completeness and stable source identity are necessary but insufficient to distinguish those cases.

## Evidence boundaries

This milestone may conclude:

- the 1997→1998 transition is directionally coherent across the current Sumatera Barat frame;
- the direction is consistent with independent NOAA ENSO-era climate context;
- the frozen geometry, coverage, and evidence class remain internally consistent;
- repeated local spatial outliers deserve targeted independent validation rather than deletion.

It may **not** conclude:

- CHIRPS equals observed station rainfall;
- NOAA's regional ENSO assessment validates a kabupaten/kota rainfall magnitude;
- ENSO alone caused each annual rainfall value;
- Pariaman, Padang Pariaman, or Padang outliers are confirmed observations;
- station validation is complete.

## Exit gate

The milestone passes when:

1. the frozen baseline validator passes;
2. the sanity unit tests pass against the exact frozen 855-row baseline;
3. all 19 geographies have higher 1998 than 1997 rainfall in the frozen series;
4. the known spatial-IQR review profile remains stable;
5. evidence class remains `model_estimate`;
6. `independent_station_validation` remains `pending`;
7. no script or workflow modifies the frozen baseline.

The next climate task, if pursued later, is targeted independent validation of selected local magnitudes. Random manual BMKG downloads are not required by this milestone.
