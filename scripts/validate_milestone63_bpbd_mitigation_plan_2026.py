#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_acquisition.json"
FINAL = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_final.json"
RAW = ROOT / "data/raw/bpbd/m63_renja_2026/renja-bpbd-sumbar-2026.pdf"
EXCERPT = ROOT / "data/processed/bpbd/mitigation_plan_2026/renja-bpbd-2026-pages-51-64.txt"
TARGETS = ROOT / "data/processed/bpbd/mitigation_plan_2026/bpbd-mitigation-targets-2026.csv"
GAPS = ROOT / "data/processed/bpbd/mitigation_plan_2026/bpbd-mitigation-gaps-2026.csv"
CATALOG = ROOT / "catalog/public-datasets.csv"

EXPECTED_TARGETS = {
    "preparedness_program_percent": ("72", "percent"),
    "hazard_information_dissemination_percent": ("56", "percent"),
    "legalized_risk_assessment_documents": ("1", "document"),
    "hazard_kie_recipients": ("425", "people"),
    "trained_population_percent": ("56", "percent"),
    "preparedness_mechanism_areas": ("3", "areas"),
    "preparedness_drill_participants": ("300", "people"),
    "priority_hazard_contingency_plan_documents": ("1", "document"),
    "risk_root_cause_actions": ("1", "activity"),
    "certified_provincial_trc_personnel": ("60", "people"),
    "high_risk_families_equipped": ("750", "families"),
    "skpdb_documents": ("1", "document"),
    "prevention_mitigation_training_participants": ("120", "people"),
}
EXPECTED_GAPS = {
    "planning_documents", "dibi_access_accuracy", "dissemination_socialization",
    "trc_formation_training", "forum_prb", "nagari_tangguh", "volunteer_development",
    "pusdalops_operations", "simulation_training", "tes_evacuation_routes",
    "preparedness_ews_equipment", "field_equipment_logistics",
    "rehab_reconstruction_support_equipment", "emergency_coordination",
    "contingency_based_operations", "emergency_monitoring_evaluation", "jitu_pasna",
    "rehab_reconstruction_coordination",
}
CATALOG_IDS = {"bpbd-mitigation-plan-targets-2026", "bpbd-mitigation-gaps-2026"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    require(acq["schema"] == "ranah-observatory/milestone63-bpbd-mitigation-plan-2026-acquisition/v1", "M63 acquisition schema drift")
    require(final["schema"] == "ranah-observatory/milestone63-bpbd-mitigation-plan-2026-final/v1", "M63 final schema drift")
    require(acq["raw_artifact"]["sha256"] == sha256(RAW), "M63 raw PDF checksum drift")
    require(acq["text_excerpt"]["sha256"] == sha256(EXCERPT), "M63 excerpt checksum drift")
    require(acq["text_excerpt"]["ocr_used"] is False, "M63 must remain non-OCR")
    require(final["source_manifest"]["sha256"] == sha256(ACQ), "M63 source manifest checksum drift")
    require(final["outputs"]["targets"]["sha256"] == sha256(TARGETS), "M63 target output checksum drift")
    require(final["outputs"]["gaps"]["sha256"] == sha256(GAPS), "M63 gap output checksum drift")

    with TARGETS.open(newline="", encoding="utf-8") as handle:
        targets = list(csv.DictReader(handle))
    require(len(targets) == 13, "M63 target row count drift")
    require(len({row["record_id"] for row in targets}) == 13, "M63 duplicate target IDs")
    require({row["record_id"] for row in targets} == set(EXPECTED_TARGETS), "M63 target ID footprint drift")
    for row in targets:
        value, unit = EXPECTED_TARGETS[row["record_id"]]
        require(row["target_value"] == value and row["target_unit"] == unit, f"M63 target value drift: {row['record_id']}")
        require(row["plan_year"] == "2026", "M63 target year drift")
        require(row["claim_type"] == "official_planning_target", "M63 target claim-type drift")
        require(row["actual_achievement_claimed"] == "false", "M63 target incorrectly promoted to actual achievement")

    with GAPS.open(newline="", encoding="utf-8") as handle:
        gaps = list(csv.DictReader(handle))
    require(len(gaps) == 18, "M63 qualitative gap row count drift")
    require({row["gap_id"] for row in gaps} == EXPECTED_GAPS, "M63 gap footprint drift")
    for row in gaps:
        require(row["plan_year"] == "2026", "M63 gap year drift")
        require(row["claim_type"] == "official_planning_diagnostic", "M63 gap claim-type drift")
        require(row["quantified"] == "false", "M63 qualitative gap unexpectedly quantified")
        require(row["municipality_identified"] == "false", "M63 gap incorrectly attributed to a municipality")

    result = final["result"]
    require(result["planning_target_count"] == 13 and result["qualitative_gap_count"] == 18, "M63 final counts drift")
    require(result["dashboard_planning_context_ready"] is True, "M63 dashboard planning context not ready")
    require(result["actual_capacity_score_materialized"] is False, "M63 fabricated capacity score detected")
    require(result["planning_targets_treated_as_actuals"] is False, "M63 planning targets treated as actuals")
    require(result["municipality_gap_attribution_authorized"] is False, "M63 municipality gap attribution unexpectedly authorized")
    require(result["prediction_claim_authorized"] is False, "M63 prediction claim unexpectedly authorized")
    require(result["budget_comparison_materialized"] is False, "M63 ambiguous budget comparison materialized")
    boundary = final["interpretation_boundary"]
    require(boundary["targets_are_forward_planning_commitments"] is True, "M63 target interpretation boundary drift")
    require(boundary["gaps_are_official_qualitative_diagnostics"] is True, "M63 gap interpretation boundary drift")
    require(boundary["gaps_are_not_numeric_capacity_scores"] is True, "M63 gap scoring boundary drift")
    require(boundary["no_unmitigated_probability_inference"] is True, "M63 probability boundary drift")

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        catalog = {row["id"]: row for row in csv.DictReader(handle) if row["id"] in CATALOG_IDS}
    require(set(catalog) == CATALOG_IDS, "M63 public catalog entries missing")
    require(catalog["bpbd-mitigation-plan-targets-2026"]["source_path"] == TARGETS.relative_to(ROOT).as_posix(), "M63 target catalog path drift")
    require(catalog["bpbd-mitigation-gaps-2026"]["source_path"] == GAPS.relative_to(ROOT).as_posix(), "M63 gap catalog path drift")
    require(all(row["status"] == "materialized" for row in catalog.values()), "M63 catalog status drift")

    print(json.dumps({"status": "ok", "targets": 13, "gaps": 18, "plan_year": 2026}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
