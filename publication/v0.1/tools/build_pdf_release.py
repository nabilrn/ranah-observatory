#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import shutil
import subprocess
from pathlib import Path

from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / "publication" / "v0.1"
PREPRINT_DIR = PUB / "preprint"
PREPRINT = PREPRINT_DIR / "preprint.md"
PREPRINT_MANIFEST = PREPRINT_DIR / "preprint-manifest.json"
RENDERED = PUB / "rendered"
RENDER_MANIFEST = RENDERED / "render-manifest.json"
METADATA = PUB / "submission" / "metadata.json"
CLAIM_LEDGER = PUB / "claim-ledger.csv"
DIST = PUB / "distribution"
PDF_NAME = "Ranah_Observatory_v0.1_Preprint_Nabil_Rizki_Navisa.pdf"
PDF_PATH = DIST / PDF_NAME

AUTHOR = "Nabil Rizki Navisa"
AFFILIATION = "Independent Researcher"
LICENSE = "CC BY 4.0"
RELEASE = "v0.1"
RELEASE_DATE = "2026-08-23"

TABLE_TITLES = {
    "T01": "Evidence and claim architecture",
    "T02": "Modern analytical panel and evidence expansion",
    "T03": "Expected performance reference and gap qualification",
    "T04": "Socioeconomic trajectory qualification results",
    "T05": "Predictive and climate negative-result qualification",
    "T06": "Post-M18 evidence expansion inventory",
    "T07": "Blocked claims and evidence required for upgrade",
}

BLOCKED_IDS = {
    "B01_MONETARY_WASTED_POTENTIAL",
    "B02_THEORETICAL_MAXIMUM",
    "B03_CAUSAL_RESIDUAL",
    "B04_GUARANTEED_POLICY_GAIN",
    "B05_CAUSAL_RAINFALL_UNEMPLOYMENT",
    "B06_EVENT_COUNTS_AS_IMPACT",
    "B07_COMPOSITE_DISASTER_RISK",
    "B08_SENSITIVITY_AS_POLICY_EFFECT",
    "B09_POLICY_RANKING",
}

CSS = r'''
@page { size: A4; margin: 19mm 17mm 20mm 18mm; @bottom-center { content: counter(page); font-size: 8pt; color: #555; } }
@page landscape-table { size: A4 landscape; margin: 13mm; @bottom-center { content: counter(page); font-size: 8pt; color: #555; } }
html { font-family: "DejaVu Sans", sans-serif; color: #111; font-size: 9.5pt; line-height: 1.5; }
body { max-width: 100%; }
h1 { font-size: 22pt; line-height: 1.15; margin: 0 0 10mm; letter-spacing: -0.3pt; }
h2 { font-size: 15pt; line-height: 1.25; margin-top: 8mm; break-after: avoid; border-bottom: 0.5pt solid #aaa; padding-bottom: 2mm; }
h3 { font-size: 11.5pt; line-height: 1.3; margin-top: 5mm; break-after: avoid; }
p { margin: 0 0 3.2mm; text-align: justify; hyphens: auto; }
blockquote { margin: 4mm 0; padding: 2.5mm 4mm; border-left: 2pt solid #555; background: #f5f5f5; }
blockquote p { text-align: left; margin: 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.2pt; background: #f3f3f3; padding: 0.2mm 0.6mm; border-radius: 1mm; overflow-wrap: anywhere; }
a { color: #111; text-decoration: underline; text-decoration-color: #999; overflow-wrap: anywhere; }
img { display: block; max-width: 100%; max-height: 225mm; margin: 5mm auto 3mm; object-fit: contain; }
nav#TOC { break-after: page; }
nav#TOC ul { padding-left: 5mm; }
nav#TOC li { margin: 1.2mm 0; }
nav#TOC a { text-decoration: none; }
#title-block-header { margin-top: 38mm; min-height: 165mm; break-after: page; text-align: left; }
#title-block-header .title { font-size: 27pt; line-height: 1.12; margin-bottom: 14mm; }
#title-block-header .author { font-size: 14pt; margin: 0 0 3mm; }
#title-block-header .date { font-size: 10pt; color: #444; max-width: 125mm; }
nav#TOC > h2 { border-bottom: 1pt solid #333; }
body > h1:first-of-type + p { font-size: 11pt; }
hr { border: 0; border-top: .5pt solid #aaa; }
.appendix-table { page: landscape-table; break-before: page; break-after: page; }
.appendix-table h3 { font-size: 12pt; margin: 0 0 4mm; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 5.7pt; line-height: 1.25; }
th, td { border: 0.35pt solid #999; padding: 1.1mm; vertical-align: top; overflow-wrap: anywhere; word-break: break-word; }
th { font-weight: 700; background: #ececec; }
tr { break-inside: avoid; }
@media print {
  h2, h3 { break-after: avoid-page; }
  figure, img { break-inside: avoid; }
}
'''


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def esc(value: str) -> str:
    return html.escape(str(value))


def table_html(path: Path, table_id: str) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows, path
    head, body = rows[0], rows[1:]
    parts = [
        f'<section class="appendix-table"><h3>Table {table_id} - {esc(TABLE_TITLES[table_id])}</h3>',
        "<table><thead><tr>",
    ]
    parts.extend(f"<th>{esc(cell.replace('_', ' '))}</th>" for cell in head)
    parts.append("</tr></thead><tbody>")
    for row in body:
        parts.append("<tr>")
        parts.extend(f"<td>{esc(cell)}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table></section>")
    return "".join(parts)


def validate_inputs() -> None:
    pre_manifest = json.loads(PREPRINT_MANIFEST.read_text(encoding="utf-8"))
    render_manifest = json.loads(RENDER_MANIFEST.read_text(encoding="utf-8"))
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))

    assert pre_manifest["author"] == AUTHOR
    assert pre_manifest["affiliation"] == AFFILIATION
    assert pre_manifest["publication_license"] == "CC-BY-4.0"
    assert pre_manifest["claim_upgrade_performed"] is False
    assert set(pre_manifest["blocked_claims_retained"]) == BLOCKED_IDS

    assert render_manifest["table_count"] == 7
    assert render_manifest["figure_count"] == 6
    assert render_manifest["new_source_acquisition"] is False
    assert render_manifest["new_statistical_or_ml_model_fit"] is False

    assert metadata["authors"] == [{"affiliation": AFFILIATION, "name": AUTHOR, "role": "author"}]
    assert metadata["publication_license"] == "CC-BY-4.0"
    assert metadata["claim_upgrade_performed"] is False

    with CLAIM_LEDGER.open(encoding="utf-8", newline="") as handle:
        ledger = list(csv.DictReader(handle))
    blocked = {row["claim_id"] for row in ledger if row["state"] == "blocked"}
    assert blocked == BLOCKED_IDS

    assert len(list((RENDERED / "figures").glob("F*.svg"))) == 6
    assert len(list((RENDERED / "tables").glob("T*.csv"))) == 7


def build_pdf() -> None:
    raw = PREPRINT.read_text(encoding="utf-8")
    raw_lines = raw.splitlines()
    assert raw_lines and raw_lines[0].startswith("# Ranah Observatory:")
    assert all(blocked in raw for blocked in BLOCKED_IDS)

    title = raw_lines[0].removeprefix("# ").strip()
    body = "\n".join(raw_lines[6:]).lstrip() + "\n"
    text = (
        "---\n"
        f'title: "{title}"\n'
        f'author: "{AUTHOR}"\n'
        f'date: "{AFFILIATION} - Technical report / preprint {RELEASE} - {RELEASE_DATE} - {LICENSE}"\n'
        "---\n\n"
        + body
    )

    appendix = [
        "\n\n## Appendix A. Canonical publication tables\n",
        "The tables below reproduce the deterministic M30 CSV assets for print readability. They add no analysis and preserve the source values exactly.\n",
    ]
    for path in sorted((RENDERED / "tables").glob("T*.csv")):
        table_id = path.name.split("-")[0]
        appendix.append(table_html(path, table_id))
    text += "\n".join(appendix) + "\n"

    work_md = PREPRINT_DIR / ".m34-pdf-work.md"
    work_html = PREPRINT_DIR / ".m34-pdf-work.html"
    work_css = PREPRINT_DIR / ".m34-pdf-work.css"
    work_md.write_text(text, encoding="utf-8")
    work_css.write_text(CSS, encoding="utf-8")

    try:
        subprocess.run(
            [
                "pandoc",
                work_md.name,
                "-f",
                "gfm+raw_html",
                "-t",
                "html5",
                "--standalone",
                "--toc",
                "--toc-depth=2",
                "--metadata",
                "pagetitle=Ranah Observatory v0.1",
                "--css",
                work_css.name,
                "-o",
                work_html.name,
            ],
            check=True,
            cwd=PREPRINT_DIR,
            env={**os.environ, "SOURCE_DATE_EPOCH": "1787490000"},
        )
        HTML(filename=str(work_html), base_url=str(PREPRINT_DIR)).write_pdf(str(PDF_PATH))
    finally:
        for path in (work_md, work_html, work_css):
            path.unlink(missing_ok=True)


def write_distribution_metadata() -> None:
    readme = f"""# Ranah Observatory {RELEASE} distribution bundle

Author: **{AUTHOR}**  
Affiliation: **{AFFILIATION}**  
Release date: **{RELEASE_DATE}**  
License: **{LICENSE}**  
Target preprint repository: **Zenodo**

This directory is the deterministic print/distribution layer for the certified Ranah Observatory v0.1 publication package.

## Included

- `{PDF_NAME}` — final citation-ready PDF preprint;
- `SHA256SUMS.txt` — portable checksum list;
- `distribution-manifest.json` — source/output integrity and scientific-boundary contract.

The PDF is typeset from `publication/v0.1/preprint/preprint.md` and embeds the six canonical M30 SVG figures plus a print appendix reproducing all seven canonical M30 CSV tables. It does not introduce new analysis or stronger claim states.

The scientific authority remains the M29 claim ledger and frozen manuscript. ORCID, public corresponding-author contact, and DOI remain unset until supplied or created through an external deposit.
"""
    (DIST / "README.md").write_text(readme, encoding="utf-8")

    sums = [
        f"{sha256(PDF_PATH)}  {PDF_NAME}",
        f"{sha256(DIST / 'README.md')}  README.md",
    ]
    (DIST / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    source_paths = [
        "publication/v0.1/claim-ledger.csv",
        "publication/v0.1/preprint/preprint.md",
        "publication/v0.1/preprint/preprint-manifest.json",
        "publication/v0.1/rendered/render-manifest.json",
        "publication/v0.1/submission/metadata.json",
    ]
    output_paths = [PDF_PATH, DIST / "README.md", DIST / "SHA256SUMS.txt"]
    manifest = {
        "schema": "ranah-observatory/publication-v0.1-distribution-manifest/v1",
        "release": RELEASE,
        "release_date": RELEASE_DATE,
        "builder": "publication/v0.1/tools/build_pdf_release.py",
        "author": AUTHOR,
        "affiliation": AFFILIATION,
        "publication_license": "CC-BY-4.0",
        "target_repository": "Zenodo",
        "pdf": PDF_NAME,
        "canonical_table_count": 7,
        "canonical_figure_count": 6,
        "new_analytical_source_acquisition": False,
        "new_statistical_or_ml_model_fit": False,
        "claim_upgrade_performed": False,
        "blocked_claims_retained": sorted(BLOCKED_IDS),
        "source_sha256": {rel: sha256(ROOT / rel) for rel in source_paths},
        "output_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in output_paths},
    }
    (DIST / "distribution-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    validate_inputs()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    build_pdf()
    write_distribution_metadata()
    print(
        {
            "distribution_outputs": 4,
            "pdf": PDF_NAME,
            "pdf_sha256": sha256(PDF_PATH),
            "tables": 7,
            "figures": 6,
            "author": AUTHOR,
            "claim_upgrade": False,
        }
    )


if __name__ == "__main__":
    main()
