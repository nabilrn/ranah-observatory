# Milestone 26 — BNPB event-impact machine-readable transport candidate

## Purpose

M26 Stage 0 already verified the official BNPB public event-impact HTML field surface but held event-level impact because the retrieval contract was not deterministic. This checkpoint records a stronger transport surface discovered on the same official BNPB ArcGIS host:

`Hosted/Data_Bencana_Dashboard/FeatureServer/0`

The purpose is to reduce the transport gap without weakening the original fail-closed design. No event values are promoted in this checkpoint.

## What is now verified

The official ArcGIS REST metadata identifies layer `0` (`Sheet2`) as a point `Feature Layer` with service item ID `cc34bb232b504e279ee1c94c081e3860`.

The layer exposes:

- an explicit `objectid` OID field;
- candidate source identifiers `id`, `xdibi`, `serial`, and `kib`;
- province and kabupaten/kota names through `nprop` and `nkab`;
- event type and date fields including `id_jenis_bencana`, `kejadian`, `tahun`, `bulan`, `tanggal`, and `tgl`;
- human-impact fields including `meninggal`, `hilang`, `terluka`, `menderita`, and `mengungsi`;
- housing-impact fields including damaged-house severity fields and `terendam`;
- public-facility damage fields;
- `kerugian_juta` plus source/documentation fields.

The service advertises Query capability, a `maxRecordCount` of 2000, JSON/geoJSON/PBF query formats, advanced queries, ordering, pagination, statistics, and standardized queries. These properties make it materially more suitable for a reproducible retrieval contract than scraping the public HTML table.

## Why this does not yet authorize an event panel

The new transport resolves only one part of the original M26 hold.

### 1. Stable event identity is still unknown

`objectid` is an ArcGIS object identifier, but this checkpoint has not established that it is stable across future service snapshots. The other candidate identifiers (`id`, `xdibi`, `serial`, `kib`) are nullable in the published schema and have not been profiled for uniqueness or persistence.

No field is therefore designated as the canonical event key yet.

### 2. Field typing is heterogeneous

The published schema itself exposes typing hazards. For example:

- `terluka` is declared as `esriFieldTypeString`, unlike several other headline casualty fields;
- `pabrik_rusak_sedang` is declared as `esriFieldTypeString`, while nearby detailed damage fields are integers.

A parser must not silently convert blanks, text tokens, malformed values, or nulls to zero. Numeric rules need to be frozen field by field after observing source-native values.

### 3. Geography mapping is not frozen

The service exposes `nprop` and `nkab` as strings. This checkpoint has not established a BPS-code field or frozen the exact source-native spelling used for Sumatera Barat and its kabupaten/kota.

The first retrieval audit must therefore enumerate distinct source-native province labels before writing a province filter, then validate district/city names against the canonical Ranah Observatory geography registry.

### 4. Duplicate semantics remain unknown

The dataset contains multiple possible identifiers and update/status fields. Without inspecting source-native rows, repeated records could represent duplicate events, updates to one event, multiple impact reports for one event, or genuinely separate events.

Blind deduplication is forbidden.

### 5. The surface is live

The dashboard is a current operational surface. A reproducible research extraction requires frozen raw pages with retrieval timestamps and checksums rather than assuming the endpoint contents are immutable.

## Transport classification

The candidate is classified as:

`official_machine_readable_transport_verified_retrieval_contract_pending`

This is a transport upgrade candidate for the already-preregistered `bnpb_event_impact_table` evidence family. It is not a new hazard family or a post-hoc search for a more favorable result.

The original M26 qualification remains authoritative until the retrieval audit passes:

`field_surface_verified_retrieval_contract_pending`

## Locked next audit

The next acquisition pass must proceed in this order:

1. freeze the FeatureServer metadata response and SHA-256;
2. retrieve distinct source-native province labels;
3. freeze the exact Sumatera Barat label;
4. query with explicit `outFields`, `returnGeometry=false`, `orderByFields=objectid ASC`, and deterministic pagination no larger than the published record limit;
5. save every raw response page with retrieval timestamp and SHA-256;
6. profile nullness and uniqueness for `objectid`, `id`, `xdibi`, `serial`, and `kib` without deduplicating;
7. profile source-native values for each proposed impact field and freeze parsing/null semantics;
8. audit `nkab` values against the canonical 19-current-boundary geography registry;
9. only then decide whether event-panel materialization can be authorized.

## Hard gate

Until that audit succeeds:

- do not replace the HTML source as the canonical M26 transport;
- do not promote event rows or impact values;
- do not treat null as zero;
- do not cast string impact fields silently;
- do not use `objectid` as a cross-snapshot event identifier;
- do not deduplicate by convenience;
- do not aggregate event values to kabupaten/kota;
- do not use `kerugian_juta` for monetary wasted-potential claims;
- do not combine this surface into a synthetic disaster-risk score;
- do not make causal disaster or climate claims.

## Result

M26's observed-impact gap is narrower than before: the project now has an official machine-readable BNPB transport candidate with query and pagination support. The remaining problem is no longer basic access; it is a research-data contract problem involving identity, typing, missingness, duplicates, geography mapping, and snapshot reproducibility.
