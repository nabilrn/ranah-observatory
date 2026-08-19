# Milestone 24 — BPS Stable-32 Province Comparator Panel Specification

## Purpose

M24 attempts to expand Ranah Observatory's comparison universe from the 19 current West Sumatra kabupaten/kota modern panel into a **longer, nationally comparable province-level regime** that can support RQ2/RQ3 and later model validation.

The design deliberately avoids silent harmonization across the 2022 Papua provincial division.

## Geography regime

M24 uses exactly **32 current Indonesian provinces** whose province boundaries are treated as stable for the 2018–2025 comparison window under this project contract.

The six current Papua-region provinces are excluded from the longitudinal panel:

- BPS code 91 — Papua Barat;
- 92 — Papua Barat Daya;
- 94 — Papua;
- 95 — Papua Selatan;
- 96 — Papua Tengah;
- 97 — Papua Pegunungan.

The exclusion prevents pre- and post-DOB values from being silently treated as the same current geography. M24 does not reconstruct historical Papua boundaries.

The remaining 32 current provinces must be present in every qualified indicator-year cell.

## Source

Official BPS WebAPI national domain `0000`, accessed only through the repository `BPS_API_KEY` secret in GitHub Actions.

Raw API credentials are never written to repository artifacts.

## Locked candidate series

M24 starts from the six selectors already qualified by the existing current-38 comparative-panel lane:

1. poverty rate — variable 192, March total, `turvar=434`, `turtahun=61`;
2. Gini ratio — variable 98, March urban+rural, `turvar=191`, `turtahun=61`;
3. unemployment rate — variable 543, August, `turvar=0`, `turtahun=190`;
4. underemployment rate — variable 1181, source annual period, `turvar=0`, `turtahun=0`;
5. real GRDP per capita — variable 288, constant 2010 price component, `turvar=531`, `turtahun=0`;
6. NEET rate — variable 1186, source annual period, `turvar=0`, `turtahun=0`.

The target discovery window is 2018–2025 inclusive.

No series is allowed to change selector after seeing coverage results merely to improve completeness.

## Stage 1 — credentialed structural probe

Before source materialization, M24 runs a credentialed read-only probe for every candidate-year.

For each candidate and year the probe must record:

- whether the requested annual BPS period exists;
- source variable title/unit/note;
- vertical geography dimension;
- whether the locked derived-variable and derived-period selector exists;
- selected-row count after exact selector filtering;
- coverage of the exact stable-32 BPS province codes;
- any missing stable-32 codes;
- any unexpected selected current province codes;
- BPS source update metadata;
- a semantic digest of the returned API payload.

A candidate is `stable32_2018_2025_probe_qualified` only if **all eight years**:

1. are available;
2. retain the exact locked selector labels/IDs;
3. expose province as the vertical geography;
4. contain exactly one selected row for every stable-32 province;
5. contain finite numeric values;
6. preserve the expected source unit contract where one was previously qualified.

Candidate failure is retained. M24 may complete with fewer than six qualified indicators.

## Stage 2 — source freeze and canonical panel

Only probe-qualified candidates may be harvested/frozen.

For every qualified candidate-year, M24 stores credential-free snapshots/checksums and normalized source-native rows, then builds a canonical stable-32 panel.

The canonical panel must retain:

- source-native BPS code and label;
- canonical province ID/name;
- exact year and reference period;
- source selector contract;
- source unit and deterministic transform;
- claim type;
- methodology/version label;
- provenance to a frozen snapshot checksum.

No imputation or geographic aggregation/disaggregation is allowed.

## Comparability boundary

M24 is a **province-level** regime and must not be pooled blindly with M10's kabupaten/kota rows in one model.

It can support:

- national province comparison and RQ3 divergence evidence;
- province-level attainable-performance experiments where features/outcomes share this regime;
- external validation concepts separated from the district/city model.

It does not automatically enlarge M11's district/city training sample.

## Required outputs

Stage 1:

1. `data/manifests/milestone24_bps_stable32_probe.json`
2. `data/analysis/engine/bps_stable32_v1/m24-probe-coverage.csv`

If at least one candidate qualifies, Stage 2 additionally requires:

3. `data/processed/bps/comparative_stable32/source/*` credential-free frozen artifacts;
4. `data/processed/bps/comparative_stable32/bps-stable32-canonical-observations.csv`;
5. `data/processed/bps/comparative_stable32/bps-stable32-provenance.csv`;
6. `data/processed/bps/comparative_stable32/bps-stable32.manifest.json`.

## Completion gate

M24 completes as a discovery milestone when the full six-series × eight-year probe is finished and evidence-qualified/held statuses are explicit.

The panel-materialization sub-gate completes only for probe-qualified series.

No post-hoc selector search, boundary backcast, imputation, or level-mixing is allowed.

## Forbidden interpretations

M24 does not claim that:

- the 32-province panel represents all Indonesian territory without exclusion;
- excluded Papua-region provinces have no development relevance;
- province-level relationships equal kabupaten/kota-level relationships;
- stable administrative codes alone prove every statistical methodology is unchanged;
- a candidate that fails the probe can be repaired by silently changing reference month, price basis, population universe, or derived selector.
