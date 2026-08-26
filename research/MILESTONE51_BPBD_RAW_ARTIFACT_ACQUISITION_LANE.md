# M51 — BPBD Raw Historical Artifact Acquisition Lane

## Purpose

M50 established that the BPBD/Pusdalops annual-report family contains useful historical impact information, but the official raw 2017 report has not been acquired. M51 converts that external-access blocker into a reproducible acquisition workflow instead of weakening evidence standards.

## Reuse the existing historical collector

Ranah Observatory already has a browser-assisted historical PDF lane that validates original PDF bytes, copies them into `data/raw/inbox/`, and prints a SHA-256. The collector accepts a custom `--queue`; M51 generalized its host check without removing the old BPS behavior:

- `official_source_url(url, allowed_host)` validates HTTPS URLs against an exact allowlisted host or its subdomains;
- `official_bps_url(url)` remains as a compatibility wrapper using `bps.go.id`;
- queue rows may optionally specify `allowed_host`;
- rows without `allowed_host` still default to `bps.go.id`;
- suffix tricks such as `sumbarprov.go.id.evil.example` remain rejected;
- HTTP remains rejected.

This is a host-policy extension, not a relaxation to arbitrary URLs.

## BPBD queue

`data/acquisition_requests/bpbd_publications.csv` now contains five government-source requests. Only one is allowed to satisfy the exit gate:

1. **P0 / exit gate — 2017 Pusdalops annual report.** The browser opens the active official BPBD PPID surface, where the archived 2017 report identified by M50/PPID record 8604 must be obtained as the original PDF.
2. **P1 — 2015 Pusdalops activity report.** This freezes the raw artifact behind M49/M50's 686-event taxonomy, incompleteness warning, methodology, and internal year-label contradiction.
3. **P1 companion — Data Kebencanaan BPBD Sumatera Barat Tahun 2015/2016.** The direct official PPID PDF `2017_90.pdf` is a historical data-lineage and impact-schema companion only.
4. **P1 companion — LAKIP BPBD Sumatera Barat Tahun 2017.** This official cross-publication reproduces the 2017 725-event total and identifies Pusdalops PB BPBD Sumbar as source. It is useful for lineage/cross-publication checks but is not the missing annual-report artifact.
5. **P2 — 2018 annual report.** This is a nearby official continuity artifact only; it must not be projected backward as proof of 2017 semantics.

All rows allow only `sumbarprov.go.id` and its subdomains. The four companion/continuity requests have `exit_gate_candidate=no`; acquiring all of them still does **not** satisfy M52's trigger if the annual 2017 report remains missing.

## Current PPID migration constraint

The current PPID frontend uses UUID-based information routes and download URLs of the form `/api/download/?id=<uuid>&link=<encrypted-publicfile-token>...`. The historical audit still proves that old record `8604` existed, but no indexed migration mapping from record 8604 to the new UUID/download token has been recovered. The companion PDFs therefore improve acquisition coverage without pretending that the annual-report bytes have been recovered.

## Commands

Inspect the P0 queue without opening a browser:

```bash
python scripts/historical_batch_collect.py \
  --queue data/acquisition_requests/bpbd_publications.csv \
  --priority P0
```

Collect the 2017 raw artifact interactively:

```bash
python scripts/historical_batch_collect.py \
  --queue data/acquisition_requests/bpbd_publications.csv \
  --priority P0 \
  --open
```

Collect P1 companion artifacts separately:

```bash
python scripts/historical_batch_collect.py \
  --queue data/acquisition_requests/bpbd_publications.csv \
  --priority P1 \
  --open
```

After PDFs exist in `data/raw/inbox/`, freeze reproducible metadata:

```bash
python scripts/historical_batch_ingest.py \
  --queue data/acquisition_requests/bpbd_publications.csv \
  --manifest data/manifests/bpbd_historical_artifacts.csv \
  --require-exit-gate
```

Exit code `3` means the acquisition lane is valid but the 2017 exit-gate artifact is still missing. Companion artifacts never override that state.

## Promotion boundary

M51 does not contain the raw 2017 annual-report PDF and does not claim its checksum. M50's indexed values remain verification targets only. Source-native extraction starts only after an allowlisted official annual-report artifact is collected and hashed.

The LAKIP 2017 and Data Kebencanaan 2015/2016 PDFs may strengthen lineage or cross-publication evidence once acquired, but they are not substitutes for the annual-report bytes. Raw PDFs remain ignored under `data/raw/`; no PDF is committed merely to make CI pass.

## Next gate

M52 starts only after `bpbd-pusdalops-sumbar-2017.pdf` has been acquired through the lane. It should freeze artifact metadata, audit raw page/table locators, compare raw values against M50's indexed targets, and materialize a **separate BPBD source-native layer**. BNPB/DIBI reconciliation remains a later qualification problem.
