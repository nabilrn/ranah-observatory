# Ranah Observatory — Final Open Gates

**Audit date:** 30 August 2026  
**Delivery deadline:** 9 September 2026  
**Mode:** ship-first finalization

This document is the human-readable view of `publication/final-open-gates.json`.

Its purpose is to stop two failure modes during the final delivery window:

1. treating every unresolved research question as a release blocker; and
2. opening new research loops while actual shipping work is still unfinished.

## Decision rule

Every remaining task belongs to one of three classes:

- **must close** — final delivery is not complete until this gate is closed or, for an external platform action, explicitly completed by the repository owner;
- **valuable if easy** — useful only when it can be completed cheaply without delaying must-close work;
- **defer** — a legitimate future research question, but not a condition for shipping the current bounded product.

## Must close

### Already satisfied

#### Frozen v0.1 package consistency

The v0.1 completeness certificate, claim ledger, negative results, and nine blocked M18 claims are already bound by release-readiness validation.

#### Public product contract consistency

The current public product narrative, readiness surface, indicator/explorer support layers, glossary, and bounded historical supplement are validated as deterministic translations of qualified evidence.

### Still open

#### 1. Enable and verify GitHub Pages

**Owner:** repository owner  
**Type:** external/manual

The deployment workflow passes its repository-side validation but GitHub refuses first-site creation with:

`Resource not accessible by integration`

Manual action:

**Repository Settings → Pages → Build and deployment → Source → GitHub Actions**

Exit condition: `Deploy Public Product` succeeds and the canonical production URL serves the repository's static site artifact.

#### 2. Clean-main reproducibility sweep

Run the final relevant validation matrix from one clean `main` candidate after release-critical integration work is done.

Exit condition: release readiness, public product, historical reconstruction, and analytical reproducibility gates are all green for the same candidate state.

#### 3. Adversarial public readability audit

Check the actual user-facing product for:

- mobile and desktop navigation;
- terminology that an ordinary reader can understand;
- caveats that remain adjacent to the numbers they constrain;
- visible negative and blocked results;
- loading/error states;
- stale or contradictory public copy.

Exit condition: only blocker fixes remain after the audit.

#### 4. Release candidate and handoff bundle

Name one immutable release-candidate commit and prepare the final release/handoff metadata around it.

Exit condition: the candidate is audited and accompanied by concise release status, citation/handoff information, and named residual limitations.

## Valuable if easy

### Translate more already-qualified post-v0.1 evidence

Do this only when the evidence is already canonical, adds clear public value, and can be rendered deterministically without changing the scientific state.

### De-network acquisition workflows when touched

Do **not** mass-delete old acquisition infrastructure. If finalization work touches an old live-probe workflow, prefer a manual-only or deterministic validation path unless live transport remains essential.

The workflow audit found no generic release blocker in the examples checked. `bmkg-wms-probe.yml` and `bps-discovery.yml` are already isolated/manual-style acquisition utilities; BIG and BMKG open-data probes are scoped to their own acquisition paths rather than ordinary release/product changes.

### Release-surface metadata polish

Improve repository navigation, release notes, citation metadata, or handoff text when it directly removes ambiguity from the final delivery.

## Deferred research — not release blockers

### 2005 construction qualification components

Do not reopen the Book II / Kecil–Menengah–Besar acquisition loop without a genuinely new official BPS/LPJK lead. The current access and semantic boundaries are already explicit.

### Causal attribution of the construction-series revision

Operational plausibility is documented, but the causal bridge from the 2005 directory update to historical value revisions remains unproven. Shipping a bounded result does not require inventing that bridge.

### Missing BPBD 2017 raw annual-report bytes

The PPID migration/access boundary is frozen. Reopen only if a semantically verified official archival locator or raw PDF appears.

### Definitive rupiah-valued “wasted potential”

The frozen M18 claim gate blocks a single definitive monetary headline. Do not weaken the research standard just to create one.

### Theoretical maximum or guaranteed policy gains

Current empirical gaps do not identify either construct.

### Rainfall → unemployment causal effect

Current climate/labor evidence does not identify causality.

### Composite disaster score and ranked policy list

Disaster components remain separate; no synthetic weighting, treatment-effect interpretation, or cost-benefit ranking is authorized.

## Workflow audit result

At this audit point there were **zero open pull requests**.

No mass deletion of workflows is authorized. The finalization objective is a stable release, not a cosmetically small repository. Permanent validators and bounded acquisition utilities may remain when their role is explicit and they do not create a general release dependency.

## What changes this classification?

A deferred gate moves back into active work only if one of these becomes true:

- genuinely new official evidence appears;
- the gate becomes necessary to reproduce an already-public claim;
- the gate becomes necessary to deploy or package the final product;
- an adversarial audit shows that leaving it unresolved creates a misleading public conclusion.

Anything else waits until after the current delivery window.
