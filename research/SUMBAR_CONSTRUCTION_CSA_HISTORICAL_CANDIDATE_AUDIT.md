# Sumatera Barat Construction — CSA Historical Candidate Audit

## Question

Does the current BPS Sumatera Barat CSA table catalog expose a construction-establishment or qualification table carrying a source-native **2005** period that can close the post-update historical evidence gap?

## Inventory audited

The official BPS WebAPI CSA catalog was enumerated for:

- domain `1300` — Sumatera Barat;
- subject `559` — `Pertambangan, Manufaktur, Konstruksi`;
- model `tablestatistic`.

The catalog returned **19 tables**.

A table was treated as relevant only when its **own title**, rather than the umbrella subject label, explicitly contained `konstruksi` and at least one of `kualifikasi`, `perusahaan`, `usaha`, or `direktori`.

This distinction matters because every row inherits the subject label `Pertambangan, Manufaktur, Konstruksi`. Using the whole catalog row for matching would therefore incorrectly classify unrelated industrial-company tables as construction tables.

## Relevant current CSA objects

Only **two** of the 19 table titles satisfy the corrected construction relevance rule.

### 1. Construction qualification table — 2016

Encoded CSA ID:

`NjUyIzI=`

Title:

`Banyaknya Usaha/Perusahaan Konstruksi menurut Kabupaten/Kota dan Kode Kualifikasi Usaha di Sumatera Barat (Usaha)`

The catalog and detail object both identify the period as **2016 only**. This is the same table already frozen in the preceding CSA table 652 checkpoint and is sourced to `Sensus Ekonomi`.

It therefore cannot substitute for the missing 2005 post-directory-update profile.

### 2. Individual construction-business table — 2020–2022

Encoded CSA ID:

`U1ZSa2VIZzBVbVpVTDBoNk4wSkxSbXRTYnpOcGR6MDkjMyMxMzAw`

Title:

`Banyaknya Sampel Usaha, Rata-Rata Pekerja Tetap, Rata-Rata Hari Orang Pekerja Harian, Median Balas Jasa dan Upah Pekerja per Tahun, serta Median Nilai Konstruksi yang Diselesaikan Usaha Konstruksi Perorangan Menurut Kabupaten/Kota di Provinsi Sumatera Barat`

The official catalog bounds this object to **2020–2022**. Its detail object is available but uses a different table-source family and does not expose the standard `available_years`/`tahun` axis returned by source-2 CSA tables.

The catalog-native oldest/latest periods are nevertheless sufficient to exclude 2005 from this object.

## Result

Final corrected audit:

- CSA subject-559 tables inventoried: **19**;
- relevant construction-title candidates: **2**;
- candidates successfully resolved: **2**;
- candidate detail errors: **0**;
- resolved candidates with exact 2005 period: **0**;
- relevant candidates whose catalog period bounds include 2005: **0**.

Classification:

`current_sumbar_csa_construction_catalog_exhausted_no_2005_candidate`

This closes the repeated-search loop for the **current Sumatera Barat CSA subject-559 catalog**. It does not establish that BPS never published the 2005 data.

## What remains open

The missing historical target remains the post-directory-update 2005 qualification composition, preferably from:

- `Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005` (`05230.0610`); or
- another contemporaneous official BPS publication that reproduces the Sumatera Barat 2005 qualification counts with enough definition context; or
- an official BPS Deep Search / archival text surface exposing the same period-specific table.

The current CSA audit does **not** authorize:

- using 2016 or 2020–2022 as a 2005 proxy;
- a 2003→2005 qualification-composition comparison;
- frame-change quantification;
- reconstructing old/new Sumatera Barat sampling-frame counts;
- attribution of the 2001–2003 value revision to the end-2005 directory updating;
- a bridge or backcast;
- bridged Panel v3 integration;
- a causal claim.

## Reproducibility

The corrected final run used the repository's existing BPS WebAPI secret without persisting it and followed only encoded table IDs returned by the official CSA catalog.

Permanent machine-readable provenance is frozen in:

`data/validation/historical/public_finance_2000/bps_construction_csa_historical_candidate_audit.json`
