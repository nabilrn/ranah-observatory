from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "validation" / "historical" / "public_finance_2000"
MANIFEST = BASE / "bps_construction_revision_period_method_support_2004_2009.json"
MECHANISM = BASE / "bps_construction_revision_mechanism_candidate.json"
PERSISTENCE = BASE / "bps_construction_revision_persistence_release_lifecycle_2002_2006.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mechanism = json.loads(MECHANISM.read_text(encoding="utf-8"))
    persistence = json.loads(PERSISTENCE.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-revision-period-method-support-2004-2009/v1"
    assert manifest["depends_on"]["mechanism_candidate"] == MECHANISM.name
    assert manifest["depends_on"]["revision_persistence"] == PERSISTENCE.name

    source = manifest["source"]
    assert source["publication_number"] == "02130.0903"
    assert source["catalog_number"] == "1202027"
    assert source["issn"] == "1907-8862"
    assert source["publisher"] == "Badan Pusat Statistik, Jakarta - Indonesia"
    assert source["preface_date"] == "Jakarta, Agustus 2009"
    assert source["screenshot_attempted"] is True
    assert source["screenshot_status"] == "remote PDF screenshot timed out"
    assert source["raw_pdf_sha256_available_in_repository"] is False

    method = manifest["annual_construction_survey_method"]
    assert method["section"] == "3.7. Survei Konstruksi Tahunan"
    assert method["report_page"] == 144
    assert method["sampling_is_used"] is True
    assert method["reported_current_sample_size"] == 12_199
    assert method["reported_active_universe_approx"] == 80_000
    assert method["sample_selection_method"] == "combination of cut-off point and stratified PPS sampling"
    assert method["collection_method"] == "interview"
    assert "qualification" in method["population_estimation_rule"].lower()
    assert "expansion factor" in method["population_estimation_rule"].lower()
    assert method["qualification_categories_documented"] == ["B", "M1", "M2", "K1", "K2", "K3"]

    counts = manifest["historical_respondent_counts"]
    assert counts["annual_construction"] == {
        "2004": 8_168,
        "2005": 8_168,
        "2006": 7_441,
        "2007": 7_441,
        "2008": 24_398,
        "2009": 23_268,
    }
    assert counts["quarterly_construction"] == {
        "2004": 5_080,
        "2005": 5_080,
        "2006": 5_076,
        "2007": 5_076,
        "2008": 20_928,
        "2009": 19_560,
    }

    period = manifest["period_link"]
    assert period["historical_year_2005_annual_survey_respondent_count_documented"] is True
    assert period["annual_sampling_design_documented_in_report_covering_2004_2009"] is True
    assert period["qualification_based_expansion_documented_in_report_covering_2004_2009"] is True
    assert period["same_approximate_80000_universe_as_2005_directory_metadata"] is True
    assert period["same_approximate_universe_is_not_frame_identity_proof"] is True
    assert period["report_proves_2005_refreshed_directory_replaced_prior_annual_survey_frame"] is False
    assert period["report_proves_2001_2003_values_were_reestimated_with_2005_frame"] is False
    assert period["report_proves_revision_cause"] is False

    effect = manifest["mechanism_candidate_effect"]
    candidate = mechanism["candidate_mechanism"]
    assert effect["candidate_id"] == candidate["id"]
    assert effect["prior_status"] == candidate["status"]
    assert effect["status_after_this_checkpoint"] == (
        "operationally_plausible_period_method_support_strengthened_causal_revision_link_unproven"
    )
    assert effect["status_change_scope"] == "evidence-strength refinement only; no causal authorization"
    assert len(effect["new_support"]) == 4
    assert len(effect["remaining_causal_gaps"]) == 5

    assert persistence["inference"]["revised_2002_2003_values_persist_in_later_dedicated_bps_series"] is True
    assert persistence["inference"]["persistence_proves_revision_mechanism"] is False

    classification = manifest["classification"]
    assert classification["period_specific_sampling_support"] == "confirmed_retrospectively_for_2004_2009"
    assert classification["period_specific_qualification_expansion_support"] == "confirmed_retrospectively_for_2004_2009"
    assert classification["historical_2005_respondent_count"] == "confirmed"
    assert classification["frame_identity_with_2005_directory_update"] == "unproven"
    assert classification["historical_revision_reestimation_link"] == "unproven"
    assert classification["causal_mechanism"] == "unproven"

    gate = manifest["gate"]
    assert gate["retain_all_vintages"] is True
    for key in (
        "silent_overwrite_authorized",
        "single_continuous_1998_2006_trajectory_authorized",
        "cross_vintage_bridge_authorized",
        "backcast_authorized",
        "attribute_revision_to_2005_directory_update_authorized",
        "causal_claim_authorized",
        "panel_v3_integration_authorized",
    ):
        assert gate[key] is False, key

    return {
        "annual_2005_respondents": counts["annual_construction"]["2005"],
        "period_specific_sampling_support": True,
        "period_specific_qualification_expansion_support": True,
        "frame_identity_proven": False,
        "revision_reestimation_link_proven": False,
        "causal_revision_link_proven": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
