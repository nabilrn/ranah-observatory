#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone64_krb_recommendations_acquisition.json"
FINAL = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"
READING = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-recommendation-reading-order-pages-98-109.txt"
SECTIONS = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-specific-recommendation-sections.csv"
ACTIONS = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-mitigation-actions-2022-2026.csv"
CONTEXT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-recommendation-context-2022-2026.csv"
CATALOG = ROOT / "catalog/public-datasets.csv"

EXPECTED_LABELS = {
    "flood": "BANJIR",
    "flash_flood": "BANJIR BANDANG",
    "extreme_weather": "CUACA EKSTRIM",
    "extreme_wave_and_coastal_erosion": "GELOMBANG EKSTRIM DAN ABRASI",
    "earthquake": "GEMPABUMI",
    "liquefaction": "LIKUEFAKSI",
    "forest_and_land_fire": "KEBAKARAN HUTAN DAN LAHAN",
    "drought": "KEKERINGAN",
    "volcanic_eruption": "LETUSAN GUNUNGAPI",
    "landslide": "TANAH LONGSOR",
    "tsunami": "TSUNAMI",
    "epidemic_and_disease_outbreak": "EPIDEMI DAN WABAH PENYAKIT",
    "technological_failure": "KEGAGALAN TEKNOLOGI",
    "covid_19": "COVID-19",
}
EXPECTED_ACTION_COUNTS = {
    "flood": 7,
    "flash_flood": 6,
    "extreme_weather": 6,
    "extreme_wave_and_coastal_erosion": 6,
    "earthquake": 2,
    "liquefaction": 5,
    "forest_and_land_fire": 4,
    "drought": 5,
    "volcanic_eruption": 7,
    "landslide": 4,
    "tsunami": 8,
}
NESTED_SOURCE_ONLY = {"epidemic_and_disease_outbreak", "technological_failure", "covid_19"}
CATALOG_IDS = {
    "bnpb-krb-sumbar-hazard-mitigation-actions-2022-2026",
    "bnpb-krb-sumbar-recommendation-sections-2022-2026",
}
RAW_SHA256 = "58e18cbc8457dc8a6f47fd3e094b8b23358966b2dba8dfae67eff05d385fddd4"
READING_SHA256 = "bdfb7ff46398c95e7567caa3c0ca0bcd5086691e83716104408e6a459c6c413f"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))

    require(acq["schema"] == "ranah-observatory/milestone64-krb-recommendations-acquisition/v1", "M64 acquisition schema drift")
    require(final["schema"] == "ranah-observatory/milestone64-krb-recommendations-final/v1", "M64 final schema drift")
    require(acq["raw_artifact"]["sha256"] == RAW_SHA256, "M64 frozen raw PDF checksum drift")
    require(acq["raw_artifact"]["committed_to_repository"] is False, "M64 large source PDF unexpectedly committed by contract")
    reading = acq["text_extraction"]["reading_order_excerpt"]
    require(reading["method"] == "pdftotext -raw" and reading["ocr_used"] is False, "M64 reading-order extraction contract drift")
    require(reading["pdf_pages_one_based"] == [98, 109], "M64 reading-order page span drift")
    require(reading["sha256"] == READING_SHA256 == sha256(READING), "M64 reading-order checksum drift")
    boundary = acq["qualification_boundary"]
    require(boundary["layout_excerpt_authorized_for_section_materialization"] is False, "M64 two-column layout text unexpectedly authorized")
    require(boundary["reading_order_excerpt_authorized_for_section_materialization"] is True, "M64 reading-order text not authorized")
    require(boundary["causal_prediction_authorized"] is False, "M64 causal prediction unexpectedly authorized")
    require(boundary["unmitigated_loss_forecast_authorized"] is False, "M64 unmitigated loss forecast unexpectedly authorized")
    require(boundary["recommendations_are_observed_outcomes"] is False, "M64 recommendations incorrectly treated as observed outcomes")
    require(final["source_manifest"]["sha256"] == sha256(ACQ), "M64 acquisition manifest checksum drift")

    outputs = final["outputs"]
    require(outputs["source_native_sections"]["sha256"] == sha256(SECTIONS), "M64 source-native section checksum drift")
    require(outputs["hazard_actions"]["sha256"] == sha256(ACTIONS), "M64 action checksum drift")
    require(outputs["priority_context"]["sha256"] == sha256(CONTEXT), "M64 context checksum drift")

    sections = read_csv(SECTIONS)
    require(len(sections) == 14, "M64 source-native section count drift")
    require({row["krb_hazard_id"] for row in sections} == set(EXPECTED_LABELS), "M64 source-native hazard footprint drift")
    require(len({row["section_id"] for row in sections}) == 14, "M64 duplicate source-native section IDs")
    for row in sections:
        hazard = row["krb_hazard_id"]
        require(row["source_hazard_label"] == EXPECTED_LABELS[hazard], f"M64 source label drift: {hazard}")
        require(row["claim_type"] == "official_risk_reduction_recommendation_section", f"M64 section claim-type drift: {hazard}")
        require(row["prediction_claim_authorized"] == "false", f"M64 section prediction claim drift: {hazard}")
        require(row["unmitigated_loss_forecast_authorized"] == "false", f"M64 section loss-forecast drift: {hazard}")
        require(len(row["recommendation_text_source_native"]) >= 120, f"M64 section unexpectedly short: {hazard}")

    actions = read_csv(ACTIONS)
    require(len(actions) == 60, "M64 action row count drift")
    by_hazard: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in actions:
        by_hazard[row["krb_hazard_id"]].append(row)
        require(row["claim_type"] == "official_risk_reduction_recommendation", "M64 action claim-type drift")
        require(row["observed_implementation_claimed"] == "false", "M64 recommendation incorrectly promoted to observed implementation")
        require(row["prediction_claim_authorized"] == "false", "M64 action prediction claim unexpectedly authorized")
        require(row["unmitigated_loss_forecast_authorized"] == "false", "M64 action loss forecast unexpectedly authorized")
        upper = row["action_text_source_native"].upper()
        require("DOKUMEN KAJIAN RISIKO" not in upper and "[PDF PAGE" not in upper, "M64 PDF page furniture leaked into action text")
    require(set(by_hazard) == set(EXPECTED_ACTION_COUNTS), "M64 flat-action hazard footprint drift")
    for hazard, expected_count in EXPECTED_ACTION_COUNTS.items():
        rows = sorted(by_hazard[hazard], key=lambda row: int(row["action_order"]))
        require(len(rows) == expected_count, f"M64 action count drift: {hazard}")
        require([int(row["action_order"]) for row in rows] == list(range(1, expected_count + 1)), f"M64 action sequence drift: {hazard}")
        require(all(row["source_hazard_label"] == EXPECTED_LABELS[hazard] for row in rows), f"M64 action source label drift: {hazard}")

    context = read_csv(CONTEXT)
    require(len(context) == 14, "M64 recommendation context count drift")
    require({row["krb_hazard_id"] for row in context} == set(EXPECTED_LABELS), "M64 context hazard footprint drift")
    for row in context:
        hazard = row["krb_hazard_id"]
        expected_status = "source_section_only_nested_structure" if hazard in NESTED_SOURCE_ONLY else "flat_actions_materialized"
        require(row["action_detail_status"] == expected_status, f"M64 action-detail status drift: {hazard}")
        require(row["claim_type"] == "official_recommendation_priority_context", f"M64 context claim type drift: {hazard}")
        require(row["cross_source_taxonomy_equivalence_authorized"] == "false", f"M64 cross-source taxonomy equivalence unexpectedly authorized: {hazard}")
        require(row["prediction_claim_authorized"] == "false", f"M64 context prediction unexpectedly authorized: {hazard}")

    result = final["result"]
    require(result["specific_recommendation_section_count"] == 14 and result["hazard_count"] == 14, "M64 final section counts drift")
    require(result["specific_recommendation_action_count"] == 60, "M64 final action count drift")
    require(result["flat_action_hazard_count"] == 11 and result["nested_source_only_hazard_count"] == 3, "M64 action structure counts drift")
    require(result["priority_context_row_count"] == 14, "M64 final context count drift")
    require(result["source_native_sections_materialized"] is True and result["reading_order_extraction_used"] is True, "M64 source section qualification drift")
    require(result["two_column_layout_materialization_rejected"] is True, "M64 two-column rejection boundary drift")
    require(result["dashboard_action_summary_ready"] is True, "M64 dashboard action layer not ready")
    require(result["nested_numbering_flattened"] is False, "M64 nested recommendation hierarchy was flattened")
    require(result["page_furniture_removed_from_action_text"] is True, "M64 action page-furniture cleanup boundary drift")
    require(result["recommendations_treated_as_observed_outcomes"] is False, "M64 recommendations treated as observed outcomes")
    require(result["observed_implementation_claimed"] is False, "M64 observed implementation unexpectedly claimed")
    require(result["causal_prediction_authorized"] is False, "M64 causal prediction unexpectedly authorized")
    require(result["unmitigated_loss_forecast_authorized"] is False, "M64 unmitigated-loss forecast unexpectedly authorized")
    require(final["taxonomy_boundary"]["cross_source_taxonomy_equivalence_authorized"] is False, "M64 cross-source taxonomy equivalence unexpectedly authorized")

    coverage = final["action_coverage_by_hazard"]
    require(set(coverage) == set(EXPECTED_LABELS), "M64 final action coverage footprint drift")
    for hazard, expected_count in EXPECTED_ACTION_COUNTS.items():
        require(coverage[hazard] == {"action_detail_status": "flat_actions_materialized", "flat_action_count": expected_count}, f"M64 final flat coverage drift: {hazard}")
    for hazard in NESTED_SOURCE_ONLY:
        require(coverage[hazard] == {"action_detail_status": "source_section_only_nested_structure", "flat_action_count": 0}, f"M64 nested coverage drift: {hazard}")

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        catalog = {row["id"]: row for row in csv.DictReader(handle) if row["id"] in CATALOG_IDS}
    require(set(catalog) == CATALOG_IDS, "M64 public catalog entries missing")
    require(catalog["bnpb-krb-sumbar-hazard-mitigation-actions-2022-2026"]["source_path"] == ACTIONS.relative_to(ROOT).as_posix(), "M64 action catalog path drift")
    require(catalog["bnpb-krb-sumbar-recommendation-sections-2022-2026"]["source_path"] == SECTIONS.relative_to(ROOT).as_posix(), "M64 section catalog path drift")
    require(all(row["status"] == "materialized" for row in catalog.values()), "M64 catalog status drift")

    print(json.dumps({
        "status": "ok",
        "sections": 14,
        "actions": 60,
        "flat_action_hazards": 11,
        "nested_source_only_hazards": 3,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
