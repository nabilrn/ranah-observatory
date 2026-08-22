#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import transform as shapely_transform

from scripts import materialize_milestone26_stage1_components as base
from scripts import materialize_milestone26_stage1_components_v2 as nodata

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_stage1_statistics_transport_probe_contract.json"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_stage1_statistics_transport_probe.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_statistics_transport_probe"


class M26StatisticsProbeError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage1-statistics-transport-probe-contract/v1":
        raise M26StatisticsProbeError("unexpected statistics-transport probe contract schema")
    if payload.get("locked_before_statistics_transport_probe") is not True:
        raise M26StatisticsProbeError("statistics transport contract was not locked before probing")
    if payload.get("source_ids") != list(base.SOURCE_IDS):
        raise M26StatisticsProbeError("statistics transport source set drift")
    if payload["pilot_selection"].get("selection_uses_raster_values") is not False:
        raise M26StatisticsProbeError("pilot geography may not be selected from raster values")
    for key in (
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26StatisticsProbeError(f"invalid statistics probe boundary: {key}")
    return payload


def post_form(url: str, params: dict[str, str], *, timeout: float = 90.0, retries: int = 3) -> tuple[str, str, bytes]:
    encoded = urllib.parse.urlencode(params).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                data=encoded,
                method="POST",
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if int(response.status) != 200:
                    raise M26StatisticsProbeError(f"HTTP {response.status}: {url}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), body
        except (urllib.error.URLError, TimeoutError, M26StatisticsProbeError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise M26StatisticsProbeError(f"POST request failed after retries: {url}") from last_error


def arcgis_polygon(projected_geometry: Any) -> dict[str, Any]:
    polygons: list[Polygon]
    if isinstance(projected_geometry, Polygon):
        polygons = [projected_geometry]
    elif isinstance(projected_geometry, MultiPolygon):
        polygons = list(projected_geometry.geoms)
    else:
        raise M26StatisticsProbeError(f"unsupported pilot geometry: {projected_geometry.geom_type}")
    rings: list[list[list[float]]] = []
    for polygon in polygons:
        fixed = orient(polygon, sign=-1.0)
        rings.append([[float(x), float(y)] for x, y in fixed.exterior.coords])
        for interior in fixed.interiors:
            rings.append([[float(x), float(y)] for x, y in interior.coords])
    if not rings:
        raise M26StatisticsProbeError("pilot polygon produced no ArcGIS rings")
    return {"rings": rings, "spatialReference": {"wkid": 3395}}


def select_geometry_only_pilot(features: list[dict[str, Any]], capacity_meta: dict[str, Any]) -> tuple[dict[str, Any], Any, tuple[float, float, float, float], int, int]:
    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    ranked: list[tuple[int, str, dict[str, Any], Any, tuple[float, float, float, float], int, int]] = []
    for feature in features:
        projected = shapely_transform(transformer.transform, shape(feature["geometry"]))
        bbox, width, height = base.aligned_window(projected.bounds, capacity_meta)
        ranked.append((width * height, feature["geography_id"], feature, projected, bbox, width, height))
    ranked.sort(key=lambda item: (item[0], item[1]))
    _area, _gid, feature, projected, bbox, width, height = ranked[0]
    return feature, projected, bbox, width, height


def local_reference_stats(source_id: str, raster_path: Path, projected_geometry: Any) -> dict[str, Any]:
    declared_min, declared_max = nodata.source_valid_range(source_id)
    with rasterio.open(raster_path) as dataset:
        if dataset.count != 1 or dataset.crs is None or dataset.crs.to_epsg() != 3395:
            raise M26StatisticsProbeError(f"unexpected pilot raster CRS/bands: {raster_path}")
        if abs(float(dataset.transform.a) - 100.0) > 1e-6 or abs(abs(float(dataset.transform.e)) - 100.0) > 1e-6:
            raise M26StatisticsProbeError(f"pilot raster is not native 100 m grid: {raster_path}")
        values = dataset.read(1).astype(np.float64, copy=False)
        inside = geometry_mask(
            [mapping(projected_geometry)],
            out_shape=(dataset.height, dataset.width),
            transform=dataset.transform,
            invert=True,
            all_touched=False,
        )
        inside_count = int(np.count_nonzero(inside))
        if inside_count <= 0:
            raise M26StatisticsProbeError("pilot has no raster cell centers inside polygon")
        candidate = inside & np.isfinite(values)
        if dataset.nodata is not None and math.isfinite(float(dataset.nodata)):
            candidate &= values != float(dataset.nodata)
        valid = candidate & (values >= declared_min) & (values <= declared_max)
        selected = values[valid]
        if selected.size <= 0:
            raise M26StatisticsProbeError("pilot has no valid source-domain raster cells")
        return {
            "inside_count": inside_count,
            "valid_count": int(selected.size),
            "valid_fraction": float(selected.size / inside_count),
            "sum": float(np.sum(selected, dtype=np.float64)),
            "mean": float(np.mean(selected, dtype=np.float64)),
            "min": float(np.min(selected)),
            "max": float(np.max(selected)),
            "declared_min": declared_min,
            "declared_max": declared_max,
        }


def compute_statistics(base_url: str, geometry: dict[str, Any]) -> tuple[str, str, bytes, dict[str, Any]]:
    endpoint = base_url.rstrip("/") + "/computeStatisticsHistograms"
    final_url, content_type, body = post_form(
        endpoint,
        {
            "geometry": json.dumps(geometry, separators=(",", ":")),
            "geometryType": "esriGeometryPolygon",
            "pixelSize": "100,100",
            "processAsMultidimensional": "false",
            "f": "json",
        },
    )
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise M26StatisticsProbeError("computeStatisticsHistograms returned non-JSON response") from exc
    if isinstance(payload, dict) and payload.get("error"):
        raise M26StatisticsProbeError(f"computeStatisticsHistograms service error: {payload['error']}")
    statistics = payload.get("statistics") if isinstance(payload, dict) else None
    if not isinstance(statistics, list) or len(statistics) != 1 or not isinstance(statistics[0], dict):
        raise M26StatisticsProbeError(f"unexpected computeStatisticsHistograms payload shape: {payload!r}")
    return final_url, content_type, body, statistics[0]


def compare_equivalence(local: dict[str, Any], remote: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    gates = contract["equivalence_gates"]
    required = set(contract["candidate_operation"]["required_statistics_fields"])
    missing = sorted(required - set(remote))
    if missing:
        raise M26StatisticsProbeError(f"server statistics missing required fields: {missing}")
    remote_count = int(remote["count"])
    remote_sum = float(remote["sum"])
    remote_mean = float(remote["mean"])
    remote_min = float(remote["min"])
    remote_max = float(remote["max"])
    count_match = remote_count == int(local["valid_count"])
    sum_match = math.isclose(
        remote_sum,
        float(local["sum"]),
        rel_tol=float(gates["statistics_sum_relative_tolerance"]),
        abs_tol=float(gates["statistics_sum_absolute_tolerance"]),
    )
    mean_match = math.isclose(
        remote_mean,
        float(local["mean"]),
        rel_tol=float(gates["statistics_mean_relative_tolerance"]),
        abs_tol=float(gates["statistics_mean_absolute_tolerance"]),
    )
    skip_match = int(remote["skipX"]) == int(gates["statistics_skipX_must_equal"]) and int(remote["skipY"]) == int(gates["statistics_skipY_must_equal"])
    range_match = remote_min >= float(local["declared_min"]) - 1e-12 and remote_max <= float(local["declared_max"]) + 1e-12
    coverage_match = float(local["valid_fraction"]) >= float(gates["local_valid_fraction_must_remain_at_least"])
    return {
        "count_match": count_match,
        "sum_match": sum_match,
        "mean_match": mean_match,
        "skip_match": skip_match,
        "range_match": range_match,
        "coverage_match": coverage_match,
        "all_equivalence_gates_passed": all((count_match, sum_match, mean_match, skip_match, range_match, coverage_match)),
        "count_difference": remote_count - int(local["valid_count"]),
        "sum_absolute_difference": abs(remote_sum - float(local["sum"])),
        "mean_absolute_difference": abs(remote_mean - float(local["mean"])),
    }


def run() -> dict[str, Any]:
    contract = load_contract()
    stage0 = base.load_stage0()
    base.verify_stage0_snapshot_hashes(stage0)
    source_urls = base.registry_urls()
    features, big_probe = base.load_qualified_big_features()
    capacity_meta = base.source_metadata("inarisk_capacity_2021")
    pilot_feature, projected, capacity_bbox, capacity_width, capacity_height = select_geometry_only_pilot(features, capacity_meta)
    arc_geometry = arcgis_polygon(projected)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    for source_id in base.SOURCE_IDS:
        source_meta = base.source_metadata(source_id)
        bbox, width, height = base.aligned_window(projected.bounds, source_meta)
        export_url = base.export_url(source_urls[source_id], bbox, width, height)
        final_url, content_type, body = base.request_bytes(export_url, retries=3, timeout=90.0)
        if not base.is_tiff(body):
            preview = body[:500].decode("utf-8", errors="replace")
            raise M26StatisticsProbeError(f"pilot export is not TIFF for {source_id}: {preview}")
        raster_path = OUT_DIR / f"{source_id}-{pilot_feature['geography_id']}-reference.tif"
        raster_path.write_bytes(body)
        local = local_reference_stats(source_id, raster_path, projected)

        stats_final_url, stats_type, stats_body, remote = compute_statistics(source_urls[source_id], arc_geometry)
        stats_path = OUT_DIR / f"{source_id}-{pilot_feature['geography_id']}-compute-statistics.json"
        stats_path.write_bytes(canonical_json_bytes(json.loads(stats_body.decode("utf-8"))))
        equivalence = compare_equivalence(local, remote, contract)
        results[source_id] = {
            "source_id": source_id,
            "pilot_geography_id": pilot_feature["geography_id"],
            "reference_export": {
                "requested_url": export_url,
                "final_url": final_url,
                "content_type": content_type,
                "path": raster_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_bytes(body),
                "bytes": len(body),
                "bbox_native": list(bbox),
                "width": width,
                "height": height,
            },
            "local_reference_statistics": local,
            "server_statistics": {
                "endpoint": source_urls[source_id].rstrip("/") + "/computeStatisticsHistograms",
                "final_url": stats_final_url,
                "content_type": stats_type,
                "path": stats_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(stats_path.read_bytes()).hexdigest(),
                "count": int(remote["count"]),
                "sum": float(remote["sum"]),
                "mean": float(remote["mean"]),
                "min": float(remote["min"]),
                "max": float(remote["max"]),
                "skipX": int(remote["skipX"]),
                "skipY": int(remote["skipY"]),
            },
            "equivalence": equivalence,
        }

    all_passed = all(result["equivalence"]["all_equivalence_gates_passed"] for result in results.values())
    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-statistics-transport-probe/v1",
        "milestone": 26,
        "stage": 1,
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": base.sha256_path(CONTRACT)},
        "pilot_selection_rule": contract["pilot_selection"]["rule"],
        "pilot_geography_id": pilot_feature["geography_id"],
        "pilot_geography_name": pilot_feature["geography_name"],
        "pilot_capacity_aligned_window": {"bbox_native": list(capacity_bbox), "width": capacity_width, "height": capacity_height},
        "big_expected_edition": big_probe.get("expected_edition"),
        "source_results": results,
        "both_sources_equivalent": all_passed,
        "statistics_transport_qualified_for_stage1": all_passed,
        "cross_geography_substantive_values_inspected": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT_MANIFEST.write_bytes(canonical_json_bytes(manifest))
    if not all_passed:
        failures = {source_id: result["equivalence"] for source_id, result in results.items() if not result["equivalence"]["all_equivalence_gates_passed"]}
        raise M26StatisticsProbeError(f"statistics transport equivalence failed: {failures}")
    return manifest


def main() -> int:
    try:
        manifest = run()
    except (OSError, ValueError, json.JSONDecodeError, base.M26Stage1Error, M26StatisticsProbeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "pilot_geography_id": manifest["pilot_geography_id"],
        "both_sources_equivalent": manifest["both_sources_equivalent"],
        "statistics_transport_qualified_for_stage1": manifest["statistics_transport_qualified_for_stage1"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
