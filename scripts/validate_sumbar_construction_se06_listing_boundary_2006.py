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

    assert manifest["schema"] == "ranah-observatory/bps-construction-se06-listing-boundary-2006/v1"
    assert manifest["se06_source"]["publication_number"] == "05000.0733"
    assert manifest["se06_source"]["catalog_number"] == "9102005.13"

    permanent = manifest["se06_sumatera_barat_construction"]["permanent_location"]
    assert permanent == {
        "large": 20,
        "medium": 110,
        "small": 828,
        "micro": 3540,
        "not_classified": 6,
        "total": 4504,
    }
    assert sum(permanent[key] for key in ("large", "medium", "small", "micro", "not_classified")) == 4504

    non_permanent = manifest["se06_sumatera_barat_construction"]["non_permanent_location"]
    assert all(value == 0 for value in non_permanent.values())
    assert manifest["se06_sumatera_barat_construction"]["all_locations_total"] == 4504

    cross = manifest["cross_check"]
    assert cross["table_14_construction_total"] == 4504
    assert cross["table_1c_sumatera_barat_construction_total"] == 4504
    assert cross["independent_table_totals_match"] is True

    annual_2006 = annual["sumatera_barat"]["2006"]["count"]
    assert annual_2006 == 2664
    comparison = manifest["same_year_2006_comparison"]
    assert comparison["se06_listing_count"] == 4504
    assert comparison["annual_survey_published_count"] == annual_2006
    assert comparison["difference_annual_minus_se06"] == -1840
    assert abs(comparison["annual_count_as_percent_of_se06_listing"] - 59.147425) < 1e-9
    assert abs(comparison["difference_percent_of_se06_listing"] - (-40.852575)) < 1e-9
    assert comparison["numeric_identity"] is False

    interpretation = manifest["interpretation"]
    assert interpretation["se06_construction_listing_total_confirmed"] is True
    assert interpretation["annual_2006_and_se06_2006_counts_are_materially_different"] is True
    assert interpretation["annual_table_4_count_equals_full_se06_construction_listing_universe"] is False
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
        "se06_construction_listing": 4504,
        "annual_2006_count": annual_2006,
        "same_year_difference": -1840,
        "annual_count_equals_full_se06_listing": False,
        "annual_count_as_sampling_frame_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
