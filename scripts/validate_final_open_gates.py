from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "publication/final-open-gates.json"
PAGES_EVIDENCE = ROOT / "publication/pages-deployment.json"
CLEAN_SWEEP_EVIDENCE = ROOT / "publication/clean-main-sweep.json"
DOC = ROOT / "docs/FINAL_OPEN_GATES.md"

EXPECTED_MUST_CLOSE = {
    "frozen_v01_package_consistency": "satisfied",
    "public_product_contract_consistency": "satisfied",
    "github_pages_enablement": "satisfied",
    "clean_main_reproducibility_sweep": "satisfied",
    "adversarial_public_readability_audit": "open_internal",
    "release_candidate_and_handoff_bundle": "open_internal",
}

EXPECTED_DEFER = {
    "construction_2005_qualification_component_recovery",
    "construction_revision_causal_attribution",
    "bpbd_2017_missing_raw_report_bytes",
    "definitive_monetary_wasted_potential",
    "theoretical_maximum_and_guaranteed_policy_gain",
    "rainfall_to_unemployment_causal_effect",
    "composite_disaster_score_and_policy_ranking",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def validate() -> dict[str, Any]:
    payload = load_json(REGISTRY)
    assert payload["schema"] == "ranah-observatory/final-open-gates/v1"
    assert payload["as_of"] == "2026-08-30"
    assert payload["delivery_deadline"] == "2026-09-09"
    assert payload["mode"] == "ship_first_finalization"

    must_close = {item["id"]: item for item in payload["must_close"]}
    assert set(must_close) == set(EXPECTED_MUST_CLOSE)
    assert {key: item["status"] for key, item in must_close.items()} == EXPECTED_MUST_CLOSE

    for gate_id, gate in must_close.items():
        assert gate["why_release_critical"].strip(), gate_id
        assert gate["exit_condition"].strip(), gate_id
        assert gate["evidence"], gate_id
        assert gate["status"] != "deferred", gate_id

    pages = must_close["github_pages_enablement"]
    pages_evidence = load_json(PAGES_EVIDENCE)
    assert pages["owner"] == "repository_owner"
    assert pages["production_url"] == "https://nabilrn.github.io/ranah-observatory/"
    assert pages["workflow_run_id"] == 33309643635
    assert pages_evidence["schema"] == "ranah-observatory/pages-deployment-evidence/v1"
    assert pages_evidence["workflow"] == "Deploy Public Product"
    assert pages_evidence["workflow_run_id"] == 33309643635
    assert pages_evidence["workflow_run_attempt"] == 2
    assert pages_evidence["configure_pages"] == "success"
    assert pages_evidence["upload_pages_artifact"] == "success"
    assert pages_evidence["deploy_pages"] == "success"
    assert pages_evidence["production_url"] == pages["production_url"]

    clean = must_close["clean_main_reproducibility_sweep"]
    clean_evidence = load_json(CLEAN_SWEEP_EVIDENCE)
    assert clean["verified_main_commit"] == "fa960c278d4ad69524c26e1bf984a1a29b9a2ab3"
    assert clean["workflow_run_id"] == 33318320220
    assert clean_evidence["schema"] == "ranah-observatory/clean-main-reproducibility-evidence/v1"
    assert clean_evidence["main_commit"] == clean["verified_main_commit"]
    assert clean_evidence["workflow"] == "Final Clean Main Reproducibility Sweep"
    assert clean_evidence["workflow_run_id"] == clean["workflow_run_id"]
    assert clean_evidence["event"] == "push"
    assert clean_evidence["conclusion"] == "success"
    assert clean_evidence["live_acquisition_performed"] is False
    assert clean_evidence["external_statistical_api_required"] is False
    assert clean_evidence["future_main_pushes_guarded_by_same_workflow"] is True
    assert len(clean_evidence["contracts_verified"]) == 10
    assert len(clean_evidence["defects_exposed_before_success"]) == 2

    valuable = payload["valuable_if_easy"]
    assert len(valuable) == 3
    assert all(item["status"] == "opportunistic" for item in valuable)
    assert all(item["rule"].strip() for item in valuable)

    deferred = {item["id"]: item for item in payload["defer"]}
    assert set(deferred) == EXPECTED_DEFER
    for gate_id, gate in deferred.items():
        assert gate["reason"].strip(), gate_id
        assert gate["reopen_trigger"].strip(), gate_id

    summary = payload["summary"]
    computed = {
        "must_close_total": len(must_close),
        "must_close_satisfied": sum(gate["status"] == "satisfied" for gate in must_close.values()),
        "must_close_open_internal": sum(gate["status"] == "open_internal" for gate in must_close.values()),
        "must_close_blocked_external": sum(gate["status"] == "blocked_external_manual" for gate in must_close.values()),
        "valuable_if_easy_total": len(valuable),
        "defer_total": len(deferred),
    }
    assert summary == computed

    workflow_audit = payload["workflow_audit"]
    assert workflow_audit["open_pull_requests_at_audit"] == 0
    assert workflow_audit["mass_workflow_deletion_authorized"] is False
    assert len(workflow_audit["examples_checked"]) == 4

    doc = DOC.read_text(encoding="utf-8")
    for token in (
        "6 must-close",
        "GitHub Pages",
        "https://nabilrn.github.io/ranah-observatory/",
        "Clean-main reproducibility sweep",
        "33318320220",
        "Adversarial public readability audit",
        "Release candidate and handoff bundle",
        "Deferred research — not release blockers",
        "zero open pull requests",
    ):
        assert token in doc, f"open-gate doc lost token: {token}"

    return {
        "must_close_total": computed["must_close_total"],
        "must_close_satisfied": computed["must_close_satisfied"],
        "must_close_open_internal": computed["must_close_open_internal"],
        "must_close_blocked_external": computed["must_close_blocked_external"],
        "deferred_research_gates": computed["defer_total"],
        "mass_workflow_deletion_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
