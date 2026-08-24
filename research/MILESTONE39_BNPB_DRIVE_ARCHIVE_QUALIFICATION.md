# Milestone 39 — BNPB Historical Drive Archive Qualification

## Status

**Initial 2002–2006 Drive archive tranche qualified at file-identity level. 2002–2003 workbook geography/schema audited. Numeric promotion remains blocked.**

Milestone 38 established that BNPB Satu Data exposes a continuous annual catalogue series for `Jumlah kejadian dan Dampak Bencana Tahun YYYY` from 2000 through 2017. It also established a transport split: 2000–2001 are direct BNPB-hosted XLSX resources, while 2002–2017 point to BNPB-catalogued Google Drive folders.

Milestone 39 tests whether that Drive transport is a reproducible evidence path rather than a dead external link.

The initial result is positive.

## Qualified finding

For every audited folder from **2002 through 2006**:

- the BNPB-catalogued Google Drive folder is listable;
- the listing contains **38 XLSX files** partitioned by `stat_by_wil_<code>_<year>.xlsx` naming;
- exactly one file matches the Sumatera Barat candidate `stat_by_wil_13_<year>.xlsx`;
- the candidate is downloadable as the original XLSX file;
- the file ID is stable enough to freeze as evidence metadata.

This means the 2002+ archive is not merely a human-only navigation path. The public folder layer can be traversed deterministically without asking the user to download files manually.

The frozen initial tranche is:

`data/manifests/milestone39_bnpb_drive_archive_qualification.json`

## Direct workbook audit

### 2002

The downloaded workbook `stat_by_wil_13_2002.xlsx` has SHA-256:

`6d9c2766f44648a2383dc7fbe02378c413cb93ad361d0972060b1421de21baae`

It contains sheet `statistik`, used range `A1:P12`, and explicitly labels itself:

`Propinsi : 13. Sumatera Barat, 2002`

The workbook retains the same 16-column source structure observed in the M38 direct 2000 workbook:

- `No`
- `Wilayah`
- `Jumlah Kejadian`
- `Meninggal`
- `Hilang`
- `Terluka`
- `Menderita`
- `Mengungsi`
- `Rumah Rusak Berat`
- `Rumah Rusak Sedang`
- `Rumah Rusak Ringan`
- `Rumah Terendam`
- `Fasilitas Pendidikan`
- `Fasilitas Kesehatan`
- `Fasilitas Peribadatan`
- `Fasilitas Umum`

Three body rows and a total row are present. M39 records only the structural fact that those rows exist; their disaster-impact values are not promoted.

### 2003

The downloaded workbook `stat_by_wil_13_2003.xlsx` has SHA-256:

`e3263203c3f791d79d14d9100fd50b878f571e0f53d187800d5b65fc921b7a78`

It contains sheet `statistik`, used range `A1:P13`, and explicitly labels itself:

`Propinsi : 13. Sumatera Barat, 2003`

The same 16-column source structure is present. Four body rows and a total row are present. Again, M39 does not promote the source values.

## File identities frozen for the initial Drive tranche

| Year | Sumatera Barat file | Google Drive file ID | Size |
| --- | --- | --- | ---: |
| 2002 | `stat_by_wil_13_2002.xlsx` | `1h_788IN5OfiRIG2QIwsffRSoaXlk80ye` | 27,046 bytes |
| 2003 | `stat_by_wil_13_2003.xlsx` | `1YOlUQzvh3Bk3HOX_LXyN2BPdi3VgthLW` | 27,120 bytes |
| 2004 | `stat_by_wil_13_2004.xlsx` | `1G1KdFLpFqqhU7MESZklg5AjMiAOSJXVA` | 27,448 bytes |
| 2005 | `stat_by_wil_13_2005.xlsx` | `1IjSA3FYXm-8CnzaeusARlEeX4KgXeT6j` | 27,797 bytes |
| 2006 | `stat_by_wil_13_2006.xlsx` | `1qOv0DiVsdEPChJ3RFzP8NO0P7FKBSVd3` | 27,766 bytes |

These IDs are evidence locators, not authorization to treat the workbook values as a normalized time series.

## Why numeric promotion is still blocked

The archive is now substantially easier to retrieve, but retrieval alone is not enough for an analytical panel.

Before district/city values can be normalized across 2000–2017, we still need to freeze:

1. **Archive completeness:** confirm the same one-file Sumatera Barat pattern through 2017.
2. **Schema continuity:** inspect enough later workbooks to detect column or layout changes.
3. **Missingness semantics:** the 2001 direct workbook has a valid Sumatera Barat header but no body rows. That state must not be silently interpreted as numeric zero.
4. **Administrative geography versioning:** district/city boundaries and codes can change over a 17-year interval. Source rows cannot be treated as one stable geography universe until boundary handling is explicit.
5. **Metric semantics:** confirm whether victim, house, and facility columns retain stable definitions and aggregation rules across archive years.
6. **Duplicate/total-row handling:** source total rows must be distinguished from district/city body rows before normalization.
7. **Source preservation:** downloadable files used for numeric qualification need reproducible hashes or bounded source snapshots.

## Research boundaries

M39 does **not** authorize:

- converting the 2001 empty body to zero;
- reconstructing event-level records from annual aggregates;
- assuming district/city codes are temporally stable;
- summing victim categories as unique people;
- mixing annual district/city aggregates with M37 provincial cells as though they share one aggregation contract;
- deriving causal climate effects, monetary loss, avoided loss, composite risk, or policy ranking from this archive alone.

## Relationship to prior milestones

- **M26:** event-level retrieval/identity gate remains unresolved.
- **M37:** bounded provincial observed-impact context for 2024–2025 remains unchanged.
- **M38:** qualified the annual catalogue and transport split; direct 2000–2001 workbook provenance was frozen.
- **M39:** proves the BNPB-catalogued Drive layer is practically retrievable and freezes the first 2002–2006 Sumatera Barat file identities, with 2002–2003 source-native geography/schema confirmation.

## Next evidence gate

Continue the exact same bounded procedure for **2007–2017**:

1. list each official BNPB-catalogued year folder;
2. require exactly one `stat_by_wil_13_<year>.xlsx` candidate;
3. freeze file ID, size, and downloadability;
4. sample later workbooks for schema transitions;
5. only after the full archive contract is known, design the normalized historical observed-impact table and its missingness/geography-version rules.

No user-side manual download is required while this public retrieval path remains available.
