# BPS Normalized Panel

## Purpose

The normalized BPS panel is the first repeatable modern-data layer in Ranah Observatory. Its purpose is not to maximize row count. It converts selected BPS WebAPI series into auditable source-native records and promotes only evidence-qualified families into canonical observations.

The pipeline deliberately separates four decisions:

1. **discovery** — a BPS variable exists and looks relevant;
2. **source-native ingestion** — values and BPS metadata are captured without changing their meaning;
3. **qualification** — unit, universe, reference period, methodology, geography, and known quality flags are reviewed;
4. **canonical promotion** — only qualified rows become observations under the Ranah Observatory indicator ontology.

A successful API request is therefore not sufficient evidence for canonical promotion.

## Current first-panel scope

The reviewed source panel contains eight BPS variable families over the current Sumatera Barat province and 19 kabupaten/kota.

| Source family | Canonical indicator | BPS var | Window | Decision |
|---|---|---:|---|---|
| District/city TPT | `unemployment_rate` | 139 | 2018–2025 | canonical-ready |
| District/city TPAK | `labor_force_participation` | 141 | 2018–2025 | canonical-ready |
| Internet use, persons age 5+ | `internet_access` candidate | 320 | 2018–2025 | hold source-native |
| Expected years of schooling | `expected_years_schooling` | 361 | 2018–2025 | canonical-ready |
| Mean years of schooling | `mean_years_schooling` | 363 | 2018–2025 | canonical-ready |
| Life expectancy, LF-SP2020 method | `life_expectancy` | 752 | 2020–2025 | canonical-ready |
| Poverty headcount | `poverty_rate` | 34 | 2018–2025 | canonical-ready |
| Real GRDP growth, ADHK 2010 | `real_grdp_growth` | 138 | 2018–2025 | canonical-ready |

The source-native panel has **1,240 rows**. Seven qualified families account for **1,080 canonical-ready rows**; the person-level internet family accounts for **160 held rows**.

The first reviewed source panel covers **20 canonical geographies**: the province plus its 19 current kabupaten/kota.

## Source-native layer

### Period resolution

BPS `th` values are internal period IDs. They are not treated as calendar years by convention.

`scripts/harvest_bps_series.py` first queries BPS period metadata, resolves requested labels such as `2025` to the source `th_id`, and then fetches each period independently. A missing or ambiguous source label is an error.

The pipeline intentionally uses one API request per period. A range-form request was tested earlier and rejected by the BPS data endpoint; deterministic per-period requests avoid guessing API selection semantics.

### Dynamic-table normalization

BPS dynamic values are returned through `datacontent` keys composed from source dimensions. `scripts/normalize_bps_dynamic.py` reconstructs those keys from the response metadata:

- `vervar` — vertical/geographic dimension;
- `var` — variable;
- `turvar` — derived/sub-variable;
- `th` — period;
- `turth` — derived/sub-period.

No fixed string widths are assumed. Unexpected keys fail normalization instead of being heuristically decoded.

Each normalized source row retains the original IDs and labels, variable definition/note, BPS `last_update`, retrieval timestamp, value, and source key.

### Snapshot provenance

Every period request produces a credential-free JSON snapshot and a SHA-256 sidecar in the workflow artifact. The BPS API key is supplied only through GitHub Actions Secrets and is never serialized into the snapshot.

The combined source panel links every selected value back to its exact period snapshot checksum.

## Geography mapping

BPS dynamic endpoints do not use one consistent source ID for the Sumatera Barat province aggregate.

In the first panel:

- some source families use `1300` for the province aggregate;
- others use `1378` for the same aggregate role;
- current local administrative rows use `1301..1312` and `1371..1377`.

`1300` and `1378` are therefore explicit **source aggregate aliases** mapped to canonical `idn.13`. They are not inserted into the canonical current BPS-code registry, whose province code remains `13`.

The 19 local source IDs map directly to their current canonical geography IDs only for the reviewed 2018–2025 window. This mapping is not reusable for historical periods without a separate boundary qualification.

The mapping contract is stored in:

`data/registries/bps_panel_geography_map.csv`

## Qualification decisions

Qualification evidence and decisions are stored in:

`data/registries/bps_panel_qualification.csv`

### Open unemployment rate — TPT

The selected district/city family is treated as an **August Sakernas** observation. The source unit is percent. Official Sumatera Barat labor publications at both ends of the selected window identify August Sakernas as supporting district/city estimates.

BPS source metadata notes a population-weight regime based on the SUPAS 2015 projection for 2018–2021. The selected values are still direct official observations, but cross-regime comparability is not asserted until the post-2021 weighting lineage is separately qualified.

### Labor-force participation — TPAK

The API variable itself has a blank unit field, so the pipeline does not infer the unit from the magnitude of the numbers. Official BPS indicator metadata defines TPAK as labor force divided by working-age population multiplied by 100, with unit percent.

The selected district/city family is treated as August Sakernas for the same estimation-level reason as TPT. Cross-regime comparability remains unresolved where source weighting changes are not fully documented.

### Internet access candidate

BPS variable 320 measures **persons age 5+ who accessed the internet during the previous three months**, with selected sub-variable `turvar=595` (`Pernah Mengakses Internet`).

The current canonical indicator is named *Household internet access* and its definition permits household or person source concepts only when the source definition is explicit. This first pass chooses the conservative option: variable 320 remains source-native and is **not promoted** until the ontology explicitly distinguishes the person-level measure or a household-level source is qualified.

No household value is imputed from the person-level percentage.

### Expected years of schooling — HLS

The BPS HDI methodology interprets HLS for age 7. Official HDI material identifies HLS/RLS as sourced from Susenas March. Canonical observations therefore use March as the reference period and unit `years`.

### Mean years of schooling — RLS

The BPS HDI methodology interprets RLS for population age 25+. Official HDI material identifies the source as Susenas March. The age universe is retained in the qualification record and canonical observations use unit `years`.

### Life expectancy — UHH

Variable 752 is explicitly the **Long Form SP2020** life-expectancy method. It is not chained silently to the older SP2010-projection-based variable 362.

The first canonical family starts in 2020 and stores the LF-SP2020 method as `methodology_version`.

### Poverty headcount

BPS variable 34 reports the percentage of population below the official poverty line. Its own source note states that 2015 onward uses the **March condition**, so the 2018–2025 canonical family uses March reference dates.

### Real GRDP growth

Variable 138 is district/city real GRDP growth under constant 2010 prices. Official BPS tables establish unit percent, and the source note distinguishes release status:

- 2024 — very provisional;
- 2025 — very-very provisional.

Canonical observations retain `price_basis=constant_2010` and those year-specific release flags. Revisions must be detected rather than silently replacing the reviewed baseline.

## Canonical observation layer

`scripts/build_bps_canonical_panel.py` promotes only source families whose qualification decision is `canonical_ready`.

The canonical artifact contains:

- observations matching the data-foundation indicator/geography/time/provenance contract;
- separate provenance rows linked to exact source snapshot checksums;
- explicit source release (`last_update`);
- reference-month/year bounds;
- methodology version;
- price basis where relevant;
- release-status and source-universe notes.

The person-level internet family is excluded by construction.

The reviewed first canonical build is expected to contain:

- **1,080 observations**;
- **54 provenance records** — one per promoted source family/period snapshot;
- **7 canonical indicator families**;
- **20 canonical geographies**.

`scripts/validate_bps_canonical_panel.py` enforces those invariants and checks units, reference dates, methodology labels, GRDP provisional flags, provenance resolution, and the internet exclusion.

## Semantic drift protection

Raw JSON snapshot checksums change when the snapshot envelope changes, including retrieval timestamps. That is useful for exact-byte provenance but noisy for source revision detection.

The source panel therefore also computes a **semantic fingerprint** that excludes only:

- `retrieved_at_utc`;
- source snapshot filename;
- source snapshot checksum.

It still includes source values, source IDs/labels, variable definition/note, BPS `last_update`, geography mappings, and qualification/promotion state.

The reviewed qualification baseline has semantic fingerprint:

`823a9c540e368df273fdddb5cd87855cb63dba278acfea95c16f8f865da074e5`

and is recorded in:

`data/manifests/bps_panel_baseline.json`

A fresh harvest is compared against that baseline. A changed value, source metadata revision, changed period membership, changed source release, changed qualification state, or changed mapping causes the drift gate to fail until the change is explicitly reviewed and the baseline is updated.

This is intentionally different from treating the latest API response as automatically correct for the longitudinal research dataset.

## Data retention policy

Credential-free live snapshots and generated panels are uploaded as short-lived GitHub Actions artifacts. The repository commits the durable contracts needed to reproduce and review the panel:

- source selection registry;
- qualification registry;
- geography mapping registry;
- source/client/normalization code;
- semantic baseline and acquisition provenance;
- tests and validators.

Large batches of raw API snapshots are not committed merely to create Git history volume. A small historical snapshot may still be committed when it is itself a deliberately frozen historical evidence artifact, as with the 1971 census anchor.

## What this panel does not establish

This phase does not yet establish:

- causality;
- a “wasted potential” estimate;
- historical continuity back to independence;
- comparability of labor estimates across every weighting redesign;
- a household-level internet series;
- GRDP continuity across other base-year regimes;
- health/disaster/climate/fiscal series outside the qualified BPS families.

Those are later evidence layers.

## Exit gate

This phase is ready to merge when:

1. all offline panel validators and unit tests pass;
2. a fresh credentialed BPS harvest reproduces the reviewed semantic fingerprint;
3. the generated source-native panel has 1,240 rows and 20 canonical geographies;
4. the generated canonical artifact passes the 1,080-observation / 54-provenance contract;
5. exactly seven source families are canonical-ready and the person-level internet family remains explicitly held;
6. source drift causes CI failure rather than silent replacement;
7. PR review has no unresolved blockers.
