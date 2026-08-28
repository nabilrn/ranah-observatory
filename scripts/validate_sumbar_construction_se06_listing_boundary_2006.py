#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_se06_listing_boundary_2006.json"
ANNUAL = ROOT / "data/validation/historical/public_finance_2000/bps_construction_establishment_count_trajectory_2002_2006.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    annual = json.loads(ANNUAL.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-se06-listing-boundary-2006/v2"
    assert manifest["se06_source"]["publication_number"] == "05000.0733"
    assert manifest["se06_source"]["catalog_number"] == "9102005.13"

    role = manifest["se06_role_and_scope"]
    assert role["identifies_population"] is True
    assert role["updates_directory"] is True
    assert role["builds_or_updates_master_sampling_frame"] is True
    assert role["construction_category_in_scope"] is True
    assert role["construction_category_code"] == "F"
    assert role["covers_permanent_and_non_permanent_businesses"] is True
    assert role["covers_legal_and_nonlegal_businesses"] is True

    profile = manifest["se06_sumatera_barat_construction"]["table_12_scale_profile"]
    permanent = profile["permanent_location"]
    assert permanent == {
        "large": 20,
        "medium": 110,
        "small": 828,
        "micro": 3540,
        "not_classified": 6,
        "total": 4504,
    }
    assert sum(permanent[key] for key in ("large", "medium", "small", "micro", "not_classified")) == 4504
    assert all(value == 0 for value in profile["non_permanent_location"].values())
    assert profile["all_locations_total"] == 4504

    legal = manifest["se06_sumatera_barat_construction"]["legal_status_profile"]
    legal_count = legal["table_3"]["construction_total"]
    nonlegal_count = legal["table_4"]["construction_total"]
    assert legal_count == 1379
    assert nonlegal_count == 3125
    assert legal_count + nonlegal_count == legal["legal_plus_nonlegal_total"] == 4504
    assert abs(legal["legal_share_percent"] - 30.617229) < 1e-9
    assert abs(legal["nonlegal_share_percent"] - 69.382771) < 1e-9
    assert legal["components_sum_to_full_construction_listing"] is True

    cross = manifest["cross_check"]
    assert cross["table_14_construction_total"] == 4504
    assert cross["table_1c_sumatera_barat_construction_total"] == 4504
    assert cross["table_3_plus_table_4_total"] == 4504
    assert cross["independent_table_totals_match"] is True

    annual_2006 = annual["sumatera_barat"]["2006"]["count"]
    assert annual_2006 == 2664
    comparison = manifest["same_year_2006_comparison"]
    assert comparison["se06_full_construction_listing"] == 4504
    assert comparison["se06_legal_status_construction"] == legal_count
    assert comparison["se06_nonlegal_status_construction"] == nonlegal_count
    assert comparison["annual_survey_published_count"] == annual_2006
    assert comparison["annual_minus_full_listing"] == -1840
    assert comparison["annual_minus_legal_only"] == 1285
    assert abs(comparison["annual_count_as_percent_of_full_listing"] - 59.147425) < 1e-9
    assert comparison["annual_equals_full_listing"] is False
    assert comparison["annual_equals_legal_only_subset"] is False
    assert comparison["annual_equals_nonlegal_only_subset"] is False
    assert annual_2006 not in (4504, legal_count, nonlegal_count)

    negative = manifest["negative_identification"]
    assert negative["full_se06_population_mapping_rejected"] is True
    assert negative["se06_legal_only_mapping_rejected"] is True
    assert negative["se06_nonlegal_only_mapping_rejected"] is True
    assert negative["simple_legal_status_filter_explains_annual_count"] is False
    assert negative["exact_annual_survey_frame_mapping_recovered"] is False

    interpretation = manifest["interpretation"]
    assert interpretation["se06_population_role_confirmed"] is True
    assert interpretation["se06_master_sampling_frame_role_confirmed"] is True
    assert interpretation["se06_construction_legal_status_profile_confirmed"] is True
    assert interpretation["annual_table_4_count_equals_full_se06_construction_listing_universe"] is False
    assert interpretation["annual_table_4_count_equals_se06_legal_only_population"] is False
    assert interpretation["difference_proves_annual_survey_excludes_micro_establishments"] is False
    assert interpretation["difference_proves_specific_formality_or_legal_status_filter"] is False
    assert interpretation["difference_identifies_exact_annual_sampling_frame"] is False
    assert interpretation["se06_listing_is_proven_to_be_the_annual_survey_sampling_frame"] is False
    assert interpretation["annual_table_4_count_is_proven_to_be_sampling_frame_size"] is False
    assert interpretation["2005_annual_count_is_proven_to_be_sampling_frame_size"] is False
    assert interpretation["causal_revision_attribution_authorized"] is False

    for key, value in manifest["gate"].items():
        if key == "retain_all_vintages":
            assert value is True
        else:
            assert value is False, key

    return {
        "se06_full_construction_population": 4504,
        "se06_legal_status_construction": legal_count,
        "se06_nonlegal_status_construction": nonlegal_count,
        "annual_2006_count": annual_2006,
        "annual_matches_full_population": False,
        "annual_matches_legal_only": False,
        "annual_matches_nonlegal_only": False,
        "exact_annual_frame_mapping_recovered": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
