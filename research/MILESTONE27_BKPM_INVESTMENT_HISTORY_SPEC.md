# Milestone 27 — BKPM Investment-Realization History Qualification

## Purpose

Milestone 27 executes Tier-B priority #4 from the frozen M23 data-value/model-readiness audit: qualify the official BKPM Satu Data investment-realization history before any investment values are promoted into Ranah Observatory analytical panels.

M27 is an evidence-discovery and continuity-qualification milestone first. It is **not** permission to infer investment causality, rank kabupaten/kota by investment performance, convert PMA foreign-currency values post hoc, treat quarterly releases as automatically additive annual flows, or fit a new statistical model.

## Locked upstream basis

M27 inherits without reinterpretation:

- M23 source candidate `bkpm_satudata_investment`;
- M23 work package `bkpm_investment_history_inventory`;
- the 19-current-kabupaten/kota canonical Sumatera Barat geography regime;
- existing BNPB/BPS/DJPK geography rules that source administrative labels/codes must never be assumed interchangeable with canonical BPS identifiers;
- the rule that source semantics and temporal coverage must be qualified before aggregation or model use.

## Official source family

Primary official surface:

`https://data.bkpm.go.id/`

Owner: Kementerian Investasi dan Hilirisasi/BKPM, Direktorat Data dan Informasi.

The target source family is the public **Data Realisasi Investasi Triwulan** dataset series and any directly corresponding annual/current BKPM realization dataset whose metadata explicitly exposes the same LKPM-derived investment-realization concept.

Discovery begins from official dataset metadata/pages only. Search-engine results may assist navigation but are not evidence artifacts.

## Stage 0 — value-blind inventory and transport qualification

Stage 0 may inspect only:

- dataset title/identifier;
- source page URL;
- release/modified dates;
- declared reporting period/year/quarter;
- public access state;
- declared update/collection frequency;
- declared collection method/source system;
- declared variable names and units;
- resource filename/type;
- downloadable resource URL/transport metadata;
- file header/schema after a resource is explicitly selected by metadata contract.

Stage 0 must not inspect or summarize target investment values for source selection.

### Locked discovery target

Inventory the quarterly realization series backward from 2025 through 2010, with explicit period coverage by `year × quarter` where official public dataset pages can be deterministically identified.

Do not infer a missing quarter from adjacent quarters. Do not treat a Q4-labelled dataset as an annual total until row-period semantics prove whether the file contains only Q4 flow, cumulative YTD, or all four quarter-labelled rows.

### Expected schema family

Current official pages describe fields including:

- `periode`;
- `status_penanaman_modal` (PMA/PMDN);
- `regional`;
- `negara`;
- `sektor_utama`;
- `nama_sektor`;
- `deskripsi_kbli_2digit`;
- `provinsi`;
- `kabupaten_kota`;
- `jawa_luar_jawa`;
- `pulau`;
- `investasi_rp_juta`;
- `investasi_us_ribu`;
- `tki`.

These names are discovery expectations, not permission to aggregate them.

## Geography gate

A later numeric stage may retain a row for Sumatera Barat only after:

1. `provinsi` is source-normalized to Sumatera Barat;
2. `kabupaten_kota` maps uniquely to one of the 19 current canonical geographies;
3. every distinct source geography label is frozen before numeric aggregation;
4. ambiguous Kabupaten Solok vs Kota Solok and other city/regency pairs are resolved by explicit name/admin-type mapping rather than fuzzy matching alone.

Historical boundary reconstruction is not performed in Stage 0.

## Temporal and aggregation gates

Before any annual or quarterly investment observation is promoted, M27 must establish:

- whether `periode` is quarter-specific or cumulative/YTD;
- whether separate Q1–Q4 datasets overlap in represented rows;
- whether investment fields are incremental realized additions or stock/cumulative values;
- whether PMA and PMDN are already represented in a common rupiah field and what the source says about conversion methodology;
- whether row-level duplication can occur across sector/country dimensions;
- the exact aggregation key required to avoid double counting;
- methodology/reporting discontinuities across years, especially changes in LKPM/OSS reporting scope and excluded sectors/business scales.

No annual sum is authorized before these gates are frozen.

## Promotion states

Each discovered year/quarter resolves to one of:

- `metadata_qualified_resource_transport_pending`;
- `metadata_and_transport_qualified_schema_pending`;
- `schema_qualified_aggregation_semantics_pending`;
- `qualified_for_value_materialization`;
- `held_methodology_or_coverage_discontinuity`;
- `unavailable_or_unparseable`.

Stage 0 completion does not require any `qualified_for_value_materialization` period.

## Forbidden operations

M27 Stage 0 must not:

- sum investment values;
- compute per-capita investment;
- convert currencies using an external or current exchange rate;
- combine PMA/PMDN unless source semantics explicitly support the chosen common metric;
- treat missing rows as zero;
- infer annual totals from Q4 labels;
- deduplicate rows based on target values;
- rank geographies or sectors;
- fit statistical/ML models;
- infer causal effects of investment;
- estimate monetary wasted potential.

## Required Stage 0 outputs

1. `data/manifests/milestone27_design_gate.json`
2. `data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv`
3. `data/manifests/milestone27_bkpm_resource_inventory.json`
4. frozen official metadata/page evidence under `data/processed/bkpm/m27_resource_inventory/`
5. a permanent contents-read-only reproducibility workflow after live discovery evidence is frozen.

## Stage 0 exit gate

Stage 0 is complete when:

- the official BKPM quarterly history inventory has an explicit 2010–2025 coverage matrix;
- every discovered dataset identity and resource transport is checksum-bound;
- no target investment values were used in source selection;
- all discovered schema families and discontinuities are explicit;
- missing periods remain missing rather than inferred;
- numeric materialization authorization is decided period-by-period;
- model fit, causal claims, and monetary wasted-potential estimation remain false.

## Next stage

Only after Stage 0 closes may a separately preregistered Stage 1 materialize the subset of periods whose transport, geography, temporal, unit, overlap, and aggregation semantics are qualified.
