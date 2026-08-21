from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/probe_milestone26_statistics_transport.py"

spec = importlib.util.spec_from_file_location("m26_stats_transport", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_statistics_transport_contract_is_locked_before_probe() -> None:
    contract = m26.load_contract()
    assert contract["locked_before_statistics_transport_probe"] is True
    assert contract["source_ids"] == ["inarisk_capacity_2021", "inarisk_population_2020"]
    assert contract["candidate_operation"]["name"] == "computeStatisticsHistograms"
    assert contract["candidate_operation"]["pixel_size"] == "100,100"
    assert contract["pilot_selection"]["selection_uses_raster_values"] is False
    assert contract["aggregation_semantics_changed"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_arcgis_polygon_conversion_preserves_polygon_and_hole_rings() -> None:
    from shapely.geometry import Polygon

    polygon = Polygon(
        [(0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)],
        holes=[[(200, 200), (200, 400), (400, 400), (400, 200), (200, 200)]],
    )
    payload = m26.arcgis_polygon(polygon)
    assert payload["spatialReference"] == {"wkid": 3395}
    assert len(payload["rings"]) == 2
    assert payload["rings"][0][0] == payload["rings"][0][-1]
    assert payload["rings"][1][0] == payload["rings"][1][-1]


def test_equivalence_requires_exact_count_and_tight_numeric_match() -> None:
    contract = m26.load_contract()
    local = {
        "inside_count": 100,
        "valid_count": 99,
        "valid_fraction": 0.99,
        "sum": 49.5,
        "mean": 0.5,
        "min": 0.1,
        "max": 0.8,
        "declared_min": 0.0,
        "declared_max": 1.0,
    }
    remote = {
        "count": 99,
        "sum": 49.5,
        "mean": 0.5,
        "min": 0.1,
        "max": 0.8,
        "skipX": 1,
        "skipY": 1,
    }
    result = m26.compare_equivalence(local, remote, contract)
    assert result["all_equivalence_gates_passed"] is True

    remote_bad = dict(remote)
    remote_bad["count"] = 98
    result_bad = m26.compare_equivalence(local, remote_bad, contract)
    assert result_bad["count_match"] is False
    assert result_bad["all_equivalence_gates_passed"] is False


def test_equivalence_rejects_server_subsampling_or_range_drift() -> None:
    contract = m26.load_contract()
    local = {
        "inside_count": 100,
        "valid_count": 100,
        "valid_fraction": 1.0,
        "sum": 1000.0,
        "mean": 10.0,
        "min": 0.0,
        "max": 20.0,
        "declared_min": 0.0,
        "declared_max": 20.0,
    }
    remote = {
        "count": 100,
        "sum": 1000.0,
        "mean": 10.0,
        "min": -1.0,
        "max": 20.0,
        "skipX": 2,
        "skipY": 1,
    }
    result = m26.compare_equivalence(local, remote, contract)
    assert result["skip_match"] is False
    assert result["range_match"] is False
    assert result["all_equivalence_gates_passed"] is False


def test_pilot_selection_is_geometry_only_and_deterministic() -> None:
    from shapely.geometry import Polygon, mapping

    features = [
        {"geography_id": "b", "geometry": mapping(Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)]))},
        {"geography_id": "a", "geometry": mapping(Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)]))},
    ]
    # Match the actual ImageServer metadata shape consumed by aligned_window.
    # The synthetic extent is deliberately value-free: it only defines the
    # source-grid origin and export limits needed to rank geometry footprint.
    capacity_meta = {
        "fullExtent": {
            "xmin": 0.0,
            "ymin": -2000.0,
            "xmax": 2000.0,
            "ymax": 2000.0,
            "spatialReference": {"wkid": 3395},
        },
        "maxImageWidth": 15000,
        "maxImageHeight": 4100,
    }
    feature, _projected, _bbox, _width, _height = m26.select_geometry_only_pilot(features, capacity_meta)
    assert feature["geography_id"] == "a"
