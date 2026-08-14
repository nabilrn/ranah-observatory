# Historical Artifact Acquisition

## Why this exists

Historical source discovery and historical artifact acquisition are separate steps. Search engines, BPS publication pages, and BPS OPAC can establish that a source exists and can expose indexed table text, while canonical numeric extraction requires a stable artifact whenever practical so the exact bytes, page, table, and transcription can be reproduced.

## BPS access behaviour observed on 2026-08-14

Two acquisition attempts were run from GitHub-hosted Actions runners against the public BPS publication page for *Kota Bukittinggi Dalam Angka 2009*.

1. The first request used the repository's identifiable `ranah-observatory` User-Agent.
2. A second diagnostic request used ordinary browser-compatible headers and a browser User-Agent.

Both requests received HTTP `403 Forbidden` while fetching the public publication page. The second experiment therefore ruled out the custom User-Agent as the sole cause.

The normal research validation workflow remains green. Network acquisition is not a merge gate because an external site's anti-bot policy is not evidence that the data contract or extraction code is incorrect.

The manual workflow `.github/workflows/acquire-bps-artifacts.yml` is retained as a diagnostic for future network environments but is not run automatically.

## Current evidence levels

### Discovery-qualified

The repository can qualify source existence/metadata using official BPS publication pages, BPS OPAC, BPK legal metadata, and BPS AllStats/Deep Search.

### Candidate extraction

A value exposed in indexed official publication text may be entered in `historical_extraction_candidates.csv` with a promotion blocker. It is not a canonical observation.

Current example:

- *Kota Bukittinggi Dalam Angka 2009*, table 3.1.6, page 42;
- reference year 1971;
- Bukittinggi population printed as `63,132` persons;
- the table cites BPS Kota Bukittinggi;
- status: `pending_artifact_verification`;
- reconstruction state: `observed_retrospective_official`;
- blocker: missing artifact SHA-256.

This value is useful as a search/cross-check target but must not enter the analytical panel yet.

### Canonical extraction

Promotion requires, at minimum:

- the source artifact itself or another reproducibly captured official artifact;
- SHA-256 of the exact artifact bytes;
- page and table verification;
- source-geography and reference-period verification;
- classification under the historical extraction schema.

## Publication chronology anomaly

Current BPS web metadata exposes publication pages labelled *Sumatera Barat Dalam Angka Tahun 1970* and *Tahun 1971*. Separately, a later official BPS publication catalogue describes the `Sumatera Barat Dalam Angka` series as having a first edition in 1980.

The repository records this as an unresolved bibliographic anomaly rather than selecting whichever statement best fits the desired timeline. Possible explanations include title/series normalization, retrospective digitization, or metadata migration, but none is asserted without further evidence.

Each acquired artifact remains independently valid evidence even while the series-start chronology is unresolved.

## Human-browser acquisition queue

When automated hosted acquisition is blocked, the preferred fallback is a one-time human-browser download from the official source. Do not copy values manually from screenshots when the PDF can be supplied.

Priority queue:

1. **Penduduk Sumatera Barat Sensus Penduduk 1971 Seri E No.3** — official BPS OPAC records a 1973 softcopy dedicated to Sumatera Barat. This is the highest-value artifact for establishing the first province/regency/city historical population family.
2. **Sensus Penduduk 1961 Republik Indonesia** — official BPS publication, catalog 2102002, publication 03220.0001. This is the preferred 1961 Tingkat I population anchor and boundary-warning source.
3. **Kota Bukittinggi Dalam Angka 2009** — useful to verify the currently quarantined retrospective 1971 city candidate and later census checkpoints.

Once supplied, the artifact is hashed and inspected locally. Only the small checksum/provenance/extraction records need to enter Git; the raw PDF can remain outside normal Git history.

## Security and provenance

- No BPS developer credential is required for this queue.
- Do not upload private account/session exports or cookies.
- Prefer the PDF downloaded through the official BPS publication/OPAC interface.
- Preserve the original filename if practical.
- Do not edit, print-to-PDF, compress, or re-save the file before hashing; those operations change the artifact bytes.
