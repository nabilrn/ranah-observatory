# Milestone 58 — BPBD 2024 District Event Totals

## Purpose

M58 adds a district-level 2024 disaster-event layer for the public dashboard from the official Satu Data Sumatera Barat package **Data dan Dampak Bencana Tahun 2024**.

This milestone is deliberately narrower than M57. The selected 2024 resource supports event totals by kabupaten/kota, but it does **not** contain a usable hazard dimension.

## Official source

- Package ID: `24704fb3-6b59-4a67-94a3-ab585a33f303`
- Resource ID: `9d99b5ed-a005-4b35-880c-7e9954c9ade5`
- Resource: `Jumlah Kejadian Bencana Per Kab/Kota Tahun 2024`
- Organization: Badan Penanggulangan Bencana Daerah
- CKAN DataStore: active
- Period: 2024

The source-native DataStore representation is frozen without rewriting its headers.

## Source schema issue

The source exposes three fields:

- `Kode Wilayah`
- `Jenis Bencana`
- `Jumlah Kejadian`

However, the 19 non-total values in `Jenis Bencana` are not hazard names. They are names such as `KABUPATEN AGAM`, `KOTA PADANG`, and the other current Sumatera Barat kabupaten/kota.

Each of those values forms an exact pair with its `Kode Wilayah` value and the repository's current BPS geography registry. M58 therefore interprets the observed role of this source field as **source geography name** while preserving the original misleading header in the source-native file.

This interpretation does not create a hazard dimension. M58 explicitly records `hazard_dimension_present_in_this_resource = false`.

## Geography mapping

All 19 current Sumatera Barat kabupaten/kota map exactly through the source `Kode Wilayah` to the canonical `bps_code` registry.

The promoted district table contains exactly 19 rows with:

- year;
- canonical geography ID and name;
- source geography code and source geography name;
- event count;
- source resource ID and claim type.

No missing district is fabricated and no source row is split across geographies.

## Source-internal disagreement

The source contains an important arithmetic disagreement:

- source `Total` row: **1,175 events**;
- sum of the 19 district rows: **1,166 events**;
- unexplained difference: **9 events**.

The repository's independently materialized BPBD 2024 monthly-by-hazard context also totals **1,175 events**. This is useful BPBD-organization consistency evidence for the source total, but M58 does **not** assert producer-level identity because the selected district resource does not declare `Sumber Data` in its package metadata.

No official allocation or omission explanation for the 9-event difference has been identified in this resource.

Therefore M58 does not:

- add the 9 events to any kabupaten/kota;
- proportionally distribute the difference;
- alter a district count to force reconciliation;
- claim that the district rows themselves reproduce the provincial total.

## Dashboard contract

The 19 district rows are authorized as observed district-level proof data and are suitable for a 2024 district filter or map.

The dashboard must keep two quantities distinct:

- **official source total: 1,175 events**;
- **events allocated by the source to the 19 district rows: 1,166 events**.

A coverage/data-quality note must expose the unresolved **9-event gap** whenever district rows and the provincial total are shown together.

The provincial total must not be recomputed from the district rows and presented as 1,175.

## Claim boundary

M58 does **not**:

- treat `Jenis Bencana` as a hazard field after the schema review;
- create a district × hazard matrix for 2024;
- infer the missing allocation of 9 events;
- claim equivalence with BNPB event records;
- harmonize this resource with the M57 2023 hazard taxonomy;
- silently build a cross-source or cross-year homogeneous disaster series.

M57 remains the source-native 2023 district × hazard layer. M58 adds a separate 2024 district-total layer with an explicit coverage limitation.

## Outputs

- `data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-source-native.csv`
- `data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-canonical-district.csv`
- `data/manifests/milestone58_bpbd_events_2024_acquisition.json`
- `data/manifests/milestone58_bpbd_events_2024_final.json`

## Product consequence

The public disaster workspace can now show 2024 event counts by kabupaten/kota alongside the existing 2024 BPBD casualty, monthly hazard, and preparedness context. The district layer is useful, but its 9-event allocation gap remains part of the proof data rather than being repaired away.
