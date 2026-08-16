# BPS Population Growth Canonical Candidate

## Scope

This phase converts the already-qualified BPS Table 3.1.1 source contract into **canonical-format candidate rows**.

It does not freeze them into `data/processed` yet.

## Candidate semantics

Exactly 19 rows are emitted:

- `indicator_id=population_growth`;
- `claim_type=derived`;
- `unit=percent`;
- `frequency=annual` because the value is an annualized rate;
- `time_start=2010-05-15`;
- `time_end=2020-09-30`;
- `methodology_version=bps_geometric_lpp_sp2010_may_sp2020_september_v1`.

The date bounds preserve the actual intercensal interval while `frequency=annual` describes the annualized statistic.

## Provenance

One publication-level provenance row is shared by all 19 observations.

The provenance points to the durable qualified source contract:

`repo://data/registries/bps_population_growth_2010_2020_publication.csv`

Its `checksum_sha256` is the SHA-256 of that repository source-contract CSV. It is **not** presented as the checksum of the official BPS PDF.

`extraction_method=manual_transcription` is retained deliberately because the publication table was initially exposed through a full-text transcription carrier. Provenance notes state that:

- BPS is the source authority;
- the transcription carrier is not source authority;
- all values were cross-checked against official SP2010/SP2020 counts;
- all 19 rates match BPS's geometric formula for the 124-month May-2010 → September-2020 interval.

## Evidence class

The rates are official BPS-derived statistics. They are not:

- direct observed population counts;
- Ranah Observatory model estimates;
- custom rates substituted for the published BPS values.

The materializer copies the BPS-published two-decimal rates after the source-contract validator independently confirms formula consistency.

## Output candidate

CI produces:

- `bps-population-growth-observations.csv` — 19 rows;
- `bps-population-growth-provenance.csv` — 1 row;
- `bps-population-growth.manifest.json`.

The candidate manifest must retain:

`canonical_freeze_performed=false`.

The next micro-milestone may freeze these exact candidate files after artifact review and collision checks against the existing canonical BPS datasets.
