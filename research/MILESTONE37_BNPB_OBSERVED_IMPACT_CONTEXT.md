# Milestone 37 — BNPB Provincial Observed-Impact Context

## Purpose

M37 qualifies a narrow, source-native observed-impact evidence lane for Sumatera Barat from official BNPB provincial disaster-impact resources for 2024 and 2025.

This closes a specific gap left intentionally open by M26: recorded disaster-occurrence counts must not be relabeled as deaths, affected people, injuries, displacement, or housing damage. M37 adds those impact measures from their own BNPB source resources while preserving aggregation limits.

M37 is post-v0.1 evidence work on `research/evidence`; it does not rewrite the frozen v0.1 publication package.

## Locked source releases

Two official BNPB Satu Data releases are qualified separately:

- 2024: package `f61d78e5-04c6-4ce8-9acf-e425dadc1f4d` (`Kompilasi Data Kejadian dan Dampak Bencana`);
- 2025: package `58878b43-41b5-4ffb-b851-c6d8c8c4d438` (`Kompilasi Data Kejadian dan Dampak Bencana 2025`), a separate 2026-published release.

Five exact resource IDs per year are registered in `data/registries/disaster_sources.csv`. The reviewed original XLSX workbooks were byte-digested with SHA-256 before promotion. Full workbooks are **not** claimed as committed repository artifacts.

## Repository evidence representation

The canonical M37 raw layer is:

`data/raw/bnpb/m37_observed_impact/sumatera-barat-source-rows.json`

It contains one reviewed Sumatera Barat source-row snapshot for each of the ten official resources, keyed by `Kode Wilayah Provinsi = 13` and `Provinsi = SUMATERA BARAT`.

Each snapshot retains:

- year and metric identity;
- BNPB package and resource IDs;
- SHA-256 of the reviewed original workbook;
- the nine source hazard cells;
- source-note methodology wording;
- the observed source-note label anomaly.

This is deliberately described as a **source-row snapshot with workbook digests**, not a full-workbook freeze. The distinction is encoded in the snapshot and completion manifest.

## Promoted metrics

M37 freezes five source-native impact families:

1. reported deaths;
2. reported affected people;
3. reported injured/sick people;
4. reported displaced people;
5. reported damaged houses.

Each remains separate across the nine source hazard columns: `BANJIR`, `CUACA EKSTREM`, `ERUPSI GUNUNG API`, `GELOMBANG PASANG DAN ABRASI`, `GEMPABUMI`, `KEBAKARAN HUTAN DAN LAHAN`, `KEKERINGAN`, `TANAH LONGSOR`, and `TSUNAMI`.

The normalized panel therefore contains exactly 90 year × metric × hazard cells across 2024–2025.

## Missingness rule

Numeric zero and an empty source cell are different states.

The reviewed 2024 displaced-person source contains one empty Sumatera Barat cell for `GEMPABUMI`. M37 materializes it as `source_blank` with no numeric value. It is **not** rewritten as zero.

All other reviewed M37 Sumatera Barat cells are numeric source cells, including explicit zeros.

## Source-note qualification

The workbook `Keterangan` sheets refer to BNPB No. 7 Tahun 2023 for disaster classification/threshold context. The reviewed 2024 files use `Juklak BNPB No. 7 Tahun 2023`; the reviewed 2025 files use `Peraturan BNPB No. 7 Tahun 2023`.

The source notes also contain an apparent swapped description for the `Provinsi` and `Kabupaten` labels. M37 records that source condition rather than silently correcting it. Province identity is qualified from the actual data-sheet code/name pair.

## Authorized interpretation

M37 authorizes only source-native BNPB administrative impact counts by province, hazard, metric, and year for the frozen source-row snapshots.

These counts may be used as observed-impact **context** alongside occurrence, hazard, exposure, vulnerability, capacity, or climate evidence. They are not substitutes for those evidence families.

## Prohibited upgrades

M37 does not authorize:

- event-level observed-impact reconstruction;
- district/city observed-impact inference from province totals;
- treating affected, injured, or displaced counts as unique people across events or hazard categories;
- summing person metrics across hazard categories into a unique annual population;
- combining deaths, people, and houses into a composite score;
- a composite disaster-risk index;
- causal climate/disaster attribution;
- monetary loss or monetary “wasted potential” inference;
- policy or geography ranking.

The M26 event-level retrieval gate therefore remains unresolved.

## Reproducibility contract

`scripts/build_milestone37_bnpb_observed_impact.py` is network-free. It validates the ten source-row snapshots, preserves explicit numeric zero separately from source blanks, materializes the normalized 90-cell CSV, and generates the checksum-bound completion manifest.

Focused tests verify known reviewed cells, missingness semantics, exact coverage, deterministic rebuilds, and all interpretation-expansion flags.

The final GitHub Actions lane is read-only: it rebuilds from the committed source-row snapshot and fails if the generated CSV or manifest differs from Git.

## Outputs

- `data/raw/bnpb/m37_observed_impact/sumatera-barat-source-rows.json`
- `data/processed/bnpb/m37_observed_impact/sumatera-barat-observed-impact-2024-2025.csv`
- `data/manifests/milestone37_bnpb_observed_impact.json`
- `scripts/build_milestone37_bnpb_observed_impact.py`
- `tests/test_milestone37_bnpb_observed_impact.py`
- read-only M37 verification workflow

## Completion gate

M37 completes when all ten source-row snapshots validate offline; province identity remains code/name locked; the normalized output contains exactly 90 cells; the single reviewed source blank remains non-numeric; every snapshot retains the original workbook SHA-256 and exact BNPB resource ID; all interpretation-expansion flags remain false; and deterministic rebuild plus focused tests pass.
