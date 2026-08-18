#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/analysis/engine/final_synthesis_v1"
NODES_OUT = OUT_DIR / "m18-evidence-nodes.csv"
EDGES_OUT = OUT_DIR / "m18-evidence-edges.csv"
RQ_OUT = OUT_DIR / "m18-research-question-readiness.csv"
CLAIMS_OUT = OUT_DIR / "m18-claim-boundary-ledger.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone18_final_analytical_synthesis.json"

INPUT_PATHS = {
    "research_charter": ROOT / "research/RESEARCH_CHARTER.md",
    "phase2_roadmap": ROOT / "research/PHASE2_ANALYTICAL_ENGINE_ROADMAP.md",
    "research_foundation": ROOT / "data/manifests/research_foundation_complete.json",
    "m6_historical": ROOT / "data/manifests/milestone6_historical_eda_audit.json",
    "m8_quasi_causal": ROOT / "data/manifests/milestone8_complete_audit.json",
    "m9_hydroclimate": ROOT / "data/manifests/milestone9_hydroclimate_case_study.json",
    "m10_panel": ROOT / "data/manifests/milestone10_analytical_panel.json",
    "m11_expected": ROOT / "data/manifests/milestone11_expected_performance_v2.json",
    "m12_frontier": ROOT / "data/manifests/milestone12_attainable_frontier.json",
    "m13_gaps": ROOT / "data/manifests/milestone13_development_gap_decomposition.json",
    "m14_association": ROOT / "data/manifests/milestone14_bottleneck_association.json",
    "m15_causal_library": ROOT / "data/manifests/milestone15_causal_evidence_expansion.json",
    "m16_spatial_climate": ROOT / "data/manifests/milestone16_spatial_climate_risk.json",
    "m17_scenarios": ROOT / "data/manifests/milestone17_scenario_intervention.json",
    "m17_mappings": ROOT / "data/analysis/engine/scenario_intervention_v1/m17-model-sensitivity-mappings.csv",
}

NODE_IDS = [
    "observed_trajectory_foundation",
    "expected_performance",
    "attainable_reference",
    "development_gaps",
    "associated_bottlenecks",
    "causal_evidence",
    "spatial_climate_constraints",
    "intervention_scenarios",
    "uncertainty_evidence_strength",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require(payload: dict[str, Any], key: str, expected: Any, label: str) -> None:
    actual = payload.get(key)
    if actual != expected:
        raise RuntimeError(f"{label} contract drift: {key} expected {expected!r}, got {actual!r}")


def load_json(key: str) -> dict[str, Any]:
    return json.loads(INPUT_PATHS[key].read_text(encoding="utf-8"))


def main() -> int:
    for key, path in INPUT_PATHS.items():
        if not path.exists():
            raise RuntimeError(f"missing M18 input {key}: {path.relative_to(ROOT)}")

    foundation = load_json("research_foundation")
    m6 = load_json("m6_historical")
    m8 = load_json("m8_quasi_causal")
    m9 = load_json("m9_hydroclimate")
    m10 = load_json("m10_panel")
    m11 = load_json("m11_expected")
    m12 = load_json("m12_frontier")
    m13 = load_json("m13_gaps")
    m14 = load_json("m14_association")
    m15 = load_json("m15_causal_library")
    m16 = load_json("m16_spatial_climate")
    m17 = load_json("m17_scenarios")

    require(foundation, "initial_research_foundation_complete", True, "foundation")
    require(foundation, "completed_criterion_count", 9, "foundation")
    require(m6, "milestone6_complete", True, "M6")
    require(m8, "milestone8_complete", True, "M8")
    require(m9, "milestone9_complete", True, "M9")
    for number, payload in (
        (10, m10), (11, m11), (12, m12), (13, m13),
        (14, m14), (15, m15), (16, m16), (17, m17),
    ):
        require(payload, f"milestone{number}_complete", True, f"M{number}")

    # Hard claim-boundary contracts.
    require(m10, "geography_count", 19, "M10")
    require(m10, "start_year", 2018, "M10")
    require(m10, "end_year", 2025, "M10")
    require(m10, "indicator_count", 15, "M10")
    require(m10, "imputation_performed", False, "M10")
    require(m11, "benchmark_qualified_target_count", 3, "M11")
    require(m11, "causal_analysis_performed", False, "M11")
    require(m11, "coefficient_causal_interpretation_authorized", False, "M11")
    require(m12, "primary_frontier_calibrated_target_count", 3, "M12")
    require(m12, "theoretical_maximum_claim", False, "M12")
    require(m12, "policy_counterfactual_claim", False, "M12")
    require(m13, "gap_panel_row_count", 342, "M13")
    require(m13, "frontier_gap_sign_disagreement_count", 50, "M13")
    require(m13, "weighted_composite_score_computed", False, "M13")
    require(m13, "monetary_wasted_potential_claim", False, "M13")
    require(m14, "stable_association_signal_count", 1, "M14")
    require(m14, "causal_analysis_performed", False, "M14")
    require(m14, "policy_priority_claim_authorized", False, "M14")
    require(m15, "completed_quasi_causal_study_count", 1, "M15")
    require(m15, "not_identification_ready_count", 2, "M15")
    require(m15, "new_causal_model_fit_count", 0, "M15")
    require(m16, "risk_synthesis_authorized", False, "M16")
    require(m16, "composite_risk_score_created", False, "M16")
    require(m17, "quantitative_model_sensitivity_scenario_count", 5, "M17")
    require(m17, "blocked_intervention_scenario_count", 2, "M17")
    require(m17, "model_sensitivity_mapping_count", 15, "M17")
    require(m17, "policy_recommendation_authorized", False, "M17")
    require(m17, "cost_benefit_analysis_performed", False, "M17")

    interval_counts = m13.get("expected_interval_classification_counts", {})
    if interval_counts != {
        "materially_less_favorable_than_expected": 15,
        "materially_more_favorable_than_expected": 14,
        "within_expected_interval": 313,
    }:
        raise RuntimeError(f"M13 expected-interval classification drift: {interval_counts}")

    m17_mapping_rows = read_csv(INPUT_PATHS["m17_mappings"])
    if len(m17_mapping_rows) != 15:
        raise RuntimeError("M17 mapping footprint drift")
    min_retention_row = min(m17_mapping_rows, key=lambda row: float(row["dominant_sign_retention"]))
    min_retention = float(min_retention_row["dominant_sign_retention"])

    nodes = [
        {
            "node_id": "observed_trajectory_foundation",
            "stage_order": 1,
            "upstream": "M6;M10",
            "claim_class": "observed_and_derived_evidence_foundation",
            "evidence_strength": "qualified_but_historically_incomplete",
            "status": "active_with_scope_limit",
            "key_facts_json": compact_json({
                "m6_historical_population_anchor_count": m6["historical_population_anchor_count"],
                "m6_modern_series_count": m6["modern_series_count"],
                "m6_trend_qualified_modern_series_count": m6["trend_qualified_modern_series_count"],
                "m10_geography_count": m10["geography_count"],
                "m10_years": [m10["start_year"], m10["end_year"]],
                "m10_indicator_count": m10["indicator_count"],
                "m10_missing_indicator_cells": m10["missing_indicator_cells"],
            }),
            "uncertainty_or_limit": "1945-onward historical ambition remains sparsely reconstructed; no general historical-boundary harmonization; M10 is fixed-current-boundary 2018-2025",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "expected_performance",
            "stage_order": 2,
            "upstream": "M11",
            "claim_class": "cross_fitted_predictive_model_estimate",
            "evidence_strength": "benchmark_qualified_for_three_targets",
            "status": "active_scope_bounded",
            "key_facts_json": compact_json({
                "benchmark_qualified_target_count": m11["benchmark_qualified_target_count"],
                "target_ids": m11["benchmark_qualified_target_ids"],
                "crossfit_prediction_count": m11["crossfit_prediction_count"],
            }),
            "uncertainty_or_limit": "predictive residuals and coefficients are non-causal; same-year support warnings remain visible",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "attainable_reference",
            "stage_order": 3,
            "upstream": "M12",
            "claim_class": "empirical_favorable_peer_reference",
            "evidence_strength": "calibrated_for_three_modeled_targets",
            "status": "active_scope_bounded",
            "key_facts_json": compact_json({
                "district_row_count": m12["district_row_count"],
                "calibrated_target_count": m12["primary_frontier_calibrated_target_count"],
                "primary_method": m12["district_primary_method"],
                "alternative_method": m12["district_alternative_method"],
            }),
            "uncertainty_or_limit": "favorable empirical reference is not a theoretical maximum and not a policy counterfactual",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "development_gaps",
            "stage_order": 4,
            "upstream": "M13",
            "claim_class": "derived_multidimensional_reference_gaps",
            "evidence_strength": "authorized_on_supported_rows_with_method_disagreement_visible",
            "status": "active_scope_bounded",
            "key_facts_json": compact_json({
                "gap_rows": m13["gap_panel_row_count"],
                "authorized_rows": m13["gap_interpretation_authorized_row_count"],
                "blocked_rows": m13["gap_interpretation_blocked_row_count"],
                "expected_interval_counts": interval_counts,
                "frontier_sign_disagreements": m13["frontier_gap_sign_disagreement_count"],
            }),
            "uncertainty_or_limit": "three modeled dimensions remain separate; no weighted composite, welfare weight, population aggregation, or monetary loss claim",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "associated_bottlenecks",
            "stage_order": 5,
            "upstream": "M14",
            "claim_class": "stable_association_screen",
            "evidence_strength": "one_preregistered_stable_noncausal_signal",
            "status": "active_noncausal",
            "key_facts_json": compact_json({
                "primary_pair_count": m14["primary_pair_count"],
                "stable_signal_count": m14["stable_association_signal_count"],
                "stable_signals": m14["stable_association_signals"],
            }),
            "uncertainty_or_limit": "feature association is not a causal bottleneck or policy priority",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "causal_evidence",
            "stage_order": 6,
            "upstream": "M8;M15",
            "claim_class": "quasi_causal_evidence_and_identification_failures",
            "evidence_strength": "one_completed_quasi_causal_negative_or_nonrobust_result_plus_two_blocked_designs",
            "status": "active_mixed_evidence",
            "key_facts_json": compact_json({
                "m8_classification": m8["claim_classification"],
                "m8_directional_nonzero_claim_authorized": m8["directional_nonzero_effect_claim_authorized"],
                "m15_completed_studies": m15["completed_quasi_causal_study_count"],
                "m15_not_identification_ready": m15["not_identification_ready_count"],
                "m15_new_causal_models": m15["new_causal_model_fit_count"],
            }),
            "uncertainty_or_limit": "credible design does not guarantee a nonzero effect; failed identification attempts are retained and M14 association is not promoted",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "spatial_climate_constraints",
            "stage_order": 7,
            "upstream": "M9;M16",
            "claim_class": "hazard_climate_and_recorded_occurrence_components",
            "evidence_strength": "qualified_components_with_explicit_risk_chain_gaps",
            "status": "active_risk_synthesis_blocked",
            "key_facts_json": compact_json({
                "m9_geography_count": m9["geography_count"],
                "m9_climate_claim_type": m9["climate_claim_type"],
                "m16_substantive_component_count": m16["substantive_component_count"],
                "m16_blocked_or_gap_component_count": m16["blocked_or_gap_component_count"],
                "m16_required_missing_components": m16["required_missing_component_classes"],
            }),
            "uncertainty_or_limit": "hazard, exposure, vulnerability, capacity, recorded occurrence, and observed impact remain separate; full risk synthesis unauthorized",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "intervention_scenarios",
            "stage_order": 8,
            "upstream": "M17",
            "claim_class": "predictive_model_sensitivity_and_blocked_intervention_mapping",
            "evidence_strength": "five_noncausal_sensitivities_two_blocked_interventions",
            "status": "active_not_policy_ready",
            "key_facts_json": compact_json({
                "scenario_count": m17["scenario_count"],
                "quantitative_sensitivity_count": m17["quantitative_model_sensitivity_scenario_count"],
                "blocked_intervention_count": m17["blocked_intervention_scenario_count"],
                "mapping_count": m17["model_sensitivity_mapping_count"],
            }),
            "uncertainty_or_limit": "no causal policy counterfactual, forecast, cost-benefit estimate, qualified costs, or implementation horizon",
            "causal_claim_authorized": False,
        },
        {
            "node_id": "uncertainty_evidence_strength",
            "stage_order": 9,
            "upstream": "M10;M11;M12;M13;M14;M15;M16;M17",
            "claim_class": "synthesis_metadata",
            "evidence_strength": "explicit_claim_boundaries_and_method_disagreement",
            "status": "active_cross_cutting",
            "key_facts_json": compact_json({
                "m13_frontier_sign_disagreements": m13["frontier_gap_sign_disagreement_count"],
                "m15_failed_identification_attempts": m15["not_identification_ready_count"],
                "m16_blocked_or_gap_components": m16["blocked_or_gap_component_count"],
                "m17_min_dominant_sign_retention": min_retention,
                "m17_min_retention_feature": min_retention_row["feature_id"],
                "m17_min_retention_target": min_retention_row["target_id"],
            }),
            "uncertainty_or_limit": "disagreement is retained rather than averaged into false certainty",
            "causal_claim_authorized": False,
        },
    ]
    if [row["node_id"] for row in nodes] != NODE_IDS:
        raise RuntimeError("M18 node order/footprint drift")

    edges = [
        ("e01", "observed_trajectory_foundation", "expected_performance", "analytical_dependency", "M11 models are built from the qualified analytical panel; historical evidence supplies broader context but is not backfilled into the modern panel"),
        ("e02", "expected_performance", "attainable_reference", "analytical_dependency", "M12 favorable residual references are calibrated relative to M11 cross-fitted expectations"),
        ("e03", "expected_performance", "development_gaps", "analytical_dependency", "M13 expected-performance gaps inherit M11 predictions and uncertainty"),
        ("e04", "attainable_reference", "development_gaps", "analytical_dependency", "M13 favorable-reference gaps inherit M12 empirical frontier objects"),
        ("e05", "development_gaps", "associated_bottlenecks", "analytical_dependency", "M14 screens preregistered lagged candidates against M13 adverse expected-gap objects"),
        ("e06", "associated_bottlenecks", "causal_evidence", "evidence_extension", "M15 tests whether association candidates have identification opportunities; failed identification remains evidence"),
        ("e07", "spatial_climate_constraints", "associated_bottlenecks", "evidence_extension", "qualified climate evidence can enter association screens while retaining model-estimate semantics"),
        ("e08", "causal_evidence", "intervention_scenarios", "readiness_constraint", "intervention mappings cannot exceed the causal identification strength in M8/M15"),
        ("e09", "spatial_climate_constraints", "intervention_scenarios", "readiness_constraint", "disaster intervention scenarios remain blocked while the compatible risk-component chain is incomplete"),
        ("e10", "expected_performance", "intervention_scenarios", "analytical_dependency", "M17 quantitative sensitivities use M11 outer-fold predictive coefficients and remain non-causal"),
    ]
    for node_id in NODE_IDS[:-1]:
        edges.append((f"u{len(edges)+1:02d}", node_id, "uncertainty_evidence_strength", "uncertainty_annotation", "node-specific support, claim boundaries, blocked states, and method disagreement are retained in final synthesis"))
    edge_rows = [
        {
            "edge_id": edge_id,
            "from_node": source,
            "to_node": target,
            "edge_type": edge_type,
            "interpretation": interpretation,
            "causal_edge": False,
        }
        for edge_id, source, target, edge_type, interpretation in edges
    ]

    rq_rows = [
        {
            "research_question_id": "RQ1",
            "research_question": "Historical trajectory",
            "readiness_state": "bounded_partial",
            "answer_scope": "qualified exploratory historical evidence plus fixed-current-boundary modern analytical panel",
            "evidence_basis": "M6;M10",
            "current_answer": "Modern district/city trajectories can be analyzed reproducibly for selected indicators, while the long-run 1945-onward trajectory remains incompletely reconstructed.",
            "limitation": "only one historical population anchor in M6; sparse historical series; no general historical-boundary harmonization",
            "next_evidence_required": "additional table-qualified historical series with explicit geography/vintage semantics and defensible boundary reconstruction",
            "fully_resolved": False,
        },
        {
            "research_question_id": "RQ2",
            "research_question": "Attainable development",
            "readiness_state": "bounded_answer",
            "answer_scope": "poverty, unemployment, and real-GRDP growth for 19 current kabupaten/kota in the M11/M12 2019-2024 regime",
            "evidence_basis": "M11;M12",
            "current_answer": "For the three modeled outcomes the engine supplies benchmark-qualified conditional expectations and calibrated empirical favorable-peer references.",
            "limitation": "the reference is empirical rather than a theoretical maximum and does not cover all development dimensions or historical regimes",
            "next_evidence_required": "broader qualified outcome families, larger comparison universes, and method-specific validation before expanding attainable-development claims",
            "fully_resolved": False,
        },
        {
            "research_question_id": "RQ3",
            "research_question": "Divergence",
            "readiness_state": "bounded_partial",
            "answer_scope": "current-boundary 2019-2024 multidimensional gaps for three modeled district/city outcomes",
            "evidence_basis": "M13",
            "current_answer": "The engine identifies when current-period observations are unusually less/more favorable than conditional expectations and how they compare with favorable empirical references.",
            "limitation": "M13 does not identify long-run divergence timing from comparable Indonesian regions across the Charter's broad dimensions",
            "next_evidence_required": "longer comparable regional panels and historically valid cross-region boundary/methodology alignment",
            "fully_resolved": False,
        },
        {
            "research_question_id": "RQ4",
            "research_question": "Explanatory factors",
            "readiness_state": "bounded_answer",
            "answer_scope": "pre-registered association screening plus currently qualified quasi-causal/identification studies",
            "evidence_basis": "M14;M8;M15",
            "current_answer": "The engine distinguishes one stable non-causal rainfall/unemployment-gap association from causal evidence, retains a completed earthquake quasi-causal study, and records two identification failures instead of upgrading them.",
            "limitation": "one stable association is not a causal explanation; the completed earthquake study did not authorize a robust directional nonzero effect claim",
            "next_evidence_required": "new independent time variation or credible natural experiments for priority mechanisms, with pre-event diagnostics and small-cluster inference where required",
            "fully_resolved": False,
        },
        {
            "research_question_id": "RQ5",
            "research_question": "Action",
            "readiness_state": "not_action_ready",
            "answer_scope": "five predictive model-state sensitivities plus two explicitly blocked intervention scenarios",
            "evidence_basis": "M17;M15;M16",
            "current_answer": "The engine can expose scenario sensitivity and why candidate rainfall/labor and disaster-risk interventions are not yet authorized, but it cannot rank real policies by expected impact.",
            "limitation": "no causal policy counterfactual, qualified costs, implementation horizon, complete disaster-risk mapping, or cost-benefit evidence",
            "next_evidence_required": "intervention-specific causal effect evidence, implementation feasibility/horizon data, qualified cost data, and complete risk-component mapping for resilience interventions",
            "fully_resolved": False,
        },
    ]

    claim_rows = [
        {
            "claim_id": "c01",
            "blocked_claim": "definitive monetary value of West Sumatra wasted potential",
            "status": "not_authorized",
            "blocking_evidence": "M12/M13/M17 explicitly prohibit monetary aggregation and policy counterfactual interpretation",
            "upgrade_requirement": "explicit defensible accounting or causal counterfactual model, valid aggregation basis, population/price-basis treatment, and uncertainty",
        },
        {
            "claim_id": "c02",
            "blocked_claim": "M12 favorable reference is the theoretical maximum West Sumatra should attain",
            "status": "not_authorized",
            "blocking_evidence": "M12 is an empirical favorable-peer reference and theoretical_maximum_claim=false",
            "upgrade_requirement": "separately qualified production/frontier theory and assumptions appropriate to the outcome semantics",
        },
        {
            "claim_id": "c03",
            "blocked_claim": "M11 predictive residual is causal underperformance",
            "status": "not_authorized",
            "blocking_evidence": "M11 is cross-fitted predictive estimation with causal_analysis_performed=false",
            "upgrade_requirement": "credible causal design identifying the mechanism responsible for the residual",
        },
        {
            "claim_id": "c04",
            "blocked_claim": "M12 favorable-reference distance is a policy target or guaranteed attainable gain",
            "status": "not_authorized",
            "blocking_evidence": "M12 policy_counterfactual_claim=false and favorable reference is empirical",
            "upgrade_requirement": "intervention-specific causal mapping, feasibility constraints, implementation horizon, and uncertainty",
        },
        {
            "claim_id": "c05",
            "blocked_claim": "M14 rainfall association causes unemployment gaps",
            "status": "not_authorized",
            "blocking_evidence": "M14 causal_analysis_performed=false; M15 rainfall causal design is not identification-ready",
            "upgrade_requirement": "independent identification opportunity or new post-discovery variation with a preregistered causal design",
        },
        {
            "claim_id": "c06",
            "blocked_claim": "M16 recorded flood/landslide event counts measure observed disaster impact",
            "status": "not_authorized",
            "blocking_evidence": "M16 classifies them as recorded_event_occurrence and observed_impact remains missing",
            "upgrade_requirement": "qualified affected-population, casualty, damage, disruption, or loss observations linked to events/geographies",
        },
        {
            "claim_id": "c07",
            "blocked_claim": "M16 spatial component frame is a composite disaster-risk score",
            "status": "not_authorized",
            "blocking_evidence": "M16 risk_synthesis_authorized=false and composite_risk_score_created=false",
            "upgrade_requirement": "compatible qualified hazard, exposure, vulnerability, capacity, and validation/impact components with explicit methodology and vintage",
        },
        {
            "claim_id": "c08",
            "blocked_claim": "M17 model sensitivity is a policy treatment effect or forecast",
            "status": "not_authorized",
            "blocking_evidence": "M17 causal_policy_counterfactual_estimated=false and forecast_authorized=false",
            "upgrade_requirement": "intervention-specific causal effect, raw-unit delivery mapping, invariance assumptions, and out-of-sample validation",
        },
        {
            "claim_id": "c09",
            "blocked_claim": "M17 scenarios can be ranked by policy attractiveness or cost-benefit",
            "status": "not_authorized",
            "blocking_evidence": "M17 policy_recommendation_authorized=false, cost_benefit_analysis_performed=false, costs and horizons unqualified",
            "upgrade_requirement": "comparable causal impacts, qualified implementation costs, horizons, feasibility, risks, and common decision criteria",
        },
    ]

    write_csv(NODES_OUT, nodes)
    write_csv(EDGES_OUT, edge_rows)
    write_csv(RQ_OUT, rq_rows)
    write_csv(CLAIMS_OUT, claim_rows)

    input_manifest = {
        key: {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        for key, path in INPUT_PATHS.items()
    }
    output_manifest = {
        "evidence_nodes": {"path": str(NODES_OUT.relative_to(ROOT)), "sha256": sha256(NODES_OUT)},
        "evidence_edges": {"path": str(EDGES_OUT.relative_to(ROOT)), "sha256": sha256(EDGES_OUT)},
        "research_question_readiness": {"path": str(RQ_OUT.relative_to(ROOT)), "sha256": sha256(RQ_OUT)},
        "claim_boundary_ledger": {"path": str(CLAIMS_OUT.relative_to(ROOT)), "sha256": sha256(CLAIMS_OUT)},
    }
    manifest = {
        "schema": "ranah-observatory/milestone18-final-analytical-synthesis/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 18,
        "criterion": "coherent evidence graph with explicit uncertainty, method disagreement, research-question readiness, and claim boundaries",
        "evidence_node_count": len(nodes),
        "evidence_edge_count": len(edge_rows),
        "research_question_count": len(rq_rows),
        "research_question_readiness_counts": {
            state: sum(row["readiness_state"] == state for row in rq_rows)
            for state in ("bounded_answer", "bounded_partial", "not_action_ready")
        },
        "fully_resolved_research_question_count": sum(row["fully_resolved"] is True for row in rq_rows),
        "blocked_claim_count": len(claim_rows),
        "m13_frontier_gap_sign_disagreement_count": m13["frontier_gap_sign_disagreement_count"],
        "m15_not_identification_ready_count": m15["not_identification_ready_count"],
        "m16_blocked_or_gap_component_count": m16["blocked_or_gap_component_count"],
        "m17_min_dominant_sign_retention": min_retention,
        "m17_min_dominant_sign_retention_mapping": {
            "feature_id": min_retention_row["feature_id"],
            "target_id": min_retention_row["target_id"],
        },
        "new_statistical_model_fit": False,
        "new_causal_estimate_created": False,
        "method_disagreement_averaged_away": False,
        "policy_ranking_performed": False,
        "cost_benefit_analysis_performed": False,
        "definitive_monetary_wasted_potential_estimated": False,
        "public_dashboard_required_for_phase2_completion": False,
        "phase2_analytical_engine_complete": True,
        "scientific_research_agenda_complete": False,
        "public_product_complete": False,
        "inputs": input_manifest,
        "outputs": output_manifest,
        "milestone18_complete": True,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
