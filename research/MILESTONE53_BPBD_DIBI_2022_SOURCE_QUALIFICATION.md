# M53 — BPBD/Pusdalops DIBI 2022 Source Qualification

## Why this source matters

The public disaster workspace needs more than one headline count. To support a useful Sumatera Barat panel, the evidence layer must eventually expose:

- where events happened;
- which hazard was involved;
- deaths, missing persons, injuries and displacement;
- housing and public-facility damage;
- recorded monetary loss;
- a month-by-month time series;
- proof rows that can be traced back to an official source.

The BPBD/Pusdalops publication **Buku DIBI Tahun 2022** is unusually valuable because its indexed structure contains all of those dimensions in one source family.

This milestone only qualifies the source and creates a raw-artifact acquisition target. It does **not** materialize the indexed values as canonical data.

## Official PPID evidence

The Sumatera Barat PPID search index exposes an official record titled **Buku DIBI Tahun 2022**, published on 18 September 2023 and controlled by Badan Penanggulangan Bencana Daerah. The indexed description says the publication is Data dan Informasi Bencana Provinsi Sumatera Barat.

Official detail page:

`https://ppid.sumbarprov.go.id/home/details/20769-buku-dibi-tahun-2022.html`

Legacy direct PDF path indexed by search engines:

`https://ppid.sumbarprov.go.id/images/2023/09/file/Buku_DIBI_2022.pdf`

The PPID 2024 download audit also lists record **980 — Buku DIBI Tahun 2022 — Badan Penanggulangan Bencana Daerah**, with 120 downloads.

During the 2026-09-02 review, the legacy direct PDF path returned HTTP 404. Therefore the raw bytes, checksum and page-level artifact contract are **not** frozen yet.

## Indexed report scope

The indexed publication states that it covers 1 January–31 December 2022 and compiles reports from BPBD in all 19 kabupaten/kota to Pusdalops PB Provinsi Sumatera Barat.

The indexed methodology says:

- the same event on the same date is counted once;
- administrative details, impacts and losses are accumulated for one event;
- source completeness depends on Pusdalops input and reports supplied by kabupaten/kota.

This is a local operational reporting system. It must remain separate from BNPB/DIBI event data unless lineage and taxonomy equivalence are separately demonstrated.

## Verification targets for the raw artifact

The indexed copy exposes a province total of **1,021 events** in 2022.

Table 3.2 indexes the following event counts:

| Hazard | Events |
|---|---:|
| Abrasi pantai | 5 |
| Angin kencang | 674 |
| Banjir | 123 |
| Banjir bandang | 5 |
| Gempa bumi | 2 |
| Kebakaran hutan dan lahan | 92 |
| Longsor | 120 |
| **Total** | **1,021** |

Table 3.9 indexes a monthly series totaling the same 1,021 events:

`89, 84, 81, 92, 85, 97, 65, 110, 97, 100, 102, 19`

for January through December respectively.

The indexed impact totals include:

- 28 deaths;
- 456 injured/sick;
- 26,265 displaced;
- a clearly rendered appendix grand-total recorded loss of **Rp1,136,849,586,796**.

These are **verification targets only** until official raw bytes are recovered.

## Important internal disagreements

This source should not be ingested from index text without raw-page verification because the indexed tables already reveal internal inconsistencies.

### Missing-person total

Table 3.3 indexes no missing-person total, while Table 3.4 indexes **4 missing persons**. The raw report must decide whether this is a table-specific omission, indexing defect or source inconsistency. No value is normalized away in M53.

### District event counts

Seven district counts differ between the general event tables and the district human-impact table:

| District/city | Table 3.1 / 3.2 | Table 3.4 |
|---|---:|---:|
| Kabupaten Lima Puluh Kota | 51 | 52 |
| Kabupaten Pasaman | 66 | 67 |
| Kabupaten Pasaman Barat | 33 | 31 |
| Kabupaten Pesisir Selatan | 75 | 76 |
| Kabupaten Tanah Datar | 43 | 45 |
| Kota Padang Panjang | 35 | 33 |
| Kota Payakumbuh | 20 | 19 |

Both table families nevertheless sum to **1,021** events. That makes the discrepancy substantive rather than a simple grand-total typo.

### Search-index corruption

Several monetary cells are rendered by the search index as link placeholders. This prevents trustworthy district-level loss extraction from cached text alone.

## Dashboard value once raw bytes are recovered

The report family can support clean public views that match the intended Ranah Observatory disaster dashboard:

1. **Sebaran kejadian** — kabupaten/kota × jenis bencana.
2. **Dampak korban** — meninggal, hilang, luka/sakit, mengungsi.
3. **Kerusakan** — rumah and public-facility impacts.
4. **Kerugian tercatat** — kept distinct from inferred economic potential.
5. **Timeseries bulanan** — monthly event counts by hazard.
6. **Proof data** — source-native tables and incident-history appendix.
7. **Hazard detail** — dedicated sections for angin kencang, banjir, longsor and gempa bumi.

This is exactly the kind of evidence that can sit behind simple dashboard filters without exposing research jargon to normal users.

## Decision

M53 qualifies **Buku DIBI Tahun 2022** as a **high-value official source family** and adds it to an executable acquisition queue.

M53 does **not** authorize:

- treating indexed search snippets as raw evidence;
- using the Scribd copy as an official artifact;
- resolving the table disagreements by assumption;
- merging BPBD local operational counts with BNPB/DIBI counts;
- publishing a cross-year disaster time series from these values yet.

The promotion gate remains fail-closed.

## Next acquisition step

Recover the current PPID UUID/download route or another allowlisted `sumbarprov.go.id` copy of the 2022 DIBI PDF, freeze SHA256 and page count, then verify Tables 3.1–3.10 plus the appendices before materialization.

M52 remains separately blocked on the missing official 2017 Pusdalops annual-report bytes. M53 does not bypass that gate.
