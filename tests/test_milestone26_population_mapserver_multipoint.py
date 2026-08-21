from __future__ import annotations

import json
from pathlib import Path

from scripts import probe_milestone26_population_mapserver_multipoint as probe


def test_contract_and_semantic_amendment_keep_claims_closed() -> None:
    contract = json.loads(Path(probe.CONTRACT).read_text(encoding="utf-8"))
    semantics = json.loads(Path(probe.SEMANTICS).read_text(encoding="utf-8"))
    assert contract["locked_before_live_probe"] is True
    assert semantics["locked_before_multipoint_probe"] is True
    assert semantics["semantic_binding"]["accepted_field_name"] == "Stretch.Pixel Value"
    assert semantics["semantic_binding"]["renderer_color_code_interpretation_rejected"] is True
    assert semantics["semantic_binding"]["byte_exact_equivalence_to_image_server_source_proven"] is False
    for payload in (contract, semantics):
        for key in (
            "numeric_aggregation_authorized",
            "substantive_value_promotion_authorized",
            "cross_geography_numeric_extraction_authorized",
            "aggregation_semantics_changed",
            "source_family_changed",
            "minimum_valid_fraction_changed",
            "risk_synthesis_authorized",
            "statistical_model_fit_authorized",
            "causal_claim_authorized",
            "monetary_wasted_potential_estimate_authorized",
        ):
            assert payload[key] is False


def test_extract_pixel_result_accepts_bound_field_only() -> None:
    result = {
        "layerId": 0,
        "attributes": {"Stretch.Pixel Value": "45.974602"},
        "geometry": {"x": 1.0, "y": 2.0},
    }
    parsed = probe.extract_pixel_result(result, "Stretch.Pixel Value")
    assert parsed == {"value": 45.974602, "geometry": [1.0, 2.0], "field": "Stretch.Pixel Value"}
    assert probe.extract_pixel_result(result, "Pixel Value") is None


def test_geometry_match_requires_one_to_one_points() -> None:
    inputs = [[0.0, 0.0], [100.0, 0.0]]
    matching = [
        {"geometry": [100.0, 0.0]},
        {"geometry": [0.0, 0.0]},
    ]
    duplicate = [
        {"geometry": [0.0, 0.0]},
        {"geometry": [0.0, 0.0]},
    ]
    assert probe.one_to_one_geometry_match(inputs, matching, 0.001) is True
    assert probe.one_to_one_geometry_match(inputs, duplicate, 0.001) is False


def test_geometry_match_fails_when_result_geometry_missing() -> None:
    assert probe.one_to_one_geometry_match([[0.0, 0.0]], [{"geometry": None}], 0.001) is False


def test_nonfinite_pixel_values_are_rejected() -> None:
    result = {
        "layerId": 0,
        "attributes": {"Stretch.Pixel Value": "nan"},
        "geometry": {"x": 1.0, "y": 2.0},
    }
    assert probe.extract_pixel_result(result, "Stretch.Pixel Value") is None
