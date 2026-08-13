# Reproducibility Contract

Material analyses in Ranah Observatory must be reproducible from documented data and code revisions.

## Minimum retained metadata

For every analysis or model that supports a published claim, retain:

- source dataset identifier and snapshot/version;
- retrieval timestamp or source publication date;
- transformation script or pipeline revision;
- analysis/model code revision;
- geography and boundary version;
- indicator definition/version;
- parameters and configuration;
- random seed when stochastic methods are used;
- generated-at timestamp;
- output artifact or sufficient information to recreate it;
- provenance linking the result back to input observations.

## Raw and derived data

Raw source artifacts are immutable. Harmonization, cleaning, aggregation, interpolation, and reconstruction occur only in derived layers.

If a raw artifact is too large or restricted from Git, retain a manifest containing its identifier, retrieval path, expected checksum when practical, and the code needed to reproduce the local copy.

## Determinism

Prefer deterministic transformations. When an operation is stochastic, fix and record a seed unless doing so would invalidate the method.

## Environment

Executable analysis should declare the runtime and dependency versions needed to reproduce results. Environment pinning can be introduced with the first executable data pipeline; it is not required for documentation-only research artifacts.

## Generated outputs

Charts, tables, model summaries, and public metrics should identify the data snapshot and code revision that produced them when material.

## Updates and revisions

New source revisions must not overwrite historical snapshots silently. If a source changes previously published values, record the revision and regenerate affected outputs explicitly.

## Failure rule

If a result cannot be reproduced from retained inputs, code, and metadata, it is not considered publication-ready evidence.