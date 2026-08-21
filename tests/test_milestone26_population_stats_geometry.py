from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, box

from scripts import build_milestone26_population_stats_geometry as stats_geom


def test_contract_forbids_live_stats_and_value_access() -> None:
    contract = json.loads(Path(stats_geom.CONTRACT).read_text(encoding="utf-8"))
    assert contract["locked_before_geometry_simplification"] is True
    assert contract["maximum_encoded_statistics_url_length"] == 6000
    assert contract["source_values_accessed"] is False
    assert contract["statistics_live_request_authorized_in_this_contract"] is False
    assert contract["stage1_population_aggregation_authorized"] is False
    assert contract["numeric_source_value_extraction_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_rounding_coordinates_is_deterministic() -> None:
    payload = [[[1.23456, 2.34567], [3.45678, 4.56789]]]
    assert stats_geom.round_coordinates(payload, 3) == [[[1.235, 2.346], [3.457, 4.568]]]


def test_arcgis_polygon_has_clockwise_outer_ring() -> None:
    geom = box(0.0, 0.0, 100.0, 100.0)
    payload = stats_geom.arcgis_polygon(geom)
    ring = payload["rings"][0]
    signed_twice_area = sum(
        ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
        for i in range(len(ring) - 1)
    )
    assert signed_twice_area < 0
    assert payload["spatialReference"]["wkid"] == 3395


def test_pixel_mask_detects_membership_change() -> None:
    original = box(0.0, 0.0, 200.0, 200.0)
    changed = box(0.0, 0.0, 99.0, 200.0)
    bbox = (0.0, 0.0, 200.0, 200.0)
    mask_a = stats_geom.mask_for_geometry(original, bbox, 2, 2)
    mask_b = stats_geom.mask_for_geometry(changed, bbox, 2, 2)
    assert np.array_equal(mask_a, mask_b) is False
    assert int(np.count_nonzero(mask_a)) == 4
    assert int(np.count_nonzero(mask_b)) == 2


def test_topology_preserving_candidate_can_preserve_simple_mask() -> None:
    geom = Polygon([(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (100.0, 100.0), (0.0, 100.0), (0.0, 0.0)])
    candidate = stats_geom.candidate_geometry(geom, 1.0, 3)
    bbox = (0.0, 0.0, 100.0, 100.0)
    original_mask = stats_geom.mask_for_geometry(geom, bbox, 1, 1)
    candidate_mask = stats_geom.mask_for_geometry(candidate, bbox, 1, 1)
    assert np.array_equal(original_mask, candidate_mask) is True
    assert stats_geom.vertex_count(candidate) <= stats_geom.vertex_count(geom)


def test_stats_url_uses_locked_native_pixel_size() -> None:
    geometry = {"rings": [[[0.0, 0.0], [0.0, 100.0], [100.0, 100.0], [100.0, 0.0], [0.0, 0.0]]], "spatialReference": {"wkid": 3395}}
    url = stats_geom.stats_url("https://example.test/ImageServer", geometry)
    assert "computeStatisticsHistograms" in url
    assert "geometryType=esriGeometryPolygon" in url
    assert "pixelSize=100%2C100" in url
    assert "f=json" in url
