# Milestone 13 — Development Gap Decomposition v1

## Purpose

Milestone 13 turns two separate Phase 2 references into a multidimensional diagnostic:

1. **M11 conditional expectation** — ordinary peer-conditioned expected performance;
2. **M12 empirical favorable-peer reference** — deliberately ambitious favorable-decile / structural-neighbor performance.

The distinction is central. Being below a favorable top-decile reference is not the same thing as performing unexpectedly poorly.

M13 therefore keeps poverty, unemployment, and real-GRDP growth as three parallel dimensions and does not produce a weighted "Sumbar development score".

## Locked dimensions

| Dimension | Target | Favorable direction |
|---|---|---|
| Living standards / inclusion | poverty rate | lower |
| Labor market | unemployment rate | lower |
| Economic dynamism | real GRDP growth | higher |

District/city scope is exact 19 current West Sumatra kabupaten/kota over 2019–2024.

The national real-GRDP-per-capita anchor remains a separate province-level object.

## Gap orientation

Every M13 gap is oriented consistently:

> **positive = observed performance is less favorable than the relevant reference.**

### Expected gap

For poverty/unemployment:

`observed - M11 expected`

For growth:

`M11 expected - observed`

### Favorable-peer gap

M12 already supplies a signed distance with the same favorable orientation.

Both the primary M12 residual-quantile reference and the alternative structural-neighbor reference remain visible.

## Standardized diagnostic scale

Native percentage-point units differ across poverty, unemployment, and growth. M13 therefore also divides each gap by the relevant target's M11 cross-fitted RMSE.

For example:

`favorable_peer_gap_rmse_units = favorable_peer_gap / M11_target_RMSE`

This is only a predictive-error scale. It is not a utility function and M13 never sums RMSE-unit gaps across targets.

## Expected-performance interval result

Across all 342 target-geography-year rows:

- **313** are within the M11 focal-excluded empirical expected interval;
- **15** are materially less favorable than that interval;
- **14** are materially more favorable than that interval.

This means the large majority of observations are not extreme surprises relative to the ordinary conditional expectation.

## Favorable-peer persistence result

M13 also asks a different question: among rows with enough M12 support, how often is the observed outcome less favorable than the M12 favorable-peer reference?

Across the 57 geography-target persistence series (`19 × 3`), locked persistence labels currently produce:

- 37 `persistent_less_favorable_than_favorable_reference`;
- 3 `mixed_relative_to_favorable_reference`;
- 2 `mostly_meets_or_exceeds_favorable_reference`;
- 15 `insufficient_supported_years`.

### Why 37 persistent series is NOT evidence that 37 dimensions are "failing"

The M12 primary reference was deliberately calibrated around a favorable **top/bottom decile** of conditional peer performance. Most ordinary observations should therefore be less favorable than that reference.

A persistent favorable-peer gap means:

> the geography repeatedly did not match an ambitious empirical favorable-peer reference in supported years.

It does **not** mean:

- the geography performed unexpectedly badly;
- the gap is technically inefficient;
- the favorable reference was feasible under a specific policy;
- the geography "lost" the arithmetic difference.

The expected-interval classification is the more appropriate object for identifying performance that is unusually weak/strong relative to M11 conditional expectation.

## Persistence rule

A persistence label is issued only if at least 4 of 6 rows are authorized by M12 support/calibration gates.

Among authorized years:

- positive favorable-peer gap rate >= 2/3 → `persistent_less_favorable_than_favorable_reference`;
- positive gap rate <= 1/3 → `mostly_meets_or_exceeds_favorable_reference`;
- otherwise → `mixed_relative_to_favorable_reference`;
- fewer than four authorized years → `insufficient_supported_years`.

These thresholds were frozen before persistence outputs were inspected.

## Support and method disagreement

M13 inherits M11/M12 support rather than hiding it.

Current footprint:

- 342 total gap rows;
- 243 primary favorable-peer rows authorized for substantive interpretation;
- 99 rows blocked, primarily because the focal feature profile falls outside at least one same-year M11 marginal support range.

Primary and structural-neighbor favorable-gap signs agree in 292 of 342 rows and disagree in 50. Disagreement is preserved as a method-uncertainty signal.

## Geography profiles

The geography profile table has one row per current kabupaten/kota. It places the three target diagnostics beside one another.

It includes only counts such as:

- persistent target count;
- mostly-meets/exceeds target count;
- mixed target count;
- insufficient-support target count.

The following columns are intentionally blank:

- `weighted_composite_score`;
- `cross_target_rank`.

M13 does not authorize a league table from these counts.

## National income/productivity anchor

M13 separately carries the M12 national 2024 Sumatera Barat reference:

- observed real GRDP/capita: about Rp34.17m/person ADHK 2010;
- M7 conditional expected context: about Rp36.34m/person;
- M12 favorable-peer reference: about Rp66.74m/person.

The arithmetic observed-vs-expected and favorable-reference-vs-observed differences remain context only.

They are not:

- causal losses;
- technical inefficiency;
- theoretical maximum gaps;
- population-aggregated "wasted potential";
- multi-year accumulated losses.

The province income anchor is not numerically combined with district poverty, unemployment, or growth gaps.

## Outputs

- `data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv`
- `data/analysis/engine/gap_decomposition_v1/m13-persistence-by-geography-target.csv`
- `data/analysis/engine/gap_decomposition_v1/m13-geography-profiles.csv`
- `data/analysis/engine/gap_decomposition_v1/m13-national-income-anchor.json`
- `data/manifests/milestone13_development_gap_decomposition.json`

## Downstream implication

M13 identifies **where** gap signals persist and how they differ between an ordinary conditional expectation and an ambitious favorable-peer reference.

It still does not answer **why** those gaps occur.

That is the purpose of Milestone 14: Bottleneck Association Engine. M14 may study stable associations between structural variables and gap signals, but feature importance or regression coefficients remain non-causal unless a later causal design supports that interpretation.
