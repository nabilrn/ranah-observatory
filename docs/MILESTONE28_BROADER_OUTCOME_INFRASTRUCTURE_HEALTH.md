# Milestone 28 — Broader Outcome, Infrastructure, Health, and Demographic Evidence

Status: **complete; M23 Tier-B priority #5 closed**.

Milestone 28 broadens the existing current-boundary Sumatera Barat analytical regime without shortening the 2018–2025 window or manufacturing a balanced panel. It qualifies additional BPS district/city evidence in economic level, health, infrastructure/basic services, and demographic structure, then integrates that evidence into a separate Panel v2 while preserving the original M10 panel unchanged.

## Final promoted evidence

Seven source families qualify for bounded numeric use:

1. **real GRDP per capita, constant 2010 prices** — BPS variable 169;
2. **morbidity rate** — variable 547;
3. **JKN membership coverage** — variable 763;
4. **internet access among persons age 5+ in the previous three months** — variable 320;
5. **adequate sanitation access** — variable 341;
6. **adequate drinking-water access** — variable 352;
7. **dependency ratio** — variable 756.

A household-lighting candidate, variable 337, is explicitly held. The source exposes PLN electricity, non-PLN electricity, and non-electricity categories but no source-native total-electricity-access selector. M28 therefore does not sum PLN and non-PLN or relabel either category as household electricity access.

## Acquisition result

The Stage 2A preregistered 2024 numeric pilot qualifies all seven retained series across all 19 current kabupaten/kota, producing exactly **133 observations** with zero geography, selector, unit, duplicate, or range failures.

The subsequent bounded history covers 56 possible series-year cells over 2018–2025. Exactly **49 series-year requests** are authorized by the source/methodology contracts. All 49 qualify, producing **931 observations**. The remaining seven series-year cells remain explicit structured missingness rather than being requested, imputed, or zero-filled.

Structured missing series-years are:

- real GRDP per capita: 2025;
- morbidity: 2025;
- JKN membership coverage: 2018;
- adequate drinking-water access: 2018;
- dependency ratio: 2018, 2019, and 2025.

Internet access and adequate sanitation are fully populated for all 19 geographies across 2018–2025.

## Methodology boundaries retained

### Adequate drinking-water access

BPS metadata states that the SDGs-aligned concept is used from 2019 and that 2019–2020 are backcast data. Therefore:

- 2018 is excluded from the promoted SDGs-aligned series;
- 2019–2020 remain `backcast_estimate`;
- 2021–2025 remain source observations under the qualified SDGs-aligned definition.

Adequate drinking-water source access must not be described as piped-water service.

### Dependency ratio

BPS metadata separates the source regime:

- 2020 is the Long Form SP2020 anchor and remains `observed_census_anchor`;
- 2021–2024 are population-projection values and remain `model_estimate_projection`.

Projection years are never relabeled observed.

### Real GRDP per capita

Variable 169 uses source-local ordinal geography identifiers rather than global BPS administrative codes. M28 freezes an explicit 19-row local-ID-plus-label mapping. This representation is qualified only for variable 169, and every numeric year revalidates the exact local ordinal and source label before promotion. Source aggregate rows are excluded.

## Offline reproducibility

All 49 frozen Stage 2B dynamic snapshots are checksum-verified and replayed without network access. The offline rebuild regenerates the canonical observations, provenance, audit, and coverage products byte-for-byte.

Certified result:

- 49 frozen snapshots verified;
- 49 series-year cells replayed;
- 49 series-year cells qualified;
- 7 structured-missing series-years retained;
- 931 observations regenerated;
- all four canonical Stage 2B outputs byte-identical.

## Panel v2 integration

M28 does **not** overwrite M10. It creates a separate widened analytical substrate under the same `sumbar_current_kabkota_2018_2025_v1` geography/year regime.

Panel v2 contains:

- 19 current kabupaten/kota;
- 8 analytical years, 2018–2025;
- 152 geography-year rows;
- 22 indicators: 15 from M10 plus 7 from M28;
- 2,679 present geography-year-indicator observations;
- 3,344 possible cells;
- 665 explicit missing cells;
- zero duplicate geography-year-indicator keys.

All **1,748 M10 long rows are preserved field-for-field**, while all **931 M28 values, units, claim types, and methodology regimes are preserved**. The number of indicators complete across the full 2018–2025 window increases from eight to **ten**, with internet access and adequate sanitation joining the eight M10 balanced indicators.

## Scientific claim boundary

M28 is an evidence acquisition, qualification, and harmonization milestone. It does **not** perform:

- imputation or missing-as-zero;
- global window shortening;
- cross-year or cross-indicator aggregation;
- statistical or machine-learning model fitting;
- causal inference;
- policy or intervention ranking;
- monetary wasted-potential estimation.

The new variables enlarge the substrate for later bounded analysis; they do not by themselves establish why Sumatera Barat underperforms or how much economic potential is lost.

## Canonical outputs

Stage 2B evidence:

- `data/analysis/engine/broader_panel_v1/m28-broader-panel-observations.csv`
- `data/analysis/engine/broader_panel_v1/m28-broader-panel-provenance.csv`
- `data/analysis/engine/broader_panel_v1/m28-full-history-audit.csv`
- `data/analysis/engine/broader_panel_v1/m28-indicator-year-coverage.csv`
- `data/manifests/milestone28_stage2b_full_history.json`
- `data/manifests/milestone28_stage2b_offline_reproducibility.json`

Integrated analytical substrate:

- `data/analysis/engine/panel_v2/m28-panel-long.csv`
- `data/analysis/engine/panel_v2/m28-panel-wide.csv`
- `data/analysis/engine/panel_v2/m28-indicator-coverage.csv`
- `data/analysis/engine/panel_v2/m28-indicator-metadata.csv`
- `data/manifests/milestone28_panel_integration.json`
- `data/manifests/milestone28_completion.json`

## Next project gate

The evidence layer is now broad enough for a bounded **v0.1 publication freeze**. M23 Tier-B priority #6, BMKG station/daily climate validation, remains scientifically valuable but is not a completion dependency for the first technical report/preprint. It can proceed after or alongside the publication package rather than delaying publication indefinitely.
