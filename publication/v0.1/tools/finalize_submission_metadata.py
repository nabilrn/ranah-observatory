#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

import build_submission

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / "publication" / "v0.1"
SUB = PUB / "submission"
AUTHOR_DISPLAY = "Nabil Rizki Navisa"
AUTHOR_ZENODO = "Navisa, Nabil Rizki"
AFFILIATION = "Independent Researcher"
LICENSE_ID = "CC-BY-4.0"
PUBLICATION_DATE = "2026-08-23"


def abstract_from_manuscript(text: str) -> str:
    match = re.search(r"## Abstract\n\n(.*?)(?=\n## 1\.)", text, flags=re.S)
    assert match, "abstract section not found"
    abstract = re.sub(r"\s*`\[[A-Z0-9_]+\]`", "", match.group(1))
    abstract = re.sub(r"\s+", " ", abstract).strip()
    return abstract


def sha256(path: Path) -> str:
    return build_submission.sha256(path)


def main() -> None:
    build_submission.main()

    metadata_path = SUB / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "status": "preprint_deposit_ready",
            "author_record_status": "confirmed",
            "authors": [
                {
                    "name": AUTHOR_DISPLAY,
                    "affiliation": AFFILIATION,
                    "role": "author",
                }
            ],
            "corresponding_author_name": AUTHOR_DISPLAY,
            "corresponding_author_contact": None,
            "publication_license": LICENSE_ID,
            "target_repository": "Zenodo",
            "venue": "Zenodo",
            "publication_date": PUBLICATION_DATE,
            "orcid": None,
            "doi": None,
            "pending_human_confirmation": [
                "ORCID if available",
                "corresponding-author contact before external deposit",
                "DOI after Zenodo publication",
            ],
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manuscript = (PUB / "manuscript.md").read_text(encoding="utf-8")
    zenodo = {
        "metadata": {
            "upload_type": "publication",
            "publication_type": "preprint",
            "publication_date": PUBLICATION_DATE,
            "title": metadata["title"],
            "creators": [
                {
                    "name": AUTHOR_ZENODO,
                    "affiliation": AFFILIATION,
                }
            ],
            "description": abstract_from_manuscript(manuscript),
            "access_right": "open",
            "license": "cc-by-4.0",
            "keywords": metadata["keywords"],
            "version": metadata["release"],
            "language": "eng",
        }
    }
    (SUB / "zenodo-deposit.json").write_text(json.dumps(zenodo, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    readme = (SUB / "README.md").read_text(encoding="utf-8")
    readme = readme.replace(
        "## Human confirmation still required before external submission\n\nFinal author/affiliation formatting, ORCID if used, corresponding-author contact, publication license, target venue/deposit repository, DOI, and venue-specific formatting remain intentionally unset in `metadata.json`.\n",
        "## Authorship and deposit target\n\nAuthor: **Nabil Rizki Navisa**  \nAffiliation: **Independent Researcher**  \nTarget repository: **Zenodo**  \nResource type: **Publication / Preprint**  \nLicense: **CC BY 4.0**\n\n`zenodo-deposit.json` contains a ready-to-use deposit metadata payload. ORCID and corresponding-author contact remain unset rather than guessed; the DOI remains unset until Zenodo publishes the record.\n",
    )
    (SUB / "README.md").write_text(readme, encoding="utf-8")

    manifest_path = SUB / "submission-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["builder"] = "publication/v0.1/tools/finalize_submission_metadata.py"
    manifest["author_record_status"] = "confirmed"
    manifest["publication_license"] = LICENSE_ID
    manifest["target_repository"] = "Zenodo"
    manifest["source_sha256"]["publication/v0.1/tools/finalize_submission_metadata.py"] = sha256(
        PUB / "tools" / "finalize_submission_metadata.py"
    )
    output_paths = sorted(p for p in SUB.iterdir() if p.is_file() and p.name != "submission-manifest.json")
    manifest["output_sha256"] = {str(path.relative_to(ROOT)): sha256(path) for path in output_paths}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        {
            "author": AUTHOR_DISPLAY,
            "affiliation": AFFILIATION,
            "license": LICENSE_ID,
            "target": "Zenodo publication/preprint",
            "orcid": "unset",
            "doi": "pending deposit",
        }
    )


if __name__ == "__main__":
    main()
