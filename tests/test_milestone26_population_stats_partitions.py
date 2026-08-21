from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts import build_milestone26_population_stats_partitions as partitions


def test_partition_contract_keeps_value_access_closed() -> None:
    contract = json.loads(Path(partitions.CONTRACT).read_text(encoding="utf-8"))
    assert contract["locked_before_partition_build"] is True
    assert contract["source_values_accessed"] is False
    assert contract["adaptive_partition"]["maximum_encoded_statistics_url_length"] == 6000
    assert contract["statistics_live_request_authorized_in_this_contract"] is False
    assert contract["stage1_population_aggregation_authorized"] is False
    assert contract["numeric_source_value_extraction_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_window_bbox_uses_native_cell_edges() -> None:
    global_bbox = (1000.0, 0.0, 1400.0, 400.0)
    assert partitions.window_bbox(global_bbox, 1, 3, 1, 4) == (1100.0, 100.0, 1400.0, 300.0)


def test_polygonized_mask_rasterizes_back_exactly() -> None:
    mask = np.array([[True, True, False], [True, False, False], [True, True, True]], dtype=bool)
    bbox = (0.0, 0.0, 300.0, 300.0)
    geom = partitions.polygonize_mask(mask, bbox)
    rebuilt = partitions.rerasterize(geom, bbox, 3, 3)
    assert np.array_equal(mask, rebuilt) is True


def test_split_window_is_deterministic_on_longer_dimension() -> None:
    assert partitions.split_window(0, 4, 0, 8) == [(0, 4, 0, 4), (0, 4, 4, 8)]
    assert partitions.split_window(0, 8, 0, 4) == [(0, 4, 0, 4), (4, 8, 0, 4)]
    assert partitions.split_window(0, 4, 0, 4) == [(0, 2, 0, 4), (2, 4, 0, 4)]
    assert partitions.split_window(0, 1, 0, 1) == []


def test_simple_full_mask_is_one_uri_safe_partition() -> None:
    mask = np.ones((4, 4), dtype=bool)
    leaves = partitions.partition_mask(
        full_mask=mask,
        global_bbox=(0.0, 0.0, 400.0, 400.0),
        source_url="https://example.test/ImageServer",
        tolerances=[49.0, 0.0],
        decimals=3,
        max_url=6000,
    )
    assert len(leaves) == 1
    assert leaves[0]["selected_cell_count"] == 16
    assert leaves[0]["candidate"]["encoded_url_length"] <= 6000


def test_partitioning_preserves_selected_cell_sum_when_forced_to_split() -> None:
    mask = np.array(
        [
            [True, True, False, False],
            [True, True, False, False],
            [False, False, True, True],
            [False, False, True, True],
        ],
        dtype=bool,
    )
    leaves = partitions.partition_mask(
        full_mask=mask,
        global_bbox=(0.0, 0.0, 400.0, 400.0),
        source_url="https://example.test/ImageServer",
        tolerances=[0.0],
        decimals=3,
        max_url=500,
    )
    assert sum(row["selected_cell_count"] for row in leaves) == int(np.count_nonzero(mask))
    assert all(row["candidate"]["encoded_url_length"] <= 500 for row in leaves)
