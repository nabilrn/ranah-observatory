# Ranah Observatory Branching Policy

This repository uses **workstream branches**, not one branch per milestone, probe, dataset, diagnostic, or workflow.

The purpose of this policy is to keep the research history understandable while preserving the repository's evidence-first and fail-closed workflow.

## Branch model

`main` is the canonical, reviewable, reproducible state of the project.

At most three normal workstream branches should be active at the same time:

| Branch | Scope |
|---|---|
| `research/evidence` | Source discovery, acquisition, provenance, geography harmonization, data qualification, frozen raw evidence, canonical panels, and evidence-readiness milestones. |
| `research/analysis` | Statistical models, comparative analysis, causal-identification work, scenario engines, sensitivity analysis, synthesis, and analytical validation. |
| `release/publication` | Publication freeze, manuscript/report, figures/tables, claim ledger, public datasets, documentation, dashboard/public-product work, and release preparation. |

Exceptional repository-maintenance work may use `infra/maintenance` only when it is genuinely cross-workstream and cannot reasonably be included in one of the three branches above.

Emergency fixes may use a short-lived `hotfix/<topic>` branch.

## Hard rules

1. **Do not create a branch for a milestone.**
   - Bad: `agent/milestone28-health-panel`
   - Bad: `agent/milestone29-bmkg-stations`
   - Good: continue both on `research/evidence`.

2. **Do not create a branch for a probe, diagnostic, transport workaround, parser correction, or temporary workflow.** These are commits inside the current workstream branch.

3. **Reuse the current workstream branch while the work remains in the same scientific layer.** A new milestone number alone is never a reason to create a new branch.

4. **Maximum normal branch concurrency is three workstream branches plus `main`.** Prefer fewer. If only evidence acquisition is active, only `research/evidence` should be open.

5. **One workstream branch may contain multiple consecutive milestones.** Milestone boundaries are represented by specs, manifests, documentation, tags/releases, and commits—not branch proliferation.

6. **Temporary acquisition/writer workflows must be retired before a workstream PR is merged** when the final state is intended to be read-only and reproducible.

7. **Scientific boundaries remain milestone-specific even when branches are shared.** Sharing a branch does not authorize cross-milestone inference, post-hoc source selection, causal claims, model fitting, or monetary estimates.

8. **Do not mix unrelated workstreams in one commit.** A shared branch may contain many milestones, but commits should remain logically scoped and auditable.

9. **Merge coherent checkpoints, not every small experiment.** A workstream PR should be merged when it reaches a defensible checkpoint with frozen evidence, documentation, and required reproducibility gates. After merge, the same canonical branch name may be recreated/rebased from the new `main` for the next batch.

10. **`main` remains the publication authority.** Results that exist only on a workstream branch are provisional until merged.

## Routing rule

Before creating any branch, classify the task:

- Does it primarily add or qualify evidence/data? -> `research/evidence`
- Does it primarily fit/analyze/interpret qualified evidence? -> `research/analysis`
- Does it primarily package frozen research for external consumption? -> `release/publication`
- Is it a repository-wide maintenance issue with no sensible research owner? -> `infra/maintenance`
- Is it an urgent fix to a broken canonical state? -> `hotfix/<topic>`

If an appropriate workstream branch already exists, **reuse it**.

## Milestone examples

Under this policy, the expected near-term sequence is:

- M27 BKPM investment history -> `research/evidence`
- broader health/infrastructure/outcome evidence -> `research/evidence`
- station/daily climate validation -> `research/evidence`
- post-expansion analytical reruns or new identification work -> `research/analysis`
- v0.1 research freeze, manuscript, figures, dashboard -> `release/publication`

This keeps dozens of scientific milestones possible without creating dozens of long-lived branches.

## Transition

PR #52 / `agent/milestone27-bkpm-investment-history` is the final accepted transition branch using the old milestone-per-branch convention.

After that PR is merged or otherwise closed, new Ranah Observatory work should follow this policy. M27 follow-up evidence work may be continued on `research/evidence` rather than spawning additional milestone-specific branches.
