from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validate_final_model_testing import validate as validate_final_model_testing
from validate_final_open_gates import validate as validate_final_open_gates
from validate_public_history import validate as validate_public_history
from validate_public_product import validate as validate_public_product
from validate_public_readiness import validate as validate_public_readiness

ROOT = Path(__file__).resolve().parents[1]
CERTIFICATE = ROOT / "publication/v0.1/completeness-certificate.json"
README = ROOT / "README.md"
FINAL_PLAN = ROOT / "docs/FINAL_10_DAY_DELIVERY.md"
FINAL_GATES_DOC = ROOT / "docs/FINAL_OPEN_GATES.md"
MODEL_VALIDATION_DOC = ROOT / "docs/FINAL_MODEL_VALIDATION.md"
PAGES_EVIDENCE = ROOT / "publication/pages-deployment.json"
CLEAN_SWEEP_EVIDENCE = ROOT / "publication/clean-main-sweep.json"
PAGES_WORKFLOW = ROOT / ".github/workflows/deploy-public-product.yml"
CLEAN_SWEEP_WORKFLOW = ROOT / ".github/workflows/final-clean-main-sweep.yml"

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

    model_testing = validate_final_model_testing()
    assert model_testing == {
        "model_testing_gate_passed": True,
        "m11_crossfit_predictions": 342,
        "m11_benchmark_qualified_targets": 3,
        "m19_out_of_time_predictions": 285,
        "m19_forecast_qualified_targets": 0,
        "m19_forecast_blocked_targets": 3,
        "posthoc_algorithm_search_performed": False,
    }

    open_gates = validate_final_open_gates()
    assert open_gates == {
        "must_close_total": 6,
        "must_close_satisfied": 4,
        "must_close_open_internal": 2,
        "must_close_blocked_external": 0,
        "deferred_research_gates": 7,
        "mass_workflow_deletion_authorized": False,
    }

    pages = load_json(PAGES_EVIDENCE)
    assert pages["deploy_pages"] == "success"
    assert pages["production_url"] == "https://nabilrn.github.io/ranah-observatory/"

    clean_sweep = load_json(CLEAN_SWEEP_EVIDENCE)
    assert clean_sweep["main_commit"] == "fa960c278d4ad69524c26e1bf984a1a29b9a2ab3"
    assert clean_sweep["workflow_run_id"] == 33318320220
    assert clean_sweep["event"] == "push"
    assert clean_sweep["conclusion"] == "success"
    assert clean_sweep["live_acquisition_performed"] is False
    assert clean_sweep["external_statistical_api_required"] is False

    for path in REQUIRED_PUBLIC_FILES:
        assert path.is_file() and path.stat().st_size > 0, f"missing public release file: {path.relative_to(ROOT)}"

    readme = README.read_text(encoding="utf-8")
    final_plan = FINAL_PLAN.read_text(encoding="utf-8")
    final_gates_doc = FINAL_GATES_DOC.read_text(encoding="utf-8")
    model_validation_doc = MODEL_VALIDATION_DOC.read_text(encoding="utf-8")
    pages_workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
    clean_sweep_workflow = CLEAN_SWEEP_WORKFLOW.read_text(encoding="utf-8")

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
        "https://nabilrn.github.io/ranah-observatory/",
        "GitHub Pages deployment verified",
        "Definition of “done”",
    ):
        assert token in final_plan, f"final delivery contract lost token: {token}"

    for token in (
        "6 must-close",
        "4 satisfied and 2 internal open",
        "GitHub Pages",
        "https://nabilrn.github.io/ranah-observatory/",
        "Clean-main reproducibility sweep",
        "33318320220",
        "Adversarial public readability audit",
        "Release candidate and handoff bundle",
        "Deferred research — not release blockers",
    ):
        assert token in final_gates_doc, f"final open-gate document lost token: {token}"

    for token in (
        "342 leave-one-geography-out cross-fitted predictions",
        "285 total",
        "0 / 3 targets qualify",
        "failure is a research result",
    ):
        assert token in model_validation_doc, f"model validation document lost token: {token}"

    assert "pages: write" in pages_workflow
    assert "id-token: write" in pages_workflow
    assert "actions/configure-pages@v5" in pages_workflow
    assert "enablement: true" in pages_workflow
    assert "actions/upload-pages-artifact@v4" in pages_workflow
    assert "actions/deploy-pages@v4" in pages_workflow

    for token in (
        "Final Clean Main Reproducibility Sweep",
        "push:",
        "branches:",
        "- main",
        "validate_final_model_testing.py",
        "validate_historical_reconstruction.py",
        "build_milestone10_analytical_panel",
        "build_milestone11_expected_performance_v2",
        "build_milestone19_dynamic_forecast_engine.py",
        "git diff --exit-code",
    ):
        assert token in clean_sweep_workflow, f"clean-main workflow lost token: {token}"

    return {
        "internal_release_readiness_passed": True,
        "frozen_claims": certificate["claim_count"],
        "blocked_claims_retained": certificate["state_counts"]["blocked"],
        "public_stories": public["stories"],
        "research_questions": readiness["questions"],
        "fully_resolved_questions": readiness["fully_resolved"],
        "historical_context_cards": history["cards"],
        "model_testing_gate_passed": model_testing["model_testing_gate_passed"],
        "m11_benchmark_qualified_targets": model_testing["m11_benchmark_qualified_targets"],
        "m19_forecast_qualified_targets": model_testing["m19_forecast_qualified_targets"],
        "m19_forecast_blocked_targets": model_testing["m19_forecast_blocked_targets"],
        "must_close_gates_total": open_gates["must_close_total"],
        "must_close_gates_satisfied": open_gates["must_close_satisfied"],
        "must_close_gates_open_internal": open_gates["must_close_open_internal"],
        "external_manual_blockers": open_gates["must_close_blocked_external"],
        "clean_main_reproducibility_verified": True,
        "clean_main_verified_commit": clean_sweep["main_commit"],
        "clean_main_workflow_run_id": clean_sweep["workflow_run_id"],
        "public_product_url": pages["production_url"],
        "deferred_research_gates": open_gates["deferred_research_gates"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
