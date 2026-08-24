# Milestone 41 — BNPB Historical Normalization Contract

## Status

**The historical normalization contract is frozen. Source-native integer parsing is allowed only in staging; historical district/city impact values remain blocked from analytical promotion.**

M38–M40 closed source discovery, transport, file identity, and bounded schema-span qualification for the BNPB annual district/city impact archive. M41 addresses the next failure mode: a technically parseable workbook can still produce a false historical panel if missing rows, changing administrative geography, retrospective source labels, totals, or raw codes are interpreted incorrectly.

The machine-readable contract is frozen at:

`data/manifests/milestone41_bnpb_historical_normalization_contract.json`

The verified legal-lineage seed is frozen at:

`data/registries/bnpb_historical_geography_lineage.csv`

## New evidence from source-native workbook audits

M41 extends workbook inspection beyond M40's start/mid/end samples by auditing the 2004–2006 Sumatera Barat workbooks as well. The audited set is now **2002, 2003, 2004, 2005, 2006, 2012, and 2017**.

For every audited non-empty workbook:

- the sheet is `statistik`;
- source geography rows preserve raw `Wilayah` strings such as `1303. SOLOK`;
- all 14 metric columns are parseable as non-negative integer counts after removing source thousands separators;
- the explicit `Jumlah` row reconciles exactly to the sum of explicit body rows across all 14 metric columns;
- the total row is therefore useful as a reproducibility/QA constraint, but it is not a district/city observation.

M41 still does not promote those counts into the analytical panel.

## Critical finding 1 — absent row is not zero

The archive is sparse by observed geography rather than a complete district/city grid.

Three districts were legally created by **UU No. 38 Tahun 2003**, effective **18 December 2003**:

- Kabupaten Solok Selatan from Kabupaten Solok;
- Kabupaten Pasaman Barat from Kabupaten Pasaman;
- Kabupaten Dharmasraya from Kabupaten Sawahlunto/Sijunjung.

All three therefore existed for the full 2004 calendar year. Yet none appears as a source row in the audited 2004 workbook.

This gives a direct counterexample to two unsafe interpretations:

1. an absent row does **not** mean the geography did not exist;
2. an absent row does **not** mean every metric for that geography was zero.

The only defensible source-native state is `absent_entity_active_full_year` until BNPB documentation proves a stronger meaning.

## Critical finding 2 — source labels are not guaranteed contemporaneous legal names

The audited **2003** workbook contains:

`1304. SIJUNJUNG`

However, the official legal rename from **Kabupaten Sawahlunto/Sijunjung** to **Kabupaten Sijunjung** became effective only on **10 March 2008** under **PP No. 25 Tahun 2008**.

Therefore the workbook's `Wilayah` string cannot automatically be interpreted as the legal name in force during the observation year. The archive may contain retrospective normalization or source-system naming conventions.

M41 consequently separates:

- `source_name_raw` — exactly what BNPB exported;
- temporal legal-name/version evidence — maintained independently in the lineage registry.

Source labels are never rewritten in the raw layer.

## Critical finding 3 — BNPB raw code regime changes across eras

The existing registry `data/registries/bnpb_geography_map.csv` is deliberately scoped to the qualified 2024 BNPB resources.

Historical workbook examples prove that those raw codes cannot be carried backward:

| Entity | Historical source code (2012 sample) | Qualified BNPB 2024 source code |
| --- | --- | --- |
| Kepulauan Mentawai | `1301` | `1309` |
| Pesisir Selatan | `1302` | `1301` |
| Solok | `1303` | `1302` |

M41 therefore prohibits raw-code-only joins across BNPB eras. Historical mapping must use a compound identity:

`source era + source year + raw code + raw name + legal lineage`

## Verified administrative-lineage anchors

M41 freezes only legal changes needed to prevent obvious historical geography errors.

| Effective date | Change | Boundary effect | Legal basis |
| --- | --- | --- | --- |
| 4 Oct 1999 | Kepulauan Mentawai created from Padang Pariaman | split | UU No. 49 Tahun 1999 |
| 10 Apr 2002 | Kota Pariaman created from part of Padang Pariaman | split | UU No. 12 Tahun 2002 |
| 18 Dec 2003 | Solok Selatan created from Solok | split | UU No. 38 Tahun 2003 |
| 18 Dec 2003 | Pasaman Barat created from Pasaman | split | UU No. 38 Tahun 2003 |
| 18 Dec 2003 | Dharmasraya created from Sawahlunto/Sijunjung | split | UU No. 38 Tahun 2003 |
| 10 Mar 2008 | Sawahlunto/Sijunjung renamed Sijunjung | rename, same entity | PP No. 25 Tahun 2008 |

The registry stores official BPK legal-database URLs for these anchors.

## Transition-year rule

Annual data cannot represent a within-year boundary split without ambiguity.

M41 therefore marks:

- **2002** as a boundary-transition year for Padang Pariaman / Kota Pariaman;
- **2003** as a boundary-transition year for the parent/successor systems involving Solok, Pasaman, and Sawahlunto/Sijunjung;
- **2008** as a legal-name transition for Sawahlunto/Sijunjung → Sijunjung, without treating the rename itself as a spatial split.

For boundary-transition years, annual parent values must remain attached to the source-native geography identity. They may not be proportionally allocated or silently relabeled to current boundaries.

## Missingness contract

### Workbook state

Allowed states:

- `observed_body`
- `empty_body`
- `unavailable`
- `parse_error`

The 2001 Sumatera Barat workbook remains `empty_body`. That is not equivalent to zero.

### Row state

Only rows explicitly present in the workbook exist in raw staging:

- `observed_geography`
- `source_total`

A complete geography-year grid may be derived later, but missing source rows must be labelled rather than imputed.

### Derived presence state

When a legal geography registry is available, an absent geography may be classified as:

- `absent_entity_active_full_year`
- `absent_entity_active_partial_year`
- `entity_not_active_during_year`
- `transition_year_unresolved`

None of these states is numeric zero.

### Cell state

Explicit metric cells use:

- `observed_zero`
- `observed_positive`
- `source_blank`
- `source_non_numeric`
- `parse_error`

Only a literal numeric zero in an explicit observed row becomes zero.

## Three-layer data contract

### 1. Raw row staging

Must preserve at minimum:

- source year;
- source file identity and digest;
- sheet and source row number;
- exact `Wilayah` string;
- raw code and raw name parsed without overwriting the original;
- exact raw metric cell values;
- row type (`observed_geography` or `source_total`).

No geography harmonization occurs here.

### 2. Source-native cell staging

Explicit metric strings may be parsed to non-negative integers while preserving raw strings and cell state.

Observed commas are treated as thousands separators, e.g. `35,564` → integer `35564` in staging. Negative values are invalid under the current count contract and must fail validation rather than be silently accepted.

This layer is still **not** the analytical historical panel.

### 3. Canonical historical panel

This future layer remains blocked until every annual workbook passes parser/schema checks, temporal geography mappings are applied, totals reconcile, metric-definition provenance is frozen, and transition years are explicitly handled.

## Total-row contract

`Wilayah = Jumlah` is not a geography.

For each non-empty workbook:

1. parse all explicit geography rows;
2. parse the source total row independently;
3. sum the explicit body rows for each of the 14 metric columns;
4. require exact equality with the source total;
5. block that year from panel promotion if reconciliation fails.

The source total must never be used to manufacture values for missing districts/cities.

## Metric boundary

The stable 16-column structure observed across audited years is structural evidence, not proof that BNPB definitions/counting procedures never changed.

M41 therefore keeps these claims blocked:

- semantic definition identity for every year;
- treating `Menderita`, `Mengungsi`, `Terluka`, `Meninggal`, and `Hilang` as mutually exclusive unique persons;
- converting house/facility damage counts into monetary loss;
- joining annual totals to event-level records without event identity.

## What M41 closes

M41 closes the design questions for:

- explicit zero vs missing row vs empty workbook;
- source total handling;
- raw integer parsing in staging;
- raw-code regime separation;
- raw source label preservation;
- temporal legal-lineage anchors;
- transition-year protection against false current-boundary comparisons.

## What remains blocked

M41 does **not** yet authorize the final historical numerical panel. The next evidence gate must execute this contract against every annual workbook and produce machine-verifiable row/cell staging evidence.

The next milestone should therefore be **full annual parser + geography qualification**, not another source-discovery milestone.

## Research boundaries

M41 prohibits:

- zero-filling absent district/city rows;
- zero-filling the 2001 empty workbook;
- using the 2024 BNPB raw-code crosswalk for historical workbooks;
- treating BNPB source labels as guaranteed contemporaneous legal names;
- reallocating pre-split parent observations to successor districts/cities;
- using source totals as geography rows;
- summing victim categories as unique persons;
- event-level reconstruction from annual aggregates;
- causal attribution, monetary-loss estimation, avoided-loss estimation, composite-risk scoring, or policy ranking from this contract alone.
