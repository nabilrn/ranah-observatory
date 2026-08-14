# Historical Artifact Acquisition

## Goal

Historical source discovery and historical artifact acquisition are separate steps. Search engines, official BPS publication pages, and BPS OPAC can establish that a source exists, but canonical numeric extraction should use an exact artifact whenever practical so the bytes, page, table, and transcription can be reproduced.

The acquisition workflow is therefore designed around **batch human-browser collection + automated local verification**, not one-document-at-a-time handoff.

## Why browser collection is a separate lane

On 2026-08-14, two diagnostic requests from GitHub-hosted Actions runners attempted to fetch a public BPS publication page. Both received HTTP `403 Forbidden`, including a diagnostic request with ordinary browser-compatible headers. This is treated as an external access constraint rather than a research-validation failure.

Normal CI never attempts to bypass the restriction. The repository does not store BPS cookies, browser sessions, CAPTCHA material, or private account data.

## Anchor-year strategy

The first acquisition batch intentionally prioritizes longitudinal anchors instead of downloading every annual publication.

### P0 — first batch

1. `sp1961_indonesia` — *Sensus Penduduk 1961 Republik Indonesia*.
2. `sp1971_sumbar_e3` — *Penduduk Sumatera Barat Sensus Penduduk 1971 Seri E No.3*.
3. `sumbar_1970` — *Sumatera Barat Dalam Angka Tahun 1970*.
4. `sumbar_1980` — *Sumatera Barat Dalam Angka Tahun 1980*.
5. `sumbar_1990` — *Sumatera Barat Dalam Angka Tahun 1990*.
6. `sumbar_2000` — *Sumatera Barat Dalam Angka Tahun 2000*.
7. `sumbar_2010` — *Sumatera Barat Dalam Angka 2010*.
8. `sumbar_2020` — *Provinsi Sumatera Barat Dalam Angka 2020*.

The two census publications are marked `exit_gate_candidate=yes`. At least one artifact-backed historical population family can satisfy the extraction exit gate; both are preferred because they bracket an important early period.

### P1 — cross-check and densification

The queue also contains 1971, 1975, 2015, 2026 annual volumes and *Kota Bukittinggi Dalam Angka 2009*. These are useful for methodology checks, retrospective-table verification, and later densification but should not delay the first longitudinal panel.

The authoritative queue is:

`data/acquisition_requests/bps_publications.csv`

## Local workflow

Raw PDFs stay under `data/raw/` and are ignored by Git.

### 1. Inspect the P0 queue

Windows:

```powershell
py -3 scripts/historical_batch_collect.py
```

Linux/macOS:

```bash
python3 scripts/historical_batch_collect.py
```

This prints the eight P0 anchors without opening a browser.

### 2. Collect the batch interactively

Windows:

```powershell
py -3 scripts/historical_batch_collect.py --open
```

Linux/macOS:

```bash
python3 scripts/historical_batch_collect.py --open
```

For each queue item the script:

1. opens the official BPS page in the default browser;
2. asks the contributor to click the official **Unduh/Download** control;
3. waits for Enter;
4. detects the newest changed PDF in the local `Downloads` directory;
5. validates the `%PDF` signature and end marker;
6. copies the bytes into `data/raw/inbox/` using the canonical queue filename;
7. prints the SHA-256 immediately;
8. skips already-valid inbox artifacts, so interrupted batches can be resumed safely.

If the browser downloads somewhere else:

```powershell
py -3 scripts/historical_batch_collect.py --open --downloads-dir "D:\Downloads"
```

If automatic detection fails, the script accepts a pasted PDF path for that one item.

To collect P1 later:

```powershell
py -3 scripts/historical_batch_collect.py --priority P1 --open
```

To collect P0 and P1 in one session:

```powershell
py -3 scripts/historical_batch_collect.py --priority P0 --priority P1 --open
```

## Manifest generation

After browser collection:

```powershell
py -3 scripts/historical_batch_ingest.py
```

The ingester validates each expected artifact again, hashes the exact bytes, and writes only reproducible metadata to:

`data/manifests/historical_artifacts.csv`

Manifest fields include:

- request/source reference;
- canonical artifact filename;
- SHA-256;
- byte count;
- official source page;
- anchor year and priority;
- exit-gate status;
- `artifact_verified` state;
- acquisition timestamp.

Existing acquisition timestamps are preserved when the file hash has not changed, so rerunning the command does not create meaningless manifest churn.

To test whether the historical extraction exit gate has at least one real artifact:

```powershell
py -3 scripts/historical_batch_ingest.py --require-exit-gate
```

Exit code `3` means the workflow itself is valid but neither census exit-gate artifact is present yet.

## Promotion boundary

A manifest row proves that a specific official artifact has been acquired and hashed. It does **not** prove that every value inside the PDF is canonical.

Numeric promotion still requires:

- page/table verification;
- source-era geography verification;
- reference-period and unit verification;
- extraction method;
- comparability/reconstruction state;
- mapping to a canonical indicator.

A later official publication that reproduces an older number remains distinguishable from a contemporaneous source-era observation.

## Candidate quarantine

`historical_extraction_candidates.csv` may contain official indexed values that are useful for discovery before the PDF is available. Those rows must remain quarantined while `artifact_sha256` is blank or while the promotion blocker is unresolved.

Current example: *Kota Bukittinggi Dalam Angka 2009* reproduces a 1971 population value for Bukittinggi. The candidate is useful as a cross-check target but cannot enter the analytical panel until the artifact and table are verified.

## Publication chronology anomaly

Current BPS web metadata exposes publication pages labelled *Sumatera Barat Dalam Angka Tahun 1970* and *Tahun 1971*. Separately, another official BPS catalogue describes the series chronology differently. The repository records this as an unresolved bibliographic anomaly rather than forcing one interpretation.

Artifact validity and series-history interpretation are therefore separate questions.

## Security and provenance rules

- Never commit `data/raw/` PDFs merely for convenience.
- Never commit BPS credentials, cookies, or session exports.
- Download from the official source page in the queue whenever possible.
- Do not edit, print-to-PDF, compress, optimize, or re-save a source before hashing.
- If an official artifact is revised, preserve the new hash as a new provenance event rather than silently replacing the old evidence.
- Unknown PDFs in the inbox are rejected by the batch ingester instead of being guessed into a request.
