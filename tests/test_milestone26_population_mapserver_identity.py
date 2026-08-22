from __future__ import annotations

import json
from pathlib import Path

from scripts import probe_milestone26_population_mapserver_identity as probe


def test_contract_keeps_scientific_boundaries_closed() -> None:
    contract = json.loads(Path(probe.CONTRACT).read_text(encoding="utf-8"))
    assert contract["locked_before_live_probe"] is True
    assert contract["required_layer_name"] == "INARISKPOP_2020_TOPDOWN_KECAMATAN"
    assert contract["required_layer_type"] == "Raster Layer"
    assert contract["required_crs_epsg"] == 3395
    for key in (
        "numeric_aggregation_authorized",
        "substantive_value_promotion_authorized",
        "cross_geography_numeric_extraction_authorized",
        "pilot_selection_changed",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        assert contract[key] is False


def test_extent_match_is_strict_to_locked_tolerance() -> None:
    left = (1.0, 2.0, 3.0, 4.0)
    assert probe.extent_matches(left, (1.0005, 2.0, 3.0, 4.0), 0.001) is True
    assert probe.extent_matches(left, (1.0011, 2.0, 3.0, 4.0), 0.001) is False


def test_raw_pixel_candidate_accepts_only_explicit_pixel_value() -> None:
    payload = {
        "results": [
            {
                "layerId": 0,
                "displayFieldName": "Pixel Value",
                "value": "12.5",
                "attributes": {"Pixel Value": "12.5"},
            }
        ]
    }
    result = probe.raw_pixel_candidate(payload)
    assert result is not None
    assert result["value"] == 12.5


def test_raw_pixel_candidate_rejects_renderer_stretched_value() -> None:
    payload = {
        "results": [
            {
                "layerId": 0,
                "displayFieldName": "Stretched Value",
                "value": "127",
                "attributes": {"Stretched Value": "127"},
            }
        ]
    }
    assert probe.raw_pixel_candidate(payload) is None


def test_raw_pixel_candidate_ignores_other_layers() -> None:
    payload = {
        "results": [
            {
                "layerId": 1,
                "displayFieldName": "Pixel Value",
                "value": "99",
                "attributes": {"Pixel Value": "99"},
            }
        ]
    }
    assert probe.raw_pixel_candidate(payload) is None
