# Milestone 42 — BNPB Historical Source-Native Staging

## Status

**Complete at source-native staging level. Canonical longitudinal historical promotion remains blocked.**

M42 executes the M41 normalization contract against the complete official Sumatera Barat annual workbook series for 2000–2017.

The result is a deterministic staging artifact containing explicit source rows only:

`data/processed/bnpb_historical_source_native_rows_2000_2017.csv.gz`

The audit freeze is:

`data/manifests/milestone42_bnpb_historical_source_native_staging.json`

The deterministic builder is:

`scripts/build_milestone42_bnpb_historical_staging.py`

## Full-series audit result

All **18 annual workbooks from 2000 through 2017** were read from their original official-file identities.

The complete result is:

- 18/18 workbooks audited;
- 17 workbooks contain explicit geography rows plus a `Jumlah` total row;
- 2001 remains the single `empty_body` workbook and contributes no staged geography rows;
- one structural 16-column schema is observed throughout 2000–2017;
- 202 explicit source geography rows are preserved;
- 2,828 explicit source metric cells are staged (202 rows × 14 metrics);
- all 2,828 observed metric cells parse as non-negative integer counts;
- zero source-blank metric cells are present in explicit rows;
- zero non-numeric metric cells are present in explicit rows;
- all 17 non-empty workbook `Jumlah` rows reconcile exactly against the sum of explicit geography rows in **14/14 metric columns**.

This is substantially stronger evidence than the earlier start/mid/end schema sampling. It executes the same parser and reconciliation rules across every annual workbook in the archive window.

## What the staging artifact contains

Each explicit source geography row preserves:

- source year;
- exact source-file SHA-256;
- source sheet and row number;
- exact raw `Wilayah` label;
- raw historical source code;
- raw historical source name;
- canonical entity ID resolved by exact name identity plus M41 legal lineage, not by 2024 raw code;
- M41 geography-lineage status;
- source-label timing status;
- `current_boundary_comparability = not_proven`;
- for each of 14 metrics:
  - exact raw source cell string;
  - parsed non-negative integer value;
  - cell state (`observed_zero` or `observed_positive`).

The compressed CSV is deterministic (`gzip mtime = 0`) and both compressed and uncompressed SHA-256 digests are frozen in the manifest.

## Why this is staging rather than the canonical historical panel

The staged numbers are faithful source-native observations, but source fidelity is not equivalent to longitudinal comparability.

M41 proved multiple historical hazards:

1. absent rows cannot be interpreted as zero;
2. 2001 is an empty workbook, not a zero year;
3. historical BNPB raw codes use a different regime from the qualified 2024 BNPB resources;
4. source labels can be retrospective rather than the legal name in force during the observation year;
5. administrative splits create boundary regimes that annual source rows cannot silently bridge.

M42 preserves all of these constraints rather than smoothing them away.

## Historical code profile

Within the 2000–2017 workbook series, each of the 19 observed Sumatera Barat geography names has one stable source code in the audited archive. Examples include:

- `1301` → `KEPULAUAN MENTAWAI`;
- `1302` → `PESISIR SELATAN`;
- `1303` → `SOLOK`;
- `1304` → `SIJUNJUNG`;
- `1309` → `PASAMAN`.

Those codes are source identity for this historical archive only.

The qualified 2024 BNPB crosswalk uses a different raw-code regime (for example 2024 `1301` maps to Pesisir Selatan and `1309` maps to Kepulauan Mentawai). Therefore the M42 builder explicitly ignores the 2024 registry's source-code column when resolving historical canonical entity identity. It uses exact source-name identity plus the M41 lineage contract instead.

## Geography execution

M42 attaches legal-lineage flags to every observed row where M41 froze a known transition.

Examples:

- 2002 `SOLOK` is flagged `pre_solok_selatan_split_parent`;
- 2003 `SOLOK` is flagged `transition_year_parent_solok_selatan_split`;
- 2000 `SIJUNJUNG` is flagged `pre_dharmasraya_split_parent`;
- 2003 `SIJUNJUNG` is flagged `transition_year_parent_dharmasraya_split`;
- pre-2008 source rows labelled `SIJUNJUNG` retain the warning `retrospective_or_source_normalized_name_before_legal_rename`.

No observed row is marked current-boundary comparable. That question requires a stronger temporal-boundary qualification than the legal-lineage seed alone.

## Missingness remains explicit

M42 stages only source rows that actually exist.

It does not create a 19-geography × 18-year rectangle. This matters because a rectangular panel would require synthesizing rows for source absences, and M41 already demonstrated that an absent row may represent a legally active geography rather than a zero-valued geography.

Consequently:

- 2001 produces zero staged rows because its workbook body is empty;
- an absent geography in any other year produces no source-native staged row;
- no absent row is filled with fourteen zeros;
- later derived presence-state work must remain separate from source-native staging.

## Total-row invariant

`Jumlah` is excluded from staging as a geography row.

For every non-empty workbook, M42 independently parses the source total and requires exact equality against the sum of explicit body rows for each metric. A failure in any metric would block staging for that workbook.

All 17 non-empty workbooks pass this invariant across all 14 metrics.

## Reproducibility

Given local copies of the official workbooks named:

`stat_by_wil_13_<YEAR>.xlsx`

for every year 2000–2017, the artifact can be rebuilt with:

```bash
python -m pip install openpyxl==3.1.5
python scripts/build_milestone42_bnpb_historical_staging.py \
  --input-dir <official-xlsx-directory> \
  --output data/processed/bnpb_historical_source_native_rows_2000_2017.csv.gz \
  --qa-json /tmp/m42-qa.json
```

The builder validates:

- exact structural schema;
- exact province/year label;
- source geography-label parseability;
- non-negative integer metric-cell semantics;
- the special 2001 empty-body state;
- existence and reconciliation of the total row for every other year;
- exact name-based canonical entity identity;
- deterministic CSV and gzip serialization.

## What M42 closes

M42 closes the mechanical ingestion gate for the official 2000–2017 annual archive:

- complete annual parsing;
- explicit raw-row preservation;
- explicit raw-cell preservation;
- integer normalization with cell state;
- full annual source-total reconciliation;
- historical code-profile freeze;
- row-level M41 lineage flags;
- deterministic source-native staging artifact.

## What remains blocked

The next gate is **not** another extraction milestone.

Before source-native staged values become a canonical longitudinal historical panel, the project still needs:

1. evidence for metric-definition and counting-convention stability across the archive era;
2. defensible temporal-boundary comparability rules for geography-year observations;
3. explicit handling of sparse/absent geography rows outside the source-native layer;
4. exclusion or special treatment of boundary-transition years such as 2002 and 2003;
5. continued separation of annual aggregates from event-level records because event identity is absent.

## Research boundaries

M42 does not authorize:

- zero-filling missing geography rows or 2001;
- treating historical raw codes as 2024 BNPB raw-code identities;
- current-boundary longitudinal comparisons;
- allocating parent-area observations to successor districts/cities;
- treating victim categories as mutually exclusive unique persons;
- event-level reconstruction from annual aggregates;
- causal attribution;
- monetary or avoided-loss estimation;
- composite-risk scoring;
- policy ranking.
