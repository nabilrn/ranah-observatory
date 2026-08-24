# Milestone 38 — BNPB Historical District/City Impact Qualification

## Status

**Transport metadata qualified. Numeric district/city impact promotion is not authorized.**

Milestone 38 qualifies a separate source-native historical evidence lane from the M37 provincial 2024–2025 observed-impact compilation: BNPB Satu Data annual datasets titled `Jumlah kejadian dan Dampak Bencana Tahun YYYY`.

The official dataset descriptions state that the annual packages contain disaster occurrence and impact data by `kabupaten/kota` for the named year. The read-only CKAN probe confirms a continuous catalogue series for **2000–2017** with no missing annual package in that interval.

This milestone freezes source identity and transport behavior only. It does not promote historical impact values.

## Why this lane matters

M37 added bounded, source-native **provincial** observed-impact context for Sumatera Barat in 2024–2025. It explicitly did not infer district/city values and did not resolve the M26 event-level retrieval gate.

M38 asks a narrower question:

> Does BNPB provide a deterministic, source-native annual district/city impact archive for Sumatera Barat that can be qualified independently of event-level reconstruction?

The answer is **partly yes**: the annual package series is deterministic and complete at catalogue level for 2000–2017, but its resource transport changes after 2001 and the later archive still needs source-file/schema qualification before numeric ingestion.

## Qualified transport finding

The live BNPB CKAN probe found all 18 annual packages from 2000 through 2017.

- **2000–2001:** direct BNPB-hosted XLSX resources partitioned by province-style filename.
- **2002–2017:** package resources resolve to external Google Drive folders rather than direct BNPB-hosted tabular files.
- **2014:** two resource records point to the same Google Drive folder, so resource-record count must not be interpreted as two distinct annual archives.
- No duplicate annual package candidate was found for the exact title pattern.

The frozen transport evidence is committed at:

`data/manifests/milestone38_bnpb_historical_district_impact_transport.json`

## Direct Sumatera Barat workbook audit

The `stat_by_wil_13_YYYY.xlsx` filename candidate was downloaded only for the two direct-file years and inspected for geography/schema qualification. Full workbooks are **not** committed; source SHA-256 digests are frozen in the M38 manifest.

### 2000

Resource:

`stat_by_wil_13_2000.xlsx`

The workbook itself states:

`Propinsi : 13. Sumatera Barat, 2000`

This upgrades code `13` from a filename-only clue to source-native workbook geography evidence for the direct 2000 resource.

The workbook uses sheet `statistik`, range `A1:P12`, with 16 source columns covering:

- `No`
- `Wilayah`
- `Jumlah Kejadian`
- victim fields: `Meninggal`, `Hilang`, `Terluka`, `Menderita`, `Mengungsi`
- house-damage fields: `Rusak Berat`, `Rusak Sedang`, `Rusak Ringan`, `Terendam`
- facility fields: `Pendidikan`, `Kesehatan`, `Peribadatan`, `Umum`

There are three source body rows plus a total row. M38 intentionally does not promote the impact values from those rows.

Frozen workbook digest:

`c9ecfe81673f1680c4a6d4d257a1c26b24005152e72820d4c01c206ec1a904fe`

### 2001

Resource:

`stat_by_wil_13_2001.xlsx`

The workbook states:

`Propinsi : 13. Sumatera Barat, 2001`

The same 16-column header contract is present on sheet `statistik`, but the used range ends at `A1:P8`: there are **no body rows and no total row**.

This empty body is deliberately treated as **unresolved missingness semantics**, not as proof of zero disasters or zero impact. A future numeric milestone must resolve whether the empty body means no recorded rows, unavailable data, an export defect, or another source-native state.

Frozen workbook digest:

`00d9ceac4fde0febf17f02cda92c60d10d297f0d2b413354e56ce5adb168ba01`

## Later-year archive boundary

For 2002–2017 the BNPB package metadata points to year-specific Google Drive folders. That is official BNPB catalogue provenance, but it is not yet a frozen tabular transport contract.

Before those years can be ingested numerically, a follow-up milestone must qualify each folder/file layer for:

- deterministic public file retrieval;
- exact Sumatera Barat file identity;
- workbook/CSV schema and schema changes across years;
- geography coding and administrative-boundary changes;
- metric definitions and units;
- blank/zero/missing semantics;
- duplicate and aggregation semantics;
- reproducible source-file digests.

## Reproducibility contract

`.github/workflows/milestone38-bnpb-historical-district-impact-probe.yml` runs a read-only live CKAN probe and verifies the live source against the committed transport freeze.

The workflow asserts:

1. all annual packages 2000–2017 remain discoverable;
2. only 2000–2001 expose direct files under the observed contract;
3. 2002–2017 remain link/external-resource years;
4. direct Sumatera Barat resource IDs, names, and URLs match the freeze;
5. external folder URLs match the freeze;
6. no numeric values are requested, downloaded by the metadata probe, or promoted;
7. the workflow has no repository writer permission.

The initial live transport artifact was produced by GitHub Actions run `32729125584` and frozen with artifact digest:

`sha256:64e54a6a3c94521202ed5bba8eedfbb5d24e094274363c8781e281755a121611`

## Research boundary

M38 prohibits:

- interpreting the 2001 empty workbook body as numeric zero;
- treating link-only resources as equivalent to direct files;
- concatenating annual archives without schema-version checks;
- converting blank cells to zero without source-native semantics;
- summing affected/displaced/injured categories as unique people;
- reconstructing event-level rows from annual aggregates;
- allocating M37 provincial values to districts/cities;
- merging annual district/city aggregates with DIBI occurrence layers as if they share event identity;
- causal, monetary-loss, avoided-loss, composite-risk, or policy-ranking claims from this source alone.

## Relationship to earlier milestones

- **M26 event-level gate:** remains unresolved. M38 annual aggregates do not create event identity.
- **M37 provincial observed-impact context:** remains valid and unchanged for its bounded 2024–2025 scope.
- **M38:** qualifies historical annual-package transport and direct 2000–2001 Sumatera Barat workbook geography/schema, while keeping numeric historical district/city impact blocked.

## Next evidence gate

The highest-value next step is to qualify the **2002–2017 Google Drive archive layer** without manual user work if deterministic public retrieval can be established. If that transport cannot be made reproducible, the fallback is to promote only independently qualified direct-file years rather than silently mixing source contracts.
