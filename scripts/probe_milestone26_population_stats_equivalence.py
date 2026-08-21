#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from scripts import build_milestone26_population_stats_geometry as stats_geom
from scripts import materialize_milestone26_stage1_components as stage1
from scripts import probe_milestone26_population_mapserver_multipoint as map_multi
from scripts import probe_milestone26_population_mapserver_scale as map_scale

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_stats_equivalence_contract.json"
PARTITIONS = ROOT / "data/manifests/milestone26_population_stats_partitions.json"
MAP_IDENTITY = ROOT / "data/manifests/milestone26_population_mapserver_identity.json"
MAP_SEMANTICS = ROOT / "data/manifests/milestone26_population_mapserver_pixel_semantics_amendment.json"
MAP_SCALE = ROOT / "data/manifests/milestone26_population_mapserver_scale.json"
IMAGE_EVIDENCE = ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_population_2020.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_stats_equivalence"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_stats_equivalence.json"


class M26PopulationStatsEquivalenceError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-stats-equivalence-contract/v1":
        raise M26PopulationStatsEquivalenceError("unexpected stats-equivalence contract schema")
    if contract.get("locked_before_live_equivalence_probe") is not True:
        raise M26PopulationStatsEquivalenceError("stats-equivalence contract is not locked")
    if contract.get("pilot_numeric_transport_validation_authorized") is not True:
        raise M26PopulationStatsEquivalenceError("pilot numeric transport validation is not authorized")
    if contract["pilot"].get("geography_id") != "idn.13.1374":
        raise M26PopulationStatsEquivalenceError("pilot geography drift")
    if contract["pilot"].get("inside_native_cell_count_expected") != 2354:
        raise M26PopulationStatsEquivalenceError("pilot cell-count drift")
    for key in (
        "stage1_population_production_extraction_authorized",
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
            raise M26PopulationStatsEquivalenceError(f"invalid locked boundary: {key}")
    return contract


def request_json_with_retries(url: str, *, timeout: float = 30.0, attempts: int = 3) -> tuple[dict[str, Any], dict[str, Any], int]:
    last: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        response = map_multi.request_once(url, timeout=timeout)
        body = response.get("body", b"")
        payload = map_multi.parse_json(body) if isinstance(body, bytes) else None
        arcgis_error = bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict))
        success = bool(response.get("status") == 200 and response.get("exception_class") is None and isinstance(payload, dict) and not arcgis_error)
        response["arcgis_error_present"] = arcgis_error
        if success:
            return response, payload, attempt
        last = response
        if attempt < attempts:
            time.sleep(float(2 ** (attempt - 1)))
    raise M26PopulationStatsEquivalenceError(
        f"request failed after {attempts} attempts: {url} status={None if last is None else last.get('status')} exception={None if last is None else last.get('exception_class')}"
    )


def pilot_native_centers() -> tuple[list[list[float]], dict[str, Any]]:
    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    meta = stage1.source_metadata("inarisk_population_2020")
    features, big_probe = stage1.load_qualified_big_features()
    feature = next((row for row in features if row["geography_id"] == "idn.13.1374"), None)
    if feature is None:
        raise M26PopulationStatsEquivalenceError("Padang Panjang missing from qualified BIG frame")
    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    projected = shapely_transform(transformer.transform, shape(feature["geometry"]))
    bbox, width, height = stage1.aligned_window(projected.bounds, meta)
    inside = stats_geom.mask_for_geometry(projected, bbox, width, height)
    indices = np.argwhere(inside)
    left, _bottom, _right, top = bbox
    points = [
        [left + (int(col) + 0.5) * 100.0, top - (int(row) + 0.5) * 100.0]
        for row, col in indices
    ]
    return points, {
        "geography_id": feature["geography_id"],
        "geography_name": feature["geography_name"],
        "bbox_native": list(bbox),
        "width": width,
        "height": height,
        "big_expected_edition": big_probe.get("expected_edition"),
    }


def coordinate_key(point: list[float]) -> str:
    return f"{float(point[0]):.6f},{float(point[1]):.6f}"


def associate_partial_results(
    requested: list[list[float]], parsed_results: list[dict[str, Any]], tolerance: float
) -> dict[str, float]:
    requested_keys = {coordinate_key(point): point for point in requested}
    mapping: dict[str, float] = {}
    for result in parsed_results:
        geometry = result.get("geometry")
        if not isinstance(geometry, list) or len(geometry) != 2:
            raise M26PopulationStatsEquivalenceError("MapServer result missing point geometry")
        matched_key: str | None = None
        for key, source in requested_keys.items():
            if abs(float(source[0]) - float(geometry[0])) <= tolerance and abs(float(source[1]) - float(geometry[1])) <= tolerance:
                matched_key = key
                break
        if matched_key is None:
            raise M26PopulationStatsEquivalenceError("MapServer returned geometry outside requested native centers")
        if matched_key in mapping:
            raise M26PopulationStatsEquivalenceError("MapServer returned duplicate geometry")
        mapping[matched_key] = float(result["value"])
    return mapping


def freeze_response(name: str, response: dict[str, Any], attempts_used: int) -> dict[str, Any]:
    body = response.pop("body")
    if not isinstance(body, bytes):
        raise M26PopulationStatsEquivalenceError("response body is not bytes")
    path = OUT_DIR / f"{name}.json"
    path.write_bytes(body)
    return {
        **response,
        "attempts_used": attempts_used,
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def reference_mapserver(contract: dict[str, Any], points: list[list[float]], declared_min: float, declared_max: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    batch_size = int(contract["pilot"]["mapserver_reference_batch_size"])
    mapserver = str(contract["reference_transport"]["service"])
    field_name = str(contract["reference_transport"]["accepted_pixel_field"])
    tolerance = float(contract["reference_transport"]["result_geometry_tolerance_m"])
    all_values: dict[str, float] = {}
    responses: list[dict[str, Any]] = []

    for batch_index, start in enumerate(range(0, len(points), batch_size), start=1):
        batch = points[start : start + batch_size]
        url = map_scale.build_url(mapserver, batch)
        response, payload, attempts_used = request_json_with_retries(url)
        raw_results = payload.get("results") if isinstance(payload.get("results"), list) else []
        parsed_results: list[dict[str, Any]] = []
        for row in raw_results:
            if not isinstance(row, dict):
                raise M26PopulationStatsEquivalenceError("MapServer result is not an object")
            parsed = map_multi.extract_pixel_result(row, field_name)
            if parsed is None:
                continue
            value = float(parsed["value"])
            if not (declared_min <= value <= declared_max):
                raise M26PopulationStatsEquivalenceError("MapServer pixel outside frozen ImageServer range")
            parsed_results.append(parsed)
        batch_mapping = associate_partial_results(batch, parsed_results, tolerance)
        overlap = set(all_values).intersection(batch_mapping)
        if overlap:
            raise M26PopulationStatsEquivalenceError("reference batches overlap in native-center keys")
        all_values.update(batch_mapping)
        frozen = freeze_response(f"mapserver-batch-{batch_index:02d}", response, attempts_used)
        frozen.update(
            {
                "batch_index": batch_index,
                "requested_point_count": len(batch),
                "raw_result_count": len(raw_results),
                "valid_mapped_result_count": len(batch_mapping),
                "requested_url_length": len(url),
            }
        )
        responses.append(frozen)

    values = list(all_values.values())
    if not values:
        raise M26PopulationStatsEquivalenceError("MapServer reference produced no valid pixel values")
    valid_count = len(values)
    valid_fraction = valid_count / len(points)
    reference = {
        "input_cell_count": len(points),
        "batch_size": batch_size,
        "batch_count": len(responses),
        "valid_count": valid_count,
        "missing_count": len(points) - valid_count,
        "valid_fraction": valid_fraction,
        "sum": math.fsum(values),
        "mean": math.fsum(values) / valid_count,
        "min": min(values),
        "max": max(values),
        "all_returned_points_mapped_one_to_one": True,
    }
    return reference, responses


def parse_statistics(payload: dict[str, Any], required_fields: set[str]) -> dict[str, Any]:
    statistics = payload.get("statistics")
    if not isinstance(statistics, list) or len(statistics) != 1 or not isinstance(statistics[0], dict):
        raise M26PopulationStatsEquivalenceError("unexpected computeStatisticsHistograms statistics shape")
    row = statistics[0]
    missing = sorted(required_fields - set(row))
    if missing:
        raise M26PopulationStatsEquivalenceError(f"computeStatisticsHistograms missing fields: {missing}")
    parsed = {
        "count": int(row["count"]),
        "sum": float(row["sum"]),
        "mean": float(row["mean"]),
        "min": float(row["min"]),
        "max": float(row["max"]),
        "skipX": int(row["skipX"]),
        "skipY": int(row["skipY"]),
    }
    if not all(math.isfinite(float(parsed[key])) for key in ("sum", "mean", "min", "max")):
        raise M26PopulationStatsEquivalenceError("non-finite server statistics")
    return parsed


def candidate_statistics(
    contract: dict[str, Any], partitions_manifest: dict[str, Any], declared_min: float, declared_max: float
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    geography = next(
        (row for row in partitions_manifest["geographies"] if row["geography_id"] == contract["pilot"]["geography_id"]),
        None,
    )
    if geography is None:
        raise M26PopulationStatsEquivalenceError("pilot missing from partition manifest")
    partitions = geography["partitions"]
    if len(partitions) != int(contract["pilot"]["image_server_partition_count_expected"]):
        raise M26PopulationStatsEquivalenceError("pilot partition count drift")
    required = set(contract["candidate_transport"]["required_statistics_fields"])
    service = str(contract["candidate_transport"]["service"])
    responses: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []

    for part in partitions:
        geometry = part["candidate"]["arcgis_geometry"]
        url = stats_geom.stats_url(service, geometry)
        if len(url) > 6000:
            raise M26PopulationStatsEquivalenceError("frozen partition exceeded URI gate")
        response, payload, attempts_used = request_json_with_retries(url)
        stats = parse_statistics(payload, required)
        if stats["skipX"] != int(contract["candidate_transport"]["skipX_required"]) or stats["skipY"] != int(contract["candidate_transport"]["skipY_required"]):
            raise M26PopulationStatsEquivalenceError("computeStatisticsHistograms skipX/skipY drift")
        if stats["min"] < declared_min - 1e-12 or stats["max"] > declared_max + 1e-12:
            raise M26PopulationStatsEquivalenceError("computeStatisticsHistograms range outside frozen source range")
        frozen = freeze_response(f"stats-partition-{int(part['partition_index']):02d}", response, attempts_used)
        frozen.update(
            {
                "partition_index": int(part["partition_index"]),
                "selected_cell_count": int(part["selected_cell_count"]),
                "requested_url_length": len(url),
                "statistics": stats,
            }
        )
        responses.append(frozen)
        parsed_rows.append(stats)

    total_count = sum(row["count"] for row in parsed_rows)
    total_sum = math.fsum(row["sum"] for row in parsed_rows)
    combined = {
        "partition_count": len(parsed_rows),
        "count": total_count,
        "sum": total_sum,
        "mean": total_sum / total_count if total_count else math.nan,
        "min": min(row["min"] for row in parsed_rows),
        "max": max(row["max"] for row in parsed_rows),
        "all_partition_skip_gates_passed": True,
        "all_partition_range_gates_passed": True,
    }
    return combined, responses


def compare(contract: dict[str, Any], reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    tolerances = contract["equivalence_tolerances"]
    valid_count = int(reference["valid_count"])
    sum_abs_tolerance = valid_count * float(tolerances["per_cell_absolute_quantization_bound"]) + 1e-9
    sum_match = math.isclose(
        float(candidate["sum"]),
        float(reference["sum"]),
        rel_tol=float(tolerances["sum_relative_tolerance"]),
        abs_tol=sum_abs_tolerance,
    )
    mean_match = math.isclose(
        float(candidate["mean"]),
        float(reference["mean"]),
        rel_tol=float(tolerances["mean_relative_tolerance"]),
        abs_tol=float(tolerances["mean_absolute_tolerance"]),
    )
    range_tolerance = float(tolerances["min_max_absolute_tolerance"])
    min_match = math.isclose(float(candidate["min"]), float(reference["min"]), rel_tol=0.0, abs_tol=range_tolerance)
    max_match = math.isclose(float(candidate["max"]), float(reference["max"]), rel_tol=0.0, abs_tol=range_tolerance)
    count_match = int(candidate["count"]) == valid_count
    reference_coverage = float(reference["valid_fraction"]) >= float(contract["reference_transport"]["minimum_valid_fraction"])
    gates = {
        "reference_expected_input_count_match": int(reference["input_cell_count"]) == int(contract["pilot"]["inside_native_cell_count_expected"]),
        "reference_expected_batch_count_match": int(reference["batch_count"]) == int(contract["pilot"]["mapserver_reference_request_count_expected"]),
        "reference_all_returned_points_mapped_one_to_one": reference["all_returned_points_mapped_one_to_one"] is True,
        "reference_valid_fraction_gate": reference_coverage,
        "candidate_partition_count_match": int(candidate["partition_count"]) == int(contract["pilot"]["image_server_partition_count_expected"]),
        "candidate_all_partition_skip_gates_passed": candidate["all_partition_skip_gates_passed"] is True,
        "candidate_all_partition_range_gates_passed": candidate["all_partition_range_gates_passed"] is True,
        "combined_count_match": count_match,
        "combined_sum_match": sum_match,
        "combined_mean_match": mean_match,
        "combined_min_match": min_match,
        "combined_max_match": max_match,
    }
    return {
        **gates,
        "all_equivalence_gates_passed": all(gates.values()),
        "sum_absolute_tolerance": sum_abs_tolerance,
        "sum_absolute_difference": abs(float(candidate["sum"]) - float(reference["sum"])),
        "mean_absolute_difference": abs(float(candidate["mean"]) - float(reference["mean"])),
        "min_absolute_difference": abs(float(candidate["min"]) - float(reference["min"])),
        "max_absolute_difference": abs(float(candidate["max"]) - float(reference["max"])),
    }


def run() -> dict[str, Any]:
    contract = load_contract()
    partitions_manifest = json.loads(PARTITIONS.read_text(encoding="utf-8"))
    map_identity = json.loads(MAP_IDENTITY.read_text(encoding="utf-8"))
    map_semantics = json.loads(MAP_SEMANTICS.read_text(encoding="utf-8"))
    map_scale = json.loads(MAP_SCALE.read_text(encoding="utf-8"))
    image = json.loads(IMAGE_EVIDENCE.read_text(encoding="utf-8"))

    if map_identity.get("same_dataset_transport_candidate_qualified") is not True:
        raise M26PopulationStatsEquivalenceError("MapServer identity gate is not frozen qualified")
    if map_semantics.get("semantic_binding", {}).get("accepted_field_name") != contract["reference_transport"]["accepted_pixel_field"]:
        raise M26PopulationStatsEquivalenceError("MapServer pixel semantic binding drift")
    if map_scale.get("production_batch_transport_qualified") is not True or map_scale.get("qualified_production_batch_size") != 64:
        raise M26PopulationStatsEquivalenceError("MapServer batch-64 transport is not frozen qualified")
    if partitions_manifest.get("all_partition_cell_counts_exact") is not True or partitions_manifest.get("all_partition_urls_within_gate") is not True:
        raise M26PopulationStatsEquivalenceError("stats partitions are not frozen exact/URI-safe")

    image_meta = image["primary"]
    declared_min = float(image_meta["minValues"][0])
    declared_max = float(image_meta["maxValues"][0])
    points, pilot_frame = pilot_native_centers()
    if len(points) != int(contract["pilot"]["inside_native_cell_count_expected"]):
        raise M26PopulationStatsEquivalenceError(f"pilot native cell count mismatch: {len(points)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reference, map_responses = reference_mapserver(contract, points, declared_min, declared_max)
    candidate, stats_responses = candidate_statistics(contract, partitions_manifest, declared_min, declared_max)
    equivalence = compare(contract, reference, candidate)

    manifest = {
        "schema": "ranah-observatory/milestone26-population-stats-equivalence/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": sha256_path(CONTRACT)},
        "frozen_inputs": {
            "stats_partitions_sha256": sha256_path(PARTITIONS),
            "mapserver_identity_sha256": sha256_path(MAP_IDENTITY),
            "mapserver_pixel_semantics_sha256": sha256_path(MAP_SEMANTICS),
            "mapserver_scale_sha256": sha256_path(MAP_SCALE),
            "image_server_metadata_sha256": sha256_path(IMAGE_EVIDENCE),
        },
        "pilot": pilot_frame,
        "reference_mapserver": reference,
        "candidate_image_server_statistics": candidate,
        "mapserver_response_count": len(map_responses),
        "stats_response_count": len(stats_responses),
        "mapserver_responses": map_responses,
        "stats_responses": stats_responses,
        "equivalence": equivalence,
        "statistics_transport_equivalent_on_complete_pilot": equivalence["all_equivalence_gates_passed"],
        "population_stats_production_transport_candidate_qualified": equivalence["all_equivalence_gates_passed"],
        "cross_geography_substantive_values_inspected": False,
        "stage1_population_production_extraction_authorized": False,
        "substantive_value_promotion_performed": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT_MANIFEST.write_bytes(canonical_json_bytes(manifest))
    if not equivalence["all_equivalence_gates_passed"]:
        raise M26PopulationStatsEquivalenceError(f"population stats equivalence failed: {equivalence}")
    return manifest


def main() -> int:
    try:
        manifest = run()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "pilot_geography_id": manifest["pilot"]["geography_id"],
        "reference_input_cell_count": manifest["reference_mapserver"]["input_cell_count"],
        "reference_valid_count": manifest["reference_mapserver"]["valid_count"],
        "mapserver_response_count": manifest["mapserver_response_count"],
        "stats_response_count": manifest["stats_response_count"],
        "statistics_transport_equivalent_on_complete_pilot": manifest["statistics_transport_equivalent_on_complete_pilot"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
