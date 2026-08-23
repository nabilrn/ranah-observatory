# Ranah Observatory — Public Product v0.1

## Objective

Turn the repository's qualified research into a public-facing observatory that a non-technical reader can understand without reading the full preprint, while keeping every visible claim traceable to the same evidence and claim boundaries used by the research workflow.

The product is not a second analytical pipeline. It is a **translation layer over frozen evidence**.

## Primary audience

- West Sumatra residents who want to understand development conditions;
- journalists and civil-society readers who need defensible context quickly;
- students and researchers who want a guided entry point before opening raw evidence;
- policymakers and practitioners who need to know what is supported, uncertain, contextual, or not yet answerable.

## Product promise

A reader should be able to answer three questions in less than five minutes:

1. **What do we actually know?**
2. **How strong is the evidence?**
3. **What are we explicitly not claiming?**

## Information architecture

### 1. Landing summary

The first screen presents the project's main conclusion in plain language:

> West Sumatra has measurable development differences relative to empirical expectations and peers, but the evidence does not yet support a single rupiah-valued "wasted potential" number or a ranked policy prescription.

This framing preserves the original research ambition without pretending the unresolved headline has already been solved.

### 2. Evidence-state legend

Every substantive card uses exactly one public evidence state:

- `supported` — maps only to `publishable_bounded` claims or a later explicitly bounded evidence milestone;
- `negative_result` — maps only to `publishable_negative_result` claims;
- `context` — maps only to `context_only` claims;
- `not_supported` — maps to blocked claims and is displayed only as a boundary, never as a positive conclusion.

The UI must never hide negative results simply because they are less visually attractive.

### 3. Main story cards

The first release prioritizes a small set of high-value stories rather than exposing every available field:

- development-gap distribution;
- unemployment and labor-force-participation trajectories;
- rice-yield trajectory evidence;
- failed 2026 forecast qualification;
- failed robust monotonic rainfall-trend qualification;
- 1997→1998 rainfall cross-check using the historical Tabing station;
- disaster evidence as separate components rather than a synthetic score;
- investment-history coverage and its held 2024-Q1 period.

Each card contains:

- one plain-language headline;
- one concise explanation;
- a visible evidence-state badge;
- a short "why this matters" sentence;
- a caveat/boundary sentence;
- traceable source claim IDs or canonical evidence paths.

### 4. "What we still cannot answer" section

The nine blocked claims remain visible in human language. The product must be explicit that the project currently cannot defensibly provide:

- a single monetary wasted-potential estimate;
- a theoretical maximum for West Sumatra;
- causal interpretation of predictive residuals;
- guaranteed policy gains from closing empirical gaps;
- causal rainfall→unemployment effects;
- disaster impact inferred from event counts;
- a composite disaster-risk score;
- policy treatment effects from predictive sensitivities;
- a ranked policy/cost-benefit list.

## Technical architecture

v0.1 uses a static product surface under `site/`:

- no backend dependency;
- no runtime connection to BPS, BMKG, NCEI, BNPB, BKPM, or DJPK;
- deployable on GitHub Pages, Cloudflare Pages, Netlify, Vercel static hosting, or any basic web server;
- all public copy is loaded from a versioned JSON data contract;
- no user tracking or analytics is required for the first release.

This keeps the public product reproducible and prevents a source outage from silently changing what readers see.

## Claim-gating architecture

`site/data/overview.json` is the public narrative contract.

`scripts/validate_public_product.py` verifies that:

1. every claim ID used by the public product exists in `publication/v0.1/claim-ledger.csv`;
2. evidence states in the UI match the allowed claim-ledger states;
3. blocked claims appear only in the `not_supported` boundary section;
4. the post-v0.1 M36 station card matches the frozen M36 manifest and remains non-causal;
5. no card silently promotes context evidence into a supported analytical conclusion.

## Visual principles

- content-first, minimal, high contrast;
- restrained neutral palette with semantic state labels;
- no decorative dashboard density;
- charts are used only when they make the underlying result easier to understand;
- every number has nearby language explaining what it does and does not mean;
- mobile layout is a first-class requirement.

## Release boundary

Public Product v0.1 is considered a usable first product when:

- the static landing page renders without a build step;
- the narrative JSON passes claim gating;
- the core stories and blocked boundaries are visible on mobile and desktop;
- no publication/scientific source is modified by the product layer;
- CI validates the narrative contract.

Interactive maps, district drill-down, downloadable indicator explorer, richer charts, and live data refresh are follow-up product increments on the same `release/publication` workstream branch. They are not prerequisites for the first understandable public surface.
