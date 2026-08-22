# Milestone 26 — Disaster-Risk Evidence Chain Qualification

## Result

M26 is complete as a **staged evidence-qualification package**, not as a composite disaster-risk model.

Three official BNPB/InaRISK component sources were qualified and materialized across all 19 current Sumatera Barat kabupaten/kota:

- population exposure proxy: 2020, 19 observations;
- capacity index: 2021, 19 observations;
- DIBI recorded hydrometeorological occurrence/context: source-declared aggregate coverage 2015–2024, 19 observations.

The DIBI component is crosswalked through the previously qualified BNPB/Permendagri-to-canonical geography registry. Source `NO_KAB` values are retained in provenance and are **not** treated as BPS codes.

## Components that remain held

Flood and landslide hazard/vulnerability ImageServers remain blocked because exact official raster vintage/methodology binding is unresolved. The current InaRISK methodology page is framework evidence only and cannot supply a missing raster vintage.

Event-level observed impact also remains held. The legacy BNPB Data Bencana page exposes the desired impact fields, but the dated POST transport did not qualify deterministically. BNPB Satu Data was checked through metadata-only discovery in both the primary compilation package and the dedicated 2024 package; those packages expose aggregate impact resources but no metadata-qualified event-level candidate compatible with the locked Stage 2 estimand.

A zero-row dated legacy-table response is **not** interpreted as zero disaster occurrence or zero observed impact. Aggregate CKAN impact resources are **not** relabeled as event rows.

## Scientific boundary

`risk_synthesis_authorized = false`.

M26 does not:

- combine 2020 exposure, 2021 capacity, 2015–2024 occurrence context, or 2024 evidence into a contemporaneous score;
- aggregate undated hazard/vulnerability rasters;
- infer observed impact from DIBI occurrence fields;
- convert missing impact values to zero;
- rank kabupaten/kota by risk;
- fit a statistical or causal model;
- infer monetary disaster loss or monetary wasted potential.

## Frozen status

| Component | Status | Numeric footprint |
|---|---|---:|
| Population exposure proxy | qualified_and_materialized | 19 |
| Capacity | qualified_and_materialized | 19 |
| DIBI occurrence/context | qualified_and_materialized_source_native_aggregate | 19 |
| Event-level observed impact | held_event_level_transport_unqualified | 0 promoted |
| Flood hazard | endpoint_verified_version_binding_unresolved | 0 |
| Landslide hazard | endpoint_verified_version_binding_unresolved | 0 |
| Flood vulnerability | endpoint_verified_version_binding_unresolved | 0 |
| Landslide vulnerability | endpoint_verified_version_binding_unresolved | 0 |

## Reconsideration gates

Observed impact can be revisited only if a deterministic public event-level BNPB transport appears with documented event identity, target-period coverage, geography mapping, and missing-value semantics.

Hazard or vulnerability can be revisited only when an official source binds the exact raster/service to a dated release or methodology version.

Any future risk synthesis requires a separate preregistered temporal and estimand design; M26 itself does not authorize it.
