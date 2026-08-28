#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_csa_historical_candidate_audit.json"
PARENT = ROOT / "data/validation/historical/public_finance_2000/bps_construction_current_csa_table_652_boundary.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-csa-historical-candidate-audit/v1"

    catalog = manifest["official_catalog_contract"]
    assert catalog["model"] == "tablestatistic"
    assert catalog["domain"] == "1300"
    assert catalog["subject_id"] == 559
    assert catalog["catalog_rows_seen"] == 19
    assert catalog["catalog_query_error_count"] == 0
    assert catalog["catalog_inventory_complete_within_reported_pagination"] is True

    relevance = manifest["relevance_contract"]
    assert relevance["field"] == "title"
    assert relevance["requires"] == "konstruksi"
    assert relevance["subject_text_cannot_satisfy_title_filter"] is True

    candidates = manifest["relevant_candidates"]
    assert len(candidates) == 2
    by_id = {row["encoded_id"]: row for row in candidates}
    assert set(by_id) == {
        "NjUyIzI=",
        "U1ZSa2VIZzBVbVpVTDBoNk4wSkxSbXRTYnpOcGR6MDkjMyMxMzAw",
    }

    qualification = by_id["NjUyIzI="]
    assert qualification["catalog_oldest_period"] == 2016
    assert qualification["catalog_latest_period"] == 2016
    assert qualification["detail_status"] == "OK"
    assert qualification["detail_data_availability"] == "available"
    assert qualification["detail_exact_years"] == ["2016"]
    assert qualification["contains_2005_period"] is False
    assert qualification["source_subject_text"] == "Sensus Ekonomi"
    assert parent["public_page_identity"]["encoded_id"] == qualification["encoded_id"]
    assert parent["official_csa_response"]["available_years"] == qualification["detail_exact_years"]

    individual = by_id["U1ZSa2VIZzBVbVpVTDBoNk4wSkxSbXRTYnpOcGR6MDkjMyMxMzAw"]
    assert individual["catalog_oldest_period"] == 2020
    assert individual["catalog_latest_period"] == 2022
    assert individual["detail_status"] == "OK"
    assert individual["detail_data_availability"] == "available"
    assert individual["detail_exact_years"] == []
    assert individual["contains_2005_period"] is False

    result = manifest["audit_result"]
    assert result["relevant_title_candidate_count"] == 2
    assert result["resolved_candidate_count"] == 2
    assert result["candidate_detail_error_count"] == 0
    assert result["resolved_exact_2005_candidate_count"] == 0
    assert result["any_candidate_catalog_bounds_include_2005"] is False
    assert result["current_csa_catalog_closes_2005_gap"] is False
    assert result["classification"] == "current_sumbar_csa_construction_catalog_exhausted_no_2005_candidate"

    bounded = manifest["bounded_inference"]
    assert bounded["proves_bps_never_published_2005_data"] is False
    assert bounded["proves_book_ii_05230_0610_absent"] is False
    assert bounded["proves_no_2005_source_exists_in_deep_search_or_archival_publications"] is False
    assert bounded["supports_stopping_repeated_csa_subject_559_search"] is True

    comparison = manifest["comparison_gate"]
    assert comparison["pre_update_baseline_available"] is True
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
        "catalog_rows_seen": catalog["catalog_rows_seen"],
        "relevant_candidates": result["relevant_title_candidate_count"],
        "resolved_candidates": result["resolved_candidate_count"],
        "exact_2005_candidates": result["resolved_exact_2005_candidate_count"],
        "csa_search_loop_closed": True,
        "historical_comparison_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
