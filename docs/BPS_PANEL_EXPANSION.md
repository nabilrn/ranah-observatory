# BPS Structural-Economic Panel Expansion

## Purpose

This phase extends the first modern BPS panel with structural outcomes that are directly relevant to long-run development analysis: labor slack, inequality, sector composition, agricultural productivity, exports, and a clean population census anchor.

The expansion follows the same evidence ladder as the first panel. A source being present in BPS WebAPI does not make it canonical. Each logical series passes through source-native selection, explicit geography mapping, evidence qualification, deterministic transformation where needed, canonical promotion, semantic-drift review, and durable materialization.

## Reviewed logical series

| Logical family | Canonical indicator | BPS var | Window | Source selection | Canonical scope |
|---|---|---:|---|---|---|
| Underemployment | `underemployment_rate` | 668 | 2018–2024 | `turvar=1081` Setengah Pengangguran | province + 19 kab/kota |
| Gini | `gini_ratio` | 83 | 2018–2025 | no derived category | province only |
| Agriculture share of GRDP | `agriculture_share_grdp` | 282 | 2018–2023 | sector A / total PDRB | province + 19 kab/kota |
| Manufacturing share of GRDP | `manufacturing_share_grdp` | 282 | 2018–2023 | sector C / total PDRB | province + 19 kab/kota |
| Rice yield | `rice_yield` | 276 | 2018–2025 | `turvar=244` productivity | province + 19 kab/kota |
| Export value | `export_value` | 463 | 2018–2023 | annual `Jumlah`, `Nilai (US$)` | province only |
| SP2020 population | `population_total` | 484 | 2020 | total sex category | province + 19 kab/kota |

The reviewed logical source panel contains **726 rows**. The canonical layer contains **574 observations** and **36 provenance records**. **152 local Gini rows** remain held source-native rather than being promoted beyond the province-level canonical concept.

## Why the expansion builder is separate

BPS dynamic-table dimensions are not structurally uniform.

Most first-panel sources use `vervar` as geography. In this expansion:

- underemployment, Gini, rice, and SP2020 population use `vervar` as geography;
- PDRB-by-industry var 282 uses `vervar` for industry and `turvar` for geography;
- export var 463 uses `vervar` for month/annual-total and `turvar` for volume/value, with the whole source family scoped to Sumatera Barat.

A generic assumption such as “`vervar` always means geography” would therefore corrupt the data silently. `bps_expansion_series.csv` declares the geography dimension and selectors for every logical series, while `bps_expansion_geography_map.csv` maps both source-dimension systems explicitly.

## Geography rules

For modern `vervar` sources:

- current local codes `1301..1312` and `1371..1377` map directly to the 19 canonical current kabupaten/kota for the reviewed modern window;
- `1300` and `1378` are source aggregate aliases for canonical `idn.13` and are not inserted as canonical administrative BPS codes.

For PDRB var 282, `turvar=464..483` is an API source-dimension encoding for the same 19 local units plus the province. These IDs are mapped explicitly and must not be interpreted as administrative BPS codes.

Export is scoped as a constant province source family. It does not create a fictitious geographic code from the month dimension.

## Qualification decisions

### Underemployment

BPS var 668 provides `Setengah Pengangguran` as `turvar=1081`, unit percent, from August Sakernas. The selected source is canonical as an observed underemployment rate.

As with the first-panel labor indicators, the source carries weighting/projection-regime notes. Values remain official observations, but cross-regime comparability is left unresolved until the full weighting lineage is qualified.

### Gini ratio

The BPS variable is sourced from Susenas, and the official Sumatera Barat release confirms province Gini for March 2025 at 0.282, matching the API province row.

The API also exposes 19 local values, but the current canonical indicator is province-level and the local estimation level has not been independently qualified. The conservative decision is therefore:

- province row → canonical observed Gini;
- 19 local rows → held source-native.

No district/city Gini is promoted merely because the API emits a number.

### Agriculture and manufacturing shares

Var 282 contains current-price GRDP by industry in million rupiah, with:

- sector A (`vervar=100`) = agriculture, forestry, and fisheries;
- sector C (`vervar=300`) = manufacturing;
- total PDRB (`vervar=990`).

The source geography is in `turvar`. For each geography-year, the pipeline derives:

`share = 100 × sector value / total PDRB`

The numerator and denominator are retained in the source panel. Denominators must be positive and derived shares must remain within 0–100. The canonical claim type is `derived`, not `observed`, and the price basis is retained as current-price series 2010.

### Rice yield

BPS var 276 `turvar=244` reports productivity in **quintal per hectare**. The canonical indicator uses tonnes per hectare, so the deterministic transform is:

`tonnes_per_hectare = quintal_per_hectare × 0.1`

The canonical claim type remains `derived` because the unit-transformed value is not copied verbatim from the source.

The source notes identify KSA and state that 2018–2022 values use the KSA-2022 recalculation. The 2025 source also carries a Kota Pariaman/LBS caveat, so 2025 cross-year comparability is not asserted automatically.

### Export value

Var 463 is structured by month/annual total and measure. The pipeline selects only:

- `vervar=13` — annual `Jumlah`;
- `turvar=420` — `Nilai (US$)`.

The canonical observations are province-level annual USD values. The source concept is retained as the official Sumatera Barat BPS export-statistics family. The values are not reinterpreted as production-origin exports when the source is framed through commodity/destination/port documentation.

### SP2020 population

Var 484 explicitly distinguishes census years from SUPAS years. The expansion selects only 2020 and the total-sex category (`turvar=34`). The official SP2020 result is referenced to September 2020, so canonical observations use September date bounds rather than a generic calendar-year timestamp.

This avoids using mixed census/projection/registration population families as if they were one homogeneous annual observed series.

## Source-native and canonical counts

Expected source rows:

- underemployment: 140;
- Gini: 160;
- agriculture share source rows: 120;
- manufacturing share source rows: 120;
- rice yield: 160;
- exports: 6;
- SP2020 population: 20;
- total: **726**.

Expected canonical rows:

- underemployment: 140;
- Gini province only: 8;
- agriculture share: 120;
- manufacturing share: 120;
- rice yield: 160;
- exports: 6;
- SP2020 population: 20;
- total: **574**.

Held source-native rows: **152**, all local Gini values.

## Provenance

The canonical expansion is expected to use **36 source-period provenance records**:

- underemployment: 7 snapshots;
- Gini: 8;
- PDRB var 282: 6 shared snapshots for both derived sector-share families;
- rice: 8;
- export: 6;
- population: 1.

Derived agriculture/manufacturing observations intentionally share the same source-period provenance because numerator and denominator come from the same BPS var 282 snapshot.

## Drift protection

The reviewed expansion baseline is stored at:

`data/manifests/bps_expansion_baseline.json`

Its semantic fingerprint is:

`4afbf2cabac2afbd4980ff492c0d072ce27f9398be35141a07bc196f8fc12dc4`

The fingerprint excludes only retrieval-only volatility:

- `retrieved_at_utc`;
- source snapshot filename;
- source snapshot SHA-256.

It still includes source values, numerator/denominator values, BPS `last_update`, dimension selectors, geography mappings, transformation rule, claim type, and canonical promotion state.

A fresh harvest that changes any of those semantics fails the drift gate until the revision is reviewed explicitly.

## What this phase does not claim

This expansion does not establish causality or quantify unrealized potential. It also does not:

- promote local Gini without estimation-level evidence;
- infer household internet access from the separate person-level internet source;
- treat sector shares as direct BPS observed percentages;
- hide KSA revisions or the 2025 rice caveat;
- reinterpret port/document-based exports as production-origin exports;
- interpolate population between census/SUPAS anchors;
- treat labor weighting regimes as automatically comparable.

These constraints are part of the research result, not missing cleanup.

## Exit gate

The phase is ready to merge when:

1. offline expansion registries and baseline validators pass;
2. full repository unit-test discovery passes;
3. a fresh credentialed BPS harvest reproduces the reviewed semantic fingerprint;
4. generated artifacts validate as 726 source rows, 574 canonical observations, 152 held rows, and 36 provenance records;
5. all deterministic transforms and reference-period rules pass validation;
6. durable materialization contains no credentials or bulk raw API snapshots;
7. PR-triggered checks are green and there are no unresolved review blockers.
