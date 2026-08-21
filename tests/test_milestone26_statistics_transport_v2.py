from __future__ import annotations

from shapely.geometry import Polygon

from scripts import probe_milestone26_statistics_transport_v2 as m26v2


def test_arcgis_polygon_xy_drops_only_third_ordinate() -> None:
    polygon = Polygon(
        [
            (0.0, 0.0, 7.0),
            (1000.0, 0.0, 8.0),
            (1000.0, 1000.0, 9.0),
            (0.0, 1000.0, 10.0),
            (0.0, 0.0, 7.0),
        ]
    )
    payload = m26v2.arcgis_polygon_xy(polygon)
    assert payload["spatialReference"] == {"wkid": 3395}
    assert len(payload["rings"]) == 1
    assert all(len(coord) == 2 for coord in payload["rings"][0])
    assert payload["rings"][0][0] == payload["rings"][0][-1]


def test_arcgis_polygon_xy_preserves_hole_count() -> None:
    polygon = Polygon(
        [(0, 0, 1), (1000, 0, 1), (1000, 1000, 1), (0, 1000, 1), (0, 0, 1)],
        holes=[[(200, 200, 2), (200, 400, 2), (400, 400, 2), (400, 200, 2), (200, 200, 2)]],
    )
    payload = m26v2.arcgis_polygon_xy(polygon)
    assert len(payload["rings"]) == 2
    assert all(len(coord) == 2 for ring in payload["rings"] for coord in ring)
