# Milestone 44 — BNPB Event-Count Overlap Reconciliation

## Status

**The 2010–2017 overlap between the M42 historical BNPB archive and the qualified modern BNPB district/city total-event matrix has been reconciled at value level. The releases are highly aligned but not identical.**

M44 compares only one metric with genuinely like-for-like dimensions:

- historical metric: `Jumlah Kejadian` from M42;
- modern metric family: `recorded_disaster_events_total` from the qualified `Jumlah Kejadian Bencana Menurut Kabupaten Tahun 2010-2024` resource;
- overlap: 2010–2017;
- join key: year + canonical geography ID;
- historical side: explicit source rows only;
- no zero-filling of historically absent rows.

The frozen result is:

`data/manifests/milestone44_bnpb_event_overlap_reconciliation.json`

The deterministic analyzer is:

`scripts/analyze_milestone44_bnpb_event_overlap.py`

## Why this is the first M44 comparison

M43 established that most historical victim and physical-impact fields cannot yet be treated as semantically identical to current BNPB concepts. `Menderita` cannot simply be renamed to `Terdampak`, facility `Umum` remains arithmetically ambiguous, and victim categories cannot be summed as unique persons.

`Jumlah Kejadian` has a stronger overlap path because the repository already contains a qualified modern BNPB district/city matrix for 2010–2024 with the same annual all-disaster count concept and explicit canonical geography mapping.

M44 therefore starts with the narrowest comparison that can be executed without manufacturing dimensions that do not exist in both releases.

## Frozen result

Across 2010–2017:

- M42 contains **119 explicit historical geography-year rows**;
- the modern BNPB matrix contains **152 rows** = 19 districts/cities × 8 years;
- every one of the 119 historical explicit rows has a modern counterpart;
- **113 / 119 rows match exactly**;
- exact-match rate = **94.96%**;
- **6 rows disagree**;
- every disagreement is exactly **+1 event in the modern release**;
- historical explicit sum across the overlap = **523 events**;
- modern full-matrix sum = **529 events**;
- net modern-minus-historical difference = **+6 events**.

This is strong cross-release continuity evidence, but not identity.

## Exact years

Five overlap years reproduce exactly across every historical explicit geography:

- 2011
- 2013
- 2014
- 2015
- 2017

For each of these years, the historical explicit sum also equals the complete modern matrix sum because every modern row absent from the historical workbook is zero.

## Revised years

Three years contain small upward revisions in the modern release.

### 2010

Historical explicit total: **57**  
Modern matrix total: **60**

Revisions:

| Geography | Historical | Modern | Delta |
| --- | ---: | ---: | ---: |
| Lima Puluh Kota | 5 | 6 | +1 |
| Pasaman | 2 | 3 | +1 |
| Kota Padang | 4 | 5 | +1 |

### 2012

Historical explicit total: **90**  
Modern matrix total: **91**

Revision:

| Geography | Historical | Modern | Delta |
| --- | ---: | ---: | ---: |
| Padang Pariaman | 5 | 6 | +1 |

### 2016

Historical explicit total: **68**  
Modern matrix total: **70**

Revisions:

| Geography | Historical | Modern | Delta |
| --- | ---: | ---: | ---: |
| Pesisir Selatan | 2 | 3 | +1 |
| Kota Padang | 7 | 8 | +1 |

No downward revision and no disagreement larger than one event is observed in this overlap.

## Historical sparsity versus the modern complete matrix

The modern matrix contains 33 geography-year rows that have no explicit counterpart in the M42 historical workbook.

M44 profiles all 33 rather than assuming their meaning:

- modern zero where historical row is absent: **33**;
- modern positive where historical row is absent: **0**;
- positive-event backfill into historically absent rows: **none observed**.

This strongly suggests that, for `Jumlah Kejadian` in 2010–2017, the old archive used a sparse representation compatible with the modern matrix's explicit zeros.

It does **not** change the M41/M42 missingness contract.

An absent historical row remains absent in the historical release because the modern zero belongs to a different, later release. M44 never rewrites a historical missing row into an `observed_zero` cell.

This distinction matters for reproducibility:

- historical archive statement: *the row is absent*;
- modern retrospective matrix statement: *the corresponding geography-year has value 0*.

Both can be preserved simultaneously without pretending they are the same observation.

## Release revision interpretation

The six +1 differences show that the modern BNPB matrix is not merely a formatting transformation of the M42 archive. It contains at least small retrospective revisions.

M44 does not infer why the revisions occurred. Possible mechanisms such as late reporting, deduplication changes, event reclassification, or source-system correction are hypotheses until BNPB documentation proves them.

The defensible statement is narrower:

> The modern qualified BNPB release reports six more events across the 2010–2017 Sumatera Barat overlap than the historical release, concentrated in six geography-year cells, each revised upward by one event.

## Source-selection implication

For a **complete 2010–2017 all-disaster event-count context**, the modern BNPB district/city matrix is the stronger candidate source because it provides:

- all 19 districts/cities for every overlap year;
- explicit zeros;
- current qualified source provenance;
- canonical geography IDs already produced by the reviewed BNPB foundation;
- a measurable cross-release relationship to the historical archive.

M42 should remain as:

- historical-release evidence;
- a cross-release audit source;
- a record of revisions;
- an independent safeguard against silently treating current retrospective values as timeless originals.

## Why M44 still does not promote a canonical total-event panel

The existing reviewed BNPB baseline deliberately promotes only **2024 flood and landslide event indicators**, which have an independent official 2024 crosscheck. The 2010–2024 all-disaster matrix is currently retained as `source_native_context`.

M44 does not silently widen that canonical contract.

Two issues remain before promotion:

1. **Indicator contract** — decide whether Ranah Observatory should expose a dedicated canonical `all_disaster_events` indicator alongside hazard-specific flood/landslide indicators.
2. **Retrospective geography interpretation** — the modern matrix uses current Permendagri geography coding, but M44 has not yet proven whether historical values are explicitly reconstructed to current boundary geometry or are simply published under current identifier labels.

The six revision flags would also need to remain visible in provenance if the modern matrix becomes canonical.

## What M44 proves

M44 closes the following questions for `Jumlah Kejadian`, 2010–2017:

- every explicit historical row has a modern qualified counterpart;
- cross-release value continuity is high and measurable;
- the releases are not identical;
- the complete modern matrix contains six net additional events;
- all 33 modern cells corresponding to historically absent rows are zero;
- no positive backfill occurs through historical sparsity in this overlap;
- release-level provenance is necessary because the modern series includes revisions.

## What M44 does not prove

M44 does **not** prove:

- unchanged event definitions or reporting intensity over 2010–2017;
- the reason for any of the six revisions;
- current-boundary geometric equivalence of every retrospective observation;
- hazard-specific historical flood or landslide counts;
- victim/impact semantic equivalence;
- causal disaster-risk relationships;
- monetary loss or avoided-loss estimates.

## Next gate — M45

M45 should be the **retrospective total-event promotion and geography contract**.

It should:

1. decide whether the qualified modern 2010–2024 matrix deserves a dedicated canonical all-disaster event indicator;
2. freeze the exact retrospective geography interpretation of its Permendagri codes;
3. preserve all six M44 revision flags in provenance if promotion occurs;
4. retain the M42 archival values rather than overwriting them;
5. keep all-disaster event totals explicitly separate from flood/landslide indicators.

That is a smaller and more defensible next step than trying to force victim or damage metrics into a canonical historical panel before their semantics can be reconciled.
