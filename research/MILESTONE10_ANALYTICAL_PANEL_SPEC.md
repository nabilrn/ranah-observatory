# Milestone 10 — Analytical Panel v1 Specification

## Phase 2 role

Milestone 10 is the first milestone of the Final Analytical Research Engine.

It does **not** estimate expected performance, a frontier, causal effects, development gaps, or intervention impacts. Its job is to create a trustworthy analysis-ready substrate from already-qualified canonical evidence.

## Analysis regime

`sumbar_current_kabkota_2018_2025_v1`

- Geography: exact 19 current West Sumatra kabupaten/kota canonical geographies.
- Years: 2018–2025 inclusive.
- Frequency: annual analytical indexing.
- Boundary interpretation: current-boundary analytical regime only.
- Historical continuity: **not claimed**.

`analysis_year` is derived from each source observation's `time_start` year. The original `time_start`, `time_end`, and source methodology remain attached to the long-form observation. Therefore a March Susenas observation, August Sakernas observation, calendar-year GRDP observation, and annual CHIRPS observation may share an `analysis_year` while retaining distinct source reference periods.

## Qualified source inputs

Only already-canonicalized evidence may enter M10:

1. `data/processed/bps/panel/bps-canonical-observations.csv`
2. `data/processed/bps/expansion/bps-expansion-canonical-observations.csv`
3. `data/processed/climate/rainfall/chirps-annual-rainfall-observations.csv`
4. `data/processed/bnpb/disaster/bnpb-disaster-canonical-observations.csv`
5. `data/registries/geographies.csv`
6. `data/registries/indicators.csv`

Held/source-native rows are excluded unless separately promoted in a later qualification milestone.

## Preregistered indicator set

### BPS longitudinal/social-economic panel

- `expected_years_schooling`
- `mean_years_schooling`
- `life_expectancy`
- `labor_force_participation`
- `unemployment_rate`
- `poverty_rate`
- `real_grdp_growth`

### BPS structural/agricultural/demographic expansion

- `agriculture_share_grdp`
- `manufacturing_share_grdp`
- `rice_yield`
- `underemployment_rate`
- `population_total`

`population_total` is expected to be sparse because the currently qualified district/city observation is the SP2020 census anchor. M10 must preserve that sparsity and must not interpolate population between years.

### Climate and disaster context

- `annual_rainfall`
- `flood_events`
- `landslide_events`

CHIRPS `annual_rainfall` remains `model_estimate` evidence with station-observation equivalence explicitly false/pending independent station validation.

BNPB disaster counts remain observed **recorded-event counts**, not unique affected-person counts and not proof that an unrecorded event did not occur.

## Explicit exclusions

M10 must not import the following into this current-kabupaten/kota analytical panel:

- province-only `gini_ratio` rows;
- province-only export-value rows;
- the national 38-province comparative panel as if it were the same geography regime;
- M8 ADHK-2000 historical GRDP as if it were continuous with the modern ADHK-2010 series;
- historical source-era geography observations;
- held source-native observations;
- reconstructed values created only to fill gaps.

## Output products

M10 produces four analytical views plus one manifest:

1. `data/analysis/engine/panel_v1/m10-panel-long.csv`
   - one row per available `geography_id × analysis_year × indicator_id`;
   - retains source observation ID, provenance ID, claim type, unit, reference dates, comparability, methodology version, price basis, and source artifact path.

2. `data/analysis/engine/panel_v1/m10-panel-wide.csv`
   - exact `19 geographies × 8 years = 152 rows`;
   - one value column for each of the 15 preregistered indicators;
   - missing cells remain empty.

3. `data/analysis/engine/panel_v1/m10-indicator-coverage.csv`
   - coverage counts and rates over the 152-cell geography-year universe;
   - first/last year;
   - years represented;
   - years with exact 19-geography coverage;
   - missing-cell count;
   - units, claim types, methodology versions, and source reference-period patterns encountered.

4. `data/analysis/engine/panel_v1/m10-indicator-metadata.csv`
   - registry definition/domain plus M10 source assignment and semantic cautions.

5. `data/manifests/milestone10_analytical_panel.json`
   - source and output SHA-256 checksums;
   - exact geography/year/indicator footprint;
   - integrity diagnostics;
   - explicit non-imputation/non-harmonization flags.

## Integrity rules

M10 fails closed if any of the following occur:

1. the canonical geography registry does not yield exactly 19 current West Sumatra kabupaten/kota;
2. the wide view is not exactly 152 geography-year rows;
3. the preregistered indicator set is not exactly 15 indicators;
4. a source produces duplicate `geography_id × analysis_year × indicator_id` rows;
5. a selected row has no `observation_id` or `provenance_id`;
6. source values are non-finite when present;
7. a source indicator is silently relabelled to another indicator;
8. a missing cell is filled by interpolation, forward-fill, backward-fill, zero-fill, or model prediction;
9. province aggregates or historical geography versions enter the 19-kabupaten/kota panel;
10. CHIRPS is relabelled as station observation;
11. BNPB zero counts are generalized into a claim of no physical disaster occurrence;
12. source/output checksums or deterministic rebuilds drift.

## Missingness rule

Missingness is an analytical object, not an inconvenience.

M10 may report coverage and downstream eligibility diagnostics, but it does not choose an imputation method. Any later imputation or balanced-panel restriction requires its own preregistered downstream rule.

## Claim rule

M10 creates **derived analytical views** only. It does not upgrade the claim strength of source observations.

- `observed` stays observed;
- `derived` stays derived;
- `model_estimate` stays model estimate.

No causal, frontier, counterfactual, or monetary wasted-potential claim is authorized.

## Completion gate

Milestone 10 is complete when:

- exact 19 × 8 wide geography-year frame exists;
- all 15 preregistered indicators are represented in the coverage/metadata layer, including sparse indicators;
- long-form lineage is complete;
- duplicate key count is zero;
- no imputation/historical harmonization occurred;
- source and output hashes are recorded;
- focused tests pass;
- permanent read-only CI reproduces the committed outputs byte-for-byte;
- existing Research Foundation audits remain green.
