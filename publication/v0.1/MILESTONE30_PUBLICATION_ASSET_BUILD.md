# Milestone 30 — Publication Asset Materialization

## Purpose

Materialize the already-planned v0.1 publication tables and figures from the frozen analytical/evidence base without acquiring new data, fitting new statistical or ML models, changing claim authorization, or upgrading context-only evidence.

## Scope

M30 reuses the existing `research/publication` branch and the M29 v0.1 publication package. It adds a deterministic Python-standard-library renderer under `publication/v0.1/tools/`.

The renderer must produce exactly:

- 7 CSV publication tables corresponding to T01–T07 in `table-plan.csv`;
- 6 monochrome SVG publication figures corresponding to F01–F06 in `figure-plan.csv`;
- one render manifest containing source and output SHA-256 identities.

## Scientific constraints

M30 does not authorize:

- new source acquisition;
- imputation or missing-as-zero;
- new model fitting or refitting;
- post-hoc model or breakpoint search;
- causal claim upgrades;
- composite development/disaster scores;
- monetary wasted-potential aggregation;
- treatment-effect interpretation of predictive sensitivities;
- policy or cost-benefit ranking.

Negative-result and blocked-claim visibility remains mandatory.

## Rendering rules

- F01 must preserve non-causal edge semantics from M18.
- F02 must retain support-blocked rows and frontier-method disagreement.
- F03 must display all seven preregistered M22 indicators, including failed gates.
- F04 must show all three failed M19 forecast targets against own-lag persistence.
- F05 must display candidate climate patterns only alongside failed M20/M21 qualification states.
- F06 must not place unlike source-native observation counts on a common quantitative magnitude axis.
- T07 must retain all nine blocked claims.

## Completion rule

M30 is complete only when CI builds all 13 assets from committed upstream evidence, the generated outputs are committed byte-identically, a second CI rebuild leaves them unchanged, and the M29 publication claim/completeness audit remains green.
