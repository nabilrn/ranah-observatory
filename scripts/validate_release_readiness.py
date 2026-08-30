from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validate_public_history import validate as validate_public_history
from validate_public_product import validate as validate_public_product
from validate_public_readiness import validate as validate_public_readiness

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATE = ROOT / "publication/v0.1/completeness-certificate.json"
README = ROOT / "README.md"
FINAL_PLAN = ROOT / "docs/FINAL_10_DAY_DELIVERY.md"
PAGES_WORKFLOW = ROOT / ".github/workflows/deploy-public-product.yml"

REQUIRED_PUBLIC_FILES = [
    ROOT / "site/index.html",
    ROOT / "site/data/overview.json",
    ROOT / "site/data/readiness.json",
    ROOT / "site/data/indicators.json",
    ROOT / "site/data/districts.json",
    ROOT / "site/data/glossary.json",
    ROOT / "site/data/history.json",
    ROOT / "site/history.js",
    ROOT / "site/history.css",
]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def validate() -> dict[str, Any]:
    certificate = load_json(CERTIFICATE)
    assert certificate["schema"] == "ranah-observatory/publication-v0.1-completeness-certificate/v1"
    assert certificate["release"] == "v0.1"
    assert certificate["offline_verification_passed"] is True
    assert certificate["claim_count"] == 30
    assert certificate["state_counts"] == {
        "blocked": 9,
        "context_only": 5,
        "publishable_bounded": 11,
        "publishable_negative_result": 5,
    }
    assert certificate["evidence_row_count"] == 17
    assert certificate["manuscript_unique_claim_reference_count"] == 30
    assert certificate["all_ledger_claims_referenced_in_manuscript"] is True
    assert certificate["required_negative_results_retained"] is True
    assert certificate["all_nine_m18_blocked_claims_retained"] is True
    assert len(certificate["blocked_claim_ids"]) == 9

    public = validate_public_product()
    assert public == {
        "stories": 9,
        "headline_stats": 5,
        "blocked_boundaries": 9,
        "ledger_claims": 30,
    }

    readiness = validate_public_readiness()
    assert readiness == {
        "questions": 5,
        "fully_resolved": 0,
        "not_action_ready": 1,
    }

    history = validate_public_history()
    assert history["cards"] == 3
    assert history["annual_points"] == 5
    assert history["historical_context_display"] is True
    assert history["harmonized_series_authorized"] is False
    assert history["causal_claim_authorized"] is False

    for path in REQUIRED_PUBLIC_FILES:
        assert path.is_file() and path.stat().st_size > 0, f"missing public release file: {path.relative_to(ROOT)}"

    readme = README.read_text(encoding="utf-8")
    final_plan = FINAL_PLAN.read_text(encoding="utf-8")
    pages_workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")

    for token in (
        "v0.1 research/publication package is frozen",
        "docs/FINAL_10_DAY_DELIVERY.md",
        "Public product",
        "9 September 2026",
    ):
        assert token in readme, f"README lost current-release token: {token}"

    for token in (
        "30 August 2026 → 9 September 2026",
        "ship-first finalization",
        "Resource not accessible by integration",
        "GitHub Actions",
        "Definition of “done”",
    ):
        assert token in final_plan, f"final delivery contract lost token: {token}"

    assert "pages: write" in pages_workflow
    assert "id-token: write" in pages_workflow
    assert "actions/configure-pages@v5" in pages_workflow
    assert "enablement: true" in pages_workflow
    assert "actions/upload-pages-artifact@v4" in pages_workflow
    assert "actions/deploy-pages@v4" in pages_workflow

    return {
        "internal_release_readiness_passed": True,
        "frozen_claims": certificate["claim_count"],
        "blocked_claims_retained": certificate["state_counts"]["blocked"],
        "public_stories": public["stories"],
        "research_questions": readiness["questions"],
        "fully_resolved_questions": readiness["fully_resolved"],
        "historical_context_cards": history["cards"],
        "external_manual_blockers": 1,
        "external_manual_blocker": "enable GitHub Pages with GitHub Actions as the source",
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
