#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / "publication" / "v0.1"
SUB = PUB / "submission"

SOURCE_PATHS = [
    "publication/v0.1/manuscript.md",
    "publication/v0.1/release-manifest.json",
    "publication/v0.1/claim-ledger.csv",
    "publication/v0.1/table-plan.csv",
    "publication/v0.1/figure-plan.csv",
    "publication/v0.1/rendered/render-manifest.json",
]

TABLE_FILES = {
    "T01": "T01-evidence-claim-architecture.csv",
    "T02": "T02-modern-panel-evidence-expansion.csv",
    "T03": "T03-expected-reference-gap-qualification.csv",
    "T04": "T04-socioeconomic-trajectory-qualification.csv",
    "T05": "T05-predictive-climate-negative-results.csv",
    "T06": "T06-post-M18-evidence-expansion.csv",
    "T07": "T07-blocked-claims-upgrade-boundaries.csv",
}
FIGURE_FILES = {
    "F01": "F01-evidence-chain.svg",
    "F02": "F02-gap-qualification.svg",
    "F03": "F03-trajectory-matrix.svg",
    "F04": "F04-forecast-benchmark-failure.svg",
    "F05": "F05-rainfall-qualification.svg",
    "F06": "F06-evidence-expansion.svg",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def insert_after_heading(text: str, heading: str, block: str) -> str:
    marker = heading + "\n"
    assert marker in text, f"required manuscript heading missing: {heading}"
    return text.replace(marker, marker + "\n" + block.strip() + "\n", 1)


def build_asset_index(tables: list[dict[str, str]], figures: list[dict[str, str]], render: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in tables:
        asset_id = row["table_id"]
        filename = TABLE_FILES[asset_id]
        rel = f"publication/v0.1/rendered/tables/{filename}"
        rows.append({
            "asset_id": asset_id,
            "asset_type": "table_csv",
            "title": row["title"],
            "purpose": row["purpose"],
            "canonical_path": rel,
            "claim_ids": row["claim_ids"],
            "status": row["status"],
            "sha256": render["output_sha256"][rel],
        })
    for row in figures:
        asset_id = row["figure_id"]
        filename = FIGURE_FILES[asset_id]
        rel = f"publication/v0.1/rendered/figures/{filename}"
        rows.append({
            "asset_id": asset_id,
            "asset_type": "figure_svg",
            "title": row["title"],
            "purpose": row["purpose"],
            "canonical_path": rel,
            "claim_ids": row["claim_ids"],
            "status": row["status"],
            "sha256": render["output_sha256"][rel],
        })
    return rows


def build_manuscript(source: str, tables: list[dict[str, str]], figures: list[dict[str, str]]) -> str:
    text = insert_after_heading(
        source,
        "## 2. Evidence architecture and data regimes",
        "> **Canonical publication assets for this section:** Figure F01 (evidence chain), Table T01 (evidence/claim architecture), and Table T02 (modern panel/evidence expansion).",
    )
    text = insert_after_heading(
        text,
        "## 4. Results",
        "> **Canonical result assets:** Table T03 and Figure F02 (expected performance/reference/gap qualification); Table T04 and Figure F03 (modern trajectories); Table T05 with Figures F04–F05 (forecast and climate qualification); Table T06 and Figure F06 (post-M18 evidence expansion).",
    )

    lines = ["", "## Canonical publication tables and figures", ""]
    lines.append("The assets below are deterministic renderings of the frozen evidence package. They do not introduce new analyses or stronger claim states.")
    lines.append("")
    for row in tables:
        asset_id = row["table_id"]
        filename = TABLE_FILES[asset_id]
        lines += [f"### Table {asset_id} — {row['title']}", "", f"[Open canonical CSV](../rendered/tables/{filename})", ""]
    for row in figures:
        asset_id = row["figure_id"]
        filename = FIGURE_FILES[asset_id]
        lines += [f"### Figure {asset_id} — {row['title']}", "", f"![Figure {asset_id} — {row['title']}](../rendered/figures/{filename})", ""]
    return text.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if SUB.exists():
        shutil.rmtree(SUB)
    SUB.mkdir(parents=True)

    release = json.loads((PUB / "release-manifest.json").read_text(encoding="utf-8"))
    render = json.loads((PUB / "rendered" / "render-manifest.json").read_text(encoding="utf-8"))
    tables = read_csv(PUB / "table-plan.csv")
    figures = read_csv(PUB / "figure-plan.csv")
    assert len(tables) == 7 and all(row["status"] == "materialized" for row in tables)
    assert len(figures) == 6 and all(row["status"] == "materialized" for row in figures)

    assets = build_asset_index(tables, figures, render)
    write_csv(
        SUB / "asset-index.csv",
        ["asset_id", "asset_type", "title", "purpose", "canonical_path", "claim_ids", "status", "sha256"],
        assets,
    )

    source_manuscript = (PUB / "manuscript.md").read_text(encoding="utf-8")
    (SUB / "manuscript-with-assets.md").write_text(build_manuscript(source_manuscript, tables, figures), encoding="utf-8")

    metadata = {
        "schema": "ranah-observatory/publication-v0.1-submission-metadata/v1",
        "release": "v0.1",
        "publication_type": release["publication_type"],
        "status": "preprint_submission_package_candidate",
        "title": release["working_title"],
        "repository": "https://github.com/nabilrn/ranah-observatory",
        "frozen_research_base_commit": release["frozen_research_base_commit"],
        "publication_asset_base_commit": "a1a1c63749624d4d0a29c6b19720711889577629",
        "research_scope": release["research_scope"],
        "keywords": [
            "West Sumatra",
            "development gaps",
            "reproducible research",
            "socioeconomic trajectories",
            "empirical benchmarking",
            "climate variability",
            "disaster risk",
            "negative results",
        ],
        "canonical_table_count": 7,
        "canonical_figure_count": 6,
        "author_record_status": "pending_final_confirmation",
        "venue": None,
        "doi": None,
        "publication_license": None,
        "orcid": None,
        "corresponding_author_contact": None,
        "pending_human_confirmation": [
            "final author name and affiliation formatting",
            "ORCID if available",
            "corresponding-author contact",
            "publication license",
            "target venue or repository",
            "DOI after deposit or acceptance",
            "venue-specific manuscript style",
        ],
        "scientific_claim_source": "publication/v0.1/manuscript.md",
        "integrated_manuscript": "publication/v0.1/submission/manuscript-with-assets.md",
        "new_source_acquisition": False,
        "new_statistical_or_ml_model_fit": False,
        "claim_upgrade_performed": False,
    }
    (SUB / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    readme = """# Ranah Observatory v0.1 submission package

This directory is generated from the certified v0.1 scientific manuscript and the canonical M30 publication assets. It is a portable preprint/submission-facing layer, not a new analysis.

## Included

- `manuscript-with-assets.md` — scientific manuscript plus deterministic canonical table/figure callouts;
- `asset-index.csv` — all seven tables and six figures with claim bindings and SHA-256 identities;
- `metadata.json` — stable release metadata plus fields that still require human confirmation;
- `submission-manifest.json` — checksums binding package inputs and generated outputs.

## Scientific boundary

The frozen evidence base and claim ledger remain authoritative. This package does not authorize monetary wasted-potential aggregation, causal upgrades, qualified 2026 forecasts, composite disaster-risk scoring, treatment-effect interpretation of predictive sensitivity, or policy/cost-benefit ranking.

## Human confirmation still required before external submission

Final author/affiliation formatting, ORCID if used, corresponding-author contact, publication license, target venue/deposit repository, DOI, and venue-specific formatting remain intentionally unset in `metadata.json`.
"""
    (SUB / "README.md").write_text(readme, encoding="utf-8")

    output_paths = sorted(p for p in SUB.iterdir() if p.is_file() and p.name != "submission-manifest.json")
    manifest = {
        "schema": "ranah-observatory/publication-v0.1-submission-manifest/v1",
        "release": "v0.1",
        "builder": "publication/v0.1/tools/build_submission.py",
        "asset_count": 13,
        "table_count": 7,
        "figure_count": 6,
        "new_source_acquisition": False,
        "new_statistical_or_ml_model_fit": False,
        "claim_upgrade_performed": False,
        "source_sha256": {rel: sha256(ROOT / rel) for rel in SOURCE_PATHS},
        "output_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in output_paths},
    }
    (SUB / "submission-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print({"submission_outputs": 5, "indexed_assets": 13, "tables": 7, "figures": 6})


if __name__ == "__main__":
    main()
