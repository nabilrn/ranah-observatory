from __future__ import annotations

import json
from pathlib import Path

from scripts import probe_milestone26_population_mapserver_scale as probe


def test_contract_locks_production_candidate_before_live_probe() -> None:
    contract = json.loads(Path(probe.CONTRACT).read_text(encoding="utf-8"))
    assert contract["locked_before_live_probe"] is True
    assert contract["production_batch_candidate"] == 64
    assert [row["batch_size"] for row in contract["batch_plan"]] == [16, 64, 128]
    assert [row["repeat_count"] for row in contract["batch_plan"]] == [1, 2, 1]
    assert contract["stage1_population_aggregation_authorized"] is False
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
        assert contract[key] is False


def test_lattice_points_follow_native_100m_grid() -> None:
    points = probe.lattice_points(1000.0, 2000.0, 4, 4)
    assert len(points) == 16
    assert points[0] == [1000.0, 2000.0]
    assert points[1] == [1100.0, 2000.0]
    assert points[4] == [1000.0, 2100.0]
    assert points[-1] == [1300.0, 2300.0]


def test_associate_points_is_order_independent_and_one_to_one() -> None:
    inputs = [[0.0, 0.0], [100.0, 0.0]]
    results = [
        {"geometry": [100.0, 0.0], "value": 2.0},
        {"geometry": [0.0, 0.0], "value": 1.0},
    ]
    mapping = probe.associate_points(inputs, results, 0.001)
    assert mapping == {"0.000000,0.000000": 1.0, "100.000000,0.000000": 2.0}


def test_associate_points_rejects_duplicate_result_geometry() -> None:
    inputs = [[0.0, 0.0], [100.0, 0.0]]
    results = [
        {"geometry": [0.0, 0.0], "value": 1.0},
        {"geometry": [0.0, 0.0], "value": 2.0},
    ]
    assert probe.associate_points(inputs, results, 0.001) is None


def test_mapping_reproducibility_uses_locked_absolute_tolerance() -> None:
    left = {"0,0": 1.0, "1,1": 2.0}
    assert probe.mappings_equal(left, {"0,0": 1.0 + 5e-10, "1,1": 2.0}, 1e-9) is True
    assert probe.mappings_equal(left, {"0,0": 1.0 + 2e-9, "1,1": 2.0}, 1e-9) is False
    assert probe.mappings_equal(left, {"0,0": 1.0}, 1e-9) is False


def test_build_url_records_multipoint_and_return_geometry() -> None:
    url = probe.build_url("https://example.test/MapServer", [[0.0, 0.0], [100.0, 0.0]])
    assert "geometryType=esriGeometryMultipoint" in url
    assert "returnGeometry=true" in url
    assert "layers=all%3A0" in url
