# Ranah Observatory

Open research infrastructure for understanding West Sumatra's past, measuring its present, and evaluating plausible futures.

Ranah Observatory combines historical reconstruction, official statistics, geospatial evidence, climate and disaster data, comparative regional analysis, statistical modeling, and explicit claim gating. The objective is not to manufacture a single dramatic number, but to distinguish what the evidence supports, what remains contextual, and what is still unresolved.

## Core questions

- How has West Sumatra changed across major development dimensions?
- How does realized development compare with structurally similar Indonesian regions?
- When did important divergences emerge?
- Which relationships are descriptive, predictive, or supported by stronger explanatory evidence?
- Which interventions deserve further testing?

The project does **not** assume a fixed amount of "wasted potential." A monetary wasted-potential estimate, theoretical maximum, causal residual interpretation, guaranteed policy gain, and ranked policy prescription remain blocked unless their evidence gates are actually satisfied.

## Current state

The original **v0.1 research/publication package is frozen** and has a deterministic completeness certificate:

- 30 claims in the frozen claim ledger;
- 11 `publishable_bounded` claims;
- 5 `publishable_negative_result` claims;
- 5 `context_only` claims;
- 9 explicitly `blocked` claims;
- 17 evidence-table rows;
- all 30 ledger claims referenced by the manuscript;
- all required negative results and all nine blocked M18 claims retained.

Post-v0.1 work extends the evidence base without silently rewriting the frozen scientific package. Recent additions include stronger historical construction boundaries, disaster-source qualification, public research-readiness surfaces, an indicator catalog, a district explorer, glossary, and a bounded historical-context layer.

## Public product

The repository contains a static public observatory under `site/` designed for non-technical readers. It currently exposes:

- the main claim-gated stories and all blocked headline claims;
- five research questions with their current readiness states;
- a bounded 23-indicator Panel v3 catalog;
- a 19-district/city explorer for four trajectory-qualified indicators;
- a research glossary;
- a post-v0.1 **Jejak historis** section derived deterministically from qualified construction evidence.

The public product has no runtime dependency on external statistical APIs. Its JSON contracts are validated against frozen repository evidence before deployment.

GitHub Pages deployment is implemented in `.github/workflows/deploy-public-product.yml`. The repository owner still needs to enable **Settings → Pages → Source: GitHub Actions** once; the deployment workflow cannot create the Pages site with the repository integration token. This is a hosting-setting boundary, not a failed product validation.

## Research readiness

The frozen M18 synthesis contains five main research questions:

- 2 `bounded_answer`;
- 2 `bounded_partial`;
- 1 `not_action_ready`;
- 0 fully resolved.

That distinction is intentional. "Data available" is not treated as equivalent to "question solved," and predictive evidence is not promoted to a causal or policy claim.

## Historical evidence rule

Historical source vintages, definition changes, geography changes, preliminary/revised values, and incompatible statistical operations are preserved rather than silently harmonized. A bridge/backcast is allowed only when its semantics and transformation are explicitly supported.

For example, the current construction evidence can show published 2002–2006 establishment counts and the separate SE06 population/listing benchmark, but it does not authorize treating those quantities as one sampling-frame series or reconstructing the missing 2005 qualification composition.

## Finalization window

The project is now in a shipping-focused finalization window through **9 September 2026**. The operating rule is:

> finish qualified evidence, product translation, reproducibility, and release packaging before opening new research fronts.

See `docs/FINAL_10_DAY_DELIVERY.md` for the concrete cut line and completion gates. See `docs/FINAL_OPEN_GATES.md` for the current must-close / valuable-if-easy / defer classification.

## Development workflow

Work uses grouped workstream branches rather than one branch per milestone:

- `research/evidence` — source acquisition, provenance, and semantic boundaries;
- `research/analysis` — analytical models and diagnostics;
- `release/publication` — release packaging, documentation, and finalization;
- product-focused branches may be used for bounded public-surface increments before merge.

`main` remains the canonical publication authority. See `docs/BRANCHING_POLICY.md` for the mandatory branching rules.

## Key entry points

- Research charter: `research/RESEARCH_CHARTER.md`
- Original sprint roadmap: `docs/ROADMAP_25_DAYS.md`
- Final 10-day delivery contract: `docs/FINAL_10_DAY_DELIVERY.md`
- Final open-gate registry: `docs/FINAL_OPEN_GATES.md`
- Public product specification: `docs/PRODUCT_V0_1_SPEC.md`
- Frozen claim ledger: `publication/v0.1/claim-ledger.csv`
- Publication completeness certificate: `publication/v0.1/completeness-certificate.json`
- Public product source: `site/`
