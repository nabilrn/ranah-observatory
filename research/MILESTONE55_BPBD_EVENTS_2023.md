# Milestone 55 — BPBD 2023 District-by-Hazard Event Matrix

## Purpose

M55 fills a concrete dashboard proof-data gap for 2023: an official machine-readable matrix of disaster-event counts by current Sumatera Barat kabupaten/kota and source-native hazard label.

The source is Satu Data Sumatera Barat package **Jumlah Kejadian Bencana Tahun 2023**, produced by BPBD Provinsi Sumatera Barat with `Pusdalop BPBD Sumatera Barat` recorded as the data source.

## Official source

- Package ID: `e953d109-88d4-4be7-a0ad-ffc720b3c4a4`
- Resource ID: `e5d974eb-95a0-4570-93d1-9ca45c9fb77b`
- Resource: `Data Per Jenis Bencana.xlsx`
- Resource format: XLSX
- CKAN DataStore: active
- Year: 2023

The frozen acquisition uses the official CKAN DataStore representation and preserves the resource's own labels and values.

## Source-native footprint

The table contains exactly:

- 19 kabupaten/kota rows;
- one source `Jumlah` row;
- 10 hazard columns;
- one row total column.

Source-native hazard totals are:

| Hazard label | Events |
|---|---:|
| Abrasi pantai | 8 |
| Angin kencang | 562 |
| Banjir | 144 |
| Banjir Bandang | 10 |
| Erupsi Gunung Api | 44 |
| Gelombang Pasang | 1 |
| Gempa Bumi | 1 |
| Kebakaran Hutan & Lahan | 76 |
| Kekeringan | 19 |
| Longsor | 166 |
| **Total** | **1,031** |

Three independent additive checks reproduce **1,031 events**:

1. the source `Jumlah` row;
2. the sum of the 19 district row totals;
3. the sum of the ten hazard totals.

## Same-producer validation

The repository already contains an independently materialized 2023 BPBD/Pusdalops social-impact table. That table reports **1,031 disaster events** across the same 19 current kabupaten/kota.

M55 therefore gains a strong same-producer consistency check: the event-by-hazard matrix and the social-impact table independently reproduce the same annual event total.

This does not establish equivalence with other source families.

## Geography mapping

All 19 source district/city labels map exactly to the current Sumatera Barat geography registry.

The final dashboard-oriented long table contains:

- 19 geographies;
- 10 source-native hazard labels;
- 190 geography-hazard rows;
- canonical `geography_id`;
- source geography label;
- source hazard label;
- event count;
- source resource ID and claim type.

No historical-boundary claim is made because this is a 2023 current-geography product.

## Claim boundary

M55 authorizes this table as **observed, source-native BPBD/Pusdalops event-count proof data for 2023** and as a district/hazard filtering surface for the public dashboard.

It does **not**:

- harmonize the ten BPBD labels to DIBI or BNPB hazard taxonomies;
- claim that BPBD, DIBI, and BNPB event records are event-level equivalents;
- overwrite cross-source disagreements;
- infer missing values;
- reinterpret source zeroes;
- create a unified cross-year disaster series by silently switching source families.

The M54 2022 cross-publication disagreement remains an active warning against that type of unification.

## Outputs

- `data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-source-native.csv`
- `data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-canonical-long.csv`
- `data/manifests/milestone55_bpbd_events_2023.json`
- `data/manifests/milestone55_bpbd_events_2023_final.json`

## Product consequence

The 2023 disaster view can now support a clean combination of:

- event distribution by kabupaten/kota and hazard;
- human impacts by kabupaten/kota;
- housing damage by kabupaten/kota;
- available economic-loss observations and explicit loss-coverage gaps;
- proof-table links back to source-native materializations.

This is sufficient for a useful 2023 evidence slice without pretending that every disaster source is one homogeneous timeseries.
