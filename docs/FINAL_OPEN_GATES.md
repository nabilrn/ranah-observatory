# Ranah Observatory — Final Open Gates

**Audit date:** 30 August 2026  
**Delivery deadline:** 9 September 2026  
**Mode:** ship-first finalization

**Registry summary:** 6 must-close gates — **4 satisfied and 2 internal open** — plus 3 valuable-if-easy items and 7 deferred research gates. There are **0 external/manual blockers** remaining.

This document is the human-readable view of `publication/final-open-gates.json`.

Its purpose is to stop two failure modes during the final delivery window:

1. treating every unresolved research question as a release blocker; and
2. opening new research loops while actual shipping work is still unfinished.

## Decision rule

Every remaining task belongs to one of three classes:

- **must close** — final delivery is not complete until this gate is closed;
- **valuable if easy** — useful only when it can be completed cheaply without delaying must-close work;
- **defer** — a legitimate future research question, but not a condition for shipping the current bounded product.

## Must close

### Already satisfied

#### Frozen v0.1 package consistency

The v0.1 completeness certificate, claim ledger, negative results, and nine blocked M18 claims are bound by release-readiness validation.

#### Public product contract consistency

The current public product narrative, readiness surface, indicator/explorer support layers, glossary, and bounded historical supplement are validated as deterministic translations of qualified evidence.

#### GitHub Pages enablement and deployment

The repository owner changed **Settings → Pages → Build and deployment → Source** to **GitHub Actions** on 30 August 2026.

The previously failed `Deploy Public Product` workflow was rerun successfully:

- workflow run: `33309643635`, attempt 2;
- `Configure GitHub Pages`: success;
- public artifact upload: success;
- `Deploy to GitHub Pages`: success;
- production URL: **https://nabilrn.github.io/ranah-observatory/**.

Machine-readable deployment evidence is frozen in `publication/pages-deployment.json`. The earlier `Resource not accessible by integration` error is historical, not an active blocker.

#### Clean-main reproducibility sweep

The integrated offline sweep is now verified on canonical `main`:

- verified commit: `fa960c278d4ad69524c26e1bf984a1a29b9a2ab3`;
- workflow: `Final Clean Main Reproducibility Sweep`;
- push run: **`33318320220`**;
- conclusion: **success**.

The same checkout rebuilt and audited the frozen release contract, public-product data, historical reconstruction chain, M10 analytical panel, M11 expected-performance model, and M19 strict forecast backtest, then required the tracked analytical outputs to remain byte-identical.

The integrated sweep was useful because it exposed two issues before the successful run:

1. the historical public JSON rebuild was semantically identical but serialized object keys differently; the sweep was aligned with the existing semantic JSON contract rather than weakening the check; and
2. M19 still fingerprinted an older M10 manifest SHA. The M19 provenance fingerprint was refreshed to the current canonical M10 manifest. Prediction rows, metrics, and the **0/3 forecast qualification result did not change**.

M11 remains a bounded conditional expected-performance model: 342 leave-one-geography-out cross-fitted predictions and 3/3 benchmark-qualified targets. M19 remains the future-facing test: 285 strictly out-of-time predictions and 0/3 qualified targets, so substantive 2026 forecasting remains blocked.

Machine-readable evidence is frozen in `publication/clean-main-sweep.json`. The permanent workflow runs on future PRs and pushes to `main`, so later repository drift is still guarded.

### Still open

#### 1. Adversarial public readability audit

Check the actual user-facing product for:

- mobile and desktop navigation;
- terminology that an ordinary reader can understand;
- caveats that remain adjacent to the numbers they constrain;
- visible negative and blocked results;
- loading/error states;
- stale or contradictory public copy;
- accessibility and anchor/link behavior.

Exit condition: only blocker fixes remain after the audit.

#### 2. Release candidate and handoff bundle

Name one immutable release-candidate commit and prepare the final release/handoff metadata around it.

Exit condition: the candidate is audited and accompanied by concise release status, citation/handoff information, and named residual limitations.

## Valuable if easy

### Translate more already-qualified post-v0.1 evidence

Do this only when the evidence is already canonical, adds clear public value, and can be rendered deterministically without changing the scientific state.

### De-network acquisition workflows when touched

Do **not** mass-delete old acquisition infrastructure. If finalization work touches an old live-probe workflow, prefer a manual-only or deterministic validation path unless live transport remains essential.

The workflow audit found no generic release blocker in the examples checked. `bmkg-wms-probe.yml` and `bps-discovery.yml` are already isolated/manual-style acquisition utilities; BIG and BMKG open-data probes are scoped to their own acquisition paths rather than ordinary release/public-product changes.

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
