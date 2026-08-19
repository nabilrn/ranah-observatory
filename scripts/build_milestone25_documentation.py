#!/usr/bin/env python3
from __future__ import annotations

import json
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
    if final.get("schema") != "ranah-observatory/milestone25-djpk-public-finance-complete/v1":
        raise ValueError("unexpected M25 completion schema")
    if final.get("milestone25_complete") is not True:
        raise ValueError("M25 is not complete")
    results = {row["conceptual_family"]: row for row in taxonomy["conceptual_account_family_results"]}
    promoted = list(final["promoted_exact_label_families"])
    held = list(final["held_families"])

    lines: list[str] = [
        "# Milestone 25 — DJPK/SIKD Public-Finance Panel",
        "",
        "Status: **complete for the exact-label fiscal subset; taxonomy-ambiguous families remain held**.",
        "",
        "M25 adds a district/city fiscal evidence layer for all 19 current West Sumatra kabupaten/kota over 2018–2025 using official DJPK/SIKD APBD realization pages. The taxonomy was locked on Kota Padang before fiscal values from the other 18 local governments were inspected.",
        "",
        "## Frozen evidence footprint",
        "",
        f"- **{final['geography_count']}** kabupaten/kota;",
        f"- **{final['year_count']}** fiscal years ({final['start_year']}–{final['end_year']});",
        f"- **{final['jurisdiction_year_count']}** jurisdiction-year source pages;",
        f"- **{final['promoted_exact_label_family_count']}** exact-label fiscal account families promoted;",
        f"- **{final['observation_count']}** canonical fiscal observations;",
        f"- **{final['provenance_count']}** jurisdiction-year provenance records;",
        f"- **{final['frozen_stage0_page_count']}** frozen taxonomy-reference pages;",
        f"- **{final['frozen_stage1_page_count']}** frozen full-panel source pages.",
        "",
        "All canonical values are December fiscal realizations normalized to **IDR billion**. No imputation, historical-boundary reconstruction, explicit taxonomy bridge, derived fiscal ratio, or statistical model is part of M25.",
        "",
        "## Exact-label families promoted",
        "",
    ]
    if promoted:
        for family in promoted:
            tax = results[family]
            lines.append(
                f"- `{family}` — {DISPLAY.get(family, family)}; Stage 0 status `{tax['status']}`; source label(s): `{tax.get('source_labels', '')}`."
            )
    else:
        lines.append("- None. This state should not occur for a completed M25 exact panel.")

    lines += ["", "## Families held from the exact panel", ""]
    if held:
        for family in held:
            tax = results[family]
            lines.append(
                f"- `{family}` — {DISPLAY.get(family, family)}; Stage 0 status `{tax['status']}`; observed label(s): `{tax.get('source_labels', '')}`. It remains held until a separate semantic bridge is justified."
            )
    else:
        lines.append("- None; all five predeclared families qualified under the exact-label contract.")

    lines += [
        "",
        "## Why the bridge families are not silently merged",
        "",
        "M25 treats fiscal-account continuity as an accounting-semantics problem, not a string-matching problem. A renamed or reorganized account can only be bridged in a separate design when the concept and hierarchy are demonstrably equivalent. In particular, older transfer-account structures are not automatically equated with newer central-transfer terminology.",
        "",
        "This restriction means the exact panel can contain fewer than the five conceptual families originally targeted. That is intentional: incomplete but defensible evidence is preferable to a longer panel created by silently mixing fiscal taxonomies.",
        "",
        "## What M25 unlocks",
        "",
        "The exact-label panel supplies a new institutional/fiscal mechanism layer for future analysis of West Sumatra. Because it uses the same current 19 kabupaten/kota and 2018–2025 window as the modern analytical regime, it can later be joined at geography-year level to qualified modern outcomes **after** a separate model design checks scale, timing, multicollinearity, and causal boundaries.",
        "",
        "M25 itself does not claim that fiscal realization caused poverty, unemployment, growth, or any other development outcome. It also does not rank local governments by fiscal quality or estimate a fiscal multiplier.",
        "",
        "## Reproducibility and provenance",
        "",
        "The repository retains the official DJPK HTML pages for the taxonomy reference series and every jurisdiction-year in the exact panel. Source-page SHA-256 values are bound to the probe coverage and canonical provenance. The canonical materializer re-parses each frozen page, recomputes the locked account realization, and verifies that it exactly matches the value captured during the live Stage 1 probe.",
        "",
        "Permanent CI is designed to run without live DJPK access: it verifies frozen source hashes, rebuilds the Stage 1 contract registry from the frozen taxonomy result, rebuilds the canonical fiscal panel from frozen HTML, reruns the completion audit/tests, and checks derived outputs byte-for-byte.",
        "",
        "## Claim boundary",
        "",
        "M25 is evidence acquisition and harmonization. It does not estimate fiscal causality, policy effectiveness, cost-benefit rankings, fiscal multipliers, or monetary wasted potential. Budget appropriations are not treated as realized spending, missing observations are not interpolated, and held taxonomy families remain unavailable to downstream models until separately qualified.",
        "",
        "## Core outputs",
        "",
        "- `data/registries/djpk_sumbar_pemda.csv`",
        "- `data/manifests/milestone25_taxonomy_discovery.json`",
        "- `data/registries/djpk_m25_stage1_account_contracts.csv`",
        "- `data/manifests/milestone25_stage1_contracts.json`",
        "- `data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv`",
        "- `data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv`",
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
        print(f"error: {exc}")
        return 2
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(json.dumps({"documentation": OUT.relative_to(ROOT).as_posix(), "status": "built"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
