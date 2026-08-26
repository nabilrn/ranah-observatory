# Milestone 40 — BNPB Historical Drive Archive Completion

## Status

**Transport/file identity is qualified for the complete BNPB-catalogued Drive archive from 2002 through 2017. Numeric historical district/city impact promotion remains blocked.**

Milestone 38 established the annual BNPB catalogue series and its transport split. Milestone 39 proved that the public Google Drive layer is practically retrievable and froze the initial 2002–2006 tranche. Milestone 40 completes the same bounded qualification procedure through 2017.

## Complete archive finding

For every BNPB-catalogued Drive year from **2002 through 2017**:

- the official year-specific public Drive folder is listable;
- the folder contains **38 XLSX files**;
- exactly one workbook is named `stat_by_wil_13_<year>.xlsx`;
- that workbook is downloadable;
- a unique Drive file ID and source file size are frozen in the M40 manifest.

This closes the historical Drive archive **transport/file-identity gate** for the 16-year 2002–2017 interval.

The frozen evidence is committed at:

`data/manifests/milestone40_bnpb_drive_archive_complete.json`

## Schema-span evidence

M40 does not claim that every intermediate workbook has been exhaustively schema-audited. Instead, source-native workbook inspections now cover the beginning, an early adjacent year, a midpoint, and the endpoint of the Drive series:

| Year | Source label | Sheet | Used range | Body rows | SHA-256 |
| --- | --- | --- | --- | ---: | --- |
| 2002 | `Propinsi : 13. Sumatera Barat, 2002` | `statistik` | `A1:P12` | 3 | `6d9c2766f44648a2383dc7fbe02378c413cb93ad361d0972060b1421de21baae` |
| 2003 | `Propinsi : 13. Sumatera Barat, 2003` | `statistik` | `A1:P13` | 4 | `e3263203c3f791d79d14d9100fd50b878f571e0f53d187800d5b65fc921b7a78` |
| 2012 | `Propinsi : 13. Sumatera Barat, 2012` | `statistik` | `A1:P24` | 15 | `f6b8388cba8cd8e471bb0703226a7f02abbeba5a83944fbf53909bc2ec46b081` |
| 2017 | `Propinsi : 13. Sumatera Barat, 2017` | `statistik` | `A1:P23` | 14 | `de218de3da3c16db20442a5e9fbedac1f6b6906128160b43c3400bf5a63f266d` |

All four audited workbooks expose the same 16-column structural contract:

1. `No`
2. `Wilayah`
3. `Jumlah Kejadian`
4. `Meninggal`
5. `Hilang`
6. `Terluka`
7. `Menderita`
8. `Mengungsi`
9. `Rumah Rusak Berat`
10. `Rumah Rusak Sedang`
11. `Rumah Rusak Ringan`
12. `Rumah Terendam`
13. `Fasilitas Pendidikan`
14. `Fasilitas Kesehatan`
15. `Fasilitas Peribadatan`
16. `Fasilitas Umum`

This is strong schema-span evidence: no structural transition is observed at the audited start, midpoint, or endpoint samples. It is **not** equivalent to proving byte-for-byte or semantic schema identity for every annual workbook.

## Full Sumatera Barat file-identity freeze

| Year | Drive file ID | Size (bytes) |
| --- | --- | ---: |
| 2002 | `1h_788IN5OfiRIG2QIwsffRSoaXlk80ye` | 27,046 |
| 2003 | `1YOlUQzvh3Bk3HOX_LXyN2BPdi3VgthLW` | 27,120 |
| 2004 | `1G1KdFLpFqqhU7MESZklg5AjMiAOSJXVA` | 27,448 |
| 2005 | `1IjSA3FYXm-8CnzaeusARlEeX4KgXeT6j` | 27,797 |
| 2006 | `1qOv0DiVsdEPChJ3RFzP8NO0P7FKBSVd3` | 27,766 |
| 2007 | `1qs_cgQUIdgF6ktysHP56F_n4f6unlqsC` | 28,510 |
| 2008 | `1AlZP0q2j7JmPNR9nMDCOJoTTgMbRmIS9` | 27,511 |
| 2009 | `14wgWzsmUjvf1Xex-59yVIk3BMzwpMyu2` | 28,442 |
| 2010 | `1grzKv-JYqXh8iLRXwztFOtSQL3vqiG0G` | 28,112 |
| 2011 | `1aiyS3evqAIdS_qvAIMXkPcT6ZHsYJcEJ` | 27,987 |
| 2012 | `1bH89AFGZ3-lSFyhM0uD-D58MhCF_Xq_F` | 28,150 |
| 2013 | `16xTOHKIcvm6-35MouBc5SAhWzHCFMfAJ` | 28,150 |
| 2014 | `1iX-fioBCs0ucwYWdJcPauWrBBNPfeT0g` | 28,030 |
| 2015 | `1vRof8V29l81XhKfA0ERodnV8AzBChwCe` | 28,032 |
| 2016 | `14TV7RFzAJwFHYTzbkfOEvFcYbSbueNJY` | 28,312 |
| 2017 | `1qRNz3QLxm0UERt1L_qiZNcP25tSZ25YN` | 28,058 |

The 2014 BNPB catalogue had two resource records that resolve to the same Drive folder. M40 treats that folder/archive once and does not double-count it.

## What M40 closes

M40 closes these evidence questions:

- whether the 2002–2017 external archive links remain traversable;
- whether each annual archive exposes a deterministic Sumatera Barat candidate;
- whether those candidates are downloadable original XLSX files;
- whether the candidate filename code `13` is corroborated by source-native workbook labels in audited samples;
- whether the observed 16-column structure is present across start/mid/end samples.

## What remains blocked

Transport readiness is not analytical readiness. Before historical values can become a normalized district/city panel, a separate normalization milestone must resolve the following.

### 1. 2001 missingness semantics

The direct 2001 Sumatera Barat workbook has the expected header but no body rows and no total row. M40 does not reinterpret that state. It cannot be converted to zero without source-native evidence.

### 2. Administrative geography versioning

The archive spans many years in which district/city administrative composition and codes may change. Historical `Wilayah` rows need temporal identity preservation and an explicit crosswalk policy before comparisons with current geography.

### 3. Absent-row semantics

Audited workbooks contain different numbers of district/city body rows. Absence from a yearly workbook must not automatically mean zero impact. It may represent no recorded disaster, missing source data, or another source-native state.

### 4. Metric-definition stability

The column labels remain structurally stable in audited samples, but M40 has not yet proven that definitions, counting rules, or aggregation procedures are semantically identical across all years.

### 5. Total-row and blank handling

Source total rows must be separated from district/city observations. Blank cells, string-formatted numbers, and source totals need deterministic normalization rules.

## Research boundaries

M40 does **not** authorize:

- promotion of disaster-impact values;
- interpreting the 2001 empty body as zero;
- interpreting absent yearly district/city rows as zero;
- assuming administrative codes/boundaries are time-invariant;
- reconstructing event-level observations from annual aggregates;
- summing victim categories as unique persons;
- mixing this annual panel with M37 provincial cells as if they share a single aggregation contract;
- causal climate attribution, monetary-loss estimation, avoided-loss estimation, composite-risk scoring, or policy ranking from this source alone.

## Relationship to prior milestones

- **M26:** event-level retrieval and identity gate remains unresolved.
- **M37:** provincial observed-impact context for 2024–2025 remains unchanged.
- **M38:** qualified the BNPB annual catalogue and transport split; froze direct 2000–2001 source evidence.
- **M39:** qualified the first 2002–2006 Drive tranche and early workbook schema evidence.
- **M40:** completes deterministic 2002–2017 Drive file identity and adds midpoint/end schema-span evidence.

## Next evidence gate

The highest-value next milestone is no longer source discovery or transport. It is **historical normalization design**:

1. preserve raw source year + source `Wilayah` code/name;
2. explicitly encode observed row, absent row, blank cell, and empty-workbook states;
3. build a temporal administrative-geography crosswalk rather than forcing historical rows into current boundaries;
4. freeze source metric definitions and total-row handling;
5. only then promote a bounded district/city annual observed-impact panel with evidence-grade provenance.

No user-side manual download is required for the qualified 2002–2017 archive.
