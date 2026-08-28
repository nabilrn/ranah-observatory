#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_post_update_opac_detail_transport_boundary.json"
PARENT = ROOT / "data/validation/historical/public_finance_2000/bps_construction_qualification_pre_post_update_acquisition_boundary.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-post-update-opac-detail-transport-boundary/v1"
    assert manifest["target"]["record_id"] == parent["post_update_target"]["opac_record_id"]
    assert manifest["target"]["detail_url"] == parent["post_update_target"]["opac_detail_url"]
    assert manifest["target"]["read_url"] == parent["post_update_target"]["opac_read_url"]

    detail = manifest["detail_probe"]
    assert detail["http_status"] == 200
    assert detail["final_url"] == "https://sso-pst.bps.go.id/login"
    assert detail["content_type"].startswith("text/html")
    assert detail["exact_title_present"] is False
    assert detail["record_id_present"] is False
    assert detail["relevant_public_official_links"] == 0
    assert detail["classification"] == "verified_opac_detail_locator_sso_gated_before_record_metadata"

    combined = manifest["combined_transport_finding"]
    assert combined["detail_locator_public_metadata_reachable_without_sso"] is False
    assert combined["read_locator_public_pdf_reachable_without_sso"] is False
    assert combined["detail_page_exposes_additional_public_download_locator"] is False
    assert combined["detail_page_exposes_public_api_locator"] is False
    assert combined["both_verified_record_routes_sso_gated"] is True
    assert combined["sso_gate_is_transport_access_blocker_not_absence_evidence"] is True
    assert combined["authentication_bypass_attempted"] is False
    assert combined["hidden_route_guessing_performed"] is False

    comparison = manifest["comparison_gate"]
    assert comparison["post_update_raw_pdf_acquired"] is False
    assert comparison["post_update_sumbar_qualification_values_acquired"] is False
    assert comparison["post_update_table_semantics_confirmed"] is False
    assert comparison["pre_post_qualification_comparison_authorized"] is False
    assert comparison["frame_change_quantification_authorized"] is False
    assert comparison["causal_revision_attribution_authorized"] is False

    for key, value in manifest["gate"].items():
        if key == "retain_all_vintages":
            assert value is True
        else:
            assert value is False, key

    return {
        "detail_route_sso_gated": True,
        "read_route_sso_gated": True,
        "alternate_public_transport_recovered": False,
        "post_update_comparison_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
