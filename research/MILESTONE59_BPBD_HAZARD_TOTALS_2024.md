# Milestone 59 — BPBD 2024 Hazard Totals Reconciliation

## Purpose

M59 qualifies the official BPBD/Pusdalop **Jumlah Kejadian Bencana 2024** aggregate resource and uses it as an independent cross-table check against the already materialized 2024 monthly event table.

The goal is not to create a new incompatible hazard taxonomy. The goal is to prove that the seven annual hazard totals used by the dashboard are reproduced independently by a second official source table from the same producer and `Sumber Data` lineage.

## Official aggregate source

- Package ID: `fd77b7eb-a2e4-4ee7-8a6a-78df1b15e4c6`
- Resource ID: `43fc1b1b-bd4e-4a8e-887d-754029f0b074`
- Resource: `Jumlah Kejadian Bencana 2024.xlsx`
- Producer: BPBD Provinsi Sumatera Barat
- Sumber Data: Pusdalop BPBD Sumatera Barat
- CKAN DataStore: active
- Period: 2024

The source contains seven hazard rows plus one `Total` row.

## Source-native totals

| Jenis bencana | Kejadian |
|---|---:|
| Banjir | 253 |
| Cuaca ekstrem | 587 |
| Erupsi Gunung Api | 9 |
| Gelombang Pasang dan abrasi | 14 |
| Kebakaran Hutan dan Lahan | 25 |
| Kekeringan | 2 |
| Tanah Longsor | 285 |
| **Total** | **1,175** |

The seven hazard rows sum exactly to the source `Total` row: **1,175**.

## Independent monthly cross-check

The repository already contains the official BPBD/Pusdalop 2024 monthly event table with 84 rows: 12 months × 7 hazards.

When those monthly rows are summed by the same hazard labels, every annual total matches the separate aggregate resource exactly:

- Banjir: 253 = 253;
- Cuaca ekstrem: 587 = 587;
- Erupsi Gunung Api: 9 = 9;
- Gelombang Pasang dan abrasi: 14 = 14;
- Kebakaran Hutan dan Lahan: 25 = 25;
- Kekeringan: 2 = 2;
- Tanah Longsor: 285 = 285.

The total is also identical: **1,175 = 1,175**.

This is a 7/7 hazard-level reconciliation, not only a matching grand total.

## Lineage check

The aggregate resource and the monthly resource both declare:

- producer: `BPBD Provinsi Sumatera Barat`;
- source data: `Pusdalop BPBD Sumatera Barat`.

M59 therefore records this as a same-producer / same-source-data reconciliation.

That lineage statement does not extend to BNPB or other disaster databases.

## Hazard IDs

M59 reuses the same seven internal hazard IDs already assigned to the BPBD monthly table:

- `flood`
- `extreme_weather`
- `volcanic_eruption`
- `tidal_wave_and_coastal_erosion`
- `forest_and_land_fire`
- `drought`
- `landslide`

This is a same-family representation mapping for identical BPBD/Pusdalop source labels. It is **not** authorization to equate these records with BNPB/DIBI hazard taxonomies or event identities.

## Dashboard contract

The seven annual hazard totals are authorized for a clean 2024 hazard filter, summary card, or proof table.

The dashboard may state that the annual hazard totals are independently reproduced from the monthly BPBD/Pusdalop table.

It must not state that the same counts necessarily equal BNPB counts or that cross-source event identity has been proven.

## Relation to M58

M58 and M59 expose two different 2024 facts:

- M58 district rows allocate **1,166** events across 19 kabupaten/kota while the source total is **1,175**, leaving a 9-event unresolved district allocation gap;
- M59 hazard rows allocate the full **1,175** events across seven hazards and reconcile perfectly with the monthly hazard table.

Therefore the unresolved M58 problem is specifically a district-allocation problem. M59 does not justify assigning the missing nine events to any district.

## Claim boundary

M59 does **not**:

- infer district allocation for the M58 nine-event gap;
- claim event-level equivalence between the aggregate and monthly rows;
- equate BPBD/Pusdalop records with BNPB/DIBI;
- authorize cross-source taxonomy harmonization;
- convert source blanks in the monthly table into independently observed zeros.

Monthly blank semantics remain governed by the existing BPBD context materialization.

## Outputs

- `data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-source-native.csv`
- `data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-canonical.csv`
- `data/manifests/milestone59_bpbd_hazard_totals_2024_acquisition.json`
- `data/manifests/milestone59_bpbd_hazard_totals_2024_final.json`

## Product consequence

The 2024 disaster dashboard now has a strongly validated hazard-total layer: seven annual hazard totals from a dedicated official aggregate table, independently reproduced by the 84-row monthly BPBD/Pusdalop source.
