# Ranah Observatory — Final 10-Day Delivery Contract

**Window:** 30 August 2026 → 9 September 2026  
**Mode:** ship-first finalization  
**Canonical authority:** `main`

## Objective

Use the remaining project window to turn the existing research substrate into a coherent, reproducible, understandable release rather than expanding the research frontier indefinitely.

The project already has a frozen v0.1 publication package, comparative/trajectory analysis, claim gates, a public product, district explorer, research-readiness surface, indicator catalog, glossary, and substantial post-v0.1 evidence expansion. The remaining work is therefore primarily **integration, closure, audit, and release quality**.

## Hard operating rule

A new task is accepted during this window only if it does at least one of the following:

1. closes a currently material evidence or semantic gate;
2. moves already-qualified evidence into the final public product;
3. removes a reproducibility, validation, deployment, or release blocker;
4. improves the ability of a non-technical reader to understand a qualified result;
5. completes the final release/deposit/handoff package.

Otherwise it is deferred.

## Explicitly deprioritized

Until the release candidate is frozen, do **not** spend the remaining window on:

- repeating acquisition probes that already have a frozen no-hit/access boundary;
- speculative historical backcasts or semantic bridges;
- broad new model families or hyperparameter searches;
- performance benchmarking unrelated to research correctness;
- new composite scores;
- causal or policy-ranking claims unsupported by the current design;
- manual BMKG work unless a concrete release-critical gate cannot be closed through already-qualified sources;
- polishing low-value internal artifacts while public/release surfaces remain incomplete.

## Current verified baseline

### Frozen v0.1 science package

`publication/v0.1/completeness-certificate.json` currently certifies:

- 30 frozen claims;
- 11 publishable bounded claims;
- 5 publishable negative results;
- 5 context-only claims;
- 9 blocked claims;
- 17 evidence rows;
- complete manuscript claim coverage;
- all required negative results retained;
- all nine M18 blocked claims retained.

### Public translation layer

The public product currently has machine-validated contracts for:

- 9 main story cards;
- 5 headline statistics;
- all 9 blocked headline claims;
- 5 research-readiness questions;
- a 23-indicator Panel v3 catalog;
- 19 kabupaten/kota in the district explorer;
- 4 trajectory-qualified district indicators;
- 3 bounded historical construction cards.

### Current research-question state

M18 remains deliberately fail-closed:

- 2 bounded answers;
- 2 bounded partial answers;
- 1 not-action-ready question;
- 0 fully resolved questions;
- no policy ranking;
- no definitive monetary wasted-potential estimate.

This is a valid research outcome. The final release must not manufacture a stronger conclusion merely to appear more complete.

## External/manual blocker

GitHub Pages deployment is technically implemented and all product validation/rebuild/static checks pass. Automatic first-site creation fails with:

`Resource not accessible by integration`

The repository owner must perform one manual setup action:

**Repository Settings → Pages → Build and deployment → Source → GitHub Actions**

After that, rerun `Deploy Public Product` or push a relevant `main` change.

This blocker is external to the product contract and does not authorize bypassing validation.

## Delivery sequence

### Days 1–2 — Release surface and product truth

- bring README/current-phase documentation up to date;
- expose already-qualified high-value post-v0.1 evidence where it materially improves the public product;
- ensure every public number has a nearby interpretation boundary;
- keep scientific source packages immutable from product-only work;
- enable GitHub Pages manually and confirm the production URL once available.

**Exit gate:** a non-technical reader can navigate from repository → public product → evidence boundary without reading internal milestone history.

### Days 3–4 — Evidence closure audit

- inventory remaining open evidence gates by impact on final conclusions;
- classify each as `must_close`, `valuable_if_easy`, or `defer`;
- pursue only `must_close` items or genuinely new official leads;
- freeze no-hit/access boundaries instead of looping searches;
- ensure historical vintages and definition breaks remain explicit.

**Exit gate:** every unresolved high-salience question has either sufficient evidence or an explicit final boundary and next-evidence statement.

### Days 5–6 — Reproducibility and data-package audit

- run the complete relevant CI matrix from a clean `main` state;
- verify deterministic public-data builders against frozen inputs;
- verify publication completeness and claim-ledger consistency;
- remove or quarantine temporary probe workflows/artifacts that no longer serve the final product;
- verify no secrets or source credentials are persisted in release artifacts.

**Exit gate:** no known repository-internal reproducibility blocker remains.

### Day 7 — Public readability pass

- mobile and desktop reading pass;
- simplify technical labels without changing meaning;
- verify glossary coverage for terms used by public stories;
- check empty/error states and navigation;
- keep negative and blocked results visually visible.

**Exit gate:** public copy remains accurate under validator checks and is understandable without opening raw JSON.

### Day 8 — Release candidate freeze

- declare the release-candidate commit;
- prohibit new research fronts;
- run claim/evidence/readiness/history validators;
- verify release notes and authorship/citation metadata;
- record any remaining external/manual actions separately from science blockers.

**Exit gate:** one immutable commit is the candidate for final delivery.

### Day 9 — Adversarial audit and blocker-only fixes

Audit for:

- overclaiming;
- silent definition/geography drift;
- stale public numbers;
- dead links or missing assets;
- mismatch between manuscript, ledger, public product, and evidence manifests;
- accidental causal/policy language;
- deployment or packaging regressions.

Only blocker fixes are accepted after this audit starts.

### Day 10 — Final delivery

- merge blocker fixes;
- run final release-readiness CI;
- confirm public-product deployment if Pages is enabled;
- freeze final commit/tag/release bundle as appropriate;
- preserve deposit/handoff metadata and citation instructions;
- produce a concise final status: what is supported, what remains blocked, and what future work would be required.

## Release completion gates

The final window is considered successfully closed when all **repository-internal** gates below are true:

- [ ] v0.1 completeness certificate remains valid;
- [ ] frozen claim ledger remains internally consistent;
- [ ] all required negative results remain visible;
- [ ] all nine blocked M18 claims remain blocked and visible;
- [ ] public product validators pass;
- [ ] public research-readiness validator passes;
- [ ] public historical-context validator passes;
- [ ] deterministic public builders reproduce their frozen contracts;
- [ ] release/publication documentation reflects the actual current phase;
- [ ] no unresolved CI failure is caused by repository code/data;
- [ ] final release candidate is identified and audited.

The following is tracked separately because it requires owner/platform state rather than research code:

- [ ] GitHub Pages is enabled and the canonical public product is deployed.

## Definition of “done”

“Done” does **not** mean every research question is fully resolved.

“Done” means:

- the strongest defensible answers are reproducible;
- unresolved questions are explicitly bounded;
- negative results are retained;
- the public product reflects the evidence rather than aspirations;
- the release package can be inspected and reproduced;
- future work starts from named evidence gaps instead of undocumented assumptions.
