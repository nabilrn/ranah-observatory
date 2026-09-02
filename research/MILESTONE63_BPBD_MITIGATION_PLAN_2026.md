# Milestone 63 — BPBD Sumatera Barat 2026 Mitigation Planning Context

## Goal

Add an official mitigation-planning context layer to the disaster product without misrepresenting forward targets as achieved capacity and without converting qualitative institutional problems into invented scores.

## Official source

**Rencana Kerja BPBD Provinsi Sumatera Barat Tahun 2026**, published by Badan Penanggulangan Bencana Daerah Provinsi Sumatera Barat and contained within the 2026 provincial planning framework referenced by Peraturan Gubernur Sumatera Barat Nomor 23 Tahun 2025.

The official PDF is frozen at:

`data/raw/bpbd/m63_renja_2026/renja-bpbd-sumbar-2026.pdf`

A non-OCR `pdftotext -layout` excerpt covering physical PDF pages 51–64 is frozen at:

`data/processed/bpbd/mitigation_plan_2026/renja-bpbd-2026-pages-51-64.txt`

## Two distinct product layers

M63 deliberately produces two different datasets.

### 1. 2026 planning targets

`data/processed/bpbd/mitigation_plan_2026/bpbd-mitigation-targets-2026.csv`

Thirteen source-supported targets are materialized:

| Planning indicator | 2026 target |
|---|---:|
| Preparedness for facing disasters | 72% |
| Hazard-information dissemination | 56% |
| Legalized provincial disaster-risk assessment | 1 document |
| KIE recipients in high-risk areas | 425 people |
| Population trained for prevention/preparedness | 56% |
| Areas targeted for preparedness-capacity strengthening | 3 areas |
| Preparedness-drill participants | 300 people |
| Priority-hazard contingency plans | 1 document |
| Risk root-cause handling | 1 activity |
| Certified provincial TRC personnel | 60 people |
| High-risk families receiving protection/preparedness equipment | 750 families |
| Legalized SKPDB/process/procedure document | 1 document |
| Prevention and mitigation training participants | 120 people |

Every row is typed `official_planning_target` and explicitly carries `actual_achievement_claimed=false`.

M63 does not materialize the planning-table budget columns. The source juxtaposes `Rancangan Awal RKPD` and `Hasil Analisis Kebutuhan`, and some indicative budget values differ even when output targets remain the same. Avoiding a budget comparison here prevents two separate planning columns from being collapsed into a misleading single figure.

### 2. Official qualitative mitigation/implementation gaps

`data/processed/bpbd/mitigation_plan_2026/bpbd-mitigation-gaps-2026.csv`

The Renja lists **18** problems/constraints, which M63 preserves as concise source-faithful diagnostic labels covering:

1. incomplete disaster-planning documents;
2. limited DIBI access/accuracy;
3. incomplete disaster-information dissemination/socialization;
4. TRC PB formation/development gaps;
5. Forum PRB formation gaps;
6. nagari tangguh formation/development gaps;
7. disaster-volunteer development gaps;
8. inadequate PUSDALOPS PB operations;
9. insufficient simulation/training;
10. inadequate temporary evacuation sites and evacuation routes;
11. inadequate preparedness and early-warning equipment;
12. inadequate field equipment and disaster logistics;
13. inadequate rehabilitation/reconstruction support equipment;
14. emergency-standby and response coordination gaps;
15. incomplete contingency-plan-based emergency operations;
16. emergency monitoring/evaluation gaps;
17. JITU PASNA preparation gaps; and
18. rehabilitation/reconstruction coordination and monitoring/evaluation gaps.

These rows are typed `official_planning_diagnostic`, `quantified=false`, and `municipality_identified=false`.

The document says that some province/kabupaten/kota actors still have particular gaps, but it does not identify a complete municipality-by-municipality matrix in this excerpt. M63 therefore does not assign any gap to a specific kabupaten/kota.

## Interpretation boundary

M63 authorizes statements such as:

- “BPBD's 2026 plan targets 300 preparedness-drill participants.”
- “The 2026 Renja identifies inadequate early-warning equipment as an implementation gap.”
- “The plan contains a 72% preparedness target.”

M63 does **not** authorize statements such as:

- “Current Sumatera Barat preparedness is 72%.”
- “750 families have already received preparedness equipment.”
- “A specific municipality has no Forum PRB” unless another source proves it.
- “The mitigation-capacity score is X.”
- “Without mitigation, disaster probability will rise by Y%.”

No composite capacity score is derived from these planning targets and qualitative gaps.

## Dashboard consequence

The public disaster experience can now present three conceptually separate layers:

1. **Observed events and impacts** — BPBD/BNPB event datasets;
2. **Risk** — BNPB IRBI overall and hazard-specific indices from M61–M62;
3. **Mitigation planning context** — BPBD 2026 commitments and documented implementation gaps from M63.

This separation keeps a user-facing “what happened / what is risky / what is planned or still lacking” structure without implying that a planning target is measured achievement or that a risk index predicts the next disaster.

## Reproducibility

The permanent M63 gate validates:

- raw PDF and excerpt checksums;
- non-OCR extraction boundary;
- exactly 13 planning targets and their source-supported values/units;
- exactly 18 qualitative diagnostic gaps;
- target and gap claim types;
- absence of municipality-specific gap attribution;
- absence of derived capacity scores, forecast claims, or budget comparisons;
- public catalog registration; and
- byte-identical deterministic regeneration of both canonical CSVs and the final manifest from the frozen excerpt.
