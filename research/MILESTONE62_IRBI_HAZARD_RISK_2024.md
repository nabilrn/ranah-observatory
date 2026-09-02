# Milestone 62 — BNPB IRBI 2024 Hazard-Specific Risk by District

## Goal

Materialize the official 2024 BNPB IRBI hazard-specific risk tables for Sumatera Barat into a canonical district × hazard dataset that can support dashboard filtering and maps without conflating risk scores with disaster-event frequency.

## Official source

Publication: **Indeks Risiko Bencana Indonesia Tahun 2024** published by Badan Nasional Penanggulangan Bencana (BNPB).

The acquisition lane reads the official InaRISK basic-HTML publication pages and selects rows whose province is `SUMATERA BARAT`. The source-native table is frozen at:

`data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-source-native.csv`

The canonical table is:

`data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-canonical.csv`

## Source footprint

Nine IRBI hazard sections produce **124 observed district × hazard pairs** for the 19 current Sumatera Barat kabupaten/kota.

| IRBI hazard | Observed Sumbar areas |
|---|---:|
| Banjir | 9 |
| Gempabumi | 19 |
| Tsunami | 7 |
| Letusan Gunung Api | 7 |
| Kebakaran Hutan dan Lahan | 19 |
| Tanah Longsor | 19 |
| Gelombang Ekstrim dan Abrasi | 7 |
| Kekeringan | 18 |
| Cuaca Ekstrim | 19 |

A complete 19 × 9 grid would contain 171 pairs, so **47 pairs are absent from the source tables**.

Those 47 absent pairs are not assigned score `0`, class `rendah`, or any inferred value.

## Geography mapping

All 124 source rows map to the canonical current Sumatera Barat geography registry.

The canonical primary key is:

`(year, geography_id, irbi_hazard_id)`

The geography summary is keyed by `geography_id`, not by display name. This is required because Kabupaten Solok (`idn.13.1303`) and Kota Solok (`idn.13.1372`) share the canonical display name `Solok` in the current registry.

## Taxonomy boundary

`irbi_hazard_id` is a local identifier namespace for this BNPB IRBI product.

M62 does **not** authorize direct taxonomy equivalence with BPBD/Pusdalops event labels. Similar-looking labels across IRBI and BPBD remain distinct source families unless a later explicit bridge is qualified.

Therefore:

- IRBI `flood` is not automatically joined to BPBD event `flood` as the same statistical variable;
- IRBI risk scores are not event counts;
- IRBI risk classes are not event probabilities;
- absence from a hazard table does not mean zero risk.

## Dashboard authorization

M62 authorizes the dashboard to:

- filter the 2024 risk layer by IRBI hazard;
- map observed district × hazard risk scores/classes;
- sort and compare areas within a source hazard table;
- expose coverage so users can distinguish observed source pairs from absent pairs;
- link each observation to its BNPB publication page provenance.

M62 does **not** authorize:

- converting scores into probabilities or percentages;
- claiming that a hazard will occur next year;
- ranking future event frequency from the IRBI score;
- treating missing district × hazard rows as zero;
- silently joining IRBI scores to BPBD event taxonomy.

## Risk-class observations

The source-native classes are preserved. Examples of the 2024 source footprint include:

- earthquake: 19 `tinggi`;
- drought: 18 `tinggi`;
- extreme weather: 11 `tinggi`, 8 `sedang`;
- landslide: 8 `tinggi`, 11 `sedang`;
- volcanic eruption: 6 `sedang`, 1 `rendah`.

These are source classifications, not Ranah Observatory predictions.

## Reproducibility contract

The permanent M62 gate validates:

1. exact source-native checksum and source-manifest lineage;
2. the 124-row canonical footprint;
3. exact 9-hazard source coverage;
4. uniqueness of every `(irbi_hazard_id, geography_id)` pair;
5. 19-area union and explicit Kabupaten/Kota Solok identity separation;
6. 47 absent pairs remaining absent rather than imputed;
7. taxonomy and prediction boundaries remaining fail-closed;
8. public catalog registration;
9. byte-identical deterministic canonical rebuild from the frozen source table.

## Product consequence

Together with M61, the disaster dashboard can now distinguish two different risk views:

- **overall composite IRBI trend**: 19 areas, 2015–2024;
- **hazard-specific IRBI risk**: 124 observed area × hazard combinations for 2024.

These risk products remain separate from BPBD/BNPB observed disaster-event datasets.
