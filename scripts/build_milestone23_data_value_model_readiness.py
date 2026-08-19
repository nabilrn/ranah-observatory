#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
M10 = ROOT / "data/manifests/milestone10_analytical_panel.json"
M16 = ROOT / "data/manifests/milestone16_spatial_climate_risk.json"
M18 = ROOT / "data/manifests/milestone18_final_analytical_synthesis.json"
M19 = ROOT / "data/manifests/milestone19_dynamic_forecast_engine.json"
M20 = ROOT / "data/manifests/milestone20_historical_climate_trend.json"
M21 = ROOT / "data/manifests/milestone21_climate_regime_shift.json"
M22 = ROOT / "data/manifests/milestone22_hierarchical_socioeconomic_trajectory.json"
RQ = ROOT / "data/analysis/engine/final_synthesis_v1/m18-research-question-readiness.csv"
SOURCE_REGISTRY = ROOT / "data/registries/m23-official-source-candidates.csv"
SPEC = ROOT / "research/MILESTONE23_DATA_VALUE_MODEL_READINESS_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/data_value_readiness_v1"
PRIORITIES_OUT = OUT_DIR / "m23-data-priorities.csv"
READINESS_OUT = OUT_DIR / "m23-model-readiness.csv"
ACTIONS_OUT = OUT_DIR / "m23-next-actions.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone23_data_value_model_readiness.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_upstream() -> dict[str, dict[str, Any]]:
    manifests = {
        "m10": load_json(M10),
        "m16": load_json(M16),
        "m18": load_json(M18),
        "m19": load_json(M19),
        "m20": load_json(M20),
        "m21": load_json(M21),
        "m22": load_json(M22),
    }
    required = {
        "m10": ("milestone10_complete", True),
        "m16": ("milestone16_complete", True),
        "m18": ("milestone18_complete", True),
        "m19": ("milestone19_complete", True),
        "m20": ("milestone20_complete", True),
        "m21": ("milestone21_complete", True),
        "m22": ("milestone22_complete", True),
    }
    for key, (field, expected) in required.items():
        if manifests[key].get(field) is not expected:
            raise ValueError(f"M23 requires completed {key}: {field}")
    if manifests["m18"].get("scientific_research_agenda_complete") is not False:
        raise ValueError("M23 expects scientific agenda to remain incomplete")
    if manifests["m16"].get("risk_synthesis_authorized") is not False:
        raise ValueError("M23 expects M16 risk synthesis to remain blocked")
    if manifests["m19"].get("forecast_qualified_target_count") != 0:
        raise ValueError("M23 is locked to the M19 0-qualified-target result")
    if manifests["m20"].get("robust_monotonic_geography_count") != 0:
        raise ValueError("M23 is locked to the M20 0/19 robust monotonic result")
    if manifests["m21"].get("public_claim_authorized") is not False:
        raise ValueError("M23 expects M21 regime-shift claim blocked")
    if manifests["m22"].get("hierarchical_trajectory_qualified_indicator_count") != 4:
        raise ValueError("M23 is locked to M22 4/7 qualified indicators")
    return manifests


def validate_sources() -> dict[str, dict[str, str]]:
    rows = read_csv(SOURCE_REGISTRY)
    if len(rows) != 5:
        raise ValueError(f"M23 expects 5 verified official source candidates, got {len(rows)}")
    if {row["verified_date"] for row in rows} != {"2026-08-19"}:
        raise ValueError("M23 official-source discovery snapshot date drift")
    if len({row["source_candidate_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate M23 source candidate")
    return {row["priority_family"]: row for row in rows}


def build_priorities(sources: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    # Explicit dependency tiers; not a numeric optimization score.
    rows = [
        {
            "priority_order": 1,
            "priority_tier": "A",
            "data_family": "national_comparable_regional_panel",
            "primary_source_candidate_id": sources["national_comparable_regional_panel"]["source_candidate_id"],
            "research_question_unlocks": "RQ2|RQ3",
            "engine_unlocks": "M11_expected_performance|M12_frontier|M13_gap|future_forecast_validation",
            "current_blocker": "comparison universe limited to 19 Sumbar geographies and short modern panel",
            "why_now": "directly expands sample/comparison universe after M19 forecast failure and M22 mixed partial-pooling gains",
            "credential_state": sources["national_comparable_regional_panel"]["credential_state"],
            "next_action": sources["national_comparable_regional_panel"]["next_probe"],
            "new_model_before_acquisition_authorized": False,
        },
        {
            "priority_order": 2,
            "priority_tier": "A",
            "data_family": "public_finance_panel",
            "primary_source_candidate_id": sources["public_finance_panel"]["source_candidate_id"],
            "research_question_unlocks": "RQ4|RQ5",
            "engine_unlocks": "institutional_mechanism|scenario_feasibility|cost_context",
            "current_blocker": "fiscal capacity, realized expenditure, capital expenditure, and implementation resource evidence absent",
            "why_now": "adds a major actionable institutional mechanism and addresses RQ5 feasibility/cost evidence gap",
            "credential_state": sources["public_finance_panel"]["credential_state"],
            "next_action": sources["public_finance_panel"]["next_probe"],
            "new_model_before_acquisition_authorized": False,
        },
        {
            "priority_order": 3,
            "priority_tier": "A",
            "data_family": "complete_disaster_risk_chain",
            "primary_source_candidate_id": sources["complete_disaster_risk_chain"]["source_candidate_id"],
            "research_question_unlocks": "RQ5",
            "engine_unlocks": "M16_risk_synthesis|resilience_scenario",
            "current_blocker": "M16 missing exposure, vulnerability, capacity, and observed impact",
            "why_now": "risk synthesis is explicitly unauthorized until required components are qualified",
            "credential_state": sources["complete_disaster_risk_chain"]["credential_state"],
            "next_action": sources["complete_disaster_risk_chain"]["next_probe"],
            "new_model_before_acquisition_authorized": False,
        },
        {
            "priority_order": 4,
            "priority_tier": "B",
            "data_family": "investment_realization_panel",
            "primary_source_candidate_id": sources["investment_realization_panel"]["source_candidate_id"],
            "research_question_unlocks": "RQ4|RQ5",
            "engine_unlocks": "structural_explanatory_features|investment_scenario_context",
            "current_blocker": "capital formation/investment realization absent from modern district-city panel",
            "why_now": "adds a distinct production and capital-allocation mechanism after higher-priority comparison/fiscal gaps",
            "credential_state": sources["investment_realization_panel"]["credential_state"],
            "next_action": sources["investment_realization_panel"]["next_probe"],
            "new_model_before_acquisition_authorized": False,
        },
        {
            "priority_order": 5,
            "priority_tier": "B",
            "data_family": "broader_outcome_infrastructure_health_panel",
            "primary_source_candidate_id": "bps_webapi_national",
            "research_question_unlocks": "RQ2|RQ3|RQ4",
            "engine_unlocks": "broader_attainable_development|multidimensional_gap",
            "current_blocker": "attainable-development models cover only poverty, unemployment, and real GRDP growth",
            "why_now": "broadens development dimensions after comparator-panel substrate is established",
            "credential_state": sources["national_comparable_regional_panel"]["credential_state"],
            "next_action": "After comparator harvest, qualify real GRDP per capita, health, infrastructure, and demographic indicators without shortening the core panel arbitrarily",
            "new_model_before_acquisition_authorized": False,
        },
        {
            "priority_order": 6,
            "priority_tier": "B",
            "data_family": "station_daily_climate_validation",
            "primary_source_candidate_id": sources["station_daily_climate_validation"]["source_candidate_id"],
            "research_question_unlocks": "RQ1|RQ4",
            "engine_unlocks": "climate_evidence_class|extreme_rainfall_measurement",
            "current_blocker": "CHIRPS remains model-estimate evidence and extreme daily rainfall is absent",
            "why_now": "improves climate evidence but does not itself solve rainfall-to-socioeconomic causal identification",
            "credential_state": sources["station_daily_climate_validation"]["credential_state"],
            "next_action": sources["station_daily_climate_validation"]["next_probe"],
            "new_model_before_acquisition_authorized": False,
        },
        {
            "priority_order": 7,
            "priority_tier": "C",
            "data_family": "archival_historical_series",
            "primary_source_candidate_id": "bps_archives_and_government_archives",
            "research_question_unlocks": "RQ1",
            "engine_unlocks": "long_run_public_narrative|historical_context",
            "current_blocker": "historical evidence remains sparse and boundary reconstruction incomplete",
            "why_now": "valuable for long-run narrative, but continuous 1945-present reconstruction is no longer a project completion requirement",
            "credential_state": "source_specific",
            "next_action": "Add only table-qualified historical series with explicit source-era geography and methodology; never backfill continuity",
            "new_model_before_acquisition_authorized": False,
        },
    ]
    return rows


def build_readiness(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    m22_ids = set(manifests["m22"]["hierarchical_trajectory_qualified_indicator_ids"])
    return [
        {
            "analytical_task": "modern_sumbar_descriptive_trajectory",
            "readiness_state": "partially_ready",
            "evidence_basis": "M22",
            "current_capability": "hierarchical trajectory evidence qualified for 4/7 complete non-climate indicators",
            "blocking_issue": "schooling and poverty hierarchy gates fail; growth geography slopes are unstable",
            "data_needed_before_new_model": "larger comparable regional panel and broader stable outcome families",
            "new_algorithm_priority": "low",
        },
        {
            "analytical_task": "one_year_ahead_socioeconomic_forecast",
            "readiness_state": "data_limited",
            "evidence_basis": "M19",
            "current_capability": "strict forecast harness and persistence benchmark exist",
            "blocking_issue": "0/3 dynamic-ridge targets beat persistence",
            "data_needed_before_new_model": "longer temporal panel and/or larger comparable geography universe before algorithm escalation",
            "new_algorithm_priority": "blocked_before_data_expansion",
        },
        {
            "analytical_task": "attainable_development_comparison",
            "readiness_state": "partially_ready",
            "evidence_basis": "M11|M12|M18",
            "current_capability": "bounded expected-performance and favorable-reference results for three outcomes",
            "blocking_issue": "comparison universe and development dimensions are narrow",
            "data_needed_before_new_model": "national comparable district-city panel",
            "new_algorithm_priority": "low",
        },
        {
            "analytical_task": "long_run_regional_divergence",
            "readiness_state": "data_limited",
            "evidence_basis": "M18_RQ3",
            "current_capability": "current-boundary 2019-2024 gap patterns",
            "blocking_issue": "no longer comparable national regional panel with boundary/method alignment",
            "data_needed_before_new_model": "national comparator panel with explicit geography/version semantics",
            "new_algorithm_priority": "blocked_before_data_expansion",
        },
        {
            "analytical_task": "rainfall_to_unemployment_causal_explanation",
            "readiness_state": "identification_limited",
            "evidence_basis": "M14|M15|M20|M21",
            "current_capability": "stable association signal plus richer descriptive climate history",
            "blocking_issue": "descriptive climate trend/regime analysis does not create exogenous socioeconomic treatment variation",
            "data_needed_before_new_model": "independent time variation or credible natural experiment with pre-event diagnostics",
            "new_algorithm_priority": "blocked_by_identification_not_predictor_count",
        },
        {
            "analytical_task": "disaster_risk_synthesis",
            "readiness_state": "component_limited",
            "evidence_basis": "M16",
            "current_capability": "hazard intensity, climate context, and recorded event occurrence",
            "blocking_issue": "exposure, vulnerability, capacity, and observed impact missing",
            "data_needed_before_new_model": "complete qualified risk-component chain",
            "new_algorithm_priority": "blocked_before_components",
        },
        {
            "analytical_task": "policy_action_ranking",
            "readiness_state": "component_limited",
            "evidence_basis": "M17|M18_RQ5",
            "current_capability": "predictive model sensitivities and blocked scenarios",
            "blocking_issue": "causal policy effects, qualified costs, implementation horizon, fiscal feasibility, and complete disaster risk chain absent",
            "data_needed_before_new_model": "fiscal/cost panel plus intervention-specific causal evidence and risk components",
            "new_algorithm_priority": "blocked_before_evidence",
        },
        {
            "analytical_task": "qualified_labor_and_yield_trajectory_summary",
            "readiness_state": "ready_with_current_data",
            "evidence_basis": "M22",
            "current_capability": f"qualified indicators include {','.join(sorted(m22_ids))}",
            "blocking_issue": "interpretation remains descriptive and modern-period only",
            "data_needed_before_new_model": "none for bounded descriptive publication; more data required for causal or long-run claims",
            "new_algorithm_priority": "none_for_current_estimand",
        },
    ]


def build_actions() -> list[dict[str, Any]]:
    return [
        {"sequence": 1, "work_package": "national_comparator_bps_discovery_and_harvest", "action_type": "data_acquisition", "dependency": "BPS_API_KEY repository secret", "stop_condition": "core variable/domain semantics cannot be mapped comparably", "model_fit_authorized_in_same_package": False},
        {"sequence": 2, "work_package": "djpk_public_finance_panel_probe", "action_type": "data_acquisition", "dependency": "public SIKD surface", "stop_condition": "regional code/download contract or account taxonomy cannot be versioned", "model_fit_authorized_in_same_package": False},
        {"sequence": 3, "work_package": "inarisk_risk_component_version_resolution", "action_type": "evidence_qualification", "dependency": "official BNPB/InaRISK metadata", "stop_condition": "raster/component vintage remains unbound", "model_fit_authorized_in_same_package": False},
        {"sequence": 4, "work_package": "bkpm_investment_history_inventory", "action_type": "data_discovery", "dependency": "public BKPM Satu Data", "stop_condition": "kabupaten-kota historical continuity cannot be established", "model_fit_authorized_in_same_package": False},
        {"sequence": 5, "work_package": "rebuild_analytical_readiness_after_new_data", "action_type": "model_gate_review", "dependency": "at least one Tier A dataset materially qualified", "stop_condition": "new evidence does not change sample/component/identification regime", "model_fit_authorized_in_same_package": True},
    ]


def build_outputs() -> dict[str, Any]:
    manifests = validate_upstream()
    sources = validate_sources()
    priorities = build_priorities(sources)
    readiness = build_readiness(manifests)
    actions = build_actions()

    write_csv(PRIORITIES_OUT, list(priorities[0].keys()), priorities)
    write_csv(READINESS_OUT, list(readiness[0].keys()), readiness)
    write_csv(ACTIONS_OUT, list(actions[0].keys()), actions)

    manifest = {
        "schema": "ranah-observatory/milestone23-data-value-model-readiness/v1",
        "milestone": 23,
        "phase": "post_phase2_evidence_expansion_planning",
        "criterion": "explicit dependency-based evidence acquisition priorities before additional model complexity",
        "milestone23_complete": True,
        "statistical_model_fit": False,
        "numeric_priority_score_created": False,
        "posthoc_algorithm_search_authorized": False,
        "official_source_candidate_count": len(sources),
        "data_priority_family_count": len(priorities),
        "priority_tier_counts": {
            "A": sum(row["priority_tier"] == "A" for row in priorities),
            "B": sum(row["priority_tier"] == "B" for row in priorities),
            "C": sum(row["priority_tier"] == "C" for row in priorities),
        },
        "model_readiness_task_count": len(readiness),
        "next_action_count": len(actions),
        "first_next_action": actions[0]["work_package"],
        "bps_repository_secret_expected": True,
        "user_contribution_required_for_first_action": False,
        "inputs": {
            "m10": {"path": str(M10.relative_to(ROOT)), "sha256": sha256(M10)},
            "m16": {"path": str(M16.relative_to(ROOT)), "sha256": sha256(M16)},
            "m18": {"path": str(M18.relative_to(ROOT)), "sha256": sha256(M18)},
            "m19": {"path": str(M19.relative_to(ROOT)), "sha256": sha256(M19)},
            "m20": {"path": str(M20.relative_to(ROOT)), "sha256": sha256(M20)},
            "m21": {"path": str(M21.relative_to(ROOT)), "sha256": sha256(M21)},
            "m22": {"path": str(M22.relative_to(ROOT)), "sha256": sha256(M22)},
            "m18_rq_readiness": {"path": str(RQ.relative_to(ROOT)), "sha256": sha256(RQ)},
            "source_registry": {"path": str(SOURCE_REGISTRY.relative_to(ROOT)), "sha256": sha256(SOURCE_REGISTRY)},
            "spec": {"path": str(SPEC.relative_to(ROOT)), "sha256": sha256(SPEC)},
        },
        "outputs": {
            "data_priorities": {"path": str(PRIORITIES_OUT.relative_to(ROOT)), "sha256": sha256(PRIORITIES_OUT)},
            "model_readiness": {"path": str(READINESS_OUT.relative_to(ROOT)), "sha256": sha256(READINESS_OUT)},
            "next_actions": {"path": str(ACTIONS_OUT.relative_to(ROOT)), "sha256": sha256(ACTIONS_OUT)},
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = build_outputs()
    print(json.dumps({
        "milestone23_complete": manifest["milestone23_complete"],
        "first_next_action": manifest["first_next_action"],
        "priority_tier_counts": manifest["priority_tier_counts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
