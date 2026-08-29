#!/usr/bin/env python3
"""Validate the Sumbar 2003-2005 construction qualification semantic bridge boundary."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_qualification_semantic_bridge_boundary_2003_2005.json"
PRE_POST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_qualification_pre_post_update_acquisition_boundary.json"
VAR216 = ROOT / "data/validation/historical/public_finance_2000/bps_construction_legacy_var216_retention_boundary.json"


def validate() -> dict[str, object]:
    """Bind the arithmetic candidate to existing official-source checkpoints and fail closed on semantics."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pre_post = json.loads(PRE_POST.read_text(encoding="utf-8"))
    var216 = json.loads(VAR216.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-qualification-semantic-bridge-boundary-2003-2005/v1"
    assert manifest["classification"] == "arithmetic_aggregation_candidate_reproducible_semantic_bridge_not_authorized"

    source_2003 = manifest["official_bps_2003_source"]
    frozen_2003 = pre_post["pre_update_published_baseline"]
    assert source_2003["publication_number"] == frozen_2003["publication_number"] == "05230.0506"
    assert source_2003["isbn"] == frozen_2003["isbn"] == "979-724-383-4"
    assert source_2003["table_number"] == frozen_2003["table_number"] == "4.3"
    assert source_2003["source_native_columns"] == ["B", "M1", "M2", "K1", "K2", "K3", "TOTAL"]

    expected_2003 = {"B": 0, "M1": 16, "M2": 134, "K1": 334, "K2": 1084, "K3": 1314, "TOTAL": 2882}
    assert source_2003["province_total"] == expected_2003
    assert frozen_2003["province_total"] == {
        "B": expected_2003["B"],
        "M1": expected_2003["M1"],
        "M2": expected_2003["M2"],
        "K1": expected_2003["K1"],
        "K2": expected_2003["K2"],
        "K3": expected_2003["K3"],
        "total": expected_2003["TOTAL"],
    }

    candidate = manifest["arithmetic_three_group_candidate_2003"]
    small = expected_2003["K1"] + expected_2003["K2"] + expected_2003["K3"]
    medium = expected_2003["M1"] + expected_2003["M2"]
    large = expected_2003["B"]
    assert candidate["definition_status"] == "arithmetic_candidate_not_semantic_bridge"
    assert candidate["candidate_values"] == {
        "Kecil": small,
        "Menengah": medium,
        "Besar": large,
        "Jumlah": expected_2003["TOTAL"],
    }
    assert candidate["reconciliation"] == {
        "component_sum": small + medium + large,
        "published_total": expected_2003["TOTAL"],
        "difference": 0,
        "exact": True,
    }
    assert abs(candidate["candidate_shares_percent"]["Kecil"] - (small / expected_2003["TOTAL"] * 100)) < 1e-12
    assert abs(candidate["candidate_shares_percent"]["Menengah"] - (medium / expected_2003["TOTAL"] * 100)) < 1e-12
    assert candidate["candidate_shares_percent"]["Besar"] == 0.0

    surface_2005 = manifest["official_bps_2005_digital_surface"]
    frozen_var = var216["legacy_variable"]
    frozen_total = var216["legacy_2005_total"]
    assert surface_2005["variable_id"] == frozen_var["var_id"] == 216
    assert surface_2005["title"] == frozen_var["title"] == "Banyaknya Perusahaan Konstruksi"
    assert surface_2005["source"] == frozen_var["source"] == "Direktori Perusahaan Konstruksi"
    assert surface_2005["period"] == frozen_var["target_period"] == {"th": "2005", "th_id": 105}
    assert [(x["label"], x["turvar_id"]) for x in surface_2005["derived_variables"]] == [
        ("Kecil", 454), ("Menengah", 455), ("Besar", 456), ("Jumlah", 457)
    ]
    assert surface_2005["sumatera_barat_total_2005"] == frozen_total["sumatera_barat"]["value"] == 2435
    assert surface_2005["small_medium_large_values_retrievable_under_tested_contract"] is False
    assert surface_2005["detailed_b_m1_m2_k1_k2_k3_values_exposed_for_2005"] is False
    assert surface_2005["semantic_definition_linking_2005_aggregate_labels_to_2003_six_classes_recovered"] is False

    audit = manifest["semantic_audit"]
    assert audit["2003_six_class_labels_source_native"] is True
    assert audit["2005_three_group_labels_source_native"] is True
    assert audit["2003_to_2005_exact_category_mapping_source_native"] is False
    assert audit["period_specific_2005_definition_recovered"] is False
    assert audit["category_drift_risk"] is True

    gates = manifest["research_gates"]
    true_gates = {
        "2003_detailed_qualification_composition_confirmed",
        "2003_arithmetic_three_group_candidate_reproducible",
        "2005_sumbar_total_confirmed",
    }
    for key, value in gates.items():
        if key in true_gates:
            assert value is True, key
        else:
            assert value is False, key

    return {
        "detailed_2003_composition_confirmed": True,
        "arithmetic_small_2003": small,
        "arithmetic_medium_2003": medium,
        "arithmetic_large_2003": large,
        "arithmetic_total_2003": expected_2003["TOTAL"],
        "sumbar_total_2005": 2435,
        "period_specific_semantic_mapping_verified": False,
        "pre_post_composition_comparison_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
