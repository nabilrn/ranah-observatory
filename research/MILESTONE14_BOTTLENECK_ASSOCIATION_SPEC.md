# Milestone 14 — Bottleneck Association Engine Specification

## Phase 2 role

Milestone 14 begins answering the question that Milestone 13 deliberately leaves open:

> Which measurable structural/capability variables are stably associated with adverse development-gap signals across current West Sumatra kabupaten/kota?

M14 is an **association engine**, not a causal engine. It does not identify policy effects, treatment effects, structural parameters, technical inefficiency, or monetary wasted potential.

## Upstream evidence

Primary inputs are frozen Phase 2 outputs:

1. `data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv`
2. `data/analysis/engine/panel_v1/m10-panel-wide.csv`

M13 supplies three parallel adverse-gap targets:

- poverty-rate gap — living standards/inclusion;
- unemployment-rate gap — labor market;
- real-GRDP-growth gap — economic dynamism.

For M14 the primary gap object is M13 `expected_gap_rmse_units`, which is already oriented so that **positive = observed performance is less favorable than the M11 conditional expectation**.

The M12 favorable-peer gap is retained only as a labelled sensitivity because it measures distance from an intentionally ambitious favorable reference rather than ordinary conditional underperformance.

## Circularity guard

M11 built its expected-performance model from exactly five lagged structural features:

- mean years schooling;
- labor-force participation;
- agriculture share of GRDP;
- manufacturing share of GRDP;
- rice yield.

M14 does **not** use these same five variables as primary bottleneck candidates. Regressing M11 residuals back on the variables used to construct M11 expectations would create a mechanically residualized diagnostic and could be misleadingly interpreted as a bottleneck test.

Primary M14 candidates therefore come only from qualified M10 variables that were not in the M11 primary feature set.

## Locked primary candidate set

Candidate values are measured at `target_year - 1`.

### Core candidate A — expected years of schooling

`expected_years_schooling`

Interpretation: forward-looking education-system participation/capability proxy distinct from the M11 stock variable `mean_years_schooling`.

Caveat: it is adjacent to mean years schooling and therefore should not be interpreted as an independent causal education channel.

### Core candidate B — underemployment rate

`underemployment_rate`

Interpretation: labor-utilization stress proxy.

Target-specific rule:

- eligible for poverty-gap association;
- eligible for real-GRDP-growth-gap association;
- **excluded from the primary unemployment-gap screen** because it is another closely related labor-market outcome.

An unemployment-gap association with underemployment may be reported only as an explicitly outcome-adjacent sensitivity, never as a primary bottleneck signal.

### Core candidate C — annual rainfall

`annual_rainfall`

Interpretation: annual hydroclimate context from CHIRPS v3 Final.

Claim type remains `model_estimate`. It is not BMKG station observation and does not represent event-day rainfall.

### Health extension — life expectancy

`life_expectancy`

Qualified district/city coverage begins in 2020. Therefore lagged life expectancy supports only target years 2021–2024.

It is analyzed as a **health-extension screen**, not mixed into the full-window core model.

## Explicit exclusions

M14 primary association screening excludes:

- the M11 five-feature structural set listed above;
- poverty, unemployment, or growth as explanatory variables for their own gap;
- contemporaneous target-year candidate values;
- population because M10 contains only the SP2020 anchor rather than an annual district/city population series;
- flood and landslide event counts because qualified district/city coverage is 2024 only;
- any variable added after inspecting M14 association signs or permutation results.

## Primary analytical frame

Target years: 2019–2024.

For every target-geography-year row:

- gap year = `target_year`;
- candidate year = `target_year - 1`;
- target must be `m11_benchmark_qualified=true`;
- primary screen requires `m11_support_warning=false`;
- no missing candidate value;
- no imputation.

Rows outside M11 marginal support remain in an explicit all-row sensitivity but cannot drive the primary association classification.

## Association statistics

M14 intentionally starts with transparent low-capacity diagnostics rather than SHAP or black-box feature importance.

For each target × candidate pair report:

1. **within-year Pearson association**
   - demean candidate and gap within target year;
   - pool the demeaned rows;
   - calculate Pearson correlation.

2. **within-year rank association**
   - rank candidate and gap within each target year using average ranks for ties;
   - center ranks within year;
   - calculate pooled Pearson correlation of centered ranks;
   - this is the primary nonparametric stability statistic.

3. **geography-block permutation p-value**
   - permute the geography identities of the entire candidate trajectory while preserving each geography's time profile;
   - use a fixed pseudo-random seed `140014`;
   - use 4,999 permutations;
   - two-sided p-value based on absolute within-year rank association;
   - permutation results quantify how unusual the observed alignment is under this restricted null, not causal significance.

4. **leave-one-geography-out stability**
   - recompute the within-year rank association after excluding each of the 19 geographies;
   - report min, max, median, and proportion retaining the full-sample sign.

5. **leave-one-year-out stability**
   - recompute after excluding each supported target year;
   - report min, max, median, and sign-retention proportion.

## Pre-locked association-signal classification

A target × candidate pair receives `stable_association_signal=true` only when all of the following are satisfied in the primary support-clean frame:

- absolute within-year rank association >= `0.20`;
- geography-block permutation two-sided p <= `0.10`;
- leave-one-geography-out sign retention >= `0.90`;
- leave-one-year-out sign retention >= `0.80`;
- at least 4 target years represented;
- at least 60 geography-year rows represented.

These thresholds are screening rules, not scientific laws. They are frozen before M14 outputs are inspected.

A stable association signal means only:

> this candidate co-moves with the adverse gap in a reasonably stable way under the preregistered descriptive diagnostics.

It does **not** mean the candidate causes the gap.

## Direction semantics

Because M13 gap orientation is always positive = less favorable performance:

- positive association → higher candidate values align with larger adverse gaps;
- negative association → higher candidate values align with smaller adverse gaps.

No direction may be relabeled as "good" or "bad" without substantive context.

## Sensitivities

### Support sensitivity

Repeat the association statistics using all benchmark-qualified rows including M11 support-warning rows. These results cannot replace the primary support-clean classification.

### Favorable-peer-gap sensitivity

For rows where M13 `gap_interpretation_authorized=true`, repeat within-year rank associations using `favorable_peer_gap_rmse_units`.

This remains an ambitious-reference sensitivity and must not be conflated with expected underperformance.

### Outcome-adjacent underemployment sensitivity

For unemployment only, underemployment may be shown in a separate sensitivity table with `outcome_adjacent=true` and `stable_association_signal_authorized=false` regardless of its numerical result.

## Why no SHAP in v1

The core support-clean sample is small and clustered: at most 19 geographies × 6 years per target, with fewer rows after support filtering. M14 v1 therefore does not justify training a flexible black-box model merely to produce SHAP rankings.

SHAP, partial dependence, or accumulated-local-effects diagnostics may be added in a later M14 revision only if a genuinely benchmarked predictive association model provides incremental validated performance and sample/support conditions justify it.

## Required outputs

1. `data/analysis/engine/bottleneck_association_v1/m14-association-screen.csv`
2. `data/analysis/engine/bottleneck_association_v1/m14-geography-loo.csv`
3. `data/analysis/engine/bottleneck_association_v1/m14-year-loo.csv`
4. `data/analysis/engine/bottleneck_association_v1/m14-favorable-peer-sensitivity.csv`
5. `data/analysis/engine/bottleneck_association_v1/m14-outcome-adjacent-sensitivity.csv`
6. `data/manifests/milestone14_bottleneck_association.json`

## Completion gate

M14 completes when:

- primary candidates are fixed before association outputs are inspected;
- candidate values are lagged exactly one year;
- M11 structural features are excluded from primary screening;
- primary screening is support-clean and benchmark-qualified;
- all preregistered target-candidate pairs are present, including negative/null results;
- geography-block permutation uses the locked seed and 4,999 permutations;
- geography and year leave-one-out diagnostics are complete;
- support-warning, favorable-peer, health-extension, and outcome-adjacent sensitivities remain separately labeled;
- no causal, technical-efficiency, policy-counterfactual, or monetary-wasted-potential claim is emitted;
- focused tests pass;
- permanent read-only CI rebuilds committed outputs byte-for-byte;
- M10–M13 and the 9/9 Research Foundation remain green.

## Forbidden interpretations

M14 does not authorize statements such as:

- "feature X causes poverty/unemployment/growth";
- "feature X is the bottleneck that policy should fix first";
- "changing X by one unit will close Y units of gap";
- "feature importance proves mechanism";
- "a stable association is a causal effect";
- "the gap associated with X is wasted potential in rupiah".

M14 is an evidence-ranking layer for later causal investigation, not the causal evidence itself.
