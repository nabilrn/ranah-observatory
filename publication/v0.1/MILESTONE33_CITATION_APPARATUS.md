# Milestone 33 — Bibliography and citation apparatus

## Purpose

M33 adds an editorial citation layer above the frozen Ranah Observatory v0.1 scientific package. It makes the technical report easier to cite, inspect, and deposit without changing any analytical result, claim state, model, data value, or canonical publication asset.

## Inputs that remain authoritative

- `publication/v0.1/manuscript.md` — frozen scientific prose and claim IDs;
- `publication/v0.1/submission/manuscript-with-assets.md` — M31 manuscript plus canonical table/figure callouts;
- `publication/v0.1/claim-ledger.csv` — authoritative claim states;
- `publication/v0.1/AUTHORSHIP.md` — confirmed author identity;
- `publication/v0.1/submission/metadata.json` — v0.1 deposit metadata.

M33 does not edit those scientific inputs. The new citation-ready manuscript is generated under `publication/v0.1/preprint/`.

## Citation classes

M33 introduces documentation references in two bounded classes:

1. **source documentation** — official or primary documentation for the source families already present in the frozen evidence base, including BPS, BIG, CHIRPS, DJPK, BKPM, BNPB/InaRISK/DIBI, and USGS;
2. **method documentation** — primary literature for statistical methods explicitly used by the frozen analytical pipeline, including Mann–Kendall, Theil–Sen, Hamed–Rao adjustment, Holm correction, and Pettitt change-point testing.

These references explain provenance and methods. They are not new observations and cannot upgrade a scientific claim.

## Outputs

M33 materializes:

- repository-root `CITATION.cff` for GitHub citation discovery;
- `publication/v0.1/references.bib` as the archival bibliography;
- `publication/v0.1/reference-map.csv` binding references to manuscript sections and citation roles;
- `publication/v0.1/preprint/preprint.md` as an editorially cited derivative of the certified manuscript-with-assets;
- `publication/v0.1/preprint/references.md` as the deterministic human-readable bibliography;
- `publication/v0.1/preprint/reference-map.csv` as the canonical materialized reference map;
- `publication/v0.1/preprint/README.md` describing the layer boundary;
- `publication/v0.1/preprint/preprint-manifest.json` binding inputs and outputs by SHA-256.

## Scientific boundary

M33 performs no analytical source acquisition, source-value replacement, imputation, data transformation, model fitting or refitting, statistical search, forecast qualification, causal upgrade, monetary aggregation, composite scoring, or policy ranking.

Literature and source-documentation acquisition is explicitly editorial. It does not alter the frozen evidence base. The M29 claim ledger remains authoritative, including all required negative results and all nine blocked M18 claims.

## Completion gate

M33 completes only when:

- the citation registry and bibliography contain the same 16 reference IDs;
- all references are bound to a documented source or method role;
- the generated preprint preserves the certified manuscript text and only adds authorship/citation/reference apparatus;
- the confirmed author remains Nabil Rizki Navisa, Independent Researcher;
- the v0.1 publication license remains CC BY 4.0;
- all nine blocked claim IDs remain present;
- generated preprint outputs rebuild byte-for-byte in read-only CI;
- M29 and M31 certification remain green;
- no upstream analytical artifact changes.
