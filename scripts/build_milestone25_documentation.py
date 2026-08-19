#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/manifests/milestone25_djpk_public_finance_complete.json"
TAXONOMY = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
PANEL = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json"
OUT = ROOT / "docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md"

DISPLAY = {
    "total_revenue": "Total revenue",
    "own_source_revenue_pad": "Own-source revenue (PAD)",
    "total_expenditure": "Total expenditure",
    "capital_expenditure": "Capital expenditure",
    "central_transfer_revenue": "Central-government transfer revenue",
}


def build() -> str:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    panel = json.loads(PANEL.read_text(encoding="utf-8"))
    if final.get("schema") != "ranah-observatory/milestone25-djpk-public-finance-complete/v2":
        raise ValueError("unexpected M25 completion schema")
    if final.get("milestone25_complete") is not True:
        raise ValueError("M25 is not complete")
    if panel.get("schema") != "ranah-observatory/djpk-fiscal-panel/v2":
        raise ValueError("unexpected M25 panel schema")
    results = {row["conceptual_family"]: row for row in taxonomy["conceptual_account_family_results"]}
    promoted = list(final["promoted_exact_label_families"])
    held = list(final["held_families"])

    lines: list[str] = [
        "# Milestone 25 — DJPK/SIKD Public-Finance Panel",
        "",
        "Status: **complete for the preregistered exact-label fiscal subset; taxonomy-ambiguous transfer evidence remains held**.",
        "",
        "M25 adds a district/city fiscal evidence layer for all 19 current West Sumatra kabupaten/kota over 2018–2025. The fiscal account taxonomy was locked on Kota Padang before values from the other 18 local governments were inspected.",
        "",
        "## Frozen evidence footprint",
        "",
        f"- **{final['geography_count']}** kabupaten/kota;",
        f"- **{final['year_count']}** fiscal years ({final['start_year']}–{final['end_year']});",
        f"- **{final['jurisdiction_year_count']}** jurisdiction-year records;",
        f"- **{final['promoted_exact_label_family_count']}** exact-label fiscal account families promoted;",
        f"- **{final['observation_count']}** canonical fiscal observations;",
        f"- **{final['provenance_count']}** jurisdiction-year provenance records;",
        f"- **{final['frozen_stage0_page_count']}** frozen Stage 0 taxonomy-reference HTML pages;",
        f"- **{final['frozen_stage1_html_page_count']}** frozen Stage 1 HTML semantic snapshots;",
        f"- **{final['frozen_stage1_spreadsheetml_count']}** frozen official DJPK SpreadsheetML exports;",
        f"- HTML postur tables were parseable for **{final['html_table_parseable_page_count']}** of 152 jurisdiction-years and structurally unavailable for **{final['html_table_unparseable_page_count']}**; unparseable HTML tables do not substitute or fabricate values.",
        "",
        "All canonical values are December fiscal realizations normalized to **IDR billion** from exact rupiah values in the official same-selector `csv_apbd` SpreadsheetML export. No imputation, historical-boundary reconstruction, explicit taxonomy bridge, derived fiscal ratio, or statistical model is part of M25.",
        "",
        "## Why two official representations are retained",
        "",
        "The DJPK APBD HTML page carries jurisdiction identity, fiscal year, December-realization semantics, and the link to the corresponding export. During qualification, the body-table markup proved structurally inconsistent across the full historical footprint. M25 therefore records a representation-only transport amendment: the scientific scope and account contracts stay unchanged, while exact numeric evidence is taken from the official SpreadsheetML export exposed by that same HTML page and selector set.",
        "",
        "For pages where the HTML postur table is parseable, each promoted account is cross-checked against the exact export value within the rounding tolerance implied by the two-decimal HTML display. Where the body table is not parseable, the page can qualify only when jurisdiction/year/December semantics and the exact same-selector export link remain verifiable.",
        "",
        "## Exact-label families promoted",
        "",
    ]
    for family in promoted:
        tax = results[family]
        lines.append(
            f"- `{family}` — {DISPLAY.get(family, family)}; Stage 0 status `{tax['status']}`; source label(s): `{tax.get('source_labels', '')}`."
        )

    lines += ["", "## Families held from the exact panel", ""]
    for family in held:
        tax = results[family]
        lines.append(
            f"- `{family}` — {DISPLAY.get(family, family)}; Stage 0 status `{tax['status']}`; observed label(s): `{tax.get('source_labels', '')}`. It remains held until a separate semantic bridge is justified."
        )

    lines += [
        "",
        "## Accounting and claim boundary",
        "",
        "M25 treats fiscal-account continuity as an accounting-semantics problem, not a string-matching problem. The central-transfer family is not silently bridged across `TKDD` and newer terminology. Budget appropriations are not treated as realized spending, no fiscal ratios are generated, and no causal or policy-effect interpretation is authorized.",
        "",
        "The panel can support a later preregistered geography-year design that asks whether fiscal capacity or expenditure composition adds explanatory or predictive value to modern development outcomes. M25 itself does not claim that revenue or expenditure caused poverty, unemployment, growth, or any other outcome.",
        "",
        "## Reproducibility and provenance",
        "",
        "Each jurisdiction-year provenance record binds both the official HTML snapshot and its same-selector SpreadsheetML export by SHA-256. Permanent CI can work entirely offline: it verifies frozen source hashes, revalidates HTML identity/year/December/export-link semantics, re-parses exact SpreadsheetML account values, rechecks rounded HTML values when available, rebuilds the canonical panel, reruns completion/audit tests, and compares deterministic outputs byte-for-byte.",
        "",
        "## Core outputs",
        "",
        "- `data/manifests/milestone25_transport_amendment.json`",
        "- `data/registries/djpk_sumbar_pemda.csv`",
        "- `data/manifests/milestone25_taxonomy_discovery.json`",
        "- `data/registries/djpk_m25_stage1_account_contracts.csv`",
        "- `data/manifests/milestone25_stage1_contracts.json`",
        "- `data/manifests/milestone25_stage1_full_export.json`",
        "- `data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv`",
        "- `data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv`",
        "- `data/processed/djpk/public_finance/source/` (152 HTML + 152 SpreadsheetML snapshots)",
        "- `data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv`",
        "- `data/processed/djpk/public_finance/djpk-fiscal-provenance.csv`",
        "- `data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json`",
        "- `data/manifests/milestone25_djpk_public_finance_complete.json`",
        "",
    ]
    if panel.get("observation_count") != final.get("observation_count"):
        raise ValueError("M25 panel/final observation count drift while building documentation")
    return "\n".join(lines)


def main() -> int:
    try:
        text = build()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(json.dumps({"documentation": OUT.relative_to(ROOT).as_posix(), "status": "built"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
