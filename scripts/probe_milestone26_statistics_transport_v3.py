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
from affine import Affine
from rasterio.features import geometry_mask
from shapely.geometry import mapping

from scripts import materialize_milestone26_stage1_components as stage1
from scripts import materialize_milestone26_stage1_components_v2 as nodata
from scripts import probe_milestone26_statistics_transport as v1
from scripts import probe_milestone26_statistics_transport_v2 as v2

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "data/manifests/milestone26_stage1_statistics_transport_probe_amendment_v2.json"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_stage1_statistics_transport_probe.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_statistics_transport_probe"


class M26StatisticsProbeV3Error(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_amendment() -> dict[str, Any]:
    payload = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage1-statistics-transport-probe-amendment/v2":
        raise M26StatisticsProbeV3Error("unexpected getSamples amendment schema")
    if payload.get("locked_before_getsamples_reference_probe") is not True:
        raise M26StatisticsProbeV3Error("getSamples reference amendment was not pre-locked")
    if payload["reference_operation"].get("name") != "getSamples":
        raise M26StatisticsProbeV3Error("unexpected reference operation")
    if int(payload["reference_operation"].get("batch_size_points", 0)) != 50:
        raise M26StatisticsProbeV3Error("getSamples batch-size contract drift")
    for key in (
        "pilot_selection_changed",
        "pilot_selection_uses_raster_values",
        "equivalence_tolerances_changed",
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
            raise M26StatisticsProbeV3Error(f"invalid getSamples amendment boundary: {key}")
    return payload


def grid_centers_inside_polygon(
    projected_geometry: Any,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
) -> list[list[float]]:
    left, bottom, right, top = bbox
    if width <= 0 or height <= 0:
        raise M26StatisticsProbeV3Error("invalid native-grid window")
    if abs((right - left) / width - 100.0) > 1e-6 or abs((top - bottom) / height - 100.0) > 1e-6:
        raise M26StatisticsProbeV3Error("native-grid window is not exact 100 m")
    transform = Affine(100.0, 0.0, left, 0.0, -100.0, top)
    inside = geometry_mask(
        [mapping(projected_geometry)],
        out_shape=(height, width),
        transform=transform,
        invert=True,
        all_touched=False,
    )
    rows, cols = np.nonzero(inside)
    points = [
        [float(left + (int(col) + 0.5) * 100.0), float(top - (int(row) + 0.5) * 100.0)]
        for row, col in zip(rows.tolist(), cols.tolist(), strict=True)
    ]
    if not points:
        raise M26StatisticsProbeV3Error("pilot polygon contains no native-grid centers")
    return points


def request_json_get(
    endpoint: str,
    params: dict[str, str],
    *,
    retries: int = 3,
    timeout: float = 60.0,
) -> tuple[str, str, bytes, dict[str, Any]]:
    query = urllib.parse.urlencode(params)
    url = endpoint + "?" + query
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if int(response.status) != 200:
                    raise M26StatisticsProbeV3Error(f"HTTP {response.status}: {endpoint}")
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise M26StatisticsProbeV3Error("ArcGIS response is not a JSON object")
                if payload.get("error"):
                    raise M26StatisticsProbeV3Error(f"ArcGIS service error: {payload['error']}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), body, payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, M26StatisticsProbeV3Error) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise M26StatisticsProbeV3Error(f"GET request failed after retries: {endpoint}") from last_error


def parse_one_band_sample(value: Any) -> float | None:
    text = str(value or "").strip()
    if text.casefold() in {"", "nodata", "nan", "null", "none"}:
        return None
    tokens = [token.strip() for token in text.split(",")]
    if len(tokens) != 1:
        raise M26StatisticsProbeV3Error(f"expected one-band sample value, got {text!r}")
    try:
        number = float(tokens[0])
    except ValueError as exc:
        raise M26StatisticsProbeV3Error(f"non-numeric getSamples value: {text!r}") from exc
    return number if math.isfinite(number) else None


def point_key(point: list[float] | tuple[float, float]) -> tuple[float, float]:
    return (round(float(point[0]), 3), round(float(point[1]), 3))


def get_samples_reference(
    source_id: str,
    base_url: str,
    projected_geometry: Any,
    source_meta: dict[str, Any],
    batch_size: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bbox, width, height = stage1.aligned_window(projected_geometry.bounds, source_meta)
    points = grid_centers_inside_polygon(projected_geometry, bbox, width, height)
    declared_min, declared_max = nodata.source_valid_range(source_id)
    endpoint = base_url.rstrip("/") + "/getSamples"
    valid_values: list[float] = []
    snapshots: list[dict[str, Any]] = []
    returned_locations: set[tuple[float, float]] = set()

    source_dir = OUT_DIR / source_id / "getsamples"
    source_dir.mkdir(parents=True, exist_ok=True)
    for batch_index, start in enumerate(range(0, len(points), batch_size)):
        batch = points[start : start + batch_size]
        geometry = {"points": batch, "spatialReference": {"wkid": 3395}}
        final_url, content_type, body, payload = request_json_get(
            endpoint,
            {
                "geometryType": "esriGeometryMultipoint",
                "geometry": json.dumps(geometry, separators=(",", ":")),
                "pixelSize": "100,100",
                "interpolation": "RSP_NearestNeighbor",
                "returnFirstValueOnly": "true",
                "f": "json",
            },
        )
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise M26StatisticsProbeV3Error(f"getSamples payload missing samples for {source_id} batch {batch_index}")
        expected = {point_key(point) for point in batch}
        seen_in_batch: set[tuple[float, float]] = set()
        for sample in samples:
            if not isinstance(sample, dict) or not isinstance(sample.get("location"), dict):
                raise M26StatisticsProbeV3Error("malformed getSamples sample")
            location = sample["location"]
            if "x" not in location or "y" not in location:
                raise M26StatisticsProbeV3Error("getSamples sample missing location coordinates")
            key = point_key([location["x"], location["y"]])
            if key not in expected:
                raise M26StatisticsProbeV3Error(
                    f"getSamples returned location outside requested native centers: {key}"
                )
            if key in seen_in_batch or key in returned_locations:
                raise M26StatisticsProbeV3Error(f"duplicate getSamples location: {key}")
            seen_in_batch.add(key)
            returned_locations.add(key)
            number = parse_one_band_sample(sample.get("value"))
            if number is None:
                continue
            if declared_min <= number <= declared_max:
                valid_values.append(number)

        snapshot_path = source_dir / f"batch-{batch_index:03d}.json"
        snapshot_path.write_bytes(canonical_json_bytes(payload))
        snapshots.append(
            {
                "batch_index": batch_index,
                "requested_point_count": len(batch),
                "returned_sample_count": len(samples),
                "path": snapshot_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_path(snapshot_path),
                "content_type": content_type,
                "final_url": final_url,
            }
        )

    if not valid_values:
        raise M26StatisticsProbeV3Error(f"getSamples returned no valid values for {source_id}")
    array = np.asarray(valid_values, dtype=np.float64)
    reference = {
        "inside_count": len(points),
        "valid_count": int(array.size),
        "valid_fraction": float(array.size / len(points)),
        "sum": float(np.sum(array, dtype=np.float64)),
        "mean": float(np.mean(array, dtype=np.float64)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
        "declared_min": float(declared_min),
        "declared_max": float(declared_max),
        "requested_center_count": len(points),
        "returned_location_count": len(returned_locations),
        "missing_or_nodata_center_count": len(points) - len(returned_locations),
        "bbox_native": list(bbox),
        "width": width,
        "height": height,
    }
    return reference, snapshots


def compare_capacity_bridge(
    tiff_stats: dict[str, Any],
    sample_stats: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    gates = contract["equivalence_gates"]
    count_match = int(tiff_stats["valid_count"]) == int(sample_stats["valid_count"])
    sum_match = math.isclose(
        float(tiff_stats["sum"]),
        float(sample_stats["sum"]),
        rel_tol=float(gates["statistics_sum_relative_tolerance"]),
        abs_tol=float(gates["statistics_sum_absolute_tolerance"]),
    )
    mean_match = math.isclose(
        float(tiff_stats["mean"]),
        float(sample_stats["mean"]),
        rel_tol=float(gates["statistics_mean_relative_tolerance"]),
        abs_tol=float(gates["statistics_mean_absolute_tolerance"]),
    )
    inside_match = int(tiff_stats["inside_count"]) == int(sample_stats["inside_count"])
    coverage_match = float(sample_stats["valid_fraction"]) >= float(
        gates["local_valid_fraction_must_remain_at_least"]
    )
    return {
        "inside_count_match": inside_match,
        "valid_count_match": count_match,
        "sum_match": sum_match,
        "mean_match": mean_match,
        "coverage_match": coverage_match,
        "all_bridge_gates_passed": all((inside_match, count_match, sum_match, mean_match, coverage_match)),
        "sum_absolute_difference": abs(float(tiff_stats["sum"]) - float(sample_stats["sum"])),
        "mean_absolute_difference": abs(float(tiff_stats["mean"]) - float(sample_stats["mean"])),
    }


def freeze_server_statistics(
    source_id: str,
    source_url: str,
    arc_geometry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    final_url, content_type, body, remote = v1.compute_statistics(source_url, arc_geometry)
    path = OUT_DIR / source_id / "compute-statistics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(json.loads(body.decode("utf-8"))))
    frozen = {
        "endpoint": source_url.rstrip("/") + "/computeStatisticsHistograms",
        "final_url": final_url,
        "content_type": content_type,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_path(path),
        "count": int(remote["count"]),
        "sum": float(remote["sum"]),
        "mean": float(remote["mean"]),
        "min": float(remote["min"]),
        "max": float(remote["max"]),
        "skipX": int(remote["skipX"]),
        "skipY": int(remote["skipY"]),
    }
    return frozen, remote


def run() -> dict[str, Any]:
    amendment = load_amendment()
    contract = v1.load_contract()
    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    source_urls = stage1.registry_urls()
    features, big_probe = stage1.load_qualified_big_features()
    capacity_meta = stage1.source_metadata("inarisk_capacity_2021")
    pilot_feature, projected, capacity_bbox, capacity_width, capacity_height = v1.select_geometry_only_pilot(
        features, capacity_meta
    )
    arc_geometry = v2.arcgis_polygon_xy(projected)
    batch_size = int(amendment["reference_operation"]["batch_size_points"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    capacity_bridge_passed = False
    for source_id in stage1.SOURCE_IDS:
        source_meta = stage1.source_metadata(source_id)
        sample_reference, sample_snapshots = get_samples_reference(
            source_id,
            source_urls[source_id],
            projected,
            source_meta,
            batch_size,
        )
        server_frozen, remote = freeze_server_statistics(source_id, source_urls[source_id], arc_geometry)
        statistics_equivalence = v1.compare_equivalence(sample_reference, remote, contract)
        result: dict[str, Any] = {
            "source_id": source_id,
            "pilot_geography_id": pilot_feature["geography_id"],
            "getsamples_reference_statistics": sample_reference,
            "getsamples_batch_count": len(sample_snapshots),
            "getsamples_snapshots": sample_snapshots,
            "server_statistics": server_frozen,
            "getsamples_compute_statistics_equivalence": statistics_equivalence,
        }

        if source_id == "inarisk_capacity_2021":
            bbox, width, height = stage1.aligned_window(projected.bounds, source_meta)
            export_url = stage1.export_url(source_urls[source_id], bbox, width, height)
            final_url, content_type, body = stage1.request_bytes(export_url, retries=3, timeout=90.0)
            if not stage1.is_tiff(body):
                raise M26StatisticsProbeV3Error("capacity bridge export did not return TIFF")
            tiff_path = OUT_DIR / source_id / f"{pilot_feature['geography_id']}-capacity-bridge.tif"
            tiff_path.write_bytes(body)
            tiff_stats = v1.local_reference_stats(source_id, tiff_path, projected)
            bridge = compare_capacity_bridge(tiff_stats, sample_reference, contract)
            capacity_bridge_passed = bool(bridge["all_bridge_gates_passed"])
            result["capacity_tiff_reference"] = {
                "requested_url": export_url,
                "final_url": final_url,
                "content_type": content_type,
                "path": tiff_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_path(tiff_path),
                "bytes": len(body),
                "statistics": tiff_stats,
            }
            result["capacity_tiff_getsamples_bridge"] = bridge

        results[source_id] = result

    both_stats_passed = all(
        result["getsamples_compute_statistics_equivalence"]["all_equivalence_gates_passed"]
        for result in results.values()
    )
    qualified = capacity_bridge_passed and both_stats_passed
    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-statistics-transport-probe/v2",
        "milestone": 26,
        "stage": 1,
        "base_contract": {
            "path": v1.CONTRACT.relative_to(ROOT).as_posix(),
            "sha256": stage1.sha256_path(v1.CONTRACT),
        },
        "reference_amendment": {
            "path": AMENDMENT.relative_to(ROOT).as_posix(),
            "sha256": stage1.sha256_path(AMENDMENT),
        },
        "pilot_selection_rule": contract["pilot_selection"]["rule"],
        "pilot_geography_id": pilot_feature["geography_id"],
        "pilot_geography_name": pilot_feature["geography_name"],
        "pilot_capacity_aligned_window": {
            "bbox_native": list(capacity_bbox),
            "width": capacity_width,
            "height": capacity_height,
        },
        "big_expected_edition": big_probe.get("expected_edition"),
        "source_results": results,
        "capacity_tiff_getsamples_bridge_equivalent": capacity_bridge_passed,
        "both_sources_getsamples_compute_statistics_equivalent": both_stats_passed,
        "statistics_transport_qualified_for_stage1": qualified,
        "cross_geography_substantive_values_inspected": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT_MANIFEST.write_bytes(canonical_json_bytes(manifest))
    if not qualified:
        failures = {
            source_id: result["getsamples_compute_statistics_equivalence"]
            for source_id, result in results.items()
            if not result["getsamples_compute_statistics_equivalence"]["all_equivalence_gates_passed"]
        }
        raise M26StatisticsProbeV3Error(
            f"getSamples statistics transport qualification failed: bridge={capacity_bridge_passed} failures={failures}"
        )
    return manifest


def main() -> int:
    try:
        payload = run()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "pilot_geography_id": payload["pilot_geography_id"],
                "capacity_tiff_getsamples_bridge_equivalent": payload[
                    "capacity_tiff_getsamples_bridge_equivalent"
                ],
                "both_sources_getsamples_compute_statistics_equivalent": payload[
                    "both_sources_getsamples_compute_statistics_equivalent"
                ],
                "statistics_transport_qualified_for_stage1": payload[
                    "statistics_transport_qualified_for_stage1"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
