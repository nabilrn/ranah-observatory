from __future__ import annotations

from shapely.geometry import Polygon

from scripts import probe_milestone26_statistics_transport as v1
from scripts import probe_milestone26_statistics_transport_v3 as m26v3


def test_getsamples_amendment_is_locked_and_noninferential() -> None:
    amendment = m26v3.load_amendment()
    assert amendment["locked_before_getsamples_reference_probe"] is True
    assert amendment["reference_operation"]["name"] == "getSamples"
    assert amendment["reference_operation"]["batch_size_points"] == 50
    assert amendment["reference_operation"]["random_sampling_authorized"] is False
    assert amendment["equivalence_tolerances_changed"] is False
    assert amendment["aggregation_semantics_changed"] is False
    assert amendment["risk_synthesis_authorized"] is False


def test_grid_centers_use_exact_pixel_center_membership() -> None:
    polygon = Polygon([(0, 0), (200, 0), (200, 200), (0, 200), (0, 0)])
    points = m26v3.grid_centers_inside_polygon(polygon, (0.0, 0.0, 200.0, 200.0), 2, 2)
    assert sorted(points) == sorted([[50.0, 150.0], [150.0, 150.0], [50.0, 50.0], [150.0, 50.0]])


def test_one_band_sample_parser_preserves_missingness() -> None:
    assert m26v3.parse_one_band_sample("") is None
    assert m26v3.parse_one_band_sample("NoData") is None
    assert m26v3.parse_one_band_sample("12.5") == 12.5


def test_capacity_bridge_reuses_locked_tolerances() -> None:
    contract = v1.load_contract()
    tiff = {
        "inside_count": 100,
        "valid_count": 99,
        "valid_fraction": 0.99,
        "sum": 49.5,
        "mean": 0.5,
    }
    samples = dict(tiff)
    result = m26v3.compare_capacity_bridge(tiff, samples, contract)
    assert result["all_bridge_gates_passed"] is True

    samples_bad = dict(samples)
    samples_bad["valid_count"] = 98
    result_bad = m26v3.compare_capacity_bridge(tiff, samples_bad, contract)
    assert result_bad["valid_count_match"] is False
    assert result_bad["all_bridge_gates_passed"] is False
