#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deposit"
M34_FREEZE_COMMIT = "cbdadc11de3e37995ad5ebeb97727edd5824401d"
PDF_REL = "publication/v0.1/distribution/Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf"
META_REL = "publication/v0.1/submission/metadata.json"
ZENODO_REL = "publication/v0.1/submission/zenodo-deposit.json"
DIST_MANIFEST_REL = "publication/v0.1/distribution/distribution-manifest.json"


def repo_root() -> Path:
    return ROOT.parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(rel: str) -> dict:
    return json.loads((repo_root() / rel).read_text(encoding="utf-8"))


def write_text(name: str, text: str) -> None:
    (OUT / name).write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    meta = load_json(META_REL)
    zenodo = load_json(ZENODO_REL)
    dist = load_json(DIST_MANIFEST_REL)
    zmeta = zenodo["metadata"]

    assert meta["release"] == "v0.1"
    assert meta["author_record_status"] == "confirmed"
    assert meta["authors"] == [{"affiliation": "Independent Researcher", "name": "Nabil Rizki Navisa", "role": "author"}]
    assert meta["target_repository"] == "Zenodo"
    assert meta["publication_license"] == "CC-BY-4.0"
    assert meta["claim_upgrade_performed"] is False
    assert meta["new_source_acquisition"] is False
    assert meta["new_statistical_or_ml_model_fit"] is False
    assert meta["corresponding_author_contact"] is None
    assert meta["doi"] is None

    assert zmeta["upload_type"] == "publication"
    assert zmeta["publication_type"] == "preprint"
    assert zmeta["access_right"] == "open"
    assert zmeta["license"] == "cc-by-4.0"
    assert zmeta["version"] == "v0.1"
    assert zmeta["creators"] == [{"affiliation": "Independent Researcher", "name": "Navisa, Nabil Rizki"}]

    assert dist["release"] == "v0.1"
    assert dist["author"] == "Nabil Rizki Navisa"
    assert dist["affiliation"] == "Independent Researcher"
    assert dist["publication_license"] == "CC-BY-4.0"
    assert dist["target_repository"] == "Zenodo"
    assert dist["claim_upgrade_performed"] is False
    assert dist["new_analytical_source_acquisition"] is False
    assert dist["new_statistical_or_ml_model_fit"] is False
    assert len(dist["blocked_claims_retained"]) == 9

    expected_pdf_sha = dist["output_sha256"][PDF_REL]
    pdf_path = repo_root() / PDF_REL
    if pdf_path.exists():
        actual_pdf_sha = sha256(pdf_path)
        assert actual_pdf_sha == expected_pdf_sha, (actual_pdf_sha, expected_pdf_sha)

    source_sha = {
        META_REL: sha256(repo_root() / META_REL),
        ZENODO_REL: sha256(repo_root() / ZENODO_REL),
        DIST_MANIFEST_REL: sha256(repo_root() / DIST_MANIFEST_REL),
    }

    hard_blockers = [
        {
            "id": "explicit_external_publish_authorization",
            "status": "pending",
            "reason": "External publication is irreversible enough to require an explicit author instruction to publish/deposit.",
        },
        {
            "id": "corresponding_author_contact",
            "status": "pending",
            "reason": "M32 intentionally left corresponding_author_contact unset for confirmation before external deposit.",
        },
    ]

    handoff = {
        "schema": "ranah-observatory/publication-v0.1-external-deposit-handoff/v1",
        "release": "v0.1",
        "status": "awaiting_explicit_external_authorization",
        "distribution_freeze_commit": M34_FREEZE_COMMIT,
        "target_repository": "Zenodo",
        "external_publish_authorized": False,
        "external_deposit_performed": False,
        "github_release_performed": False,
        "author": "Nabil Rizki Navisa",
        "affiliation": "Independent Researcher",
        "orcid": meta["orcid"],
        "corresponding_author_contact": meta["corresponding_author_contact"],
        "doi": meta["doi"],
        "publication_license": "CC-BY-4.0",
        "canonical_pdf": {
            "path": PDF_REL,
            "sha256": expected_pdf_sha,
        },
        "zenodo_metadata": {
            "path": ZENODO_REL,
            "sha256": source_sha[ZENODO_REL],
            "upload_type": zmeta["upload_type"],
            "publication_type": zmeta["publication_type"],
            "access_right": zmeta["access_right"],
            "license": zmeta["license"],
        },
        "submission_metadata": {
            "path": META_REL,
            "sha256": source_sha[META_REL],
        },
        "distribution_manifest": {
            "path": DIST_MANIFEST_REL,
            "sha256": source_sha[DIST_MANIFEST_REL],
        },
        "recommended_upload_set": [
            PDF_REL,
            "publication/v0.1/distribution/SHA256SUMS.txt",
        ],
        "hard_blockers": hard_blockers,
        "optional_predeposit_enrichment": [
            {"id": "orcid", "status": "unset_optional", "value": meta["orcid"]}
        ],
        "post_deposit_fields": [
            {"id": "doi", "status": "pending_deposit", "value": meta["doi"]}
        ],
        "publish_sequence": [
            "Confirm corresponding-author contact and explicit authorization to publish externally.",
            "Create a Zenodo draft record without publishing it.",
            "Upload the canonical PDF and SHA256SUMS.txt only; do not silently redistribute third-party source datasets.",
            "Apply publication/v0.1/submission/zenodo-deposit.json metadata verbatim except confirmed contact/ORCID additions.",
            "Verify title, creator, affiliation, version, license, access right, and canonical PDF SHA-256 before publication.",
            "Publish the Zenodo record only after explicit author authorization.",
            "Capture the assigned DOI and update repository publication metadata in a new audited commit.",
        ],
        "science_boundary": {
            "new_analytical_source_acquisition": False,
            "new_statistical_or_ml_model_fit": False,
            "claim_upgrade_performed": False,
            "blocked_claim_count_retained": 9,
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_text("deposit-handoff.json", json.dumps(handoff, indent=2, ensure_ascii=False, sort_keys=True))

    checklist = """# Ranah Observatory v0.1 external-deposit checklist

This checklist is a handoff artifact, not authorization to publish.

## Hard blockers before any external publication

- [ ] Receive explicit author instruction to publish/deposit v0.1 externally.
- [ ] Confirm the corresponding-author contact that may be used for the external record.

## Optional before deposit

- [ ] Add ORCID if the author wants it attached to the record.

## Frozen artifacts to verify

- [x] Canonical PDF: `publication/v0.1/distribution/Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf`
- [x] Canonical PDF SHA-256: `5325b209acb37d622151fe2ce898edd28e5d25bf4176d660e50754cae06e888a`
- [x] Zenodo metadata: `publication/v0.1/submission/zenodo-deposit.json`
- [x] Distribution manifest and checksums are committed.
- [x] M29 scientific claim freeze remains authoritative.
- [x] All nine M18 blocked claims remain blocked.

## Draft/deposit sequence

1. Create a Zenodo draft record; do not publish yet.
2. Upload the canonical PDF and `SHA256SUMS.txt`.
3. Apply the frozen Zenodo metadata.
4. Verify creator, affiliation, version, CC BY 4.0 license, open access, title, and PDF checksum.
5. Publish only after explicit author authorization.
6. Record the DOI in the repository after Zenodo assigns it.

## Not authorized by this handoff

This handoff does not authorize a GitHub Release, Zenodo publication, DOI claim, new analysis, claim upgrade, source-data redistribution, or policy/monetary interpretation.
"""
    write_text("CHECKLIST.md", checklist)

    readme = """# Ranah Observatory v0.1 deposit handoff

This directory binds the already-certified v0.1 PDF distribution to the already-frozen Zenodo metadata and makes the remaining human/external actions explicit.

The package is intentionally fail-closed: `external_publish_authorized=false`, `external_deposit_performed=false`, and `github_release_performed=false` until an explicit author instruction changes the publication state.

Use `deposit-handoff.json` as the machine-readable handoff, `CHECKLIST.md` before any external action, and `release-notes.md` as a candidate description only. The scientific authority remains the M29 claim ledger and the M34 canonical PDF distribution.
"""
    write_text("README.md", readme)

    release_notes = f"""# Ranah Observatory v0.1 — candidate release notes

**Ranah Observatory: A Reproducible Evidence Framework for Development Gaps, Socioeconomic Trajectories, and Climate-Disaster Constraints in West Sumatra**

Author: Nabil Rizki Navisa  
Affiliation: Independent Researcher  
License: CC BY 4.0  
Status: preprint deposit candidate; not externally published by M35

## What v0.1 contains

- a reproducible claim-gated evidence framework for West Sumatra;
- bounded expected-performance and empirical-reference analyses;
- modern socioeconomic trajectory qualification;
- climate, disaster, public-finance, investment, and national-comparator context;
- explicit retention of negative results and unresolved evidence;
- seven canonical tables and six canonical figures;
- a 24-page canonical PDF preprint.

## Important scientific boundaries

v0.1 does **not** provide a definitive monetary value of “wasted potential,” treat empirical favorable references as theoretical maxima, interpret predictive residuals causally, claim rainfall causes unemployment differences, synthesize incomplete disaster components into a risk score, reinterpret predictive sensitivities as treatment effects, or rank policies by expected return.

Canonical PDF SHA-256: `{expected_pdf_sha}`

This text is a release-note candidate only. M35 does not publish a GitHub Release or Zenodo record.
"""
    write_text("release-notes.md", release_notes)

    print({
        "deposit_outputs": 4,
        "status": handoff["status"],
        "hard_blockers": len(hard_blockers),
        "canonical_pdf_sha256": expected_pdf_sha,
        "external_publish_authorized": False,
    })


if __name__ == "__main__":
    main()
