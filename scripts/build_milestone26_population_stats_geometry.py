#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import transform as shapely_transform

from scripts import materialize_milestone26_stage1_components as stage1

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_stats_geometry_contract.json"
OUT = ROOT / "data/manifests/milestone26_population_stats_geometry.json"


class M26StatsGeometryError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-stats-geometry-contract/v1":
        raise M26StatsGeometryError("unexpected stats geometry contract schema")
    if contract.get("locked_before_geometry_simplification") is not True:
        raise M26StatsGeometryError("stats geometry contract is not locked")
    if contract.get("maximum_encoded_statistics_url_length") != 6000:
        raise M26StatsGeometryError("statistics URL length gate drift")
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
            raise M26StatsGeometryError(f"invalid locked boundary: {key}")
    return contract


def round_coordinates(value: Any, decimals: int) -> Any:
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(item, (int, float)) for item in value):
            return [round(float(item), decimals) for item in value]
        return [round_coordinates(item, decimals) for item in value]
    return value


def rounded_geometry(geom: Any, decimals: int) -> Any:
    payload = mapping(geom)
    payload = {**payload, "coordinates": round_coordinates(payload["coordinates"], decimals)}
    return shape(payload)


def oriented_polygons(geom: Any) -> list[Polygon]:
    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        raise M26StatsGeometryError(f"unsupported polygon geometry type: {geom.geom_type}")
    return [orient(poly, sign=-1.0) for poly in polygons]


def arcgis_polygon(geom: Any) -> dict[str, Any]:
    rings: list[list[list[float]]] = []
    for poly in oriented_polygons(geom):
        rings.append([[float(x), float(y)] for x, y, *_rest in poly.exterior.coords])
        for interior in poly.interiors:
            rings.append([[float(x), float(y)] for x, y, *_rest in interior.coords])
    return {"rings": rings, "spatialReference": {"wkid": 3395}}


def vertex_count(geom: Any) -> int:
    total = 0
    for poly in oriented_polygons(geom):
        total += len(poly.exterior.coords)
        total += sum(len(interior.coords) for interior in poly.interiors)
    return total


def mask_for_geometry(geom: Any, bbox: tuple[float, float, float, float], width: int, height: int) -> np.ndarray:
    left, _bottom, _right, top = bbox
    return geometry_mask(
        [mapping(geom)],
        out_shape=(height, width),
        transform=from_origin(left, top, 100.0, 100.0),
        invert=True,
        all_touched=False,
    )


def mask_sha(mask: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(mask, dtype=np.uint8).tobytes()).hexdigest()


def stats_url(base_url: str, geometry: dict[str, Any]) -> str:
    params = {
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryPolygon",
        "pixelSize": "100,100",
        "f": "json",
    }
    return base_url.rstrip("/") + "/computeStatisticsHistograms?" + urllib.parse.urlencode(params)


def candidate_geometry(projected: Any, tolerance: float, decimals: int) -> Any:
    simplified = projected if tolerance == 0 else projected.simplify(tolerance, preserve_topology=True)
    rounded = rounded_geometry(simplified, decimals)
    if rounded.is_empty or not rounded.is_valid or rounded.geom_type not in {"Polygon", "MultiPolygon"}:
        raise M26StatsGeometryError("simplified/rounded polygon is invalid")
    return rounded


def build() -> dict[str, Any]:
    contract = load_contract()
    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    meta = stage1.source_metadata("inarisk_population_2020")
    source_url = stage1.registry_urls()["inarisk_population_2020"]
    features, big_probe = stage1.load_qualified_big_features()
    if len(features) != 19 or len({row["geography_id"] for row in features}) != 19:
        raise M26StatsGeometryError("BIG frame is not exact 19")

    tolerances = [float(value) for value in contract["geometry_processing"]["tolerance_sequence_m_in_ascending_order"]]
    decimals = int(contract["geometry_processing"]["coordinate_rounding_decimals_m"])
    max_url = int(contract["maximum_encoded_statistics_url_length"])
    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    rows: list[dict[str, Any]] = []

    for feature in sorted(features, key=lambda row: row["geography_id"]):
        original = shape(feature["geometry"])
        projected = shapely_transform(transformer.transform, original)
        bbox, width, height = stage1.aligned_window(projected.bounds, meta)
        original_mask = mask_for_geometry(projected, bbox, width, height)
        original_sha = mask_sha(original_mask)
        inside_count = int(np.count_nonzero(original_mask))
        selected: dict[str, Any] | None = None
        diagnostics: list[dict[str, Any]] = []

        for tolerance in tolerances:
            try:
                candidate = candidate_geometry(projected, tolerance, decimals)
            except M26StatsGeometryError:
                diagnostics.append({"tolerance_m": tolerance, "valid": False, "pixel_mask_equal": False, "encoded_url_length": None})
                continue
            candidate_mask = mask_for_geometry(candidate, bbox, width, height)
            equal = bool(np.array_equal(candidate_mask, original_mask))
            geometry_json = arcgis_polygon(candidate)
            url = stats_url(source_url, geometry_json)
            diag = {
                "tolerance_m": tolerance,
                "valid": True,
                "pixel_mask_equal": equal,
                "encoded_url_length": len(url),
                "vertex_count": vertex_count(candidate),
            }
            diagnostics.append(diag)
            if equal and len(url) <= max_url:
                selected = {
                    "tolerance_m": tolerance,
                    "coordinate_rounding_decimals_m": decimals,
                    "vertex_count": vertex_count(candidate),
                    "encoded_url_length": len(url),
                    "arcgis_geometry": geometry_json,
                    "pixel_mask_sha256": mask_sha(candidate_mask),
                    "pixel_mask_equal": True,
                }
                break

        rows.append({
            "geography_id": feature["geography_id"],
            "geography_name": feature["geography_name"],
            "source_permendagri_code": feature["source_permendagri_code"],
            "aligned_window_bbox": list(bbox),
            "aligned_window_width": width,
            "aligned_window_height": height,
            "inside_boundary_native_cell_count": inside_count,
            "original_vertex_count": vertex_count(projected),
            "original_pixel_mask_sha256": original_sha,
            "selected_candidate": selected,
            "candidate_diagnostics": diagnostics,
        })

    resolved = [row for row in rows if row["selected_candidate"] is not None]
    padang_panjang = next(row for row in rows if row["geography_id"] == "idn.13.1374")
    manifest = {
        "schema": "ranah-observatory/milestone26-population-stats-geometry/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "source_metadata_sha256": hashlib.sha256(stage1.SOURCE_META_SNAPSHOT["inarisk_population_2020"].read_bytes()).hexdigest(),
        "big_expected_edition": big_probe.get("expected_edition"),
        "geography_count": 19,
        "resolved_geometry_count": len(resolved),
        "unresolved_geometry_count": 19 - len(resolved),
        "all_geographies_uri_safe_mask_equivalent": len(resolved) == 19,
        "padang_panjang": padang_panjang,
        "geographies": rows,
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
    pp = manifest["padang_panjang"]
    selected = pp["selected_candidate"]
    print(json.dumps({
        "resolved_geometry_count": manifest["resolved_geometry_count"],
        "unresolved_geometry_count": manifest["unresolved_geometry_count"],
        "all_geographies_uri_safe_mask_equivalent": manifest["all_geographies_uri_safe_mask_equivalent"],
        "padang_panjang_selected_tolerance_m": selected["tolerance_m"] if selected else None,
        "padang_panjang_url_length": selected["encoded_url_length"] if selected else None,
        "padang_panjang_original_vertices": pp["original_vertex_count"],
        "padang_panjang_selected_vertices": selected["vertex_count"] if selected else None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
