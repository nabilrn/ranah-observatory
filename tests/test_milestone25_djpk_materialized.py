from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/manifests/milestone25_djpk_public_finance_complete.json"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
OBS = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv"
PROV = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-provenance.csv"
RAW = ROOT / "data/processed/djpk/public_finance/source"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_materialized_footprint_is_dynamic_exact_subset() -> None:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    contracts = rows(CONTRACTS)
    promoted = [r for r in contracts if r["stage1_promotion_status"] == "promoted_exact_label"]
    assert final["milestone25_complete"] is True
    assert len(promoted) == final["promoted_exact_label_family_count"]
    assert len(promoted) >= 1
    assert final["observation_count"] == 19 * 8 * len(promoted)
    assert final["provenance_count"] == 19 * 8


def test_full_probe_has_exact_19_by_8_pages_and_no_failures() -> None:
    coverage = rows(COVERAGE)
    assert len(coverage) == 152
    assert len({(r["geography_id"], r["year"]) for r in coverage}) == 152
    assert len({r["geography_id"] for r in coverage}) == 19
    assert {int(r["year"]) for r in coverage} == set(range(2018, 2026))
    assert all(r["page_pass"] == "True" for r in coverage)
    assert {r["missing_contracts"] for r in coverage} == {""}
    assert {r["parse_failures"] for r in coverage} == {""}


def test_probe_values_and_canonical_observations_share_exact_keys() -> None:
    values = rows(VALUES)
    obs = rows(OBS)
    probe_keys = {(r["conceptual_family"], r["geography_id"], r["year"]) for r in values}
    obs_keys = {(r["fiscal_account_id"], r["geography_id"], r["year"]) for r in obs}
    assert probe_keys == obs_keys
    assert len(probe_keys) == len(values) == len(obs)
    assert {r["taxonomy_contract_type"] for r in values} == {"exact_label"}
    assert {r["taxonomy_contract_type"] for r in obs} == {"exact_label"}


def test_frozen_source_page_footprint_and_claim_boundaries() -> None:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    pages = sorted(RAW.glob("pemda-??-????-desember.html"))
    assert len(pages) == 152
    assert final["frozen_stage1_page_count"] == 152
    assert final["explicit_bridge_used"] is False
    assert final["derived_ratio_created"] is False
    assert final["imputation_performed"] is False
    assert final["historical_boundary_reconstruction_performed"] is False
    assert final["posthoc_account_family_search_performed"] is False
    assert final["statistical_model_fit"] is False


def test_provenance_is_one_per_jurisdiction_year() -> None:
    provenance = rows(PROV)
    assert len(provenance) == 152
    assert len({(r["geography_id"], r["year"]) for r in provenance}) == 152
    assert {r["claim_type"] for r in provenance} == {"observed_recorded_fiscal_realization"}
    assert {r["reference_period"] for r in provenance} == {"realisasi_s.d._desember"}
