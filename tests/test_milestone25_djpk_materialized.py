from __future__ import annotations

import csv
import json
from collections import Counter
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/manifests/milestone25_djpk_public_finance_complete.json"
TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
STAGE1 = ROOT / "data/manifests/milestone25_stage1_full_export.json"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
OBS = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv"
PROV = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-provenance.csv"
RAW = ROOT / "data/processed/djpk/public_finance/source"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def test_materialized_footprint_is_exact_four_family_subset() -> None:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    transport = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    contracts = rows(CONTRACTS)
    promoted = [r for r in contracts if r["stage1_promotion_status"] == "promoted_exact_label"]
    assert final["schema"] == "ranah-observatory/milestone25-djpk-public-finance-complete/v2"
    assert final["milestone25_complete"] is True
    assert len(promoted) == final["promoted_exact_label_family_count"] == 4
    assert final["observation_count"] == 19 * 8 * 4 == 608
    assert final["provenance_count"] == 19 * 8 == 152
    assert transport["scientific_design_changed"] is False
    assert transport["account_family_set_changed"] is False


def test_full_probe_has_exact_19_by_8_dual_representation_pages() -> None:
    stage1 = json.loads(STAGE1.read_text(encoding="utf-8"))
    coverage = rows(COVERAGE)
    assert stage1["jurisdiction_year_page_count"] == 152
    assert stage1["html_snapshot_count"] == 152
    assert stage1["spreadsheetml_snapshot_count"] == 152
    assert stage1["html_table_parseable_page_count"] + stage1["html_table_unparseable_page_count"] == 152
    assert len(coverage) == 152
    assert len({(r["geography_id"], r["year"]) for r in coverage}) == 152
    assert len({r["geography_id"] for r in coverage}) == 19
    assert {int(r["year"]) for r in coverage} == set(range(2018, 2026))
    assert all(r["page_pass"] == "True" for r in coverage)
    assert {r["same_selector_export_link_match"] for r in coverage} == {"True"}
    assert {r["export_valid_spreadsheetml"] for r in coverage} == {"True"}
    assert {r["annual_final_realization_semantics_match"] for r in coverage} == {"True"}
    semantic_counts = Counter(r["annual_final_realization_semantics_class"] for r in coverage)
    assert dict(semantic_counts) == {key: int(value) for key, value in stage1["annual_final_realization_semantics_counts"].items()}
    assert {r["missing_contracts"] for r in coverage} == {""}
    assert {r["parse_failures"] for r in coverage} == {""}
    assert sum(int(r["html_value_crosscheck_failure_count"]) > 0 for r in coverage) == stage1["html_value_crosscheck_failure_page_count"]


def test_probe_values_and_canonical_observations_share_exact_keys_and_amounts() -> None:
    values = rows(VALUES)
    obs = rows(OBS)
    probe_keys = {(r["conceptual_family"], r["geography_id"], r["year"]) for r in values}
    obs_keys = {(r["fiscal_account_id"], r["geography_id"], r["year"]) for r in obs}
    assert probe_keys == obs_keys
    assert len(probe_keys) == len(values) == len(obs) == 608
    assert {r["taxonomy_contract_type"] for r in values} == {"exact_label"}
    assert {r["taxonomy_contract_type"] for r in obs} == {"exact_label"}
    assert {r["numeric_evidence_representation"] for r in obs} == {"djpk_csv_apbd_spreadsheetml_exact_rupiah"}
    probe_amount = {(r["conceptual_family"], r["geography_id"], r["year"]): r["realization_rupiah_raw"] for r in values}
    for row in obs:
        assert row["realization_rupiah_exact"] == probe_amount[(row["fiscal_account_id"], row["geography_id"], row["year"])]


def test_frozen_source_footprint_and_claim_boundaries() -> None:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    html_pages = sorted(RAW.glob("pemda-??-????-desember.html"))
    xml_pages = sorted(RAW.glob("pemda-??-????-desember.xml"))
    assert len(html_pages) == 152
    assert len(xml_pages) == 152
    assert final["frozen_stage1_html_page_count"] == 152
    assert final["frozen_stage1_spreadsheetml_count"] == 152
    assert final["transport_representation_amended_after_failure"] is True
    assert final["scientific_design_changed_by_transport_amendment"] is False
    assert final["explicit_bridge_used"] is False
    assert final["derived_ratio_created"] is False
    assert final["imputation_performed"] is False
    assert final["historical_boundary_reconstruction_performed"] is False
    assert final["posthoc_account_family_search_performed"] is False
    assert final["statistical_model_fit"] is False
    assert final["causal_claim_created"] is False


def test_provenance_binds_both_official_representations() -> None:
    provenance = rows(PROV)
    assert len(provenance) == 152
    assert len({(r["geography_id"], r["year"]) for r in provenance}) == 152
    assert {r["claim_type"] for r in provenance} == {"observed_recorded_fiscal_realization"}
    assert {r["reference_period"] for r in provenance} == {"annual_final_realization"}
    assert Counter(r["source_realization_semantics_class"] for r in provenance) == Counter({"calendar_year_end_december": 139, "final_accountability_perda": 11, "final_accountability_audited": 2})
    assert {r["same_selector_export_link_verified"] for r in provenance} == {"True"}
    assert all(r["html_snapshot"].endswith(".html") for r in provenance)
    assert all(r["export_snapshot"].endswith(".xml") for r in provenance)
    assert all(len(r["html_snapshot_sha256"]) == 64 for r in provenance)
    assert all(len(r["export_snapshot_sha256"]) == 64 for r in provenance)
