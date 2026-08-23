# Milestone 29 — Publication Freeze v0.1

## Purpose

Milestone 29 converts the completed reproducible evidence and analytical work through Milestone 28 into the first bounded public research package for Ranah Observatory.

This is a **synthesis and publication-freeze milestone**, not a new data-acquisition or model-development milestone.

The intended public artifact is a technical report / preprint provisionally titled:

> **Ranah Observatory: A Reproducible Evidence Framework for Development Gaps, Socioeconomic Trajectories, and Climate-Disaster Constraints in West Sumatra**

The publication must explain what the evidence supports, what failed qualification, what remains merely contextual, and which high-salience claims remain explicitly blocked.

## Frozen research base

The initial v0.1 publication base is the repository state after completion of Milestone 28:

- base commit: `e1571e63fd19222c0f6112d340b61ed5d7996e58`;
- M23 Tier-A priorities complete;
- M23 Tier-B investment and broader outcome/infrastructure/health priorities complete;
- Panel v2 contains the original M10 evidence plus the M28 additions;
- BMKG station/daily climate validation remains valuable but is not a v0.1 publication dependency.

M29 may cite later commits only for publication-package metadata, wording, tables, figures, or reproducibility certificates. It may not silently replace the frozen analytical evidence with newly acquired observations or newly fitted models.

## Publication positioning

v0.1 is an **evidence-framework and bounded empirical-results publication**. It is not a definitive estimate of West Sumatra's monetary "wasted potential" and not a policy-ranking paper.

The paper may publish:

- reproducible modern socioeconomic trajectories;
- bounded predictive expected-performance results already qualified upstream;
- empirical favorable-reference and gap results with their support rules;
- stable association findings explicitly labeled non-causal;
- completed quasi-causal null/non-directional results;
- negative model-qualification results;
- qualified climate context and non-qualified trend/regime-shift findings;
- nationally comparable, fiscal, disaster-component, investment, health, infrastructure, and demographic evidence as context where no downstream substantive model has yet been qualified;
- explicit uncertainty, disagreement, missingness, and blocked claims.

## Required claim classes

Every public-facing substantive statement must be registered in the v0.1 claim ledger with one of four states:

1. `publishable_bounded` — supported by an already-qualified upstream analytical result within its exact regime and interpretation boundary;
2. `publishable_negative_result` — a preregistered/locked analysis or model failed its qualification gate and the negative result is itself scientifically reportable;
3. `context_only` — qualified evidence exists, but no downstream substantive inference beyond description/context is authorized;
4. `blocked` — the statement is not authorized and must not appear as a positive conclusion.

No fifth informal category is allowed.

## Inclusion rules

A result may enter `publishable_bounded` only when:

- its source milestone is complete;
- its canonical output and manifest remain reproducible;
- the source milestone explicitly authorizes the interpretation being published;
- all geography, period, methodology, and claim-type boundaries are retained;
- no stronger causal, theoretical-frontier, forecast, policy, or monetary interpretation is introduced.

A failed qualification must be retained as `publishable_negative_result` when it materially changes what a reader might otherwise infer from the project.

Newly acquired evidence from M24–M28 may enter `context_only` without a new model. It may not be presented as explaining an existing gap unless an upstream qualified analysis already establishes that link.

## Negative-results rule

The publication must not hide model failures.

At minimum it must retain:

- M19: all three one-year-ahead dynamic forecast targets fail the persistence benchmark, so no substantive 2026 forecast is authorized;
- M20: zero of 19 geographies pass the full robust monotonic rainfall-trend gate;
- M21: the candidate rainfall regime shift fails the preregistered qualification gate;
- M22: only the indicators/trajectories passing the partial-pooling and robustness gates may be interpreted as qualified trajectories.

## Existing blocked claims

The nine M18 claim-boundary statements remain blocked unless a later completed milestone explicitly supplies the required upgrade evidence. Evidence expansion alone does not upgrade them.

This includes, at minimum:

- definitive monetary wasted-potential value;
- theoretical-maximum interpretation of empirical favorable references;
- causal interpretation of predictive residuals;
- guaranteed policy-gain interpretation of favorable-reference distance;
- causal rainfall→unemployment interpretation;
- event count→observed impact relabeling;
- synthetic disaster-risk score;
- predictive sensitivity→treatment-effect/forecast interpretation;
- policy/cost-benefit ranking without qualified effects, costs, horizons, feasibility, and risk evidence.

## Frozen evidence-layer updates after M18

M29 must reflect, without overinterpreting, the post-M18 evidence additions:

- M19 dynamic forecast qualification failure;
- M20 climate trend qualification failure;
- M21 climate regime-shift qualification failure;
- M22 hierarchical socioeconomic trajectory results;
- M24 stable-32 national comparator evidence;
- M25 DJPK public-finance evidence;
- M26 BNPB/InaRISK disaster-risk component evidence;
- M27 bounded BKPM investment history;
- M28 broader BPS outcome/infrastructure/health/demographic evidence and Panel v2.

## Publication-package outputs

M29 must create a versioned package under `publication/v0.1/` containing at least:

- `release-manifest.json` — frozen evidence/manifests/commit identity;
- `claim-ledger.csv` — all substantive public claims and their exact authorization state;
- `evidence-table.csv` — evidence objects used in the report and their interpretation class;
- `table-plan.csv` — publication tables and exact source artifacts;
- `figure-plan.csv` — publication figures and exact source artifacts;
- `manuscript-outline.md` — section architecture tied to claim IDs;
- eventually `manuscript.md` — the bounded v0.1 report text.

The package must also include an offline reproducibility/completeness certificate before M29 can close.

## Prohibited operations

M29 does not authorize:

- new source acquisition;
- new statistical/ML model fitting;
- post-hoc algorithm or hyperparameter search;
- re-estimation solely to improve headline results;
- imputation or missing-as-zero;
- geography backcasting;
- creation of a composite development/wasted-potential score;
- monetary aggregation of gaps;
- causal claim upgrades;
- policy treatment-effect interpretation;
- cost-benefit or intervention ranking.

## Completion rule

M29 is complete only when the publication package is internally consistent with all frozen upstream manifests, every manuscript-level substantive claim maps to a claim-ledger ID, all blocked/negative results remain visible, tables/figures are reproducibly sourced, and an offline verifier certifies that no unauthorized claim or analysis upgrade has entered the v0.1 package.
