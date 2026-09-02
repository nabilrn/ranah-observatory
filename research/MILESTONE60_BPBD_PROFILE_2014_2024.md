# Milestone 60 — BPBD historical disaster profile 2014–2024 qualification

## Outcome

M60 is complete as a **qualification hold**, not as a numerical historical-series materialization.

The repository now preserves the official BPBD/Pusdalop `Profil Bencana Sumatera Barat 2014 - 2024` JPEG and a companion official `Buku Data dan Informasi Bencana Tahun 2024` PDF. Neither artifact currently supports a defensible machine-readable 2014–2024 annual series.

## Official profile artifact

The Satu Data Sumatera Barat package `Profil Bencana Sumatera Barat 2014 - 2024` resolves to:

- package ID `8acd9009-56df-43ba-b079-a477ab844edb`;
- resource ID `b15be1ad-80b9-4ffa-9e6b-a8e0118599cb`;
- producer `BPBD Provinsi Sumatera Barat`;
- source data `Pusdalop BPBD Sumatera Barat`;
- media type `image/jpeg`;
- frozen dimensions `1280 × 720`.

The original JPEG is retained byte-for-byte under `data/raw/bpbd/m60_profile_2014_2024/`. Audit crops are enlarged visual derivatives only; they do not transform or infer numeric values.

## Diagnostic OCR boundary

A single diagnostic OCR pass was used only to test whether the low-resolution annual table could be transcribed reliably. The output contains obvious recognition noise and ambiguous digits. It is **not source truth** and is not used to materialize any observation.

No additional OCR-derived numbers are promoted by M60.

## Companion 2024 book

The official `Buku Data dan Informasi Bencana Tahun 2024` package resolves to:

- package ID `f0e9b9f4-d382-4bbc-a84a-5a5a5ffeee2a`;
- resource ID `3d7b1f51-226e-43c3-9ff8-2cbcc85fe978`;
- organization `Badan Penanggulangan Bencana Daerah`;
- release metadata `14 April 2025`;
- 128-page PDF frozen under `data/raw/bpbd/m60_book_2024/`.

`pdftotext -layout` was used as a diagnostic, non-OCR search. Searches for historical-profile anchors such as `2014`, `Profil Bencana`, `Cuaca Ekstrem`, and `Tanah Longsor` produced no matching text excerpt. This does not prove that the concepts are visually absent from all pages; it proves only that the PDF does not expose the required historical table as searchable text through this extraction path.

## Why the historical series is held back

The dashboard requires proof-grade values, not plausible transcription. At the end of M60:

1. the only explicit 2014–2024 profile artifact is a low-resolution JPEG;
2. one OCR diagnostic is too noisy to qualify the annual cells;
3. the companion PDF does not expose a searchable historical table;
4. no machine-readable official 2014–2024 table has been found;
5. therefore annual values before the already-qualified 2023/2024 anchors cannot be independently reconciled.

M60 intentionally chooses **no data** over weakly supported data.

## Authorization boundary

M60 does **not** authorize:

- an annual BPBD disaster-event series for 2014–2024;
- transcription of JPEG chart/table cells into canonical observations;
- use of OCR output as evidence;
- interpolation, smoothing, or inference of missing annual values;
- a public-catalog entry for a 2014–2024 BPBD timeseries;
- dashboard claims based on the historical profile numbers.

M57–M59 remain the qualified BPBD event evidence for 2023 and 2024.

## Reopening gate

Historical materialization can resume only if at least one stronger source becomes available:

- an official XLSX/CSV/DataStore table for 2014–2024;
- a higher-resolution official profile artifact whose cells can be independently verified;
- another official BPBD/Pusdalop document containing the annual values in extractable text/table form; or
- multiple independent official artifacts allowing full cell-by-cell reconciliation to the validated 2023 and 2024 anchors.

Until then, the qualification hold is the correct data contract.
