#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_current_csa_table_652_boundary.json"
PARENT = ROOT / "data/validation/historical/public_finance_2000/bps_construction_qualification_pre_post_update_acquisition_boundary.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-current-csa-table-652-boundary/v1"
    page = manifest["public_page_identity"]
    assert page["encoded_id"] == "NjUyIzI="
    assert page["decoded_identity"] == "652#2"
    assert page["encoded_identity_verified_by_base64_decode"] is True

    api = manifest["api_contract"]
    assert api["model"] == "tablestatistic"
    assert api["domain"] == "1300"
    assert api["id"] == page["encoded_id"]
    assert api["legacy_statictable_id_652_is_same_object"] is False
    assert api["legacy_statictable_652_data_availability"] == "not-available"

    response = manifest["official_csa_response"]
    assert response["status"] == "OK"
    assert response["data_availability"] == "available"
    assert response["available_years"] == ["2016"]
    assert response["year_dimension"] == [{"label": "2016", "val": 116}]
    assert response["source_native_2005_available"] is False
    assert response["variable"]["val"] == 652
    assert response["variable"]["unit"] == "Usaha"
    assert response["variable"]["subj"] == "Sensus Ekonomi"
    assert response["geography_rows"]["kabupaten_kota_count"] == 19
    assert response["geography_rows"]["province_total_row_present"] is True
    assert response["geography_rows"]["total_vervar_rows"] == 20

    expected_categories = [
        "Perseorangan", "K1", "K2", "K3", "M1", "M2", "B1", "B2", "Lainnya", "Jumlah"
    ]
    assert response["qualification_categories"] == expected_categories

    totals = response["province_total_2016"]
    components = [
        totals["Perseorangan"], totals["K1"], totals["K2"], totals["K3"],
        totals["M1"], totals["M2"], totals["B1"], totals["B2"], totals["Lainnya"]
    ]
    assert sum(components) == totals["Jumlah"] == 5866
    assert totals["component_sum_matches_jumlah"] is True

    historical = manifest["historical_comparability"]
    assert historical["pre_update_2003_categories"] == ["B", "M1", "M2", "K1", "K2", "K3"]
    assert historical["classification_regime_identical_to_2003"] is False
    assert historical["direct_full_composition_comparison_2003_to_2016_authorized"] is False
    assert historical["category_name_overlap_proves_definition_equivalence"] is False

    bounded = manifest["bounded_finding"]
    assert bounded["current_bps_table_identity_verified"] is True
    assert bounded["current_bps_table_machine_readable_transport_verified"] is True
    assert bounded["post_update_2005_values_recovered"] is False
    assert bounded["current_table_can_substitute_for_2005_book_ii"] is False
    assert bounded["current_table_closes_2005_acquisition_gap"] is False
    assert bounded["classification"] == "current_csa_table_verified_2016_only_not_post_update_2005_source"

    comparison = manifest["comparison_gate"]
    assert comparison["pre_update_baseline_available"] == parent["comparison_gate"]["pre_update_baseline_available"] is True
    assert comparison["post_update_2005_comparable_table_available"] is False
    assert comparison["post_update_2005_sumbar_qualification_values_acquired"] is False
    assert comparison["pre_post_qualification_comparison_authorized"] is False
    assert comparison["frame_change_quantification_authorized"] is False
    assert comparison["old_vs_new_sumbar_frame_counts_recovered"] is False
    assert comparison["causal_revision_attribution_authorized"] is False

    for key, value in manifest["gate"].items():
        if key == "retain_all_vintages":
            assert value is True
        else:
            assert value is False, key

    return {
        "csa_table_verified": True,
        "available_years": response["available_years"],
        "source_native_2005_available": False,
        "province_total_2016": totals["Jumlah"],
        "historical_comparison_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
