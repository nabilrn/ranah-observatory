#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE18_FINAL_ANALYTICAL_SYNTHESIS_SPEC.md"
MANIFEST = ROOT / "data/manifests/milestone18_final_analytical_synthesis.json"
NODES = ROOT / "data/analysis/engine/final_synthesis_v1/m18-evidence-nodes.csv"
EDGES = ROOT / "data/analysis/engine/final_synthesis_v1/m18-evidence-edges.csv"
RQ = ROOT / "data/analysis/engine/final_synthesis_v1/m18-research-question-readiness.csv"
CLAIMS = ROOT / "data/analysis/engine/final_synthesis_v1/m18-claim-boundary-ledger.csv"

EXPECTED_NODES = {
    "observed_trajectory_foundation",
    "expected_performance",
    "attainable_reference",
    "development_gaps",
    "associated_bottlenecks",
    "causal_evidence",
    "spatial_climate_constraints",
    "intervention_scenarios",
    "uncertainty_evidence_strength",
}
EXPECTED_RQ_STATES = {
    "RQ1": "bounded_partial",
    "RQ2": "bounded_answer",
    "RQ3": "bounded_partial",
    "RQ4": "bounded_answer",
    "RQ5": "not_action_ready",
}
EXPECTED_CLAIM_IDS = {f"c{i:02d}" for i in range(1, 10)}
ALLOWED_EDGE_TYPES = {
    "analytical_dependency",
    "evidence_extension",
    "readiness_constraint",
    "uncertainty_annotation",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    for path in (SPEC, MANIFEST, NODES, EDGES, RQ, CLAIMS):
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        return {
            "schema": "ranah-observatory/milestone18-audit/v1",
            "errors": errors,
            "milestone18_complete": False,
        }

    spec = SPEC.read_text(encoding="utf-8")
    spec_lower = spec.lower()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    nodes = rows(NODES)
    edges = rows(EDGES)
    rq_rows = rows(RQ)
    claims = rows(CLAIMS)

    guardrails = (
        "phase 2 analytical engine complete",
        "research question fully resolved",
        "m18 is a synthesis milestone",
        "no question may be marked fully resolved merely because an upstream milestone is complete.",
        "must remain `bounded_partial`",
        "must be `not_action_ready`",
        "no post-hoc threshold may be introduced to hide an inconvenient result.",
    )
    for phrase in guardrails:
        if phrase.lower() not in spec_lower:
            errors.append(f"M18 spec lost guardrail: {phrase}")

    if manifest.get("schema") != "ranah-observatory/milestone18-final-analytical-synthesis/v1":
        errors.append("M18 manifest schema drift")
    if manifest.get("milestone18_complete") is not True:
        errors.append("M18 completion flag false")
    if manifest.get("phase2_analytical_engine_complete") is not True:
        errors.append("Phase 2 analytical engine completion flag false")
    if manifest.get("scientific_research_agenda_complete") is not False:
        errors.append("M18 improperly marks scientific research agenda complete")
    if manifest.get("public_product_complete") is not False:
        errors.append("M18 improperly marks public product complete")
    if manifest.get("public_dashboard_required_for_phase2_completion") is not False:
        errors.append("M18 improperly requires dashboard for Phase 2 closure")

    exact_counts = {
        "evidence_node_count": 9,
        "evidence_edge_count": 18,
        "research_question_count": 5,
        "fully_resolved_research_question_count": 0,
        "blocked_claim_count": 9,
        "m13_frontier_gap_sign_disagreement_count": 50,
        "m15_not_identification_ready_count": 2,
        "m16_blocked_or_gap_component_count": 8,
    }
    for key, expected in exact_counts.items():
        if manifest.get(key) != expected:
            errors.append(f"M18 count/diagnostic drift: {key}")

    if manifest.get("research_question_readiness_counts") != {
        "bounded_answer": 2,
        "bounded_partial": 2,
        "not_action_ready": 1,
    }:
        errors.append("M18 research-question readiness counts drift")

    expected_min_mapping = {
        "feature_id": "agriculture_share_grdp",
        "target_id": "real_grdp_growth",
    }
    if manifest.get("m17_min_dominant_sign_retention_mapping") != expected_min_mapping:
        errors.append("M18 minimum M17 sign-retention mapping drift")
    if abs(float(manifest.get("m17_min_dominant_sign_retention", -1)) - (10 / 19)) > 1e-12:
        errors.append("M18 minimum M17 sign retention drift")

    for key in (
        "new_statistical_model_fit",
        "new_causal_estimate_created",
        "method_disagreement_averaged_away",
        "policy_ranking_performed",
        "cost_benefit_analysis_performed",
        "definitive_monetary_wasted_potential_estimated",
    ):
        if manifest.get(key) is not False:
            errors.append(f"M18 false guard enabled: {key}")

    for kind in ("inputs", "outputs"):
        for key, rec in manifest.get(kind, {}).items():
            path = ROOT / str(rec.get("path", ""))
            if not path.exists() or sha256(path) != rec.get("sha256"):
                errors.append(f"M18 {kind[:-1]} checksum drift: {key}")

    if len(nodes) != 9 or {row.get("node_id") for row in nodes} != EXPECTED_NODES:
        errors.append("M18 evidence-node footprint drift")
    if sorted(int(row.get("stage_order", "0")) for row in nodes) != list(range(1, 10)):
        errors.append("M18 evidence-node stage order drift")
    for row in nodes:
        if row.get("causal_claim_authorized", "").lower() != "false":
            errors.append(f"M18 synthesis node improperly authorizes causal claim: {row.get('node_id')}")

    if len(edges) != 18:
        errors.append("M18 evidence-edge count drift")
    node_ids = {row.get("node_id") for row in nodes}
    for row in edges:
        if row.get("from_node") not in node_ids or row.get("to_node") not in node_ids:
            errors.append(f"M18 edge references unknown node: {row.get('edge_id')}")
        if row.get("edge_type") not in ALLOWED_EDGE_TYPES:
            errors.append(f"M18 edge type drift: {row.get('edge_id')}")
        if row.get("causal_edge", "").lower() != "false":
            errors.append(f"M18 dependency edge improperly labeled causal: {row.get('edge_id')}")

    uncertainty_edges = [
        row for row in edges if row.get("edge_type") == "uncertainty_annotation"
    ]
    if len(uncertainty_edges) != 8:
        errors.append("M18 must retain one uncertainty edge from every substantive node")
    if {row.get("from_node") for row in uncertainty_edges} != EXPECTED_NODES - {"uncertainty_evidence_strength"}:
        errors.append("M18 uncertainty-edge source footprint drift")

    if len(rq_rows) != 5 or {row.get("research_question_id") for row in rq_rows} != set(EXPECTED_RQ_STATES):
        errors.append("M18 research-question footprint drift")
    for row in rq_rows:
        rq_id = row.get("research_question_id", "")
        if row.get("readiness_state") != EXPECTED_RQ_STATES.get(rq_id):
            errors.append(f"M18 readiness state drift: {rq_id}")
        if row.get("fully_resolved", "").lower() != "false":
            errors.append(f"M18 improperly marks question fully resolved: {rq_id}")
        if not row.get("limitation") or not row.get("next_evidence_required"):
            errors.append(f"M18 question lacks limitation/next evidence: {rq_id}")

    if len(claims) != 9 or {row.get("claim_id") for row in claims} != EXPECTED_CLAIM_IDS:
        errors.append("M18 claim-boundary footprint drift")
    for row in claims:
        if row.get("status") != "not_authorized":
            errors.append(f"M18 blocked claim unexpectedly authorized: {row.get('claim_id')}")
        if not row.get("blocking_evidence") or not row.get("upgrade_requirement"):
            errors.append(f"M18 claim lacks blocking/upgrade evidence: {row.get('claim_id')}")

    claim_text = "\n".join(row.get("blocked_claim", "") for row in claims)
    for fragment in (
        "monetary value",
        "theoretical maximum",
        "predictive residual is causal",
        "policy target",
        "rainfall association causes",
        "event counts measure observed disaster impact",
        "composite disaster-risk score",
        "policy treatment effect or forecast",
        "ranked by policy attractiveness or cost-benefit",
    ):
        if fragment not in claim_text:
            errors.append(f"M18 claim ledger lost required boundary: {fragment}")

    return {
        "schema": "ranah-observatory/milestone18-audit/v1",
        "evidence_node_count": len(nodes),
        "evidence_edge_count": len(edges),
        "research_question_count": len(rq_rows),
        "blocked_claim_count": len(claims),
        "phase2_analytical_engine_complete": manifest.get("phase2_analytical_engine_complete"),
        "scientific_research_agenda_complete": manifest.get("scientific_research_agenda_complete"),
        "milestone18_complete": manifest.get("milestone18_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_complete and not report["milestone18_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
