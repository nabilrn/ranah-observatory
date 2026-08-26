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

`data/acquisition_requests/bpbd_publications.csv` contains five government-source requests. Only one is allowed to satisfy the exit gate:

1. **P0 / exit gate — 2017 Pusdalops annual report.** The collector now opens the active official PPID inventory at `https://ppid.sumbarprov.go.id/home/dip`. The acquisition operator must filter for the exact title, BPBD as OPD, and year 2017, then obtain the original annual-report PDF corresponding to legacy PPID download-audit record 8604.
2. **P1 — 2015 Pusdalops activity report.** This freezes the raw artifact behind M49/M50's 686-event taxonomy, incompleteness warning, methodology, and internal year-label contradiction.
3. **P1 companion — Data Kebencanaan BPBD Sumatera Barat Tahun 2015/2016.** The direct official PPID PDF `2017_90.pdf` is a historical data-lineage and impact-schema companion only.
4. **P1 companion — LAKIP BPBD Sumatera Barat Tahun 2017.** This official cross-publication reproduces the 2017 725-event total and identifies Pusdalops PB BPBD Sumbar as source. It is useful for lineage/cross-publication checks but is not the missing annual-report artifact.
5. **P2 — 2018 annual report.** This is a nearby official continuity artifact only; it must not be projected backward as proof of 2017 semantics.

All rows allow only `sumbarprov.go.id` and its subdomains. The four companion/continuity requests have `exit_gate_candidate=no`; acquiring all of them still does **not** satisfy M52's trigger if the annual 2017 report remains missing.

## PPID migration forensics — 26 August 2026

A new review of the live official PPID surface narrows the blocker without pretending to solve it:

- the active catalog is `https://ppid.sumbarprov.go.id/home/dip` and exposes filters for title/description, OPD, year and information type;
- current information pages use UUID routes of the form `/home/information/<uuid>`;
- a live information page's **Download** action resolves directly to `/home/download/<uuid>` and returns the document bytes;
- indexed PPID results also show that an `/api/download/?id=<uuid>&link=<encrypted-publicfile-token>&title=<title>` wrapper exists for some records, so both download surfaces may coexist;
- the legacy 2018 Pusdalops annual report is still indexed at `home/details/7526-laporan-tahunan-pusdalops-pb.html` and its official raw PDF is still available at `images/2019/07/file/Laporan_Tahunan_PUSDALOPS_PB.pdf`;
- the official 2024 PPID download-audit PDF reconfirms record **8604**, title **Laporan Tahunan Data Kebencanaan Pusdalops PB Sumatera Barat Tahun 2017**, OPD **Badan Penanggulangan Bencana Daerah**, with 24 recorded downloads;
- no defensible mapping from legacy record 8604 to a current UUID, `/home/information/<uuid>`, `/home/download/<uuid>`, API token, or direct official 2017 PDF URL has been recovered.

Therefore the previous M51 wording that treated the tokenized `/api/download/` wrapper as the sole current frontend route is superseded. The active human workflow should start from `/home/dip`, then follow the current UUID detail/download route if the 2017 record is recovered.

This evidence reduces search ambiguity but **does not recover the 2017 bytes**. Search-indexed non-government mirrors may be used only as discovery/verification targets; they cannot satisfy the official-artifact gate.

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
