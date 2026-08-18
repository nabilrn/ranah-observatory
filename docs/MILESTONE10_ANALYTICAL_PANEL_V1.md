# Milestone 10 — Analytical Panel v1

## Purpose

Milestone 10 starts Phase 2, the Final Analytical Research Engine, by creating the first analysis-ready current-boundary West Sumatra kabupaten/kota substrate from already-qualified evidence.

It does **not** fit a model. The panel is deliberately designed to make missingness, source timing, methodology, claim type, and geography regime visible before downstream modelling begins.

## Regime

`sumbar_current_kabkota_2018_2025_v1`

- 19 current West Sumatra kabupaten/kota;
- 2018–2025;
- 8 annual analytical years;
- 152 exact geography-year rows in the wide view;
- no historical-boundary continuity claim.

## Inputs

Only qualified canonical observation products are used:

- BPS canonical panel;
- BPS expansion canonical panel;
- CHIRPS v3 Final annual rainfall materialization;
- BNPB 2024 flood/landslide canonical event counts.

Province-only or held source-native rows are excluded.

## Indicator footprint

Fifteen indicators are registered in the panel.

### Fully balanced across 2018–2025

Eight indicators have exact 19-geography coverage in all eight years:

1. expected years of schooling;
2. mean years of schooling;
3. labor-force participation;
4. unemployment rate;
5. poverty rate;
6. real GRDP growth (ADHK 2010);
7. rice yield;
8. annual rainfall (CHIRPS model estimate).

### Structured missingness retained

- life expectancy: 2020–2025;
- agriculture share of GRDP: 2018–2023;
- manufacturing share of GRDP: 2018–2023;
- underemployment rate: 2018–2024;
- population: SP2020 census anchor only;
- flood events: BNPB 2024 only;
- landslide events: BNPB 2024 only.

These gaps are not filled.

## Materialized footprint

- 15 indicators;
- 152 wide geography-year rows;
- 2,280 possible geography-year-indicator cells;
- 1,748 available canonical values;
- 532 explicit missing cells;
- zero duplicate geography-year-indicator keys;
- zero suppressed rows selected.

## Reference-period semantics

`analysis_year` is only an analytical index.

The long view preserves the original source reference period:

- HDI/education and poverty series retain March reference semantics where applicable;
- Sakernas labor indicators retain August reference semantics;
- SP2020 population retains September census-reference semantics;
- GRDP, rice, rainfall, and BNPB event counts retain their annual/calendar-year source periods.

Therefore two values sharing `analysis_year=2024` are not automatically observations from the same date.

## Claim-type semantics

No source claim is upgraded by panel construction.

- BPS observed data remain `observed`;
- source-derived BPS structural shares/rice yield remain `derived`;
- CHIRPS rainfall remains `model_estimate` and is not claimed to equal BMKG station observation;
- BNPB values remain observed recorded-event counts.

## Outputs

- `data/analysis/engine/panel_v1/m10-panel-long.csv`
- `data/analysis/engine/panel_v1/m10-panel-wide.csv`
- `data/analysis/engine/panel_v1/m10-indicator-coverage.csv`
- `data/analysis/engine/panel_v1/m10-indicator-metadata.csv`
- `data/manifests/milestone10_analytical_panel.json`

The long view is authoritative for lineage. The wide view is a convenience matrix for future modelling and must always be interpreted with the metadata/coverage products.

## What M10 tells the next milestone

M10 reveals that the repository already contains a useful dense modern district/city panel, but there is no single 2018–2025 matrix containing every desired structural, demographic, disaster, and health variable.

That is analytically important:

- an 8-year fully balanced core exists for eight indicators;
- a richer structural view exists for 2018–2023;
- a richer health-inclusive view exists from 2020 onward;
- population and disaster data currently behave as anchors/context rather than annual longitudinal controls.

Milestone 11 must preregister its modelling window and feature eligibility **before** looking at target residuals or model performance. M10 does not choose the modelling window on its behalf.

## Reproduction

```bash
python -m scripts.build_milestone10_analytical_panel
python -m scripts.audit_milestone10_analytical_panel --require-complete
python -m unittest tests.test_milestone10_analytical_panel -v
```

Permanent read-only CI must rebuild the panel and require byte-identical committed outputs.
