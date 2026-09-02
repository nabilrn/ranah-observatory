# Milestone 57 — BPBD 2023 District-by-Hazard Event Matrix

## Purpose

M57 fills a concrete dashboard proof-data gap for 2023: an official machine-readable matrix of disaster-event counts by current Sumatera Barat kabupaten/kota and source-native hazard label.

This milestone follows M56's recovery of the official DIBI 2022 raw artifact but remains an independent Satu Data Sumbar / BPBD operational-data lane. It does not merge the two source families.

## Official source

- Dataset: `Jumlah Kejadian Bencana Tahun 2023`
- Package ID: `e953d109-88d4-4be7-a0ad-ffc720b3c4a4`
- Resource ID: `e5d974eb-95a0-4570-93d1-9ca45c9fb77b`
- Resource: `Data Per Jenis Bencana.xlsx`
- Producer: BPBD Provinsi Sumatera Barat
- Source data: Pusdalop BPBD Sumatera Barat
- CKAN DataStore: active

## Verified footprint

The official table contains exactly 19 kabupaten/kota rows plus one `Jumlah` row and ten source-native hazard columns.

| Source hazard label | Events |
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

Three additive checks independently produce 1,031: the source total row, the sum of all 19 district totals, and the sum of all ten hazard totals.

## Independent same-producer check

The previously materialized 2023 BPBD/Pusdalops social-impact table also reports exactly **1,031 disaster events** across the same 19 current kabupaten/kota. M57 therefore has a same-producer cross-table consistency check without needing to force reconciliation to another institution's disaster series.

## Canonical geography mapping

All 19 source names map exactly to the current Sumatera Barat geography registry. The dashboard-oriented long output contains 190 rows (`19 geographies × 10 source hazard labels`) with canonical geography IDs while retaining original source geography and hazard labels.

## Claim boundary

M57 authorizes the final table as **observed BPBD/Pusdalops proof data for 2023** and as a district/hazard dashboard filtering surface.

It does not:

- harmonize BPBD hazard labels to DIBI or BNPB;
- claim event-level equivalence across BPBD, DIBI, or BNPB;
- overwrite cross-source disagreements;
- infer missing values;
- reinterpret source zeroes;
- create a unified cross-year series by silently switching source families.

M54's 2022 official-source disagreement and M56's raw DIBI verification remain separate evidence objects.

## Outputs

- `data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-source-native.csv`
- `data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-canonical-long.csv`
- `data/manifests/milestone57_bpbd_events_2023.json`
- `data/manifests/milestone57_bpbd_events_2023_final.json`

Together with the existing 2023 impact, housing, and loss tables, this gives the dashboard a clean 2023 evidence slice for event distribution, victims, physical damage, economic-loss coverage, and source-native proof rows.
