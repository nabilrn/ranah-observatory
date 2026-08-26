# Milestone 46 — BNPB Total-Event Registry and Panel Integration

## Objective

Move the M45-qualified `total_disaster_events` candidate into a product-facing data path without mutating the reviewed 38-row BNPB flood/landslide baseline or rewriting M10/M28 history.

M46 uses three layers:

1. **Global registry qualification** — register `total_disaster_events` as a qualified disaster-resilience indicator.
2. **Separate canonical BNPB layer** — materialize all 285 M45 observations for 2010–2024 with the exact M45 fingerprint.
3. **Panel v3 integration** — preserve all 2,679 Panel v2 observations field-for-field and append only the 2018–2024 total-event slice (133 observations).

## Why a separate canonical layer

The existing reviewed BNPB baseline is intentionally narrow: its 38 canonical observations are independently crosschecked 2024 flood and landslide counts. M45 qualifies a different source product — a complete retrospective all-disaster district/city matrix. Rewriting the old baseline would mix two review contracts.

M46 therefore gives the total-event series its own canonical artifact and provenance while retaining the existing baseline unchanged.

## Indicator semantics

`total_disaster_events` means:

> Count of all disaster events recorded by BNPB for the stated geography and calendar year under the qualified source release.

It must not be read as:

- flood events;
- landslide events;
- a sum that should be added to hazard-specific event indicators;
- unique events reconstructed across external sources;
- complete true disaster incidence.

## Geography boundary

Entity identity continuity for the 19 Sumatera Barat district/city entities is qualified for 2010–2024. Exact polygon harmonization to a single 2024 boundary geometry is not proven.

Therefore:

- the full 2010–2024 canonical layer is retained for source-defined longitudinal research;
- the generic `comparable` flag remains unset;
- the exact-polygon caveat remains attached to every canonical and panel observation;
- only 2018–2024 is integrated into the current analytical regime used by Panel v2;
- 2025 is structurally missing because the qualified source ends in 2024 and is never zero-filled.

## Panel v3 invariants

Panel v3 must satisfy all of the following:

- same regime ID as Panel v2: `sumbar_current_kabkota_2018_2025_v1`;
- 19 geographies × 8 analysis years = 152 wide rows;
- all 2,679 Panel v2 long observations preserved field-for-field;
- one new indicator only: `total_disaster_events`;
- 133 added observations = 19 geographies × seven years (2018–2024);
- 2,812 total long observations;
- 23 indicators total;
- no duplicate geography-year-indicator keys;
- no 2025 total-event observation;
- no zero fill or imputation;
- no cross-indicator aggregation;
- no causal analysis.

## Reproducibility

The canonical materialization must reproduce M45 candidate SHA-256:

`7f6c69d1e2f1b640c13dd1bf3321e1a395ecdab7263e83607dd040a9d0dd31c8`

Registry migration is performed by an idempotent anchor-based migration script. It refuses to edit unexpected prior states.

Materialization is allowed to write only the explicitly whitelisted registry, validator, canonical BNPB, Panel v3, and M46 manifest paths. A separate read-only CI workflow independently reruns the migration in workspace, rebuilds M46 under `/tmp`, and compares committed outputs byte-for-byte when materialized artifacts are present.

## Boundaries retained

M46 does not authorize:

- exact current-polygon historical claims;
- treating recorded-event trends as true incidence without reporting-practice caveats;
- hazard-specific reinterpretation of the all-disaster total;
- addition of total events to flood/landslide counts;
- causal attribution;
- monetary or avoided-loss estimation;
- composite risk scoring or policy ranking from this indicator alone.
