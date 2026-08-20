# Milestone 26 — BNPB/InaRISK Disaster-Risk Chain Qualification

## Purpose

M26 executes the third Tier-A acquisition package preregistered by M23: qualify the missing disaster-risk components required before any composite risk or resilience-intervention synthesis is allowed.

M26 is staged evidence qualification. It is **not** permission to calculate an InaRISK-like risk score, rank West Sumatra kabupaten/kota, infer disaster causality, or monetize disaster-related wasted potential.

## Locked upstream evidence

M26 inherits without reinterpretation:

- the 19-current-kabupaten/kota BIG June 2026 fixed-boundary geography regime;
- M16 earthquake shaking intensity as `hazard_intensity` for the 2009-09-30 event;
- M16 CHIRPS 2024 rainfall as `climate_context`, not station or event-day rainfall;
- M16 BNPB 2024 flood/landslide counts as `recorded_event_occurrence`, not impact;
- M16's explicit separation of hazard, exposure, vulnerability, capacity, occurrence, observed impact, and modeled risk;
- M23's Tier-A requirement to complete the disaster-risk evidence chain before additional risk-model complexity.

## Stage 0 — official-source and vintage qualification

Before any raster or event-level values are promoted into the substantive 19-geography frame, M26 must freeze and validate the official source surfaces.

### A. Capacity

Candidate: BNPB InaRISK ArcGIS ImageServer `INDEKS_KAPASITAS_2021`.

The service name exposes an explicit 2021 vintage. Stage 0 may upgrade this source from M16's generic capacity gap only if the official service is reachable, parseable, single-band, spatially national, and its identity is stable under a checksum-bound metadata snapshot.

This does not imply that the index is temporally compatible with 2009 earthquake evidence or 2024 hydroclimate evidence.

### B. Population exposure proxy

Candidate: BNPB InaRISK `INARISKPOP_2020`.

The service and item metadata explicitly identify a 2020 population-distribution raster. It may qualify only as a **population exposure proxy / element-at-risk surface**. It is not asset exposure, disaster impact, vulnerability itself, or a historical population panel.

### C. Recorded hydrometeorological occurrence context

Candidate: BNPB InaRISK `DIBI_Kabupaten_2015_2024_Hidromet` MapServer.

Stage 0 may qualify its service coverage and kabupaten-level schema as occurrence/context evidence. Aggregate fields must not be silently reinterpreted as casualties, damage, loss, or event-level observed impact.

### D. Event-level observed-impact surface

Candidate: official BNPB Data Bencana search table.

The public table exposes event date, event type, location, kabupaten/province, and impact columns including deaths, missing, injured, damaged houses, inundated houses, and damaged public facilities. Stage 0 only verifies the field/access surface. No historical impact panel is authorized until a deterministic event-level retrieval contract, missing-value semantics, duplicate/event identity rules, and geography mapping are frozen.

### E. Flood and landslide hazard/vulnerability rasters

Candidates:

- `INDEKS_BAHAYA_BANJIR`;
- `INDEKS_BAHAYA_TANAHLONGSOR`;
- `INDEKS_KERENTANAN_BANJIR`;
- `INDEKS_KERENTANAN_TANAH_LONGSOR`.

These services are official and machine-readable, but their endpoint names alone do not establish a sufficiently explicit exact vintage/methodology binding. They remain `endpoint_verified_version_binding_unresolved` unless M26 obtains an official metadata object that binds the exact service/raster to a dated methodology or release.

No raster pixel may enter the substantive frame merely because the current InaRISK web interface describes a current risk methodology.

## Current methodology surface

M26 records the current official InaRISK methodology page as framework evidence only. It supports the conceptual distinction among risk components; it does not retroactively version-bind an otherwise undated ArcGIS raster service.

## Promotion states

Every source must resolve to exactly one of:

- `qualified_explicit_vintage_metadata`;
- `qualified_explicit_coverage_metadata`;
- `field_surface_verified_retrieval_contract_pending`;
- `endpoint_verified_version_binding_unresolved`;
- `unavailable_or_unparseable`.

Only the first two states can authorize downstream numeric extraction, and only for the component class explicitly stated in the source contract.

## Stage 1 — component extraction (not authorized by Stage 0 alone)

A later Stage 1 may extract only Stage-0-qualified sources. It must preregister aggregation semantics before reading cross-geography values.

Potentially eligible objects after Stage 0:

- 2021 capacity index aggregated to the 19 fixed current boundaries;
- 2020 population-exposure proxy aggregated to the same boundaries;
- DIBI 2015–2024 occurrence/context attributes if their field semantics qualify;
- event-level impact observations only after deterministic retrieval and identity contracts are frozen.

## Risk-synthesis gate

`risk_synthesis_authorized` remains `false` unless all of the following are simultaneously true for a clearly defined hazard/temporal regime:

1. hazard evidence is explicitly version-bound;
2. exposure evidence is qualified;
3. vulnerability evidence is explicitly version-bound;
4. capacity evidence is qualified;
5. observed impact is qualified when used for validation or consequence claims;
6. component temporal compatibility is documented rather than assumed;
7. the synthesis formula/estimand is preregistered before cross-geography outcome inspection.

M26 may complete with `risk_synthesis_authorized=false`.

## Forbidden operations

M26 must not:

- aggregate an undated hazard/vulnerability raster into the substantive frame;
- infer raster vintage from visual WebGIS grouping or current website presentation;
- relabel population density as vulnerability or observed impact;
- relabel DIBI occurrence totals as deaths, damage, or monetary loss;
- combine 2009, 2020, 2021, and 2024 components into one contemporaneous risk score without an explicit temporal design;
- rank kabupaten/kota by disaster risk before the synthesis gate passes;
- claim climate-change or disaster causality;
- estimate monetary wasted potential.

## Stage 0 required outputs

1. `data/manifests/milestone26_design_gate.json`
2. `data/registries/m26-bnpb-source-candidates.csv`
3. `data/analysis/engine/disaster_risk_chain_v1/m26-source-qualification.csv`
4. `data/manifests/milestone26_source_qualification.json`
5. checksum-bound source metadata snapshots under `data/processed/bnpb/m26_source_qualification/`

## Stage 0 completion gate

Stage 0 completes when:

- every preregistered source candidate has a frozen qualification outcome;
- capacity 2021, population 2020, and DIBI 2015–2024 are verified against official machine-readable metadata rather than names alone where metadata exists;
- hazard/vulnerability services remain blocked unless an exact official version binding is found;
- the event-level impact table is not promoted before its retrieval contract is deterministic;
- no source values are aggregated to the 19-geography substantive frame;
- no risk score/model is fitted;
- focused tests pass and the qualification output is deterministic from the frozen metadata.

## Completion semantics

M26 Stage 0 is a **source/vintage qualification result**. It is not a complete disaster-risk model. A later stage may proceed component by component according to the frozen promotion states.