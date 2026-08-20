# Milestone 25 — DJPK/SIKD Public-Finance Panel

Status: **complete for the preregistered exact-label fiscal subset; taxonomy-ambiguous transfer evidence remains held**.

M25 adds a district/city fiscal evidence layer for all 19 current West Sumatra kabupaten/kota over 2018–2025. The fiscal account taxonomy was locked on Kota Padang before values from the other 18 local governments were inspected.

## Frozen evidence footprint

- **19** kabupaten/kota;
- **8** fiscal years (2018–2025);
- **152** jurisdiction-year records;
- **4** exact-label fiscal account families promoted;
- **608** canonical fiscal observations;
- **152** jurisdiction-year provenance records;
- **8** frozen Stage 0 taxonomy-reference HTML pages;
- **152** frozen Stage 1 HTML semantic snapshots;
- **152** frozen official DJPK SpreadsheetML exports;
- HTML postur tables were parseable for **150** of 152 jurisdiction-years and structurally unavailable for **2**; unparseable HTML tables do not substitute or fabricate values.

All canonical values are annual-final fiscal realizations normalized to **IDR billion** from exact rupiah values in the official same-selector `csv_apbd` SpreadsheetML export. The locked selector remains `periode=12`; source-reported final semantics across the frozen panel are **139 Desember**, **11 Perda**, and **2 Audited** records. No imputation, historical-boundary reconstruction, explicit taxonomy bridge, derived fiscal ratio, or statistical model is part of M25.

## Why two official representations are retained

The DJPK APBD HTML page carries jurisdiction identity, fiscal year, annual-final realization semantics, and the link to the corresponding export. Historical pages requested with the locked `periode=12` selector report final status as `s.d Desember`, `s.d Audited <year>`, or `s.d Perda <year>`; intermediate-month and unaudited states remain rejected. During qualification, the body-table markup proved structurally inconsistent across the full historical footprint. M25 therefore records a representation-only transport amendment: the scientific scope and account contracts stay unchanged, while exact numeric evidence is taken from the official SpreadsheetML export exposed by that same HTML page and selector set.

For pages where the HTML postur table is parseable, each promoted account receives a diagnostic rounded-display cross-check against the exact export value. That display comparison is non-blocking and cannot override exact SpreadsheetML evidence. A page qualifies only when jurisdiction, fiscal year, accepted annual-final semantics, the exact same-selector export link, valid SpreadsheetML, and all locked exact labels remain verifiable.

## Exact-label families promoted

- `capital_expenditure` — Capital expenditure; Stage 0 status `exact_label_qualified`; source label(s): `Belanja Modal`.
- `own_source_revenue_pad` — Own-source revenue (PAD); Stage 0 status `exact_label_qualified`; source label(s): `PAD`.
- `total_expenditure` — Total expenditure; Stage 0 status `exact_label_qualified`; source label(s): `Belanja Daerah`.
- `total_revenue` — Total revenue; Stage 0 status `exact_label_qualified`; source label(s): `Pendapatan Daerah`.

## Families held from the exact panel

- `central_transfer_revenue` — Central-government transfer revenue; Stage 0 status `held_semantic_bridge_review`; observed label(s): `TKDD|Pendapatan Transfer Pemerintah Pusat`. It remains held until a separate semantic bridge is justified.

## Accounting and claim boundary

M25 treats fiscal-account continuity as an accounting-semantics problem, not a string-matching problem. The central-transfer family is not silently bridged across `TKDD` and newer terminology. Budget appropriations are not treated as realized spending, no fiscal ratios are generated, and no causal or policy-effect interpretation is authorized.

The panel can support a later preregistered geography-year design that asks whether fiscal capacity or expenditure composition adds explanatory or predictive value to modern development outcomes. M25 itself does not claim that revenue or expenditure caused poverty, unemployment, growth, or any other outcome.

## Reproducibility and provenance

Each jurisdiction-year provenance record binds both the official HTML snapshot and its same-selector SpreadsheetML export by SHA-256. Permanent CI works from frozen evidence: it verifies both source hashes, revalidates HTML identity/year/annual-final/export-link semantics, re-parses exact SpreadsheetML account values, records rounded HTML checks only as diagnostics, rebuilds the canonical panel, reruns completion/audit tests, and compares deterministic outputs byte-for-byte.

## Core outputs

- `data/manifests/milestone25_transport_amendment.json`
- `data/registries/djpk_sumbar_pemda.csv`
- `data/manifests/milestone25_taxonomy_discovery.json`
- `data/registries/djpk_m25_stage1_account_contracts.csv`
- `data/manifests/milestone25_stage1_contracts.json`
- `data/manifests/milestone25_stage1_full_export.json`
- `data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv`
- `data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv`
- `data/processed/djpk/public_finance/source/` (152 HTML + 152 SpreadsheetML snapshots)
- `data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv`
- `data/processed/djpk/public_finance/djpk-fiscal-provenance.csv`
- `data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json`
- `data/manifests/milestone25_djpk_public_finance_complete.json`
