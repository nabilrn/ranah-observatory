# Historical Artifact Acquisition

## Goal

Historical source discovery and historical artifact acquisition are separate steps. Search engines, official BPS publication pages, BPS OPAC, and BPS WebAPI can establish that a source exists, but numeric extraction should use an exact reproducible artifact whenever practical so the bytes, source metadata, and transformation can be audited.

Ranah Observatory therefore has two complementary acquisition lanes:

1. **credentialed BPS WebAPI snapshots** for official data that BPS exposes programmatically;
2. **batch human-browser publication collection** for PDFs/archives that hosted automation cannot retrieve reliably.

Neither lane is allowed to erase source-era geography or definition differences.

## Credentialed BPS WebAPI lane

On 2026-08-15 the repository's `BPS_API_KEY` GitHub Actions secret passed a live request against BPS domain `1300` (Sumatera Barat). The API was then used to discover subjects, variables, periods, static tables, and dynamic data.

Historical population variable `484`, *[Hasil Sensus dan SUPAS] Jumlah Penduduk Menurut Jenis Kelamin dan Kabupaten/Kota di Sumatera Barat*, explicitly states in its BPS metadata that 1971, 1980, 1990, 2000, 2010, and 2020 are sourced from Population Censuses, while 1995, 2005, and 2015 are sourced from SUPAS.

The 1971 API response is frozen as a canonical JSON snapshot at:

`data/snapshots/bps/var-484-1971.json`

with SHA-256:

`b0d808a6b59b018c7a28f5d47b882f17248eb9ae2d0b05a6acb62366ca2813e1`

The selected total-sex (`turvar=34`) source-native rows are stored at:

`data/processed/bps/historical_population_source_native.csv`

The snapshot establishes a province total of **2,789,822 persons** for 1971. The fourteen local total rows actually present in `datacontent` sum exactly to that province total. Later/split units whose labels appear in response metadata but have no 1971 values are not synthesized.

A small API snapshot may be committed when it is intentionally frozen evidence and contains no credential. The API key itself remains only in GitHub Secrets and must never be written to a snapshot, log, manifest, or chat.

An API snapshot can satisfy a historical source-artifact gate when all of the following hold:

- the exact JSON bytes are frozen and checksummed;
- source variable/period/category IDs and labels are retained;
- the official metadata identifies the source family or measurement regime;
- source-native values are reconciled and validated;
- geography mapping does not silently project modern boundaries backward;
- unresolved conflicts with other official sources remain registered.

This means a publication PDF is no longer the only possible exit path for historical numeric evidence. PDFs remain essential for earlier periods, table-level definitions, bibliographic verification, and independent cross-checks.

## Why browser collection is a separate lane

On 2026-08-14, two diagnostic requests from GitHub-hosted Actions runners attempted to fetch a public BPS publication page. Both received HTTP `403 Forbidden`, including a diagnostic request with ordinary browser-compatible headers. This is treated as an external access constraint rather than a research-validation failure.

Normal CI never attempts to bypass the restriction. The repository does not store BPS cookies, browser sessions, CAPTCHA material, or private account data.

## Anchor-year strategy

The first publication batch intentionally prioritizes longitudinal anchors instead of downloading every annual publication.

### P0 — first publication batch

1. `sp1961_indonesia` — *Sensus Penduduk 1961 Republik Indonesia*.
2. `sp1971_sumbar_e3` — *Penduduk Sumatera Barat Sensus Penduduk 1971 Seri E No.3*.
3. `sumbar_1970` — *Sumatera Barat Dalam Angka Tahun 1970*.
4. `sumbar_1980` — *Sumatera Barat Dalam Angka Tahun 1980*.
5. `sumbar_1990` — *Sumatera Barat Dalam Angka Tahun 1990*.
6. `sumbar_2000` — *Sumatera Barat Dalam Angka Tahun 2000*.
7. `sumbar_2010` — *Sumatera Barat Dalam Angka 2010*.
8. `sumbar_2020` — *Provinsi Sumatera Barat Dalam Angka 2020*.

The two census publications remain `exit_gate_candidate=yes` for the **publication-artifact** lane. They are preferred cross-checks and SP1961 remains important for extending the population anchor earlier than the WebAPI 1971 census family. They no longer block merging the historical foundation now that a separately validated official WebAPI census artifact exists.

### P1 — cross-check and densification

The queue also contains 1971, 1975, 2015, 2026 annual volumes and *Kota Bukittinggi Dalam Angka 2009*. These are useful for methodology checks, retrospective-table verification, and later densification but should not delay the first longitudinal panel.

The authoritative publication queue is:

`data/acquisition_requests/bps_publications.csv`

## Local publication workflow

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

This prints the eight P0 publication anchors without opening a browser.

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

## Publication manifest generation

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
- publication exit-gate status;
- `artifact_verified` state;
- acquisition timestamp.

Existing acquisition timestamps are preserved when the file hash has not changed, so rerunning the command does not create meaningless manifest churn.

To test whether the publication lane has at least one census exit-gate artifact:

```powershell
py -3 scripts/historical_batch_ingest.py --require-exit-gate
```

Exit code `3` means the publication workflow itself is valid but neither census PDF is present yet. It does **not** mean the overall historical reconstruction foundation lacks a validated numeric anchor; the BPS WebAPI 1971 census snapshot is validated separately by `scripts/validate_bps_historical_anchor.py`.

## Promotion boundary

A checksum proves that a specific source artifact has been frozen. It does **not** prove that every value inside that artifact is canonical or longitudinally comparable.

Numeric promotion still requires:

- source variable/table and category verification;
- source-era geography verification;
- reference-period and unit verification;
- extraction method;
- comparability/reconstruction state;
- mapping to a canonical indicator.

A later official publication that reproduces an older number remains distinguishable from a contemporaneous census/API family. Likewise, source-native BPS geography codes in a historical response are not automatically identical to today's administrative units.

## Candidate quarantine

`historical_extraction_candidates.csv` may contain official indexed values that are useful for discovery before the PDF is available. Those rows must remain quarantined while `artifact_sha256` is blank or while the promotion blocker is unresolved.

Current example: *Kota Bukittinggi Dalam Angka 2009* reproduces a 1971 population value of `63,132` for Bukittinggi. The frozen BPS WebAPI census family reports `63,356` for the same year. The disagreement is recorded in `historical_source_anomalies.csv`; neither value is averaged or silently substituted for the other.

## Publication chronology anomaly

Current BPS web metadata exposes publication pages labelled *Sumatera Barat Dalam Angka Tahun 1970* and *Tahun 1971*. Separately, another official BPS catalogue describes the series chronology differently. The repository records this as an unresolved bibliographic anomaly rather than forcing one interpretation.

Artifact validity and series-history interpretation are therefore separate questions.

## Security and provenance rules

- Never commit `data/raw/` PDFs merely for convenience.
- Small credential-free API JSON snapshots may be committed when intentionally frozen as evidence.
- Never commit BPS credentials, cookies, or session exports.
- Download publications from the official source page in the queue whenever possible.
- Do not edit, print-to-PDF, compress, optimize, or re-save a source before hashing.
- If an official artifact/API response is revised, preserve the new hash as a new provenance event rather than silently replacing the old evidence.
- Unknown PDFs in the inbox are rejected by the batch ingester instead of being guessed into a request.
