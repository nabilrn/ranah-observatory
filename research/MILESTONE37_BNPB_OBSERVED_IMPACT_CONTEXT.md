# Milestone 37 — BNPB Provincial Observed-Impact Context

## Purpose

M37 qualifies a narrow, source-native observed-impact evidence lane for Sumatera Barat from official BNPB provincial disaster-impact workbooks for 2024 and 2025.

This milestone closes a specific evidence gap left intentionally open by M26: Ranah Observatory already has recorded disaster-occurrence context, but occurrence counts must not be relabeled as deaths, affected people, injuries, displacement, or housing damage. M37 adds those impact measures directly from BNPB source tables while preserving their aggregation limits.

M37 does **not** reopen or rewrite the frozen v0.1 publication package. It is post-v0.1 evidence work on `research/evidence`.

## Locked source releases

Two official BNPB Satu Data releases are frozen separately:

- 2024 values are taken from detailed provincial resources inside package `f61d78e5-04c6-4ce8-9acf-e425dadc1f4d` (`Kompilasi Data Kejadian dan Dampak Bencana`);
- 2025 values are taken from package `58878b43-41b5-4ffb-b851-c6d8c8c4d438` (`Kompilasi Data Kejadian dan Dampak Bencana 2025`), published as a separate 2026 release.

The two releases are not treated as one event-level archive. M37 only asserts that the reviewed province-by-hazard cells share a usable presentation structure for the five promoted impact families.

## Promoted metrics

For province code `13` / `SUMATERA BARAT`, M37 freezes five source-native impact families:

1. reported deaths;
2. reported affected people;
3. reported injured/sick people;
4. reported displaced people;
5. reported damaged houses.

Each is retained separately for the nine source hazard columns: `BANJIR`, `CUACA EKSTREM`, `ERUPSI GUNUNG API`, `GELOMBANG PASANG DAN ABRASI`, `GEMPABUMI`, `KEBAKARAN HUTAN DAN LAHAN`, `KEKERINGAN`, `TANAH LONGSOR`, and `TSUNAMI`.

This yields 90 year × metric × hazard cells across 2024–2025.

## Missingness rule

Numeric zero and an empty source cell are different states.

The reviewed 2024 displaced-person workbook contains one empty Sumatera Barat cell for `GEMPABUMI`. It is materialized as `source_blank` with no numeric value. It is **not** rewritten as zero.

All other reviewed M37 Sumatera Barat cells are numeric source cells, including explicit zeros.

## Source-note qualification

The workbook `Keterangan` sheets refer to BNPB No. 7 Tahun 2023 for disaster classification/threshold context. The 2024 workbook text uses `Juklak BNPB No. 7 Tahun 2023`; the 2025 workbook text uses `Peraturan BNPB No. 7 Tahun 2023`.

The source notes also contain an apparent swapped description for the `Provinsi` and `Kabupaten` labels. M37 records that source-note condition rather than silently editing the source. Province identity is validated from the actual data-sheet fields `Kode Wilayah Provinsi = 13` and `Provinsi = SUMATERA BARAT`.

## Authorized interpretation

M37 authorizes only source-native BNPB administrative impact counts by province, hazard, metric, and year for the frozen 2024–2025 resources.

These counts may be used as observed-impact **context** alongside, but not substituted by, occurrence, hazard, exposure, vulnerability, capacity, or climate evidence.

## Prohibited upgrades

M37 does not authorize:

- event-level observed-impact reconstruction;
- district/city observed-impact inference from province totals;
- treating affected, injured, or displaced counts as unique people across events or hazard categories;
- summing person metrics across hazard categories into a unique annual population;
- combining deaths, people, and houses into a composite score;
- a composite disaster-risk index;
- causal climate/disaster attribution;
- monetary loss inference;
- monetary “wasted potential” estimation;
- policy or geography ranking.

The M26 event-level retrieval gate therefore remains unresolved.

## Reproducibility contract

The ten official XLSX workbooks are frozen byte-for-byte as members of a deterministic archive:

`data/raw/bnpb/m37_observed_impact/official-workbooks.zip`

The archive is a repository packaging container only; each original XLSX member retains its own SHA-256 in the M37 manifest, alongside the archive SHA-256.

`scripts/build_milestone37_bnpb_observed_impact.py` uses only the Python standard library to verify workbook structure, locate province code 13 without relying on row position, preserve explicit numeric zero separately from empty source cells, materialize the normalized 90-cell CSV, and generate a checksum-bound completion manifest.

The final CI lane rebuilds the normalized CSV and manifest from the frozen workbooks and fails if committed outputs differ.

## Outputs

- `data/processed/bnpb/m37_observed_impact/sumatera-barat-observed-impact-2024-2025.csv`
- `data/manifests/milestone37_bnpb_observed_impact.json`
- deterministic raw archive containing all ten frozen official workbooks under `data/raw/bnpb/m37_observed_impact/`
- `tests/test_milestone37_bnpb_observed_impact.py`
- final read-only M37 verification workflow

## Completion gate

M37 completes when all ten frozen resources parse without network access; province identity is code/name verified; the normalized output contains exactly 90 cells; the one reviewed source blank remains non-numeric; source file SHA-256 values bind every normalized row to a frozen workbook; all interpretation-expansion flags remain false; and byte-identical rebuild plus focused tests pass.
