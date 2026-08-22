from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/materialize_milestone26_stage1_components_v3.py"

spec = importlib.util.spec_from_file_location("m26_stage1_v3", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_chunk_amendment_is_transport_only() -> None:
    amendment = m26.load_chunk_amendment()
    assert amendment["maximum_tile_width_pixels"] == 1500
    assert amendment["maximum_tile_height_pixels"] == 1500
    assert amendment["tile_overlap_pixels"] == 0
    assert amendment["tile_gap_pixels"] == 0
    assert amendment["aggregation_semantics_changed"] is False
    assert amendment["downsampling_authorized"] is False
    assert amendment["upsampling_authorized"] is False
    assert amendment["minimum_valid_fraction_inside_polygon_unchanged"] == 0.99


def test_tile_specs_cover_window_exactly_without_overlap_or_gap() -> None:
    bbox = (1000.0, 2000.0, 244800.0, 297200.0)
    specs = m26.tile_specs(bbox, 2438, 2952, 1500, 1500)
    assert len(specs) == 4
    assert sum(item["width"] * item["height"] for item in specs) == 2438 * 2952
    assert {item["width"] for item in specs} == {1500, 938}
    assert {item["height"] for item in specs} == {1500, 1452}
    row_ranges = sorted({(item["row0"], item["row1"]) for item in specs})
    col_ranges = sorted({(item["col0"], item["col1"]) for item in specs})
    assert row_ranges == [(0, 1500), (1500, 2952)]
    assert col_ranges == [(0, 1500), (1500, 2438)]
    assert {(item["row0"], item["col0"]) for item in specs} == {
        (0, 0), (0, 1500), (1500, 0), (1500, 1500)
    }


def test_single_small_window_remains_one_native_tile() -> None:
    specs = m26.tile_specs((0.0, 0.0, 100000.0, 90000.0), 1000, 900, 1500, 1500)
    assert len(specs) == 1
    assert specs[0]["bbox"] == (0.0, 0.0, 100000.0, 90000.0)
    assert specs[0]["width"] == 1000
    assert specs[0]["height"] == 900


def test_capacity_combination_is_global_valid_cell_mean() -> None:
    stats = [
        {"inside_count": 10, "valid_count": 10, "transport_invalid_count": 0, "value_sum": 2.0},
        {"inside_count": 20, "valid_count": 20, "transport_invalid_count": 0, "value_sum": 12.0},
    ]
    result = m26.combine_statistics("inarisk_capacity_2021", stats, 0.99)
    assert result["inside_pixel_count"] == 30
    assert result["valid_pixel_count"] == 30
    assert abs(result["value"] - (14.0 / 30.0)) < 1e-15


def test_population_combination_is_global_cell_sum() -> None:
    stats = [
        {"inside_count": 10, "valid_count": 10, "transport_invalid_count": 0, "value_sum": 120.0},
        {"inside_count": 20, "valid_count": 20, "transport_invalid_count": 0, "value_sum": 310.0},
    ]
    result = m26.combine_statistics("inarisk_population_2020", stats, 0.99)
    assert result["value"] == 430.0


def test_coverage_gate_is_applied_at_geography_level_after_chunking() -> None:
    passing = [
        {"inside_count": 50, "valid_count": 49, "transport_invalid_count": 1, "value_sum": 9.8},
        {"inside_count": 50, "valid_count": 50, "transport_invalid_count": 0, "value_sum": 10.0},
    ]
    assert m26.combine_statistics("inarisk_capacity_2021", passing, 0.99)["valid_fraction"] == 0.99
    failing = [
        {"inside_count": 50, "valid_count": 49, "transport_invalid_count": 1, "value_sum": 9.8},
        {"inside_count": 50, "valid_count": 49, "transport_invalid_count": 1, "value_sum": 9.8},
    ]
    try:
        m26.combine_statistics("inarisk_capacity_2021", failing, 0.99)
    except m26.M26ChunkError as exc:
        assert "below locked gate" in str(exc)
    else:
        raise AssertionError("global valid fraction below 0.99 must fail closed")
