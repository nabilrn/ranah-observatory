# Branching Strategy

Ranah Observatory uses a phase-oriented branching model. The repository is research-heavy, so branch boundaries should follow coherent research or data-engineering deliverables rather than individual files or tiny tasks.

## Core rule

`main` is the stable integration branch. Work reaches `main` only after the relevant methodology, schema, data validation, or code checks have passed.

Use one branch for one coherent deliverable:

```text
agent/<phase-or-deliverable>
```

Examples:

```text
agent/research-foundation
agent/data-foundation
agent/ingestion-bps
agent/ingestion-bmkg
agent/ingestion-bnpb
agent/ingestion-big
agent/historical-reconstruction
agent/eda-baseline
agent/model-potential-gap
agent/causal-case-study
agent/web-platform
```

Avoid micro-branches such as `add-column`, `fix-one-csv`, or `update-one-chart` unless the change is genuinely independent and reviewable.

## Dependency order

```text
main
  |
  +-- research-foundation
          |
          v
      data-foundation
          |
          +-------------------------------+
          |               |               |
          v               v               v
     ingestion-bps   ingestion-bmkg  ingestion-bnpb
          |               |               |
          +---------------+---------------+
                          |
                          v
                 historical-reconstruction
                          |
                          v
                     eda-baseline
                          |
                          v
                 model-potential-gap
                          |
                          v
                  causal-case-study
                          |
                          v
                    web-platform
```

`ingestion-big` can run in parallel with the other ingestion branches once the canonical geography and observation schemas are stable.

## Branch creation policy

Do not pre-create downstream branches before their prerequisite phase is merged. Create each branch from the latest `main` so it inherits the current research contract and schemas.

Example:

1. Merge `agent/research-foundation`.
2. Create `agent/data-foundation` from updated `main`.
3. Merge `agent/data-foundation` after schema validation.
4. Create ingestion branches from the new `main`.
5. Merge ingestion branches independently when source-specific validation passes.

This prevents long-lived branches from drifting away from the canonical research and data contracts.

## Pull request policy

Every substantial branch should use a PR. PR descriptions should state:

- what changed;
- which research phase or dataset it belongs to;
- methodology or schema implications;
- validation performed;
- known limitations;
- the next dependent phase.

Research and data PRs should explicitly distinguish observed data, reconstructed data, derived statistics, model estimates, causal estimates, and scenario assumptions.

## Merge expectations

A branch is ready for merge when the applicable checks are satisfied:

### Research/documentation

- research question and scope are explicit;
- claims do not exceed the evidence;
- terminology is consistent;
- sources and limitations are documented.

### Data foundation

- canonical identifiers are stable;
- temporal and geographic versions are represented;
- provenance is mandatory;
- schemas have validation rules;
- incompatible definitions are not silently combined.

### Ingestion

- raw inputs remain immutable;
- parsing is reproducible;
- source metadata is retained;
- validation covers units, geography, time, nulls, and duplicates;
- transformations are testable.

### Models

- baseline comparison exists;
- train/test leakage is checked;
- assumptions are documented;
- predictive association is not presented as causation;
- uncertainty and limitations are exposed.

### Web platform

- displayed metrics trace back to source or model artifacts;
- claim type is visible when material;
- charts preserve units and temporal definitions;
- builds and automated checks pass.

## Branch lifecycle

After a PR is merged, delete its working branch unless it is still required by an active dependent PR. `main` should remain the source of truth for all new work.

## Initial sequence

The intended initial branch sequence is:

```text
agent/research-foundation     # current
agent/data-foundation         # next
agent/ingestion-bps
agent/ingestion-bmkg
agent/ingestion-bnpb
agent/ingestion-big
agent/historical-reconstruction
agent/eda-baseline
agent/model-potential-gap
agent/causal-case-study
agent/web-platform
```

The order after the ingestion phase may change when data availability and research findings justify it. The branching model is a workflow constraint, not a substitute for research judgment.
