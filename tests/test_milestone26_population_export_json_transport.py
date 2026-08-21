from __future__ import annotations

import urllib.parse

from scripts import probe_milestone26_population_export_json_transport as m26


def test_export_json_contract_is_locked_and_nonpromotional() -> None:
    contract = m26.load_contract()
    assert contract["locked_before_live_probe"] is True
    assert contract["source_id"] == "inarisk_population_2020"
    assert contract["export_request"]["response_format"] == "json"
    assert contract["numeric_aggregation_authorized"] is False
    assert contract["substantive_value_promotion_authorized"] is False
    assert contract["equivalence_decision_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_export_json_request_reuses_native_grid_contract() -> None:
    url, context = m26.build_request()
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    assert parsed.path.endswith("/INARISKPOP_2020/ImageServer/exportImage")
    assert params["f"] == ["json"]
    assert params["format"] == ["tiff"]
    assert params["pixelType"] == ["F32"]
    assert params["interpolation"] == ["RSP_NearestNeighbor"]
    assert params["compression"] == ["LZ77"]
    assert params["bboxSR"] == ["3395"]
    assert params["imageSR"] == ["3395"]
    assert params["size"] == [f"{context['width']},{context['height']}"]
    assert context["width"] > 0 and context["height"] > 0
    assert context["pixel_size_m"] == 100


def test_export_json_success_gate_does_not_authorize_values() -> None:
    contract = m26.load_contract()
    assert "href" in contract["success_gate"]
    assert contract["cross_geography_numeric_extraction_authorized"] is False
    assert contract["aggregation_semantics_changed"] is False
    assert contract["source_family_changed"] is False
