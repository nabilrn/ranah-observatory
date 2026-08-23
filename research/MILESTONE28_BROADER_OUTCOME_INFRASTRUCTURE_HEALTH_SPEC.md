# Milestone 28 — Broader Outcome, Infrastructure, and Health Panel

## Purpose

Milestone 28 executes M23 Tier-B priority #5: broaden the current-boundary Sumatera Barat analytical substrate beyond the three outcome targets used by the first attainable-development engines.

The milestone targets evidence that can support broader multidimensional development analysis across the existing `sumbar_current_kabkota_2018_2025_v1` regime without shortening that regime merely to manufacture a balanced matrix.

M28 is a data-qualification milestone. It does not fit a new model and does not create causal, policy, ranking, or monetary wasted-potential claims.

## Existing analytical regime

The M10 analytical panel fixes the modern regime at:

- 19 current Sumatera Barat kabupaten/kota;
- 2018–2025;
- 8 analytical years;
- 152 geography-year rows.

M10 already contains a dense core plus structured missingness. M28 must preserve this regime and add evidence with explicit source-native coverage rather than dropping years globally when one new indicator starts later.

## Target evidence families

M28 seeks candidates in four distinct families.

### 1. Economic level

Priority concept:

- real GRDP per capita at constant prices, preferably a direct official series;
- if only a derived construction is available, numerator and population denominator must be methodology-compatible before derivation is authorized.

### 2. Health outcomes / access

Candidate concepts include:

- life expectancy under an explicitly versioned methodology;
- infant mortality or other mortality indicators where units and reference period are explicit;
- morbidity / health-complaint indicators;
- health-service access or supply only when the indicator definition is clear and comparable.

A survey/census anchor is not silently converted into an annual series.

### 3. Infrastructure / basic service access

Candidate concepts include:

- internet access;
- improved drinking-water access;
- sanitation access;
- direct household electricity access;
- housing/basic-service or road-access measures where the unit and geography are explicit.

Customer counts are not relabeled as household access rates.

### 4. Demographic structure

Candidate concepts include:

- total population under explicitly separated census/projection regimes;
- population density;
- urban population share;
- dependency ratio / age structure;
- migration indicators with explicit interval and denominator semantics.

No census, SUPAS, registration, and projection regimes may be silently concatenated.

## Stage 0 — metadata-only catalog discovery

The first M28 gate inventories the BPS Sumatera Barat dynamic-variable catalog on domain `1300`.

Allowed in Stage 0:

- BPS variable metadata;
- variable IDs;
- titles;
- units exposed in catalog metadata;
- subject/category metadata;
- keyword-family matching;
- existing repository candidate IDs as seed cross-checks.

Forbidden in Stage 0:

- requesting dynamic observation values (`datacontent`);
- using observed values to choose a series;
- deriving per-capita or rate values;
- imputing missing years;
- selecting a shorter analytical window;
- fitting any model.

The complete returned variable catalog is frozen so keyword selection can be reproduced offline.

## Stage 1 — period and structure qualification

Only candidates surviving Stage 0 may advance.

For each candidate, Stage 1 must separately establish:

1. source-native period inventory;
2. whether 2018–2025 years exist and which are genuinely absent;
3. kabupaten/kota geography structure and exact 19-current-geography mapping;
4. required turvar/turtahun/vervar selector semantics;
5. source unit and denominator semantics;
6. methodology/version notes;
7. whether the indicator is observed, projection/model-based, census/SUPAS anchor, or derived.

A candidate may qualify with structured missingness. It does not need eight complete years to be retained as evidence.

## Stage 2 — numeric materialization

Numeric harvest is authorized only after candidate-specific selector and methodology contracts are frozen.

Materialized output must retain:

- source-native reference period;
- claim type;
- methodology regime;
- unit;
- geography lineage;
- missingness;
- BPS source update metadata;
- frozen raw response/checksum provenance.

## Candidate-selection principles

Priority is given to indicators that add a genuinely new development dimension rather than redundant variants of existing M10 indicators.

Selection order within a concept:

1. direct official kabupaten/kota measure with stable semantics;
2. direct measure with explicit methodology break retained as separate regimes;
3. defensible derived measure with compatible numerator/denominator;
4. anchor/context-only series;
5. hold when semantics cannot be defended.

Availability alone is not qualification.

## Hard boundaries

M28 does not authorize:

- arbitrary 2018–2025 window shortening;
- interpolation/backfilling to create balance;
- source-regime concatenation without explicit methodology evidence;
- missing-as-zero;
- causal interpretation;
- intervention ranking;
- cost-benefit claims;
- monetary wasted-potential estimation;
- a new predictive model before acquisition/qualification is complete.

## Completion condition

M28 is complete when:

1. metadata discovery is frozen and reproducible;
2. at least one candidate in multiple new development families is either qualified or explicitly held with reason;
3. promoted numeric series have explicit period/geography/unit/methodology contracts;
4. structured missingness is retained;
5. permanent offline reproducibility rebuilds promoted outputs byte-identically;
6. the widened panel can be joined to the existing 19-geography 2018–2025 regime without silently changing its analytical window.
