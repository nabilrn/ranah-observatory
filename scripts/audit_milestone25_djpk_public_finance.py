#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
from collections import Counter
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/manifests/milestone25_djpk_public_finance_complete.json"
TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
STAGE1 = ROOT / "data/manifests/milestone25_stage1_full_export.json"
TAXONOMY = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
PANEL = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json"
OBS = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv"
PROV = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-provenance.csv"
RAW = ROOT / "data/processed/djpk/public_finance/source"
DOC = ROOT / "docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md"
PROMOTED = {"total_revenue", "own_source_revenue_pad", "total_expenditure", "capital_expenditure"}
HELD = {"central_transfer_revenue"}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    try:
        final = json.loads(FINAL.read_text(encoding="utf-8"))
        transport = json.loads(TRANSPORT.read_text(encoding="utf-8"))
        stage1 = json.loads(STAGE1.read_text(encoding="utf-8"))
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        contract_manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
        panel = json.loads(PANEL.read_text(encoding="utf-8"))
        contracts = rows(CONTRACTS)
        coverage = rows(COVERAGE)
        values = rows(VALUES)
        observations = rows(OBS)
        provenance = rows(PROV)
        doc = DOC.read_text(encoding="utf-8")

        assert final["schema"] == "ranah-observatory/milestone25-djpk-public-finance-complete/v2"
        assert final["milestone25_complete"] is True
        assert final["geography_count"] == 19
        assert final["year_count"] == 8
        assert final["jurisdiction_year_count"] == 152
        assert final["promoted_exact_label_family_count"] == 4
        assert set(final["promoted_exact_label_families"]) == PROMOTED
        assert set(final["held_families"]) == HELD
        assert final["observation_count"] == 608
        assert final["provenance_count"] == 152
        assert final["frozen_stage0_page_count"] == 8
        assert final["frozen_stage1_html_page_count"] == 152
        assert final["frozen_stage1_spreadsheetml_count"] == 152
        assert final["html_table_parseable_page_count"] + final["html_table_unparseable_page_count"] == 152
        assert final["primary_numeric_evidence"] == "djpk_csv_apbd_spreadsheetml_exact_rupiah"
        assert final["transport_representation_amended_after_failure"] is True
        assert final["scientific_design_changed_by_transport_amendment"] is False
        for key in (
            "explicit_bridge_used", "derived_ratio_created", "imputation_performed",
            "historical_boundary_reconstruction_performed", "posthoc_account_family_search_performed",
            "statistical_model_fit", "causal_claim_created", "monetary_wasted_potential_estimated",
            "user_contribution_required",
        ):
            assert final[key] is False

        assert transport["representation_amendment_after_transport_failure"] is True
        assert transport["amendment_revision"] == 3
        assert transport["annual_final_realization_semantics_required"] is True
        assert set(transport["accepted_annual_final_realization_semantics"]) == {"calendar_year_end_december", "final_accountability_audited", "final_accountability_perda"}
        assert transport["intermediate_month_or_unaudited_semantics_rejected"] is True
        assert transport["html_table_value_crosscheck_required_when_parseable"] is False
        assert transport["html_table_value_crosscheck_is_diagnostic"] is True
        assert transport["scientific_design_changed"] is False
        assert transport["account_family_set_changed"] is False
        assert transport["target_years_changed"] is False
        assert transport["geography_set_changed"] is False
        assert transport["period_selector_changed"] is False
        assert transport["posthoc_account_family_search_performed"] is False
        assert set(transport["locked_promoted_exact_label_families"]) == PROMOTED
        assert set(transport["held_families"]) == HELD

        assert taxonomy["stage0_complete"] is True
        assert taxonomy["all_pages_pass"] is True
        assert taxonomy["cross_geography_values_inspected_before_taxonomy_lock"] is False
        assert taxonomy["posthoc_account_family_search_performed"] is False

        assert contract_manifest["contracts_locked"] is True
        assert contract_manifest["cross_geography_values_inspected_before_lock"] is False
        assert contract_manifest["explicit_bridge_promoted"] is False
        assert contract_manifest["derived_ratio_authorized"] is False
        promoted = [row for row in contracts if row["stage1_promotion_status"] == "promoted_exact_label"]
        held = [row for row in contracts if row["stage1_promotion_status"] != "promoted_exact_label"]
        assert {row["conceptual_family"] for row in promoted} == PROMOTED
        assert {row["conceptual_family"] for row in held} == HELD
        assert all(row["taxonomy_contract_type"] == "exact_label" for row in promoted)

        assert stage1["schema"] == "ranah-observatory/milestone25-stage1-dual-representation/v1"
        assert stage1["jurisdiction_year_page_count"] == 152
        assert stage1["value_row_count"] == 608
        assert stage1["html_snapshot_count"] == 152
        assert stage1["spreadsheetml_snapshot_count"] == 152
        assert stage1["all_pages_pass"] is True
        assert stage1["spreadsheetml_is_primary_numeric_evidence"] is True
        assert stage1["annual_final_realization_semantics_required"] is True
        assert sum(stage1["annual_final_realization_semantics_counts"].values()) == 152
        assert set(stage1["annual_final_realization_semantics_counts"]) == {"calendar_year_end_december", "final_accountability_audited", "final_accountability_perda"}
        assert stage1["html_table_value_crosscheck_is_diagnostic"] is True
        assert stage1["html_table_parseable_page_count"] + stage1["html_table_unparseable_page_count"] == 152

        assert len(coverage) == 152
        assert all(row["page_pass"] == "True" for row in coverage)
        assert {row["same_selector_export_link_match"] for row in coverage} == {"True"}
        assert {row["export_valid_spreadsheetml"] for row in coverage} == {"True"}
        assert {row["annual_final_realization_semantics_match"] for row in coverage} == {"True"}
        semantic_counts = Counter(row["annual_final_realization_semantics_class"] for row in coverage)
        assert dict(semantic_counts) == {key: int(value) for key, value in stage1["annual_final_realization_semantics_counts"].items()}
        assert sum(int(row["html_value_crosscheck_failure_count"]) > 0 for row in coverage) == stage1["html_value_crosscheck_failure_page_count"]
        assert len(values) == 608
        assert {row["conceptual_family"] for row in values} == PROMOTED
        assert {row["taxonomy_contract_type"] for row in values} == {"exact_label"}
        assert {row["claim_type"] for row in values} == {"observed_recorded_fiscal_realization"}

        html_pages = sorted(RAW.glob("pemda-??-????-desember.html"))
        xml_pages = sorted(RAW.glob("pemda-??-????-desember.xml"))
        assert len(html_pages) == 152
        assert len(xml_pages) == 152
        coverage_by_key = {(row["djpk_pemda_selector"], row["year"]): row for row in coverage}
        for path in html_pages:
            parts = path.name.split("-")
            row = coverage_by_key[(parts[1], parts[2])]
            assert sha256(path) == row["html_response_sha256"]
        for path in xml_pages:
            parts = path.name.split("-")
            row = coverage_by_key[(parts[1], parts[2])]
            assert sha256(path) == row["export_response_sha256"]

        assert panel["schema"] == "ranah-observatory/djpk-fiscal-panel/v2"
        assert panel["observation_count"] == 608
        assert panel["provenance_count"] == 152
        assert set(panel["promoted_exact_label_families"]) == PROMOTED
        assert set(panel["held_families"]) == HELD
        assert panel["primary_numeric_evidence"] == "djpk_csv_apbd_spreadsheetml_exact_rupiah"
        assert panel["annual_final_realization_semantics_required"] is True
        assert panel["html_rounded_value_crosscheck_is_diagnostic"] is True
        assert panel["derived_ratio_count"] == 0
        assert panel["explicit_bridge_used"] is False
        assert panel["imputation_performed"] is False
        assert panel["historical_boundary_reconstruction_performed"] is False
        assert panel["posthoc_account_family_search_performed"] is False
        assert panel["statistical_model_fit"] is False

        assert len(observations) == 608
        assert len(provenance) == 152
        assert len({(row["fiscal_account_id"], row["geography_id"], row["year"]) for row in observations}) == 608
        assert len({(row["geography_id"], row["year"]) for row in provenance}) == 152
        assert {row["unit"] for row in observations} == {"IDR_billion"}
        assert {row["reference_period"] for row in observations} == {"annual_final_realization"}
        assert {row["reference_period"] for row in provenance} == {"annual_final_realization"}
        assert Counter(row["source_realization_semantics_class"] for row in provenance) == semantic_counts
        assert {row["taxonomy_contract_type"] for row in observations} == {"exact_label"}
        assert {row["numeric_evidence_representation"] for row in observations} == {"djpk_csv_apbd_spreadsheetml_exact_rupiah"}
        assert {row["imputation_performed"] for row in observations} == {"False"}
        assert {row["historical_boundary_reconstruction_performed"] for row in observations} == {"False"}
        assert {row["same_selector_export_link_verified"] for row in provenance} == {"True"}

        assert final["outputs"]["canonical_observations"]["sha256"] == sha256(OBS)
        assert final["outputs"]["provenance"]["sha256"] == sha256(PROV)
        assert final["inputs"]["transport_amendment"]["sha256"] == sha256(TRANSPORT)
        assert final["inputs"]["stage1_manifest"]["sha256"] == sha256(STAGE1)
        assert final["inputs"]["coverage"]["sha256"] == sha256(COVERAGE)
        assert final["inputs"]["probe_values"]["sha256"] == sha256(VALUES)
        assert final["inputs"]["panel_manifest"]["sha256"] == sha256(PANEL)

        doc_lower = doc.lower()
        assert "complete for the preregistered exact-label fiscal subset" in doc_lower
        assert "spreadsheetml" in doc_lower
        assert "no imputation" in doc_lower
        assert "does not claim" in doc_lower
        for family in PROMOTED | HELD:
            assert f"`{family}`" in doc
    except (AssertionError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "milestone25_audit": "pass",
        "promoted_exact_label_families": sorted(PROMOTED),
        "held_families": sorted(HELD),
        "observation_count": 608,
        "html_table_parseable_page_count": final["html_table_parseable_page_count"],
        "html_table_unparseable_page_count": final["html_table_unparseable_page_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
