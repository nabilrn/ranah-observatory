from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/materialize_milestone26_stage1_components_v4.py"

spec = importlib.util.spec_from_file_location("m26_stage1_v4", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_chunk_transport_v2_is_transport_only() -> None:
    amendment = m26.load_chunk_amendment_v2()
    assert amendment["maximum_tile_width_pixels"] == 500
    assert amendment["maximum_tile_height_pixels"] == 500
    assert amendment["tile_overlap_pixels"] == 0
    assert amendment["tile_gap_pixels"] == 0
    assert amendment["aggregation_semantics_changed"] is False
    assert amendment["downsampling_authorized"] is False
    assert amendment["upsampling_authorized"] is False
    assert amendment["minimum_valid_fraction_inside_polygon_unchanged"] == 0.99
    assert [item["workflow_run_id"] for item in amendment["transport_history"]] == [32455066555, 32460012029]


def test_v2_partition_preserves_exact_native_window() -> None:
    amendment = m26.load_chunk_amendment_v2()
    specs = m26.chunked.tile_specs(
        (1000.0, 2000.0, 244800.0, 297200.0),
        2438,
        2952,
        amendment["maximum_tile_width_pixels"],
        amendment["maximum_tile_height_pixels"],
    )
    assert len(specs) == 30
    assert sum(item["width"] * item["height"] for item in specs) == 2438 * 2952
    assert max(item["width"] for item in specs) == 500
    assert max(item["height"] for item in specs) == 500
    assert min(item["width"] for item in specs) == 438
    assert min(item["height"] for item in specs) == 452
    assert {(item["row0"], item["row1"]) for item in specs} == {
        (0, 500), (500, 1000), (1000, 1500), (1500, 2000), (2000, 2500), (2500, 2952)
    }
    assert {(item["col0"], item["col1"]) for item in specs} == {
        (0, 500), (500, 1000), (1000, 1500), (1500, 2000), (2000, 2438)
    }


def test_v2_reuses_same_global_aggregation_rules() -> None:
    capacity = m26.chunked.combine_statistics(
        "inarisk_capacity_2021",
        [
            {"inside_count": 10, "valid_count": 10, "transport_invalid_count": 0, "value_sum": 2.0},
            {"inside_count": 20, "valid_count": 20, "transport_invalid_count": 0, "value_sum": 12.0},
        ],
        0.99,
    )
    assert abs(capacity["value"] - 14.0 / 30.0) < 1e-15

    population = m26.chunked.combine_statistics(
        "inarisk_population_2020",
        [
            {"inside_count": 10, "valid_count": 10, "transport_invalid_count": 0, "value_sum": 120.0},
            {"inside_count": 20, "valid_count": 20, "transport_invalid_count": 0, "value_sum": 310.0},
        ],
        0.99,
    )
    assert population["value"] == 430.0


def test_install_transport_v2_changes_only_amendment_binding() -> None:
    original = m26.chunked.CHUNK_AMENDMENT
    m26.install_transport_v2()
    assert m26.chunked.CHUNK_AMENDMENT == m26.CHUNK_AMENDMENT_V2
    assert m26.chunked.load_chunk_amendment is m26.load_chunk_amendment_v2
    assert original.name == "milestone26_stage1_chunk_transport_amendment.json"
