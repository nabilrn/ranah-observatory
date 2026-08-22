from __future__ import annotations

import json

from scripts import probe_milestone26_population_transport_capabilities as m26


def test_capability_diagnostic_contract_is_nonpromotional() -> None:
    contract = m26.load_contract()
    assert contract["locked_before_live_capability_probe"] is True
    assert contract["source_id"] == "inarisk_population_2020"
    assert [item["name"] for item in contract["operations"]] == [
        "computeStatisticsHistograms",
        "getSamples",
        "identify",
    ]
    assert contract["substantive_value_promotion_authorized"] is False
    assert contract["equivalence_decision_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_json_surface_detects_arcgis_error_without_values() -> None:
    body = json.dumps({"error": {"code": 500, "message": "failure"}}).encode()
    surface = m26.json_surface(body)
    assert surface["json_parseable"] is True
    assert surface["arcgis_error_present"] is True
    assert surface["arcgis_error_code"] == 500
    assert surface["json_top_level_keys"] == ["error"]


def test_json_surface_accepts_success_shape_without_interpreting_numbers() -> None:
    body = json.dumps({"statistics": [{"count": 1}], "histograms": []}).encode()
    surface = m26.json_surface(body)
    assert surface["json_parseable"] is True
    assert surface["arcgis_error_present"] is False
    assert surface["json_top_level_keys"] == ["histograms", "statistics"]


def test_non_json_error_body_stays_diagnostic_only() -> None:
    surface = m26.json_surface(b"<html>gateway error</html>")
    assert surface["json_parseable"] is False
    assert surface["arcgis_error_present"] is False
