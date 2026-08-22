#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from rasterio.features import geometry_mask, shapes as raster_shapes
from rasterio.transform import from_origin
from shapely.geometry import mapping, shape
from shapely.ops import transform as shapely_transform, unary_union

from scripts import build_milestone26_population_stats_geometry as stats_geom
from scripts import materialize_milestone26_stage1_components as stage1

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_stats_partition_contract.json"
OUT = ROOT / "data/manifests/milestone26_population_stats_partitions.json"


class M26StatsPartitionError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-stats-partition-contract/v1":
        raise M26StatsPartitionError("unexpected stats partition contract schema")
    if contract.get("locked_before_partition_build") is not True:
        raise M26StatsPartitionError("stats partition contract is not locked")
    if contract["adaptive_partition"].get("maximum_encoded_statistics_url_length") != 6000:
        raise M26StatsPartitionError("partition URL gate drift")
    for key in (
        "source_values_accessed",
        "selection_uses_source_values",
        "selection_uses_model_results",
        "statistics_live_request_authorized_in_this_contract",
        "stage1_population_aggregation_authorized",
        "numeric_source_value_extraction_authorized",
        "substantive_value_promotion_authorized",
        "cross_geography_numeric_source_extraction_authorized",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise M26StatsPartitionError(f"invalid locked boundary: {key}")
    return contract


def window_bbox(global_bbox: tuple[float, float, float, float], row0: int, row1: int, col0: int, col1: int) -> tuple[float, float, float, float]:
    left, _bottom, _right, top = global_bbox
    return (
        left + col0 * 100.0,
        top - row1 * 100.0,
        left + col1 * 100.0,
        top - row0 * 100.0,
    )


def polygonize_mask(mask: np.ndarray, bbox: tuple[float, float, float, float]) -> Any:
    if mask.ndim != 2 or not np.any(mask):
        raise M26StatsPartitionError("cannot polygonize empty/non-2D mask")
    left, _bottom, _right, top = bbox
    transform = from_origin(left, top, 100.0, 100.0)
    geoms = []
    values = np.ascontiguousarray(mask, dtype=np.uint8)
    for geom_mapping, value in raster_shapes(values, mask=mask, transform=transform):
        if int(value) == 1:
            geoms.append(shape(geom_mapping))
    if not geoms:
        raise M26StatsPartitionError("polygonization produced no selected geometry")
    result = unary_union(geoms)
    if result.is_empty or result.geom_type not in {"Polygon", "MultiPolygon"}:
        raise M26StatsPartitionError(f"unexpected polygonized geometry: {result.geom_type}")
    return result


def rerasterize(geom: Any, bbox: tuple[float, float, float, float], width: int, height: int) -> np.ndarray:
    left, _bottom, _right, top = bbox
    return geometry_mask(
        [mapping(geom)],
        out_shape=(height, width),
        transform=from_origin(left, top, 100.0, 100.0),
        invert=True,
        all_touched=False,
    )


def safe_candidate(
    *,
    submask: np.ndarray,
    bbox: tuple[float, float, float, float],
    source_url: str,
    tolerances: list[float],
    decimals: int,
    max_url: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    base_geom = polygonize_mask(submask, bbox)
    diagnostics: list[dict[str, Any]] = []
    for tolerance in tolerances:
        try:
            candidate = stats_geom.candidate_geometry(base_geom, tolerance, decimals)
        except Exception:
            diagnostics.append({"tolerance_m": tolerance, "valid": False, "mask_equal": False, "url_length": None})
            continue
        candidate_mask = rerasterize(candidate, bbox, submask.shape[1], submask.shape[0])
        equal = bool(np.array_equal(candidate_mask, submask))
        if not equal:
            diagnostics.append({"tolerance_m": tolerance, "valid": True, "mask_equal": False, "url_length": None})
            continue
        arcgis = stats_geom.arcgis_polygon(candidate)
        url = stats_geom.stats_url(source_url, arcgis)
        diagnostics.append({
            "tolerance_m": tolerance,
            "valid": True,
            "mask_equal": True,
            "url_length": len(url),
            "vertex_count": stats_geom.vertex_count(candidate),
        })
        if len(url) <= max_url:
            return {
                "tolerance_m": tolerance,
                "coordinate_rounding_decimals_m": decimals,
                "vertex_count": stats_geom.vertex_count(candidate),
                "encoded_url_length": len(url),
                "arcgis_geometry": arcgis,
                "geometry_sha256": hashlib.sha256(json.dumps(arcgis, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest(),
            }, diagnostics
    return None, diagnostics


def split_window(row0: int, row1: int, col0: int, col1: int) -> list[tuple[int, int, int, int]]:
    height = row1 - row0
    width = col1 - col0
    if height <= 0 or width <= 0:
        raise M26StatsPartitionError("invalid partition window")
    if height == 1 and width == 1:
        return []
    if width > height and width > 1:
        mid = col0 + width // 2
        return [(row0, row1, col0, mid), (row0, row1, mid, col1)]
    if height > 1:
        mid = row0 + height // 2
        return [(row0, mid, col0, col1), (mid, row1, col0, col1)]
    mid = col0 + width // 2
    return [(row0, row1, col0, mid), (row0, row1, mid, col1)]


def partition_mask(
    *,
    full_mask: np.ndarray,
    global_bbox: tuple[float, float, float, float],
    source_url: str,
    tolerances: list[float],
    decimals: int,
    max_url: int,
) -> list[dict[str, Any]]:
    leaves: list[dict[str, Any]] = []
    stack: list[tuple[int, int, int, int, int]] = [(0, full_mask.shape[0], 0, full_mask.shape[1], 0)]
    while stack:
        row0, row1, col0, col1, depth = stack.pop()
        submask = full_mask[row0:row1, col0:col1]
        selected_count = int(np.count_nonzero(submask))
        if selected_count == 0:
            continue
        bbox = window_bbox(global_bbox, row0, row1, col0, col1)
        candidate, diagnostics = safe_candidate(
            submask=submask,
            bbox=bbox,
            source_url=source_url,
            tolerances=tolerances,
            decimals=decimals,
            max_url=max_url,
        )
        if candidate is not None:
            leaves.append({
                "row0": row0,
                "row1": row1,
                "col0": col0,
                "col1": col1,
                "window_height": row1 - row0,
                "window_width": col1 - col0,
                "selected_cell_count": selected_count,
                "recursion_depth": depth,
                "bbox": list(bbox),
                "candidate": candidate,
                "candidate_diagnostics": diagnostics,
            })
            continue
        children = split_window(row0, row1, col0, col1)
        if not children:
            raise M26StatsPartitionError("1x1 selected cell failed URI-safe polygon qualification")
        for child in reversed(children):
            stack.append((*child, depth + 1))
    leaves.sort(key=lambda row: (row["row0"], row["col0"], row["row1"], row["col1"]))
    for index, leaf in enumerate(leaves, start=1):
        leaf["partition_index"] = index
    return leaves


def build() -> dict[str, Any]:
    contract = load_contract()
    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    meta = stage1.source_metadata("inarisk_population_2020")
    source_url = stage1.registry_urls()["inarisk_population_2020"]
    features, big_probe = stage1.load_qualified_big_features()
    if len(features) != 19 or len({row["geography_id"] for row in features}) != 19:
        raise M26StatsPartitionError("BIG frame is not exact 19")

    tolerances = [float(value) for value in contract["mask_polygonization"]["safe_simplification_tolerances_m_in_descending_order"]]
    decimals = int(contract["mask_polygonization"]["coordinate_rounding_decimals_m"])
    max_url = int(contract["adaptive_partition"]["maximum_encoded_statistics_url_length"])
    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    geographies: list[dict[str, Any]] = []

    for feature in sorted(features, key=lambda row: row["geography_id"]):
        geom = shape(feature["geometry"])
        projected = shapely_transform(transformer.transform, geom)
        bbox, width, height = stage1.aligned_window(projected.bounds, meta)
        full_mask = stats_geom.mask_for_geometry(projected, bbox, width, height)
        inside_count = int(np.count_nonzero(full_mask))
        leaves = partition_mask(
            full_mask=full_mask,
            global_bbox=bbox,
            source_url=source_url,
            tolerances=tolerances,
            decimals=decimals,
            max_url=max_url,
        )
        partition_cell_sum = sum(int(row["selected_cell_count"]) for row in leaves)
        if partition_cell_sum != inside_count:
            raise M26StatsPartitionError(f"partition cell count mismatch: {feature['geography_id']}")
        if any(int(row["candidate"]["encoded_url_length"]) > max_url for row in leaves):
            raise M26StatsPartitionError(f"partition URL gate violation: {feature['geography_id']}")
        geographies.append({
            "geography_id": feature["geography_id"],
            "geography_name": feature["geography_name"],
            "source_permendagri_code": feature["source_permendagri_code"],
            "aligned_window_bbox": list(bbox),
            "aligned_window_width": width,
            "aligned_window_height": height,
            "inside_boundary_native_cell_count": inside_count,
            "partition_count": len(leaves),
            "partition_cell_count_sum": partition_cell_sum,
            "max_partition_url_length": max(int(row["candidate"]["encoded_url_length"]) for row in leaves),
            "max_recursion_depth": max(int(row["recursion_depth"]) for row in leaves),
            "partitions": leaves,
        })

    total_partitions = sum(row["partition_count"] for row in geographies)
    total_cells = sum(row["inside_boundary_native_cell_count"] for row in geographies)
    padang_panjang = next(row for row in geographies if row["geography_id"] == "idn.13.1374")
    manifest = {
        "schema": "ranah-observatory/milestone26-population-stats-partitions/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "source_metadata_sha256": hashlib.sha256(stage1.SOURCE_META_SNAPSHOT["inarisk_population_2020"].read_bytes()).hexdigest(),
        "big_expected_edition": big_probe.get("expected_edition"),
        "geography_count": 19,
        "total_inside_boundary_native_cell_count": total_cells,
        "total_partition_count": total_partitions,
        "padang_panjang_partition_count": padang_panjang["partition_count"],
        "padang_panjang": padang_panjang,
        "geographies": geographies,
        "all_partition_cell_counts_exact": True,
        "all_partition_urls_within_gate": True,
        "source_values_accessed": False,
        "statistics_live_request_performed": False,
        "numeric_source_value_extraction_performed": False,
        "stage1_population_aggregation_authorized": False,
        "substantive_value_promotion_performed": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT.write_bytes(canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    try:
        manifest = build()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "geography_count": manifest["geography_count"],
        "total_inside_boundary_native_cell_count": manifest["total_inside_boundary_native_cell_count"],
        "total_partition_count": manifest["total_partition_count"],
        "padang_panjang_partition_count": manifest["padang_panjang_partition_count"],
        "padang_panjang_max_url_length": manifest["padang_panjang"]["max_partition_url_length"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
