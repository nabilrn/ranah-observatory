#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from shapely.geometry import Polygon, mapping

from scripts import build_milestone26_population_stats_geometry as stats_geom
from scripts import probe_milestone26_population_mapserver_multipoint as map_multi
from scripts import probe_milestone26_population_mapserver_scale as map_scale
from scripts import probe_milestone26_population_stats_shape as shape_probe

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_empty_stats_semantics_contract.json"
SHAPE_DIAGNOSTIC = ROOT / "data/manifests/milestone26_population_stats_shape_diagnostic.json"
PARTITIONS = ROOT / "data/manifests/milestone26_population_stats_partitions.json"
MAP_IDENTITY = ROOT / "data/manifests/milestone26_population_mapserver_identity.json"
MAP_SEMANTICS = ROOT / "data/manifests/milestone26_population_mapserver_pixel_semantics_amendment.json"
MAP_SCALE = ROOT / "data/manifests/milestone26_population_mapserver_scale.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_empty_stats_semantics"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_empty_stats_semantics.json"


class M26PopulationEmptyStatsSemanticsError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-empty-stats-semantics-contract/v1":
        raise M26PopulationEmptyStatsSemanticsError("unexpected empty-stats semantics contract schema")
    if contract.get("locked_before_live_probe") is not True:
        raise M26PopulationEmptyStatsSemanticsError("empty-stats semantics contract is not locked")
    target = contract.get("target", {})
    if target.get("geography_id") != "idn.13.1377" or int(target.get("partition_index", 0)) != 1:
        raise M26PopulationEmptyStatsSemanticsError("empty-stats target drift")
    if int(target.get("selected_cell_count", 0)) != 1:
        raise M26PopulationEmptyStatsSemanticsError("empty-stats target must remain one native cell")
    if int(contract["image_server_repeat_probe"].get("repeat_count", 0)) != 3:
        raise M26PopulationEmptyStatsSemanticsError("ImageServer repeat count drift")
    if int(contract["mapserver_reference_probe"].get("repeat_count", 0)) != 3:
        raise M26PopulationEmptyStatsSemanticsError("MapServer repeat count drift")
    for key in (
        "numeric_aggregation_authorized",
        "cross_geography_component_values_materialized",
        "substantive_value_promotion_authorized",
        "stage1_population_production_extraction_authorized",
        "empty_statistics_global_semantics_authorized",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise M26PopulationEmptyStatsSemanticsError(f"invalid locked boundary: {key}")
    return contract


def load_frozen_inputs(contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    diagnostic = json.loads(SHAPE_DIAGNOSTIC.read_text(encoding="utf-8"))
    partitions = json.loads(PARTITIONS.read_text(encoding="utf-8"))
    identity = json.loads(MAP_IDENTITY.read_text(encoding="utf-8"))
    semantics = json.loads(MAP_SEMANTICS.read_text(encoding="utf-8"))
    scale = json.loads(MAP_SCALE.read_text(encoding="utf-8"))

    first = diagnostic.get("first_nonstandard")
    if diagnostic.get("schema") != "ranah-observatory/milestone26-population-stats-shape-diagnostic/v1" or not isinstance(first, dict):
        raise M26PopulationEmptyStatsSemanticsError("shape diagnostic missing or malformed")
    target = contract["target"]
    if (
        first.get("geography_id") != target["geography_id"]
        or int(first.get("partition_index", 0)) != int(target["partition_index"])
        or int(first.get("selected_cell_count", 0)) != int(target["selected_cell_count"])
        or first.get("classification") != contract["trigger"]["required_first_nonstandard_classification"]
        or first.get("raw_response_sha256") != contract["trigger"]["required_raw_response_sha256"]
    ):
        raise M26PopulationEmptyStatsSemanticsError("frozen shape anomaly drift")
    raw_path = ROOT / str(first["raw_response_path"])
    if raw_path.read_bytes() != b'{"statistics":[]}':
        raise M26PopulationEmptyStatsSemanticsError("frozen anomaly body is no longer exact empty statistics")
    if sha256_path(raw_path) != first["raw_response_sha256"]:
        raise M26PopulationEmptyStatsSemanticsError("frozen anomaly response checksum drift")

    if diagnostic.get("partition_manifest", {}).get("sha256") != sha256_path(PARTITIONS):
        raise M26PopulationEmptyStatsSemanticsError("partition manifest drift after frozen anomaly")
    if partitions.get("schema") != "ranah-observatory/milestone26-population-stats-partitions/v1":
        raise M26PopulationEmptyStatsSemanticsError("unexpected partition manifest schema")
    if identity.get("same_dataset_transport_candidate_qualified") is not True:
        raise M26PopulationEmptyStatsSemanticsError("MapServer same-dataset identity is not qualified")
    if semantics.get("semantic_binding", {}).get("accepted_field_name") != contract["mapserver_reference_probe"]["accepted_pixel_field"]:
        raise M26PopulationEmptyStatsSemanticsError("MapServer accepted-field semantic binding drift")
    if scale.get("production_batch_transport_qualified") is not True or int(scale.get("qualified_production_batch_size", 0)) != 64:
        raise M26PopulationEmptyStatsSemanticsError("MapServer batch transport is not frozen qualified")
    return diagnostic, partitions, identity, semantics, scale


def target_partition(partitions: dict[str, Any], contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    target = contract["target"]
    geography = next((row for row in partitions["geographies"] if row["geography_id"] == target["geography_id"]), None)
    if geography is None:
        raise M26PopulationEmptyStatsSemanticsError("target geography missing from frozen partitions")
    if geography.get("geography_name") != target["geography_name"] or geography.get("source_permendagri_code") != target["source_permendagri_code"]:
        raise M26PopulationEmptyStatsSemanticsError("target geography identity drift")
    partition = next((row for row in geography["partitions"] if int(row["partition_index"]) == int(target["partition_index"])), None)
    if partition is None:
        raise M26PopulationEmptyStatsSemanticsError("target partition missing")
    if int(partition["selected_cell_count"]) != 1:
        raise M26PopulationEmptyStatsSemanticsError("target partition is no longer exactly one selected cell")
    return geography, partition


def derive_exact_native_center(partition: dict[str, Any]) -> tuple[list[float], dict[str, Any]]:
    candidate = partition.get("candidate", {})
    arcgis = candidate.get("arcgis_geometry")
    if not isinstance(arcgis, dict) or arcgis.get("spatialReference", {}).get("wkid") != 3395:
        raise M26PopulationEmptyStatsSemanticsError("target candidate CRS drift")
    rings = arcgis.get("rings")
    if not isinstance(rings, list) or len(rings) != 1 or not isinstance(rings[0], list):
        raise M26PopulationEmptyStatsSemanticsError("one-cell diagnostic requires exactly one simple ArcGIS ring")
    polygon = Polygon(rings[0])
    if polygon.is_empty or not polygon.is_valid:
        raise M26PopulationEmptyStatsSemanticsError("target candidate polygon is invalid")

    bbox = tuple(float(value) for value in partition["bbox"])
    width = int(partition["window_width"])
    height = int(partition["window_height"])
    left, _bottom, _right, top = bbox
    mask = geometry_mask(
        [mapping(polygon)],
        out_shape=(height, width),
        transform=from_origin(left, top, 100.0, 100.0),
        invert=True,
        all_touched=False,
    )
    indices = np.argwhere(mask)
    if indices.shape != (1, 2):
        raise M26PopulationEmptyStatsSemanticsError(f"frozen candidate did not rerasterize to exactly one cell: {indices.shape}")
    row, col = (int(indices[0, 0]), int(indices[0, 1]))
    center = [left + (col + 0.5) * 100.0, top - (row + 0.5) * 100.0]
    return center, {
        "bbox": list(bbox),
        "window_width": width,
        "window_height": height,
        "selected_row": row,
        "selected_col": col,
        "rerasterized_selected_cell_count": 1,
        "candidate_geometry_sha256": candidate.get("geometry_sha256"),
    }


def freeze_response(prefix: str, repeat: int, response: dict[str, Any], body: bytes) -> dict[str, Any]:
    path = OUT_DIR / f"{prefix}-repeat-{repeat}.json"
    path.write_bytes(body)
    return {
        **response,
        "raw_path": path.relative_to(ROOT).as_posix(),
        "raw_bytes": len(body),
        "raw_sha256": hashlib.sha256(body).hexdigest(),
    }


def probe_image_server(contract: dict[str, Any], partition: dict[str, Any]) -> list[dict[str, Any]]:
    required_fields = {"count", "sum", "mean", "min", "max", "skipX", "skipY"}
    geometry = partition["candidate"]["arcgis_geometry"]
    url = stats_geom.stats_url(str(contract["image_server_repeat_probe"]["service"]), geometry)
    rows: list[dict[str, Any]] = []
    for repeat in range(1, int(contract["image_server_repeat_probe"]["repeat_count"]) + 1):
        response = map_multi.request_once(url, timeout=30.0)
        body = response.pop("body")
        if not isinstance(body, bytes):
            body = b""
        payload = map_multi.parse_json(body)
        classification = shape_probe.classify_payload(payload, required_fields)
        transport_ok = bool(
            response.get("status") == 200
            and response.get("exception_class") is None
            and isinstance(payload, dict)
            and not isinstance(payload.get("error"), dict)
        )
        frozen = freeze_response("image-server", repeat, response, body)
        rows.append({
            "repeat": repeat,
            "transport_ok": transport_ok,
            "arcgis_error_present": bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict)),
            "classification": classification["classification"],
            "statistics_length": classification["statistics_length"],
            "requested_url_length": len(url),
            "response": frozen,
        })
    return rows


def probe_mapserver(contract: dict[str, Any], center: list[float]) -> list[dict[str, Any]]:
    cfg = contract["mapserver_reference_probe"]
    field_name = str(cfg["accepted_pixel_field"])
    tolerance = float(cfg["result_geometry_tolerance_m"])
    url = map_scale.build_url(str(cfg["service"]), [center])
    rows: list[dict[str, Any]] = []
    for repeat in range(1, int(cfg["repeat_count"]) + 1):
        response = map_multi.request_once(url, timeout=30.0)
        body = response.pop("body")
        if not isinstance(body, bytes):
            body = b""
        payload = map_multi.parse_json(body)
        transport_ok = bool(
            response.get("status") == 200
            and response.get("exception_class") is None
            and isinstance(payload, dict)
            and not isinstance(payload.get("error"), dict)
        )
        raw_results = payload.get("results") if isinstance(payload, dict) and isinstance(payload.get("results"), list) else []
        parsed = [candidate for result in raw_results if isinstance(result, dict) and (candidate := map_multi.extract_pixel_result(result, field_name)) is not None]
        geometry_match = True
        for candidate in parsed:
            point = candidate.get("geometry")
            if not isinstance(point, list) or len(point) != 2:
                geometry_match = False
                break
            if abs(float(point[0]) - center[0]) > tolerance or abs(float(point[1]) - center[1]) > tolerance:
                geometry_match = False
                break
        frozen = freeze_response("mapserver", repeat, response, body)
        rows.append({
            "repeat": repeat,
            "transport_ok": transport_ok,
            "arcgis_error_present": bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict)),
            "raw_result_count": len(raw_results),
            "finite_accepted_pixel_value_count": len(parsed),
            "accepted_result_geometry_matches_exact_center": geometry_match,
            "requested_url_length": len(url),
            "response": frozen,
        })
    return rows


def decide(image_rows: list[dict[str, Any]], map_rows: list[dict[str, Any]]) -> str:
    if not all(row["transport_ok"] for row in image_rows + map_rows):
        return "inconclusive"
    image_classes = [str(row["classification"]) for row in image_rows]
    if any(value == "standard" for value in image_classes):
        return "transient_image_server_empty_statistics"
    if any(value != "empty_statistics" for value in image_classes):
        return "inconclusive"
    if not all(row["accepted_result_geometry_matches_exact_center"] for row in map_rows):
        return "inconclusive"
    map_valid_counts = [int(row["finite_accepted_pixel_value_count"]) for row in map_rows]
    if any(count > 0 for count in map_valid_counts):
        return "transport_disagreement"
    if all(count == 0 for count in map_valid_counts):
        return "deterministic_no_valid_source_value_for_exact_native_cell"
    return "inconclusive"


def run() -> dict[str, Any]:
    contract = load_contract()
    diagnostic, partitions, identity, semantics, scale = load_frozen_inputs(contract)
    geography, partition = target_partition(partitions, contract)
    center, center_evidence = derive_exact_native_center(partition)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image_rows = probe_image_server(contract, partition)
    map_rows = probe_mapserver(contract, center)
    decision = decide(image_rows, map_rows)

    manifest = {
        "schema": "ranah-observatory/milestone26-population-empty-stats-semantics/v1",
        "milestone": 26,
        "stage": "stage1_transport_semantics_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": sha256_path(CONTRACT)},
        "frozen_inputs": {
            "shape_diagnostic_sha256": sha256_path(SHAPE_DIAGNOSTIC),
            "partition_manifest_sha256": sha256_path(PARTITIONS),
            "mapserver_identity_sha256": sha256_path(MAP_IDENTITY),
            "mapserver_semantics_sha256": sha256_path(MAP_SEMANTICS),
            "mapserver_scale_sha256": sha256_path(MAP_SCALE),
        },
        "target": {
            "geography_id": geography["geography_id"],
            "geography_name": geography["geography_name"],
            "source_permendagri_code": geography["source_permendagri_code"],
            "partition_index": int(partition["partition_index"]),
            "selected_cell_count": int(partition["selected_cell_count"]),
            "native_center_epsg3395": center,
            "center_derivation": center_evidence,
        },
        "image_server_repeats": image_rows,
        "mapserver_repeats": map_rows,
        "decision": decision,
        "exact_cell_no_valid_source_value_qualified": decision == "deterministic_no_valid_source_value_for_exact_native_cell",
        "transient_empty_statistics_observed": decision == "transient_image_server_empty_statistics",
        "transport_disagreement_observed": decision == "transport_disagreement",
        "diagnostic_inconclusive": decision == "inconclusive",
        "empty_statistics_global_semantics_qualified": False,
        "other_empty_partitions_authorized_without_reference_confirmation": False,
        "numeric_aggregates_computed": False,
        "cross_geography_component_values_materialized": False,
        "substantive_values_promoted": False,
        "stage1_population_production_extraction_authorized": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "minimum_valid_fraction_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT_MANIFEST.write_bytes(canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    try:
        manifest = run()
    except (OSError, ValueError, KeyError, json.JSONDecodeError, M26PopulationEmptyStatsSemanticsError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "geography_id": manifest["target"]["geography_id"],
        "partition_index": manifest["target"]["partition_index"],
        "native_center_epsg3395": manifest["target"]["native_center_epsg3395"],
        "image_server_classes": [row["classification"] for row in manifest["image_server_repeats"]],
        "mapserver_valid_counts": [row["finite_accepted_pixel_value_count"] for row in manifest["mapserver_repeats"]],
        "decision": manifest["decision"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
