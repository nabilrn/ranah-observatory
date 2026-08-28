#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/validation/historical/public_finance_2000/bps_construction_establishment_count_trajectory_2002_2006.json"
QUALIFICATION = ROOT / "data/validation/historical/public_finance_2000/bps_construction_qualification_pre_post_update_acquisition_boundary.json"


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    qualification = json.loads(QUALIFICATION.read_text(encoding="utf-8"))

    assert manifest["schema"] == "ranah-observatory/bps-construction-establishment-count-trajectory-2002-2006/v1"
    assert manifest["source_geography_name"] == "Sumatera Barat"
    assert manifest["official_source"]["table_number"] == "4"
    assert manifest["official_source"]["table_title_english"] == "NUMBER OF CONSTRUCTION ESTABLISHMENT BY PROVINCE"

    counts = {year: row["count"] for year, row in manifest["sumatera_barat"].items()}
    assert counts == {
        "2002": 2779,
        "2003": 2882,
        "2004": 2837,
        "2005": 2435,
        "2006": 2664,
    }

    baseline = qualification["pre_update_published_baseline"]["province_total"]
    qualification_sum = sum(baseline[key] for key in ("B", "M1", "M2", "K1", "K2", "K3"))
    assert qualification_sum == baseline["total"] == 2882

    binding = manifest["cross_source_binding"]
    assert binding["qualification_category_sum"] == qualification_sum
    assert binding["annual_series_2003_establishment_count"] == counts["2003"]
    assert binding["exact_numeric_match"] is True

    trajectory = manifest["trajectory"]
    assert trajectory["2003_to_2005"]["delta_count"] == counts["2005"] - counts["2003"] == -447
    assert abs(trajectory["2003_to_2005"]["delta_percent"] - (-15.510062)) < 1e-9
    assert trajectory["2004_to_2005"]["delta_count"] == -402

    post = manifest["post_update_period_evidence"]
    assert post["published_2005_establishment_count_confirmed"] is True
    assert post["published_2005_establishment_count"] == 2435
    assert post["table_labels_2005_count_as_sampling_frame_size"] is False
    assert post["old_vs_new_sampling_frame_counts_recovered"] is False
    assert post["qualification_composition_2005_recovered"] is False
    assert post["frame_change_quantification_authorized"] is False

    inference = manifest["inference"]
    assert inference["published_establishment_count_trajectory_2002_2006_confirmed"] is True
    assert inference["qualification_2003_total_and_annual_series_2003_total_match_exactly"] is True
    assert inference["published_post_update_period_2005_total_confirmed"] is True
    assert inference["published_establishment_total_is_equivalent_to_sampling_frame_size"] is False
    assert inference["2003_to_2005_decline_proves_directory_refresh_effect"] is False
    assert inference["2003_to_2005_decline_proves_historical_value_revision_mechanism"] is False
    assert inference["causal_revision_attribution_authorized"] is False

    for key, value in manifest["gate"].items():
        if key == "retain_all_vintages":
            assert value is True
        else:
            assert value is False, key

    return {
        "published_establishment_trajectory_confirmed": True,
        "sumbar_2003_count": counts["2003"],
        "sumbar_2005_count": counts["2005"],
        "qualification_2003_exact_match": True,
        "delta_2003_to_2005": trajectory["2003_to_2005"]["delta_count"],
        "sampling_frame_equivalence_authorized": False,
        "frame_change_quantification_authorized": False,
        "causal_claim_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
