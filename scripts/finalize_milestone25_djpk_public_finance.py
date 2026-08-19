#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "data/manifests/milestone25_design_gate.json"
CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
TAXONOMY = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
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
REGIME_ID = "sumbar_current_kabkota_djpk_realization_2018_2025_v1"


class M25FinalizationError(RuntimeError):
    pass


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise M25FinalizationError(message)


def dynamic_stage0_pages() -> list[Path]:
    return sorted(RAW_STAGE0.glob("kota-padang-apbd-*-desember.html"))


def dynamic_stage1_pages() -> list[Path]:
    return sorted(RAW_STAGE1.glob("pemda-??-????-desember.html"))


def finalize() -> dict[str, Any]:
    required_files = [
        DESIGN, CROSSWALK, TAXONOMY, CONTRACTS, CONTRACT_MANIFEST,
        COVERAGE, PROBE_VALUES, PANEL_MANIFEST, OBS, PROV, SPEC,
    ]
    for path in required_files:
        require(path.exists(), f"missing M25 completion input: {path}")

    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    contract_manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
    panel = json.loads(PANEL_MANIFEST.read_text(encoding="utf-8"))
    crosswalk = rows(CROSSWALK)
    contracts = rows(CONTRACTS)
    coverage = rows(COVERAGE)
    probe_values = rows(PROBE_VALUES)
    observations = rows(OBS)
    provenance = rows(PROV)

    # Design and source-regime lock.
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

    # Crosswalk exactness.
    require(len(crosswalk) == 19, "DJPK crosswalk must contain 19 current Sumbar geographies")
    require(len({row["geography_id"] for row in crosswalk}) == 19, "DJPK crosswalk geography IDs not unique")
    require({row["djpk_pemda_selector"] for row in crosswalk} == {f"{value:02d}" for value in range(1, 20)}, "DJPK pemda selector set drift")
    require({row["mapping_status"] for row in crosswalk} == {"qualified_explicit"}, "unqualified DJPK crosswalk mapping")

    # Stage 0 must precede and bound Stage 1.
    require(taxonomy.get("schema") == "ranah-observatory/milestone25-taxonomy-discovery/v1", "taxonomy schema drift")
    require(taxonomy.get("stage0_complete") is True and taxonomy.get("all_pages_pass") is True, "Stage 0 taxonomy incomplete")
    require(taxonomy.get("page_count") == 8, "Stage 0 page count drift")
    require(taxonomy.get("cross_geography_values_inspected_before_taxonomy_lock") is False, "cross-geography values inspected before taxonomy lock")
    require(taxonomy.get("posthoc_account_family_search_performed") is False, "posthoc account family search detected")
    require(taxonomy.get("statistical_model_fit") is False, "Stage 0 statistical model detected")
    require(taxonomy.get("derived_ratio_created") is False, "Stage 0 derived ratio detected")
    taxonomy_results = taxonomy.get("conceptual_account_family_results")
    require(isinstance(taxonomy_results, list) and len(taxonomy_results) == 5, "Stage 0 did not classify exact five conceptual families")
    require({str(row["conceptual_family"]) for row in taxonomy_results} == CONCEPTUAL_FAMILIES, "Stage 0 conceptual family identity drift")

    stage0_pages = dynamic_stage0_pages()
    require(len(stage0_pages) == 8, f"expected 8 frozen Stage 0 Padang pages, found {len(stage0_pages)}")
    require({int(path.stem.split("-")[-2]) for path in stage0_pages} == YEARS, "Stage 0 frozen page years drift")
    raw_by_year = {int(item["year"]): item for item in taxonomy.get("raw_responses", [])}
    require(set(raw_by_year) == YEARS, "Stage 0 raw-response manifest years drift")
    for path in stage0_pages:
        year = int(path.stem.split("-")[-2])
        require(sha256(path) == str(raw_by_year[year]["sha256"]), f"Stage 0 raw page checksum drift {year}")

    # Stage 1 contract lock must promote exact labels only.
    require(contract_manifest.get("schema") == "ranah-observatory/milestone25-stage1-account-contracts/v1", "Stage 1 contract schema drift")
    require(contract_manifest.get("contracts_locked") is True, "Stage 1 contracts not locked")
    require(contract_manifest.get("cross_geography_values_inspected_before_lock") is False, "Stage 1 contracts locked after cross-geography inspection")
    require(contract_manifest.get("explicit_bridge_promoted") is False, "explicit bridge was promoted into exact panel")
    require(contract_manifest.get("derived_ratio_authorized") is False, "derived ratio authorized in Stage 1 contracts")
    require(contract_manifest.get("posthoc_account_family_search_performed") is False, "Stage 1 posthoc family search detected")
    require(contract_manifest.get("statistical_model_fit") is False, "Stage 1 contract model fit detected")
    require(len(contracts) == 5 and {row["conceptual_family"] for row in contracts} == CONCEPTUAL_FAMILIES, "Stage 1 contract registry family drift")
    promoted = [row for row in contracts if row["stage1_promotion_status"] == "promoted_exact_label"]
    held = [row for row in contracts if row["stage1_promotion_status"] != "promoted_exact_label"]
    require(len(promoted) >= 1, "M25 has no promoted exact-label fiscal family")
    require(len(promoted) == contract_manifest.get("promoted_exact_label_family_count"), "promoted exact-label family count drift")
    require({row["conceptual_family"] for row in promoted} == set(contract_manifest.get("promoted_exact_label_families", [])), "promoted family identity drift")
    require({row["conceptual_family"] for row in held} == set(contract_manifest.get("held_families", [])), "held family identity drift")
    for row in promoted:
        require(row["taxonomy_contract_type"] == "exact_label", "non-exact contract leaked into promoted panel")
        require(bool(row["locked_source_label_normalized"]), "promoted contract missing normalized source label")
        require(row["cross_geography_values_inspected_before_lock"] == "False", "promoted contract claims pre-lock crossgeo inspection")
        require(row["derived_ratio_authorized"] == "False", "promoted contract authorizes derived ratio")

    # Full Stage 1 source probe.
    require(len(coverage) == 152, f"expected 152 jurisdiction-year coverage rows, got {len(coverage)}")
    require(all(row["page_pass"] == "True" for row in coverage), "full Stage 1 contains failed page")
    require(len({(row["geography_id"], int(row["year"])) for row in coverage}) == 152, "duplicate Stage 1 coverage keys")
    require({int(row["year"]) for row in coverage} == YEARS, "Stage 1 coverage year drift")
    require(len({row["geography_id"] for row in coverage}) == 19, "Stage 1 coverage geography drift")
    require({int(row["locked_contract_count"]) for row in coverage} == {len(promoted)}, "Stage 1 locked-contract cardinality drift")
    require({int(row["matched_contract_count"]) for row in coverage} == {len(promoted)}, "Stage 1 matched-contract cardinality drift")
    require({row["missing_contracts"] for row in coverage} == {""}, "Stage 1 missing exact contracts")
    require({row["parse_failures"] for row in coverage} == {""}, "Stage 1 money parse failures")

    expected_value_count = 152 * len(promoted)
    require(len(probe_values) == expected_value_count, f"expected {expected_value_count} full-probe values, got {len(probe_values)}")
    require(len({(row["geography_id"], int(row["year"]), row["conceptual_family"]) for row in probe_values}) == expected_value_count, "duplicate Stage 1 probe value keys")
    require({row["conceptual_family"] for row in probe_values} == {row["conceptual_family"] for row in promoted}, "probe value family set drift")
    require({row["taxonomy_contract_type"] for row in probe_values} == {"exact_label"}, "non-exact taxonomy reached full probe")
    require({row["claim_type"] for row in probe_values} == {"observed_recorded_fiscal_realization"}, "full-probe claim type drift")

    stage1_pages = dynamic_stage1_pages()
    require(len(stage1_pages) == 152, f"expected 152 frozen Stage 1 pages, found {len(stage1_pages)}")
    page_by_selector_year = {(path.name.split("-")[1], int(path.name.split("-")[2])): path for path in stage1_pages}
    require(len(page_by_selector_year) == 152, "duplicate Stage 1 source page filenames")
    coverage_by_selector_year = {(row["djpk_pemda_selector"], int(row["year"])): row for row in coverage}
    require(set(page_by_selector_year) == set(coverage_by_selector_year), "Stage 1 source page selector/year set drift")
    for key, path in page_by_selector_year.items():
        require(sha256(path) == coverage_by_selector_year[key]["response_sha256"], f"Stage 1 raw page checksum drift {key}")

    # Canonical exact-label panel.
    require(panel.get("schema") == "ranah-observatory/djpk-fiscal-panel/v1", "fiscal panel schema drift")
    require(panel.get("comparability_regime") == REGIME_ID, "fiscal comparability regime drift")
    require(panel.get("geography_count") == 19 and panel.get("year_count") == 8, "fiscal panel geography/year footprint drift")
    require(panel.get("jurisdiction_year_count") == 152, "fiscal jurisdiction-year count drift")
    require(panel.get("promoted_exact_label_family_count") == len(promoted), "panel promoted family count drift")
    require(set(panel.get("promoted_exact_label_families", [])) == {row["conceptual_family"] for row in promoted}, "panel promoted family identity drift")
    require(set(panel.get("held_families", [])) == {row["conceptual_family"] for row in held}, "panel held family identity drift")
    require(panel.get("observation_count") == expected_value_count, "panel observation count drift")
    require(panel.get("provenance_count") == 152, "panel provenance count drift")
    require(panel.get("derived_ratio_count") == 0, "derived fiscal ratio leaked into exact panel")
    require(panel.get("explicit_bridge_used") is False, "explicit bridge leaked into exact panel")
    require(panel.get("imputation_performed") is False, "fiscal panel imputation detected")
    require(panel.get("historical_boundary_reconstruction_performed") is False, "fiscal panel historical boundary reconstruction detected")
    require(panel.get("statistical_model_fit") is False, "fiscal panel model fit detected")

    require(len(observations) == expected_value_count, "canonical fiscal observation file count drift")
    require(len({(row["fiscal_account_id"], row["geography_id"], int(row["year"])) for row in observations}) == expected_value_count, "duplicate canonical fiscal observation keys")
    require({row["fiscal_account_id"] for row in observations} == {row["conceptual_family"] for row in promoted}, "canonical fiscal family set drift")
    require(len({row["geography_id"] for row in observations}) == 19, "canonical fiscal geography count drift")
    require({int(row["year"]) for row in observations} == YEARS, "canonical fiscal year drift")
    require({row["reference_period"] for row in observations} == {"realisasi_s.d._desember"}, "canonical fiscal reference-period drift")
    require({row["unit"] for row in observations} == {"IDR_billion"}, "canonical fiscal unit drift")
    require({row["taxonomy_contract_type"] for row in observations} == {"exact_label"}, "canonical non-exact taxonomy detected")
    require({row["claim_type"] for row in observations} == {"observed_recorded_fiscal_realization"}, "canonical fiscal claim-type drift")
    require({row["comparability_regime"] for row in observations} == {REGIME_ID}, "canonical fiscal regime drift")
    require({row["imputation_performed"] for row in observations} == {"False"}, "canonical fiscal imputation flag drift")
    require({row["historical_boundary_reconstruction_performed"] for row in observations} == {"False"}, "canonical fiscal boundary flag drift")

    require(len(provenance) == 152, "canonical fiscal provenance file count drift")
    require(len({row["fiscal_provenance_id"] for row in provenance}) == 152, "duplicate fiscal provenance IDs")
    require({int(row["year"]) for row in provenance} == YEARS, "fiscal provenance year drift")
    require(len({row["geography_id"] for row in provenance}) == 19, "fiscal provenance geography drift")
    require({row["reference_period"] for row in provenance} == {"realisasi_s.d._desember"}, "fiscal provenance reference-period drift")
    require({row["claim_type"] for row in provenance} == {"observed_recorded_fiscal_realization"}, "fiscal provenance claim-type drift")

    class_counts = Counter(row["stage0_status"] for row in contracts)
    result = {
        "schema": "ranah-observatory/milestone25-djpk-public-finance-complete/v1",
        "milestone": 25,
        "phase": "post_phase2_fiscal_evidence_expansion",
        "criterion": "exact-label DJPK December-realization panel across 19 current West Sumatra kabupaten/kota for 2018-2025 with taxonomy locked before cross-geography extraction",
        "milestone25_complete": True,
        "stage0_taxonomy_complete": True,
        "stage1_exact_panel_complete": True,
        "source_id": "djpk_sikd_apbd_portal",
        "geography_level": "kabupaten_kota",
        "geography_count": 19,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "jurisdiction_year_count": 152,
        "conceptual_account_family_count": 5,
        "promoted_exact_label_family_count": len(promoted),
        "promoted_exact_label_families": [row["conceptual_family"] for row in promoted],
        "held_family_count": len(held),
        "held_families": [row["conceptual_family"] for row in held],
        "stage0_status_counts": dict(sorted(class_counts.items())),
        "observation_count": expected_value_count,
        "provenance_count": 152,
        "frozen_stage0_page_count": 8,
        "frozen_stage1_page_count": 152,
        "reference_period": "realisasi_s.d._desember",
        "canonical_unit": "IDR_billion",
        "claim_type": "observed_recorded_fiscal_realization",
        "explicit_bridge_used": False,
        "derived_ratio_created": False,
        "imputation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "posthoc_account_family_search_performed": False,
        "statistical_model_fit": False,
        "user_contribution_required": False,
        "inputs": {
            "design_gate": {"path": DESIGN.relative_to(ROOT).as_posix(), "sha256": sha256(DESIGN)},
            "crosswalk": {"path": CROSSWALK.relative_to(ROOT).as_posix(), "sha256": sha256(CROSSWALK)},
            "taxonomy_discovery": {"path": TAXONOMY.relative_to(ROOT).as_posix(), "sha256": sha256(TAXONOMY)},
            "stage1_contract_registry": {"path": CONTRACTS.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACTS)},
            "stage1_contract_manifest": {"path": CONTRACT_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACT_MANIFEST)},
            "full_probe_coverage": {"path": COVERAGE.relative_to(ROOT).as_posix(), "sha256": sha256(COVERAGE)},
            "full_probe_values": {"path": PROBE_VALUES.relative_to(ROOT).as_posix(), "sha256": sha256(PROBE_VALUES)},
            "panel_manifest": {"path": PANEL_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(PANEL_MANIFEST)},
            "spec": {"path": SPEC.relative_to(ROOT).as_posix(), "sha256": sha256(SPEC)},
        },
        "outputs": {
            "canonical_observations": {"path": OBS.relative_to(ROOT).as_posix(), "sha256": sha256(OBS)},
            "provenance": {"path": PROV.relative_to(ROOT).as_posix(), "sha256": sha256(PROV)},
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    try:
        result = finalize()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, M25FinalizationError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({
        "milestone25_complete": result["milestone25_complete"],
        "promoted_exact_label_families": result["promoted_exact_label_families"],
        "held_families": result["held_families"],
        "observation_count": result["observation_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
