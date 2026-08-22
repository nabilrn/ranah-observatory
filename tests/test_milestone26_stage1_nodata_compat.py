from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/materialize_milestone26_stage1_components_v2.py"

spec = importlib.util.spec_from_file_location("m26_stage1_v2", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def _write(path: Path, data: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[1],
        height=data.shape[0],
        count=1,
        dtype="float32",
        crs="EPSG:3395",
        transform=from_origin(0.0, data.shape[0] * 100.0, 100.0, 100.0),
    ) as dataset:
        dataset.write(data.astype("float32"), 1)


def test_amendment_is_transport_only_and_bound_to_frozen_ranges() -> None:
    amendment = m26.load_nodata_amendment()
    assert amendment["aggregation_semantics_changed"] is False
    assert amendment["cross_geography_substantive_values_inspected_before_amendment"] is False
    assert amendment["source_family_changed"] is False
    assert amendment["minimum_valid_fraction_inside_polygon_unchanged"] == 0.99
    assert m26.source_valid_range("inarisk_capacity_2021") == (0.0, 0.7900000214576721)
    assert m26.source_valid_range("inarisk_population_2020") == (0.0, 1976.36376953125)


def test_out_of_source_range_background_is_excluded_when_coverage_still_passes(tmp_path: Path) -> None:
    data = np.full((10, 10), 0.5, dtype="float32")
    data[0, 0] = np.float32(3.4028235e38)
    path = tmp_path / "capacity-background.tif"
    _write(path, data)
    result = m26.aggregate_component("inarisk_capacity_2021", path, box(0, 0, 1000, 1000), 0.99)
    assert result["inside_pixel_count"] == 100
    assert result["valid_pixel_count"] == 99
    assert result["transport_invalid_pixel_count"] == 1
    assert result["valid_fraction"] == 0.99
    assert abs(result["value"] - 0.5) < 1e-12


def test_out_of_source_range_background_fails_when_coverage_drops_below_gate(tmp_path: Path) -> None:
    data = np.full((10, 10), 0.5, dtype="float32")
    data[0, 0] = np.float32(3.4028235e38)
    data[0, 1] = np.float32(3.4028235e38)
    path = tmp_path / "capacity-too-much-background.tif"
    _write(path, data)
    try:
        m26.aggregate_component("inarisk_capacity_2021", path, box(0, 0, 1000, 1000), 0.99)
    except m26.M26Stage1Error as exc:
        assert "below locked gate" in str(exc)
        assert "transport_invalid=2" in str(exc)
    else:
        raise AssertionError("coverage below 0.99 must fail closed")


def test_valid_population_values_still_sum_without_clamping(tmp_path: Path) -> None:
    data = np.full((2, 2), 10.25, dtype="float32")
    path = tmp_path / "population.tif"
    _write(path, data)
    result = m26.aggregate_component("inarisk_population_2020", path, box(0, 0, 200, 200), 0.99)
    assert result["transport_invalid_pixel_count"] == 0
    assert result["value"] == 41.0
