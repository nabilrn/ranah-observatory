#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
from collections import Counter
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "data/manifests/milestone25_design_gate.json"
TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
TAXONOMY = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
STAGE1_MANIFEST = ROOT / "data/manifests/milestone25_stage1_full_export.json"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
PROBE_VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
PANEL_MANIFEST = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json"
OBS = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv"
PROV = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-provenance.csv"
RAW_STAGE0 = ROOT / "data/processed/djpk/taxonomy_probe"
RAW_STAGE1 = ROOT / "data/processed/djpk/public_finance/source"
SPEC = ROOT / "research/MILESTONE25_DJPK_PUBLIC_FINANCE_SPEC.md"
OUT = ROOT / "data/manifests/milestone25_djpk_public_finance_complete.json"

YEARS = set(range(2018, 2026))
CONCEPTUAL_FAMILIES = {
    "total_revenue",
    "own_source_revenue_pad",
    "total_expenditure",
    "capital_expenditure",
    "central_transfer_revenue",
}
PROMOTED = {
    "total_revenue",
    "own_source_revenue_pad",
    "total_expenditure",
    "capital_expenditure",
}
HELD = {"central_transfer_revenue"}
ANNUAL_FINAL_CLASSES = {
    "calendar_year_end_december",
    "final_accountability_audited",
    "final_accountability_perda",
}
REGIME_ID = "sumbar_current_kabkota_djpk_realization_2018_2025_v2"


class M25FinalizationError(RuntimeError):
    pass


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise M25FinalizationError(message)


def finalize() -> dict[str, Any]:
    required_files = [
        DESIGN, TRANSPORT, CROSSWALK, TAXONOMY, CONTRACTS, CONTRACT_MANIFEST,
        STAGE1_MANIFEST, COVERAGE, PROBE_VALUES, PANEL_MANIFEST, OBS, PROV, SPEC,
    ]
    for path in required_files:
        require(path.exists(), f"missing M25 completion input: {path}")

    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    transport = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    contract_manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
    stage1 = json.loads(STAGE1_MANIFEST.read_text(encoding="utf-8"))
    panel = json.loads(PANEL_MANIFEST.read_text(encoding="utf-8"))
    crosswalk = rows(CROSSWALK)
    contracts = rows(CONTRACTS)
    coverage = rows(COVERAGE)
    probe_values = rows(PROBE_VALUES)
    observations = rows(OBS)
    provenance = rows(PROV)

    require(design.get("schema") == "ranah-observatory/milestone25-design-gate/v1", "design schema drift")
    require(design.get("design_locked_before_taxonomy_probe") is True, "M25 design not locked before taxonomy probe")
    require(design.get("djpk_province_selector") == "03", "DJPK Sumbar province selector drift")
    require(design.get("annual_realization_period_selector") == "12", "DJPK December selector drift")
    require(design.get("target_start_year") == 2018 and design.get("target_end_year") == 2025, "target year regime drift")
    require(design.get("current_sumbar_geography_count") == 19, "design geography footprint drift")
    require(set(design.get("conceptual_account_families", [])) == CONCEPTUAL_FAMILIES, "conceptual family set drift")
    require(design.get("posthoc_account_family_search_authorized") is False, "design permits posthoc account search")
    require(design.get("derived_ratio_creation_authorized_before_component_qualification") is False, "design permits premature ratios")
    require(design.get("statistical_model_fit_authorized") is False, "design permits model fit")

    require(transport.get("schema") == "ranah-observatory/milestone25-transport-amendment/v1", "transport schema drift")
    require(transport.get("representation_amendment_after_transport_failure") is True, "transport amendment not explicit")
    for key in (
        "scientific_design_changed", "account_family_set_changed", "target_years_changed",
        "geography_set_changed", "period_selector_changed", "province_selector_changed",
        "posthoc_account_family_search_performed", "explicit_taxonomy_bridge_promoted",
        "derived_ratio_authorized", "statistical_model_fit_authorized", "causal_claim_authorized",
        "imputation_performed", "historical_boundary_reconstruction_performed", "user_contribution_required",
    ):
        require(transport.get(key) is False, f"transport amendment boundary violated: {key}")
    require(set(transport.get("locked_promoted_exact_label_families", [])) == PROMOTED, "transport promoted-family drift")
    require(set(transport.get("held_families", [])) == HELD, "transport held-family drift")
    require(transport.get("html_export_selector_match_required") is True, "transport does not require same-selector export")
    require(transport.get("amendment_revision") == 3, "transport recovery revision drift")
    require(transport.get("annual_final_realization_semantics_required") is True, "annual-final semantics gate missing")
    require(set(transport.get("accepted_annual_final_realization_semantics", [])) == ANNUAL_FINAL_CLASSES, "accepted annual-final semantics drift")
    require(transport.get("intermediate_month_or_unaudited_semantics_rejected") is True, "non-final realization semantics are not rejected")
    require(transport.get("html_table_value_crosscheck_required_when_parseable") is False, "rounded HTML display crosscheck became blocking")
    require(transport.get("html_table_value_crosscheck_is_diagnostic") is True, "rounded HTML display diagnostic flag missing")

    require(len(crosswalk) == 19, "DJPK crosswalk must contain 19 current Sumbar geographies")
    require(len({row["geography_id"] for row in crosswalk}) == 19, "DJPK crosswalk geography IDs not unique")
    require({row["djpk_pemda_selector"] for row in crosswalk} == {f"{value:02d}" for value in range(1, 20)}, "DJPK pemda selector set drift")
    require({row["mapping_status"] for row in crosswalk} == {"qualified_explicit"}, "unqualified DJPK crosswalk mapping")
    aliases = {row["djpk_pemda_selector"]: row.get("djpk_identity_alias", "") for row in crosswalk if row.get("djpk_identity_alias", "")}
    require(aliases == {"01": "Kab. Limapuluh Kota", "10": "Kota Bukit Tinggi"}, "source-verified identity alias set drift")

    require(taxonomy.get("schema") == "ranah-observatory/milestone25-taxonomy-discovery/v1", "taxonomy schema drift")
    require(taxonomy.get("stage0_complete") is True and taxonomy.get("all_pages_pass") is True, "Stage 0 taxonomy incomplete")
    require(taxonomy.get("page_count") == 8, "Stage 0 page count drift")
    require(taxonomy.get("cross_geography_values_inspected_before_taxonomy_lock") is False, "cross-geography values inspected before taxonomy lock")
    require(taxonomy.get("posthoc_account_family_search_performed") is False, "Stage 0 posthoc account family search detected")
    require(taxonomy.get("statistical_model_fit") is False and taxonomy.get("derived_ratio_created") is False, "Stage 0 analytical boundary violated")
    taxonomy_results = taxonomy.get("conceptual_account_family_results")
    require(isinstance(taxonomy_results, list) and len(taxonomy_results) == 5, "Stage 0 did not classify exact five conceptual families")
    require({str(row["conceptual_family"]) for row in taxonomy_results} == CONCEPTUAL_FAMILIES, "Stage 0 conceptual family identity drift")

    raw_by_year = {int(item["year"]): item for item in taxonomy.get("raw_responses", [])}
    require(set(raw_by_year) == YEARS, "Stage 0 raw-response manifest years drift")
    require(taxonomy.get("spreadsheetml_account_table_required") is True, "Stage 0 exact SpreadsheetML taxonomy evidence not required")
    require(taxonomy.get("taxonomy_primary_representation") == "djpk_csv_apbd_spreadsheetml_exact_rupiah", "Stage 0 taxonomy representation drift")
    stage0_html_pages = sorted(RAW_STAGE0.glob("kota-padang-apbd-*-desember.html"))
    stage0_xml_pages = sorted(RAW_STAGE0.glob("kota-padang-apbd-*-desember.xml"))
    require(len(stage0_html_pages) == 8 and len(stage0_xml_pages) == 8, "Stage 0 frozen dual-representation footprint drift")
    for year, item in raw_by_year.items():
        html_path = ROOT / str(item["html_path"])
        export_path = ROOT / str(item["export_path"])
        require(html_path.exists() and export_path.exists(), f"Stage 0 frozen source missing {year}")
        require(sha256(html_path) == str(item["html_sha256"]), f"Stage 0 HTML checksum drift {year}")
        require(sha256(export_path) == str(item["export_sha256"]), f"Stage 0 SpreadsheetML checksum drift {year}")

    require(contract_manifest.get("schema") == "ranah-observatory/milestone25-stage1-account-contracts/v1", "Stage 1 contract schema drift")
    require(contract_manifest.get("contracts_locked") is True, "Stage 1 contracts not locked")
    require(contract_manifest.get("cross_geography_values_inspected_before_lock") is False, "contracts locked after cross-geography inspection")
    require(contract_manifest.get("explicit_bridge_promoted") is False, "explicit bridge promoted")
    require(contract_manifest.get("derived_ratio_authorized") is False, "derived ratio authorized")
    require(contract_manifest.get("posthoc_account_family_search_performed") is False, "posthoc account search detected")
    require(contract_manifest.get("statistical_model_fit") is False, "contract-stage model fit detected")
    promoted = [row for row in contracts if row["stage1_promotion_status"] == "promoted_exact_label"]
    held = [row for row in contracts if row["stage1_promotion_status"] != "promoted_exact_label"]
    require({row["conceptual_family"] for row in promoted} == PROMOTED, "promoted exact-label families drift")
    require({row["conceptual_family"] for row in held} == HELD, "held family drift")
    require(all(row["taxonomy_contract_type"] == "exact_label" for row in promoted), "non-exact taxonomy promoted")

    require(stage1.get("schema") == "ranah-observatory/milestone25-stage1-dual-representation/v1", "Stage 1 dual-representation schema drift")
    require(stage1.get("years") == list(range(2018, 2026)), "Stage 1 year sequence drift")
    require(stage1.get("geography_count") == 19, "Stage 1 geography count drift")
    require(stage1.get("jurisdiction_year_page_count") == 152, "Stage 1 jurisdiction-year count drift")
    require(stage1.get("promoted_exact_label_family_count") == 4, "Stage 1 promoted-family count drift")
    require(set(stage1.get("promoted_exact_label_families", [])) == PROMOTED, "Stage 1 promoted-family identities drift")
    require(stage1.get("value_row_count") == 608, "Stage 1 exact-value count drift")
    require(stage1.get("all_pages_pass") is True, "Stage 1 contains failed pages")
    require(stage1.get("html_snapshot_count") == 152 and stage1.get("spreadsheetml_snapshot_count") == 152, "Stage 1 source snapshot count drift")
    require(stage1.get("same_selector_export_link_required") is True, "Stage 1 same-selector export link not required")
    require(stage1.get("spreadsheetml_is_primary_numeric_evidence") is True, "Stage 1 primary numeric representation drift")
    require(stage1.get("annual_final_realization_semantics_required") is True, "Stage 1 annual-final semantics gate missing")
    manifest_semantics = stage1.get("annual_final_realization_semantics_counts", {})
    require(set(manifest_semantics) == ANNUAL_FINAL_CLASSES, "Stage 1 annual-final semantic class drift")
    require(sum(int(value) for value in manifest_semantics.values()) == 152, "Stage 1 annual-final semantic count drift")
    require(stage1.get("html_table_value_crosscheck_is_diagnostic") is True, "Stage 1 HTML display crosscheck became blocking")
    require(stage1.get("cross_geography_probe_completed_after_contract_lock") is True, "Stage 1 contract-order drift")
    for key in ("explicit_bridge_used", "derived_ratio_created", "imputation_performed", "posthoc_account_family_search_performed", "statistical_model_fit"):
        require(stage1.get(key) is False, f"Stage 1 boundary violated: {key}")

    require(len(coverage) == 152, f"expected 152 jurisdiction-year coverage rows, got {len(coverage)}")
    require(all(row["page_pass"] == "True" for row in coverage), "full Stage 1 contains failed page")
    require(len({(row["geography_id"], int(row["year"])) for row in coverage}) == 152, "duplicate Stage 1 coverage keys")
    require({int(row["year"]) for row in coverage} == YEARS, "Stage 1 coverage year drift")
    require(len({row["geography_id"] for row in coverage}) == 19, "Stage 1 coverage geography drift")
    require({int(row["locked_contract_count"]) for row in coverage} == {4}, "Stage 1 locked-contract cardinality drift")
    require({int(row["matched_contract_count"]) for row in coverage} == {4}, "Stage 1 matched-contract cardinality drift")
    require({row["missing_contracts"] for row in coverage} == {""}, "Stage 1 missing exact contracts")
    require({row["parse_failures"] for row in coverage} == {""}, "Stage 1 exact-value parse failures")
    require({row["same_selector_export_link_match"] for row in coverage} == {"True"}, "Stage 1 export-selector mismatch")
    require({row["export_valid_spreadsheetml"] for row in coverage} == {"True"}, "Stage 1 invalid SpreadsheetML export")
    require({row["annual_final_realization_semantics_match"] for row in coverage} == {"True"}, "Stage 1 annual-final semantics mismatch")
    semantic_counts = Counter(row["annual_final_realization_semantics_class"] for row in coverage)
    require(set(semantic_counts) == ANNUAL_FINAL_CLASSES, "Stage 1 coverage annual-final class drift")
    require(dict(semantic_counts) == {key: int(value) for key, value in manifest_semantics.items()}, "Stage 1 coverage/manifest semantic-count drift")
    diagnostic_failure_pages = sum(int(row["html_value_crosscheck_failure_count"]) > 0 for row in coverage)
    require(diagnostic_failure_pages == int(stage1.get("html_value_crosscheck_failure_page_count", -1)), "Stage 1 HTML diagnostic accounting drift")

    require(len(probe_values) == 608, f"expected 608 full-probe values, got {len(probe_values)}")
    require(len({(row["geography_id"], int(row["year"]), row["conceptual_family"]) for row in probe_values}) == 608, "duplicate Stage 1 exact value keys")
    require({row["conceptual_family"] for row in probe_values} == PROMOTED, "Stage 1 exact-value family set drift")
    require({row["taxonomy_contract_type"] for row in probe_values} == {"exact_label"}, "non-exact taxonomy reached Stage 1 values")
    require({row["claim_type"] for row in probe_values} == {"observed_recorded_fiscal_realization"}, "Stage 1 claim-type drift")

    html_pages = sorted(RAW_STAGE1.glob("pemda-??-????-desember.html"))
    xml_pages = sorted(RAW_STAGE1.glob("pemda-??-????-desember.xml"))
    require(len(html_pages) == 152, f"expected 152 frozen Stage 1 HTML pages, found {len(html_pages)}")
    require(len(xml_pages) == 152, f"expected 152 frozen Stage 1 SpreadsheetML exports, found {len(xml_pages)}")
    html_by_key = {(path.name.split("-")[1], int(path.name.split("-")[2])): path for path in html_pages}
    xml_by_key = {(path.name.split("-")[1], int(path.name.split("-")[2])): path for path in xml_pages}
    coverage_by_key = {(row["djpk_pemda_selector"], int(row["year"])): row for row in coverage}
    require(set(html_by_key) == set(xml_by_key) == set(coverage_by_key), "Stage 1 frozen source key footprint drift")
    for key, row in coverage_by_key.items():
        require(sha256(html_by_key[key]) == row["html_response_sha256"], f"Stage 1 HTML checksum drift {key}")
        require(sha256(xml_by_key[key]) == row["export_response_sha256"], f"Stage 1 export checksum drift {key}")

    require(panel.get("schema") == "ranah-observatory/djpk-fiscal-panel/v2", "fiscal panel schema drift")
    require(panel.get("comparability_regime") == REGIME_ID, "fiscal comparability regime drift")
    require(panel.get("geography_count") == 19 and panel.get("year_count") == 8, "fiscal panel footprint drift")
    require(panel.get("jurisdiction_year_count") == 152, "fiscal jurisdiction-year count drift")
    require(panel.get("promoted_exact_label_family_count") == 4 and set(panel.get("promoted_exact_label_families", [])) == PROMOTED, "panel promoted-family drift")
    require(set(panel.get("held_families", [])) == HELD, "panel held-family drift")
    require(panel.get("observation_count") == 608, "panel observation count drift")
    require(panel.get("provenance_count") == 152, "panel provenance count drift")
    require(panel.get("html_snapshot_count") == 152 and panel.get("spreadsheetml_snapshot_count") == 152, "panel source-count drift")
    require(panel.get("html_table_parseable_page_count", 0) + panel.get("html_table_unparseable_page_count", 0) == 152, "panel HTML accounting drift")
    require(panel.get("primary_numeric_evidence") == "djpk_csv_apbd_spreadsheetml_exact_rupiah", "panel numeric source drift")
    require(panel.get("annual_final_realization_semantics_required") is True, "panel annual-final semantics gate missing")
    require(panel.get("html_rounded_value_crosscheck_is_diagnostic") is True, "panel HTML rounded display crosscheck became blocking")
    for key, expected in (
        ("derived_ratio_count", 0), ("explicit_bridge_used", False), ("imputation_performed", False),
        ("historical_boundary_reconstruction_performed", False), ("posthoc_account_family_search_performed", False),
        ("statistical_model_fit", False),
    ):
        require(panel.get(key) == expected, f"panel boundary violated: {key}")

    require(len(observations) == 608, "canonical fiscal observation count drift")
    require(len({(row["fiscal_account_id"], row["geography_id"], int(row["year"])) for row in observations}) == 608, "duplicate canonical fiscal observation keys")
    require({row["fiscal_account_id"] for row in observations} == PROMOTED, "canonical fiscal family set drift")
    require(len({row["geography_id"] for row in observations}) == 19 and {int(row["year"]) for row in observations} == YEARS, "canonical fiscal panel footprint drift")
    require({row["reference_period"] for row in observations} == {"annual_final_realization"}, "canonical fiscal reference-period drift")
    require({row["unit"] for row in observations} == {"IDR_billion"}, "canonical fiscal unit drift")
    require({row["taxonomy_contract_type"] for row in observations} == {"exact_label"}, "canonical non-exact taxonomy detected")
    require({row["claim_type"] for row in observations} == {"observed_recorded_fiscal_realization"}, "canonical fiscal claim-type drift")
    require({row["comparability_regime"] for row in observations} == {REGIME_ID}, "canonical fiscal regime drift")
    require({row["numeric_evidence_representation"] for row in observations} == {"djpk_csv_apbd_spreadsheetml_exact_rupiah"}, "canonical numeric representation drift")
    require({row["imputation_performed"] for row in observations} == {"False"}, "canonical fiscal imputation flag drift")
    require({row["historical_boundary_reconstruction_performed"] for row in observations} == {"False"}, "canonical fiscal boundary flag drift")

    require(len(provenance) == 152, "canonical fiscal provenance count drift")
    require(len({row["fiscal_provenance_id"] for row in provenance}) == 152, "duplicate fiscal provenance IDs")
    require({row["same_selector_export_link_verified"] for row in provenance} == {"True"}, "provenance export-link verification drift")
    require({row["reference_period"] for row in provenance} == {"annual_final_realization"}, "provenance reference-period drift")
    provenance_semantics = Counter(row["source_realization_semantics_class"] for row in provenance)
    require(provenance_semantics == semantic_counts, "provenance annual-final semantic-count drift")
    require({row["comparability_regime"] for row in provenance} == {REGIME_ID}, "provenance regime drift")

    result = {
        "schema": "ranah-observatory/milestone25-djpk-public-finance-complete/v2",
        "milestone": 25,
        "phase": "post_phase2_fiscal_evidence_expansion",
        "criterion": "four preregistered exact-label fiscal account families with complete 19-kabupaten/kota x 2018-2025 annual-final realization evidence using official same-selector DJPK HTML semantics and SpreadsheetML exact values",
        "milestone25_complete": True,
        "geography_count": 19,
        "year_count": 8,
        "start_year": 2018,
        "end_year": 2025,
        "jurisdiction_year_count": 152,
        "promoted_exact_label_family_count": 4,
        "promoted_exact_label_families": sorted(PROMOTED),
        "held_family_count": 1,
        "held_families": sorted(HELD),
        "observation_count": 608,
        "provenance_count": 152,
        "frozen_stage0_page_count": 8,
        "frozen_stage1_page_count": 152,
        "frozen_stage1_html_page_count": 152,
        "frozen_stage1_spreadsheetml_count": 152,
        "html_table_parseable_page_count": panel["html_table_parseable_page_count"],
        "html_table_unparseable_page_count": panel["html_table_unparseable_page_count"],
        "primary_numeric_evidence": "djpk_csv_apbd_spreadsheetml_exact_rupiah",
        "html_semantic_evidence": "identity_year_annual_final_status_same_selector_export_link",
        "annual_final_realization_semantics_counts": dict(sorted(semantic_counts.items())),
        "annual_final_realization_semantics_required": True,
        "html_rounded_value_crosscheck_is_diagnostic": True,
        "transport_representation_amended_after_failure": True,
        "scientific_design_changed_by_transport_amendment": False,
        "explicit_bridge_used": False,
        "derived_ratio_created": False,
        "imputation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "posthoc_account_family_search_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "user_contribution_required": False,
        "inputs": {
            "design_gate": {"path": DESIGN.relative_to(ROOT).as_posix(), "sha256": sha256(DESIGN)},
            "transport_amendment": {"path": TRANSPORT.relative_to(ROOT).as_posix(), "sha256": sha256(TRANSPORT)},
            "crosswalk": {"path": CROSSWALK.relative_to(ROOT).as_posix(), "sha256": sha256(CROSSWALK)},
            "taxonomy": {"path": TAXONOMY.relative_to(ROOT).as_posix(), "sha256": sha256(TAXONOMY)},
            "contracts": {"path": CONTRACTS.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACTS)},
            "contract_manifest": {"path": CONTRACT_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACT_MANIFEST)},
            "stage1_manifest": {"path": STAGE1_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(STAGE1_MANIFEST)},
            "coverage": {"path": COVERAGE.relative_to(ROOT).as_posix(), "sha256": sha256(COVERAGE)},
            "probe_values": {"path": PROBE_VALUES.relative_to(ROOT).as_posix(), "sha256": sha256(PROBE_VALUES)},
            "panel_manifest": {"path": PANEL_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(PANEL_MANIFEST)},
            "spec": {"path": SPEC.relative_to(ROOT).as_posix(), "sha256": sha256(SPEC)},
        },
        "outputs": {
            "canonical_observations": {"path": OBS.relative_to(ROOT).as_posix(), "sha256": sha256(OBS)},
            "provenance": {"path": PROV.relative_to(ROOT).as_posix(), "sha256": sha256(PROV)},
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    try:
        result = finalize()
    except (OSError, json.JSONDecodeError, ValueError, M25FinalizationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "milestone25_complete": result["milestone25_complete"],
        "observation_count": result["observation_count"],
        "frozen_stage1_html_page_count": result["frozen_stage1_html_page_count"],
        "frozen_stage1_spreadsheetml_count": result["frozen_stage1_spreadsheetml_count"],
        "held_families": result["held_families"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
