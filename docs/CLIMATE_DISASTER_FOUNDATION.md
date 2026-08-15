# Climate and Disaster Foundation

This phase adds official climate/disaster source contracts without collapsing distinct evidence layers.

## Evidence model

Ranah Observatory treats the following as different objects:

1. **Meteorological hazard** — observed rainfall, temperature, or derived extremes from BMKG.
2. **Recorded disaster event** — an event classified and recorded by BNPB/DIBI.
3. **Reported impact** — affected, displaced, injured, missing, or deceased people and damaged assets.
4. **Reported damage/loss value** — administrative accounting or proposal-derived monetary values.

A flood-event count is not rainfall intensity. A high-rainfall year is not automatically a disaster year. A reported affected-person count is not automatically a unique-person exposure count. Damage/loss records from rehabilitation and reconstruction proposals are not assumed to be a complete census of economic loss.

## Primary machine-readable disaster lane: BNPB Satu Data

BNPB's Portal Satu Data Bencana Indonesia is a CKAN portal. Public DataStore resources can be queried through the CKAN action API without project credentials.

Primary endpoints used by this repository:

- `https://data.bnpb.go.id/api/3/action/package_show`
- `https://data.bnpb.go.id/api/3/action/datastore_search`

The primary historical compilation dataset is `f61d78e5-04c6-4ce8-9acf-e425dadc1f4d` (`Kompilasi Data Kejadian dan Dampak Bencana`).

### Important scope distinction

Resource `21044ffd-c397-4b3c-acbd-5adaa03d79e3` reports **total recorded disaster events by kabupaten/kota for each year 2010–2024**. It does not provide a disaster-type-by-year-by-kabupaten cube. Therefore it is retained as source-native context and must not be relabeled as historical flood or landslide counts.

Resource `a4daec53-1119-43ef-b05e-00ec3a4c42a4` reports **2024 event counts by disaster type and kabupaten/kota**. Its `BANJIR` and `TANAH LONGSOR` columns are the first source rows eligible for canonical `flood_events` and `landslide_events` observations.

The dedicated 2024 compilation also exposes resource `5ff9f41f-8312-4b7c-aa18-fdbedac6ee7e` with the same conceptual event-by-type-by-kabupaten structure. It is used as an independent official cross-check, not silently concatenated as another year.

Resource `89eb9dac-a891-477e-b264-2265f72f4e56` reports 2024 affected-person counts by disaster type and kabupaten/kota. It remains **held source-native** until annual aggregation semantics are qualified well enough to determine whether summed values can be interpreted as unique affected persons.

### 2025 release boundary

BNPB publishes a separate `Kompilasi Data Kejadian dan Dampak Bencana 2025` dataset (`58878b43-41b5-4ffb-b851-c6d8c8c4d438`). It is a separate source release with its own schema/granularity and is not appended to 2010–2024 merely because the calendar years are adjacent.

## Geography contract

BNPB DataStore metadata describes its kabupaten/kota code and name fields as based on Permendagri. Canonical Ranah Observatory geography records use BPS statistical codes. The two code systems are never assumed interchangeable.

Live artifact review showed why this matters: in the reviewed BNPB resources, source code `1301` is `PESISIR SELATAN`, source code `1309` is `KEPULAUAN MENTAWAI`, `1310` is `DHARMASRAYA`, and `1311` is `SOLOK SELATAN`. Those assignments must not be interpreted using the canonical BPS code registry.

For the first 2024 detailed panel, `data/registries/bnpb_geography_map.csv` stores the exact **code + source-name pair** observed consistently in all four reviewed BNPB resources and maps that pair to a canonical Ranah Observatory geography ID. The source code and source name remain in provenance. A live pre-build validator requires every reviewed resource to reproduce all 19 expected code/name pairs exactly; any code/name drift is a hard failure before canonical mapping occurs.

The crosswalk is deliberately scoped to the reviewed 2024 resource family. It does not claim that these assignments describe every Permendagri vintage, nor does it authorize projecting current administrative units backward through the 2010–2024 all-disaster total series.

Historical administrative-boundary reconstruction remains a separate layer.

## BMKG hazard lane

### Satu Peta MKG

BMKG's official Satu Peta MKG API registry lists `Peta Curah Hujan dan hari Hujan` as a public WMS. The registry is a qualified discovery source for gridded/map products, but hosted-runner accessibility and temporal/product semantics must be tested before observations are materialized.

Official registry:

`https://gis.bmkg.go.id/portal/dataapi`

### Data Online

BMKG Data Online provides station climate observations, including rainfall (`RR`), but uses an authenticated user workflow and constrains download windows. It is retained as the preferred station-observation lane when reproducible acquisition can be established; it is not replaced by forecast data.

`https://dataonline.bmkg.go.id/dataonline-home`

### Forecast API exclusion

BMKG's public forecast API is useful for prospective weather applications but is not historical observed climate evidence. Ranah Observatory must not use forecasts as substitutes for annual rainfall, extreme-rainfall-day, or mean-temperature observations.

## Initial canonical scope

The first BNPB artifact may promote only:

- `flood_events` — 2024, current kabupaten/kota, source column `BANJIR`;
- `landslide_events` — 2024, current kabupaten/kota, source column `TANAH LONGSOR`.

Expected first canonical footprint: 19 geographies × 2 indicators = **38 observations**.

The following are intentionally not promoted in this phase:

- total disaster events 2010–2024 → source-native contextual series;
- affected population 2024 → held until aggregation/uniqueness semantics are qualified;
- direct disaster loss → held until monetary coverage, nominal price year, and missingness are qualified;
- BMKG rainfall/temperature → held until an observed-data acquisition route is verified.

## Provenance requirements

Every harvested artifact records:

- official CKAN action endpoint;
- package/resource ID;
- retrieval timestamp;
- full source fields and records;
- source URL where known;
- SHA-256 checksum.

Canonical rows retain the BNPB source code/name and mapping rule in notes. A second official 2024 event resource is compared before promotion; disagreement is a hard failure and must be investigated rather than averaged or silently resolved.

The CKAN portal is an external dependency. Safe GET requests retry transient network/server and Cloudflare origin errors. Package metadata discovery is useful but is not allowed to block a live DataStore build when the qualified resource IDs are already pinned; the observation-producing DataStore resources remain hard requirements.

## Exit gate

This foundation is ready to merge when:

1. offline source/qualification contracts validate;
2. CKAN client tests pass;
3. one live credential-free BNPB harvest succeeds on GitHub Actions;
4. all four reviewed DataStore resources reproduce the exact 19 Sumatera Barat code/name pairs before mapping;
5. the two official 2024 event resources agree for Sumatera Barat on flood and landslide values;
6. exactly 38 canonical event observations are produced;
7. 2010–2024 total-event and affected-person rows remain explicitly source-native/held;
8. no BMKG forecast product is promoted as observed climate evidence.
