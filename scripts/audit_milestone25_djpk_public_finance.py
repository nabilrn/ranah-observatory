#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/manifests/milestone25_djpk_public_finance_complete.json"
TAXONOMY = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
PANEL = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json"
OBS = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv"
PROV = ROOT / "data/processed/djpk/public_finance/djpk-fiscal-provenance.csv"
DOC = ROOT / "docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    try:
        final = json.loads(FINAL.read_text(encoding="utf-8"))
        taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
        contract_manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
        panel = json.loads(PANEL.read_text(encoding="utf-8"))
        contracts = rows(CONTRACTS)
        coverage = rows(COVERAGE)
        values = rows(VALUES)
        observations = rows(OBS)
        provenance = rows(PROV)
        doc = DOC.read_text(encoding="utf-8")

        assert final["schema"] == "ranah-observatory/milestone25-djpk-public-finance-complete/v1"
        assert final["milestone25_complete"] is True
        assert final["stage0_taxonomy_complete"] is True
        assert final["stage1_exact_panel_complete"] is True
        assert final["geography_count"] == 19
        assert final["year_count"] == 8
        assert final["jurisdiction_year_count"] == 152
        assert final["promoted_exact_label_family_count"] >= 1
        assert final["observation_count"] == 152 * final["promoted_exact_label_family_count"]
        assert final["provenance_count"] == 152
        assert final["frozen_stage0_page_count"] == 8
        assert final["frozen_stage1_page_count"] == 152
        assert final["reference_period"] == "realisasi_s.d._desember"
        assert final["canonical_unit"] == "IDR_billion"
        assert final["claim_type"] == "observed_recorded_fiscal_realization"
        assert final["explicit_bridge_used"] is False
        assert final["derived_ratio_created"] is False
        assert final["imputation_performed"] is False
        assert final["historical_boundary_reconstruction_performed"] is False
        assert final["posthoc_account_family_search_performed"] is False
        assert final["statistical_model_fit"] is False
        assert final["user_contribution_required"] is False

        assert taxonomy["stage0_complete"] is True
        assert taxonomy["all_pages_pass"] is True
        assert taxonomy["cross_geography_values_inspected_before_taxonomy_lock"] is False
        assert taxonomy["posthoc_account_family_search_performed"] is False

        assert contract_manifest["contracts_locked"] is True
        assert contract_manifest["cross_geography_values_inspected_before_lock"] is False
        assert contract_manifest["explicit_bridge_promoted"] is False
        assert contract_manifest["derived_ratio_authorized"] is False
        promoted = [r for r in contracts if r["stage1_promotion_status"] == "promoted_exact_label"]
        held = [r for r in contracts if r["stage1_promotion_status"] != "promoted_exact_label"]
        assert [r["conceptual_family"] for r in promoted] == final["promoted_exact_label_families"]
        assert [r["conceptual_family"] for r in held] == final["held_families"]
        assert all(r["taxonomy_contract_type"] == "exact_label" for r in promoted)
        assert all(r["derived_ratio_authorized"] == "False" for r in contracts)

        assert len(coverage) == 152
        assert all(r["page_pass"] == "True" for r in coverage)
        assert len(values) == final["observation_count"]
        assert {r["conceptual_family"] for r in values} == set(final["promoted_exact_label_families"])
        assert {r["taxonomy_contract_type"] for r in values} == {"exact_label"}
        assert {r["claim_type"] for r in values} == {"observed_recorded_fiscal_realization"}

        assert panel["observation_count"] == final["observation_count"]
        assert panel["provenance_count"] == 152
        assert panel["promoted_exact_label_families"] == final["promoted_exact_label_families"]
        assert panel["held_families"] == final["held_families"]
        assert panel["derived_ratio_count"] == 0
        assert panel["explicit_bridge_used"] is False
        assert panel["imputation_performed"] is False
        assert panel["historical_boundary_reconstruction_performed"] is False
        assert panel["statistical_model_fit"] is False

        assert len(observations) == final["observation_count"]
        assert len(provenance) == 152
        assert len({(r["fiscal_account_id"], r["geography_id"], r["year"]) for r in observations}) == len(observations)
        assert len({(r["geography_id"], r["year"]) for r in provenance}) == 152
        assert {r["unit"] for r in observations} == {"IDR_billion"}
        assert {r["reference_period"] for r in observations} == {"realisasi_s.d._desember"}
        assert {r["taxonomy_contract_type"] for r in observations} == {"exact_label"}
        assert {r["imputation_performed"] for r in observations} == {"False"}
        assert {r["historical_boundary_reconstruction_performed"] for r in observations} == {"False"}

        assert final["outputs"]["canonical_observations"]["sha256"] == sha256(OBS)
        assert final["outputs"]["provenance"]["sha256"] == sha256(PROV)
        assert final["inputs"]["taxonomy_discovery"]["sha256"] == sha256(TAXONOMY)
        assert final["inputs"]["stage1_contract_registry"]["sha256"] == sha256(CONTRACTS)
        assert final["inputs"]["stage1_contract_manifest"]["sha256"] == sha256(CONTRACT_MANIFEST)
        assert final["inputs"]["full_probe_coverage"]["sha256"] == sha256(COVERAGE)
        assert final["inputs"]["full_probe_values"]["sha256"] == sha256(VALUES)
        assert final["inputs"]["panel_manifest"]["sha256"] == sha256(PANEL)

        doc_lower = doc.lower()
        assert "complete for the exact-label fiscal subset" in doc_lower
        assert "no imputation" in doc_lower
        assert "does not claim" in doc_lower
        for family in final["promoted_exact_label_families"]:
            assert f"`{family}`" in doc
        for family in final["held_families"]:
            assert f"`{family}`" in doc
    except (AssertionError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    print(json.dumps({
        "milestone25_audit": "pass",
        "promoted_exact_label_families": final["promoted_exact_label_families"],
        "held_families": final["held_families"],
        "observation_count": final["observation_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
