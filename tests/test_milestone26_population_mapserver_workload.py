from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely.geometry import box

from scripts import build_milestone26_population_mapserver_workload as workload


def test_workload_contract_keeps_source_values_closed() -> None:
    contract = json.loads(Path(workload.CONTRACT).read_text(encoding="utf-8"))
    assert contract["locked_before_workload_computation"] is True
    assert contract["source_values_accessed"] is False
    assert contract["qualified_batch_size"] == 64
    assert contract["diagnostic_headroom_batch_size"] == 128
    assert contract["stage1_population_aggregation_authorized"] is False
    assert contract["numeric_source_value_extraction_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_inside_cell_count_uses_pixel_centers_not_all_touched() -> None:
    geom = box(0.0, 0.0, 200.0, 200.0)
    count = workload.inside_cell_count(geom, (0.0, 0.0, 200.0, 200.0), 2, 2)
    assert count == 4


def test_inside_cell_count_excludes_cells_whose_centers_are_outside() -> None:
    geom = box(0.0, 0.0, 99.0, 99.0)
    count = workload.inside_cell_count(geom, (0.0, 0.0, 200.0, 200.0), 2, 2)
    assert count == 1


def test_inside_cell_count_returns_integer() -> None:
    geom = box(0.0, 0.0, 100.0, 100.0)
    count = workload.inside_cell_count(geom, (0.0, 0.0, 100.0, 100.0), 1, 1)
    assert isinstance(count, int)
    assert count == int(np.count_nonzero(np.array([[True]])))
