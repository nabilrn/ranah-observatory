# BMKG Station Rainfall Overlap Qualification

## Objective

Ranah Observatory now has a frozen 1981–2025 CHIRPS v3 Final annual-rainfall `model_estimate` baseline. Before that baseline is treated as independently validated rainfall evidence, it needs overlap against direct station observations.

This phase evaluates credential-free BMKG-hosted routes before requesting manual Data Online downloads or relying on a secondary international archive.

No result in this phase changes:

`independent_station_validation = pending`

## Evidence hierarchy

For rainfall validation, the preferred evidence order is:

1. direct BMKG station observations with reproducible source identity and rainfall semantics;
2. another archive carrying traceable BMKG/WMO station observations, with BMKG/WIGOS retained as the station-identity authority;
3. manual authenticated BMKG Data Online extraction if no reproducible automatic historical route is available.

Operational weather feeds, gridded rainfall products, and current rainfall maps are not substitutes for a station-overlap validation dataset.

## BMKG WIS2 DayCLI

### Official collection

BMKG WIS2 exposes collection:

`urn:wmo:md:id-bmkg:climate-surface-based-observations`

The discovery metadata identifies the dataset as Daily Values Observations from Indonesia (DayCLI), with climate, temperature, precipitation, snow-depth, and DayCLI keywords.

Repository probe:

`scripts/probe_bmkg_wis2_daycli.py`

The probe inspects:

- collection metadata;
- collection queryables;
- collection schema;
- an unfiltered items request;
- the official WIS2 station registry entry for Minangkabau;
- station-filtered annual anchors for 1982, 1998, 2010, 2024, and 2025.

### Minangkabau station identity

The official BMKG WIS2 station registry resolves:

- WIGOS station identifier: `0-20000-0-96163`;
- traditional station identifier: `96163`;
- station name: `PADANG PARIAMAN/MINANGKABAU`;
- operational status in the station registry.

This establishes an authoritative machine-readable station identity for future overlap work.

It does not by itself establish rainfall-data availability.

## Live DayCLI observation finding

The live GitHub-hosted probe successfully reached:

- the DayCLI collection;
- queryables;
- schema;
- Minangkabau station metadata.

The supported GET filter form for the pygeoapi-backed endpoint was also verified. Station-filtered requests returned valid HTTP 200 GeoJSON FeatureCollections.

However, at the time of qualification:

- an **unfiltered** DayCLI items request returned `numberMatched = 0` and `numberReturned = 0`;
- Minangkabau station-filtered requests for 1982, 1998, 2010, 2024, and 2025 each returned zero features;
- no precipitation observation could therefore be extracted from DayCLI.

This is an important distinction: the API and metadata collection exist, but the observation collection exposed by this endpoint is currently empty.

The zero result is not attributed to a bad Minangkabau filter because the unfiltered collection itself also returns zero matched items.

## Qualification decision

BMKG WIS2 DayCLI is qualified in this project as:

`station_identity_and_collection_metadata_authority`

It is **not** qualified as:

- a historical station-rainfall archive;
- a recent station-rainfall validation dataset;
- an input capable of completing CHIRPS independent station validation.

Current canonical role:

`metadata_only_station_overlap_candidate`

The project must not infer observational availability from the DayCLI discovery metadata or precipitation keywords alone.

## Related BMKG WIS2 surface weather collection

BMKG WIS2 separately publishes a populated surface-weather observation collection for SYNOP data. Official WIS2 pages show Minangkabau observations and precipitation-related variables in that operational collection.

That collection is a different evidence object from DayCLI:

- it is operational SYNOP weather data;
- precipitation fields may have report-period semantics that require qualification before daily or monthly aggregation;
- recent operational availability does not establish the long historical overlap needed for 1981–2025 validation.

It may later support a recent-period spot validation, but it is not silently promoted in this phase.

## Data Online constraint

BMKG Data Online remains a direct-observation authority, but its current authenticated download workflow is operationally constrained and is not used automatically in this phase.

Ranah Observatory should only request a manual download when automated historical routes have been exhausted and the exact station, parameter, and period needed for validation are known.

## Next automatic fallback

Because DayCLI currently exposes no observation items, the next bounded acquisition step is to test archives that can carry BMKG/WMO station records while preserving Minangkabau's authoritative WIGOS/WMO identity.

Priority:

1. verify a long daily precipitation record for WMO `96163` / WIGOS `0-20000-0-96163` in a reproducible public station archive such as GHCN-D;
2. inspect BMKG-hosted SACA&D access for a directly downloadable Sumatera Barat precipitation series;
3. only if those routes cannot provide sufficient overlap, define a specific BMKG Data Online manual extraction request.

Any secondary archive transport must be documented as the archive/distribution source, while BMKG/WIGOS remains the authority for station identity.

## Promotion gate for CHIRPS validation

`independent_station_validation` must remain `pending` until a later phase has all of the following:

1. an actual station rainfall series, not metadata alone;
2. documented station identity and coordinates;
3. explicit rainfall accumulation-period and unit semantics;
4. enough overlapping complete periods with CHIRPS;
5. missing-data/completeness rules;
6. station-to-CHIRPS comparison statistics;
7. review of spatial-representativeness limits between a point gauge and a polygon/grid estimate.

A metadata endpoint, current SYNOP record, or a handful of rainfall reports is insufficient to complete this gate.
