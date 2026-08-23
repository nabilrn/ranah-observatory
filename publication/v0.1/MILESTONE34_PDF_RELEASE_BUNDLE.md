# Milestone 34 — Final PDF and distribution bundle

## Purpose

M34 converts the certified M33 citation-ready Markdown preprint and the deterministic M30 publication assets into a portable final PDF distribution bundle.

This milestone is typesetting and release engineering only. It does not change the frozen scientific manuscript, claim ledger, source observations, analytical models, or inference state.

## Author and release identity

- Author: **Nabil Rizki Navisa**
- Affiliation: **Independent Researcher**
- Release: **v0.1**
- Release date: **2026-08-23**
- Publication license: **CC BY 4.0**
- Target deposit repository: **Zenodo**

## Authoritative inputs

M34 reads only already-certified publication surfaces:

- `publication/v0.1/preprint/preprint.md` — M33 citation-ready preprint;
- `publication/v0.1/preprint/preprint-manifest.json` — M33 integrity contract;
- `publication/v0.1/rendered/` — M30 canonical seven tables and six vector figures;
- `publication/v0.1/rendered/render-manifest.json` — M30 asset integrity contract;
- `publication/v0.1/submission/metadata.json` — confirmed author/license/deposit metadata;
- `publication/v0.1/claim-ledger.csv` — authoritative claim states.

## PDF layout contract

The final PDF is typeset as an academic A4 technical report:

- portrait A4 narrative pages;
- title page with confirmed author and release metadata;
- depth-2 table of contents;
- vector SVG figures preserved from M30;
- body text set in DejaVu Sans with deterministic monochrome styling;
- page numbers;
- Appendix A reproducing all seven canonical M30 CSV tables;
- appendix tables use A4 landscape pages to avoid clipping and preserve source values.

No canonical table or figure is redrawn with new data or recalculated values.

## Distribution outputs

`publication/v0.1/distribution/` contains exactly:

1. `Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf`;
2. `README.md`;
3. `SHA256SUMS.txt`;
4. `distribution-manifest.json`.

The manifest binds the certified M30/M33 sources and all distribution outputs by SHA-256.

## Reproducible rendering environment

CI renders with:

- Pandoc `3.1.11.1`;
- WeasyPrint `68.0`;
- DejaVu fonts;
- Poppler utilities for PDF structural/text validation;
- `ubuntu-24.04` GitHub runner.

The final workflow is read-only. A one-time branch-only canonicalization step may be used to commit an already-validated generated binary, but that writer must be removed before review and merge.

## Scientific boundary

M34 performs:

- no new analytical source acquisition;
- no data imputation or source substitution;
- no model fitting or refitting;
- no statistical search;
- no forecast qualification;
- no causal upgrade;
- no monetary aggregation;
- no disaster-risk composite;
- no policy ranking.

All nine M18 blocked claims and all required negative results remain governed by the M29 claim ledger.

## Completion gate

M34 completes only when:

- M29 publication audit remains green;
- M30 canonical assets rebuild byte-for-byte;
- M31 finalized submission package rebuilds byte-for-byte;
- M33 citation-ready preprint rebuilds byte-for-byte;
- the PDF contains the confirmed author, title, all six figure IDs, all seven table IDs, all 16 reference IDs, and all nine blocked claim IDs;
- the PDF has at least 20 pages and is unencrypted;
- all seven appendix tables are present;
- all distribution checksums are internally consistent;
- the canonical distribution directory rebuilds byte-for-byte in read-only CI;
- no upstream scientific artifact changes.
