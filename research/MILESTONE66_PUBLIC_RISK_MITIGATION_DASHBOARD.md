# Milestone 66 — Public Risk + Mitigation Dashboard

## Purpose

Milestone 66 promotes the qualified M65 IRBI→KRB lookup bridge into the SvelteKit disaster explorer so a normal reader can inspect **where risk is recorded and what official risk-reduction actions are recommended** without conflating those statements with event counts, implementation evidence, or forecasts.

## Public contract

The existing public disaster artifact is upgraded in one additional deterministic step:

`v2 base builder → v3 BPBD context promoter → v4 risk/mitigation promoter`

M66 deliberately does not rewrite the stable v2 or v3 producers.

The v4 payload adds `risk_mitigation_2024` with:

- 124 source-preserving IRBI 2024 district × hazard rows;
- 9 explicitly matched IRBI/KRB hazards;
- 49 source-native KRB recommendation actions for those matched hazards;
- 5 KRB hazards that remain explicitly unmatched to an IRBI 2024 hazard table;
- 47 absent district × hazard pairs preserved as source absences rather than zero risk;
- source paths and SHA256 provenance back to M65 and M64;
- explicit fail-closed interpretation flags.

## Dashboard behavior

The disaster explorer now includes a plain-language **Risiko dan langkah pengurangan risiko** section.

A user can:

1. choose a kabupaten/kota;
2. choose one of the nine matched IRBI hazard types;
3. see the exact IRBI 2024 risk score and source risk class when that district × hazard row exists;
4. see an explicit no-data message when the source table does not contain that combination;
5. inspect all available district scores for the selected hazard;
6. read the corresponding KRB 2022–2026 source-native recommendation actions;
7. see physical PDF page provenance for each recommendation.

The region selector is bound to the existing disaster-page region state so selecting a region in the risk panel also updates the other district-level tables/map context.

## Plain-language safety copy

The public panel explicitly states that:

- an absent IRBI row does **not** mean zero risk;
- IRBI is an index, not event probability;
- KRB action order follows the source and is **not** an effectiveness ranking;
- the source recommendations are not proof of implementation;
- risk scores are not disaster forecasts.

## Scientific boundary

M66 does not authorize:

- global equivalence of IRBI, KRB, or BPBD/Pusdalops hazard taxonomies;
- joining IRBI risk directly to BPBD event counts through name similarity;
- translating IRBI scores into probability of future disaster;
- inferring zero for 47 absent IRBI pairs;
- ranking KRB recommendations by effectiveness from list order;
- claiming a recommendation was implemented;
- estimating an unmitigated monetary loss from these layers.

## Reproducibility

`scripts/promote_public_disaster_risk_mitigation.py` reads only qualified M65/M64 artifacts and validates their checksums and boundaries before upgrading v3 to v4.

`scripts/validate_public_disaster_risk_mitigation.py` then verifies:

- exact 124-row equality to the M65 lookup footprint;
- exact preservation of risk score/class and hazard/geography identity;
- exact 49-action equality to the matched M64 source-native action footprint;
- source paths and SHA256 provenance;
- exact 9 matched hazards, 5 unmatched KRB hazards, and 47 source-absent IRBI pairs;
- all prediction/taxonomy/numeric-equivalence/implementation boundaries;
- frontend schema, build-chain, component mount, and required safety copy.

The permanent M66 CI gate performs Svelte/TypeScript checking, static build, focused validation/test, and a byte-identical second v4 rebuild.
