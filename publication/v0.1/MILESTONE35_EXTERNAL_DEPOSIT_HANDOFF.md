# Milestone 35 — External Deposit Handoff

## Purpose

M35 creates a deterministic handoff between the already-certified v0.1 publication package and any later external publication action.

It does **not** publish to Zenodo, create a GitHub Release, claim a DOI, or authorize any external action.

## Locked inputs

M35 consumes only already-frozen publication artifacts:

- `publication/v0.1/submission/metadata.json`;
- `publication/v0.1/submission/zenodo-deposit.json`;
- `publication/v0.1/distribution/distribution-manifest.json`;
- `publication/v0.1/distribution/Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf`;
- `publication/v0.1/distribution/SHA256SUMS.txt`.

The M34 PDF distribution freeze commit is `cbdadc11de3e37995ad5ebeb97727edd5824401d`.

## Handoff semantics

The machine-readable handoff must remain fail-closed:

- `external_publish_authorized=false`;
- `external_deposit_performed=false`;
- `github_release_performed=false`;
- corresponding-author contact remains pending until explicitly confirmed;
- DOI remains pending until an external repository actually assigns one;
- ORCID is optional and remains unset unless the author supplies it.

M35 therefore distinguishes publication readiness from publication authorization.

## Required outputs

Under `publication/v0.1/deposit/`:

1. `deposit-handoff.json` — machine-readable binding of canonical PDF, frozen metadata, hashes, blockers, and publication sequence;
2. `CHECKLIST.md` — human pre-deposit checklist;
3. `README.md` — handoff usage and boundary statement;
4. `release-notes.md` — candidate release/deposit description only.

## Hard blockers

M35 records exactly two hard blockers before external publication:

1. explicit author instruction to publish/deposit externally;
2. confirmed corresponding-author contact.

ORCID is optional and DOI is a post-deposit field, not a reason to rewrite scientific content.

## Scientific boundary

M35 performs no:

- analytical source acquisition;
- source substitution or imputation;
- statistical or ML model fit/refit;
- forecast qualification;
- causal upgrade;
- monetary aggregation;
- composite disaster-risk synthesis;
- policy ranking;
- redistribution of third-party source datasets.

The M29 claim ledger remains the scientific authority, including all nine blocked M18 claims.

## External-action boundary

The recommended later sequence is:

1. confirm corresponding-author contact and explicit publication authorization;
2. create a Zenodo draft record without publishing it;
3. upload the canonical PDF and checksum file;
4. apply the frozen Zenodo metadata, allowing only confirmed contact/ORCID additions;
5. verify title, creator, affiliation, version, license, access right, and PDF SHA-256;
6. publish only after explicit author authorization;
7. capture the assigned DOI in a new audited repository commit.

M35 itself stops before step 2.
