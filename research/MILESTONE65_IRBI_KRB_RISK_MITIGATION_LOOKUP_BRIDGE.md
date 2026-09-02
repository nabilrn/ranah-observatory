# Milestone 65 — IRBI 2024 × KRB 2022–2026 Risk-Mitigation Lookup Bridge

## Purpose

Milestone 65 connects the BNPB IRBI 2024 hazard-risk layer from Milestone 62 to the BNPB/InaRISK KRB Sumatera Barat 2022–2026 mitigation-recommendation layer from Milestone 64.

The product goal is narrow and user-facing: when a dashboard user selects a hazard and district, the interface may show the official IRBI risk score/class together with the official KRB mitigation recommendations for the same explicitly matched hazard concept.

This is a **lookup bridge**, not a declaration that the two source taxonomies are globally equivalent.

## Inputs

M65 depends only on already-qualified BNPB source families:

- M62 IRBI 2024 hazard-specific risk table: 124 observed district × hazard rows across 9 IRBI hazards;
- M64 KRB recommendation context: 14 KRB hazards;
- M64 KRB mitigation actions: 60 source-native recommendation actions.

Input paths and SHA256 checksums are frozen in `data/manifests/milestone65_irbi_krb_lookup_bridge.json`.

## Authorized lookup matches

Nine hazards are authorized for risk-to-recommendation lookup because both the explicit hazard concepts and normalized source labels agree:

| IRBI hazard | KRB hazard | Lookup |
|---|---|---|
| Banjir | BANJIR | authorized |
| Gempabumi | GEMPABUMI | authorized |
| Tsunami | TSUNAMI | authorized |
| Letusan Gunung Api | LETUSAN GUNUNGAPI | authorized |
| Kebakaran Hutan dan Lahan | KEBAKARAN HUTAN DAN LAHAN | authorized |
| Tanah Longsor | TANAH LONGSOR | authorized |
| Gelombang Ekstrim dan Abrasi | GELOMBANG EKSTRIM DAN ABRASI | authorized |
| Kekeringan | KEKERINGAN | authorized |
| Cuaca Ekstrim | CUACA EKSTRIM | authorized |

The bridge preserves the source-native labels from both documents instead of replacing them with a synthetic universal taxonomy.

## Explicitly unmatched KRB hazards

Five KRB recommendation hazards have no corresponding table in the M62 Sumatera Barat IRBI 2024 hazard layer and therefore remain unmatched:

- Banjir Bandang;
- Likuefaksi;
- Epidemi dan Wabah Penyakit;
- Kegagalan Teknologi;
- COVID-19.

No missing IRBI row is fabricated for these hazards.

## Product lookup index

M65 materializes:

`data/processed/bnpb/irbi_krb_bridge_2024/irbi-risk-mitigation-lookup-index-2024.csv`

The table preserves all 124 M62 IRBI rows and adds only recommendation lookup metadata:

- `krb_hazard_id`;
- KRB source hazard label;
- number of available source-native mitigation actions;
- recommendation detail status;
- explicit bridge status and claim boundaries.

The original IRBI values are not recalculated. `risk_score`, `risk_class`, geography, year, and IRBI hazard identity must remain byte-equivalent at field level to the M62 rows.

## Crosswalk proof layer

`data/mappings/milestone65_irbi_krb_hazard_lookup_crosswalk.csv` contains all 14 KRB hazards:

- 9 `authorized_lookup_bridge` rows;
- 5 `no_irbi_2024_hazard_table_match` rows.

Every crosswalk row explicitly records whether risk-to-recommendation lookup is authorized and keeps numeric equivalence, event-taxonomy joining, and causal prediction disabled.

## Interpretation boundary

M65 authorizes only this operation:

> given an existing IRBI district × hazard risk observation, retrieve the KRB recommendation section/actions for the explicitly matched hazard concept.

M65 does **not** authorize the following conclusions:

1. IRBI and KRB use globally identical hazard taxonomies;
2. IRBI numeric risk values are equivalent to any KRB quantity;
3. IRBI/KRB hazards can automatically be joined to BPBD/Pusdalops event labels;
4. a high risk score predicts that a disaster will occur in a specified future period;
5. the number or order of KRB actions ranks mitigation effectiveness;
6. KRB recommendations prove that a mitigation action has been implemented;
7. absence of an IRBI hazard table means zero risk.

## Dashboard contract

The dashboard may use M65 to present a clean combined view such as:

- selected district and hazard;
- IRBI 2024 risk score and risk class;
- source family and year;
- number of official KRB mitigation recommendations available;
- link/filter to the M64 recommendation action table;
- explicit source notes.

The dashboard must not relabel the lookup as a forecast or implementation score.

## Reproducibility gate

The permanent M65 validator must enforce:

- exact upstream input checksums;
- 14 crosswalk rows;
- exactly 9 authorized lookup bridges;
- exactly 5 explicit unmatched KRB hazards;
- exact 124-row preservation of the M62 IRBI footprint;
- exact preservation of IRBI `risk_score` and `risk_class` fields;
- expected mitigation action counts for every matched hazard;
- all prediction/numeric-equivalence/event-taxonomy flags remain false;
- one public catalog entry pointing to the lookup index;
- deterministic byte-identical rebuild of crosswalk, lookup index, and manifest.
