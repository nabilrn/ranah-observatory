from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/materialize_milestone26_stage1_components.py"

spec = importlib.util.spec_from_file_location("m26_stage1", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_stage1_contract_is_locked_before_values() -> None:
    contract = m26.load_contract()
    assert contract["authorized_source_ids"] == ["inarisk_capacity_2021", "inarisk_population_2020"]
    assert contract["held_source_ids"] == ["dibi_kabupaten_hidromet_2015_2024"]
    assert contract["capacity_2021"]["primary_aggregation"].startswith("mean_of_valid_native_grid_cells")
    assert contract["population_2020"]["primary_aggregation"].startswith("sum_of_nonnegative_native_grid_cell")
    assert contract["dibi_2015_2024"]["numeric_extraction_authorized_in_stage1"] is False
    assert contract["risk_synthesis_authorized"] is False


def test_semantic_normalization_handles_html_and_dash_variants() -> None:
    body = b"<html><body><p>Pij adalah jumlah penduduk pada grid/sel</p><p>Nilai 0 &ndash; 1</p></body></html>"
    normalized = m26.normalize_text(body)
    assert "pij adalah jumlah penduduk pada grid/sel" in normalized
    assert "nilai 0 - 1" in normalized


def test_aligned_window_uses_native_grid_origin() -> None:
    meta = {
        "fullExtent": {"xmin": 25.0, "ymax": 1025.0},
        "maxImageWidth": 100,
        "maxImageHeight": 100,
    }
    bbox, width, height = m26.aligned_window((130.0, 430.0, 380.0, 770.0), meta)
    assert bbox == (125.0, 425.0, 425.0, 825.0)
    assert width == 3
    assert height == 4


def test_export_url_preserves_native_nearest_neighbor_contract() -> None:
    url = m26.export_url("https://example.test/ImageServer", (0.0, 0.0, 400.0, 300.0), 4, 3)
    assert "size=4%2C3" in url
    assert "bboxSR=3395" in url
    assert "imageSR=3395" in url
    assert "format=tiff" in url
    assert "pixelType=F32" in url
    assert "RSP_NearestNeighbor" in url


def _write_raster(path: Path, value: float) -> None:
    data = np.full((4, 4), value, dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=4,
        height=4,
        count=1,
        dtype="float32",
        crs="EPSG:3395",
        transform=from_origin(0.0, 400.0, 100.0, 100.0),
    ) as dataset:
        dataset.write(data, 1)


def test_capacity_uses_mean_not_sum(tmp_path: Path) -> None:
    path = tmp_path / "capacity.tif"
    _write_raster(path, 0.5)
    result = m26.aggregate_component("inarisk_capacity_2021", path, box(0, 0, 400, 400), 0.99)
    assert result["inside_pixel_count"] == 16
    assert result["valid_pixel_count"] == 16
    assert result["valid_fraction"] == 1.0
    assert result["value"] == 0.5


def test_population_uses_cell_sum_not_mean(tmp_path: Path) -> None:
    path = tmp_path / "population.tif"
    _write_raster(path, 2.0)
    result = m26.aggregate_component("inarisk_population_2020", path, box(0, 0, 400, 400), 0.99)
    assert result["inside_pixel_count"] == 16
    assert result["value"] == 32.0


def test_population_rejects_negative_person_values(tmp_path: Path) -> None:
    path = tmp_path / "population-negative.tif"
    _write_raster(path, -1.0)
    try:
        m26.aggregate_component("inarisk_population_2020", path, box(0, 0, 400, 400), 0.99)
    except m26.M26Stage1Error as exc:
        assert "negative population" in str(exc)
    else:
        raise AssertionError("negative population raster should fail closed")


def test_stage0_manifest_still_blocks_hazard_vulnerability() -> None:
    stage0 = json.loads(m26.STAGE0.read_text(encoding="utf-8"))
    assert stage0["hazard_vulnerability_numeric_extraction_authorized"] is False
    for source_id in (
        "inarisk_flood_hazard",
        "inarisk_landslide_hazard",
        "inarisk_flood_vulnerability",
        "inarisk_landslide_vulnerability",
    ):
        assert stage0["qualification_states"][source_id] == "endpoint_verified_version_binding_unresolved"
