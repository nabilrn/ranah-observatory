#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from scripts import build_milestone26_population_stats_geometry as stats_geom
from scripts import materialize_milestone26_population_component as base
from scripts import probe_milestone26_population_mapserver_multipoint as map_multi
from scripts import probe_milestone26_population_mapserver_scale as map_scale
from scripts import probe_milestone26_population_stats_equivalence as equiv

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "data/manifests/milestone26_population_empty_stats_production_amendment.json"
SEMANTICS_ATTEMPT2 = ROOT / "data/manifests/milestone26_population_empty_stats_semantics_attempt2.json"
MAP_SCALE = ROOT / "data/manifests/milestone26_population_mapserver_scale.json"
MAP_SEMANTICS = ROOT / "data/manifests/milestone26_population_mapserver_pixel_semantics_amendment.json"

ORIGINAL_PARSE_FROZEN_STATS = base.parse_frozen_stats
TRANSPORT_LABEL = "ImageServer_computeStatisticsHistograms_with_MapServer_NoData_confirmation"


class M26PopulationProductionV2Error(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_amendment() -> dict[str, Any]:
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    if amendment.get("schema") != "ranah-observatory/milestone26-population-empty-stats-production-amendment/v1":
        raise M26PopulationProductionV2Error("unexpected empty-stats production amendment schema")
    if amendment.get("locked_before_restarting_cross_geography_numeric_extraction") is not True:
        raise M26PopulationProductionV2Error("empty-stats production amendment is not locked")
    if amendment.get("production_restart_authorized_under_this_amendment") is not True:
        raise M26PopulationProductionV2Error("production restart is not authorized by amendment")
    cfg = amendment["empty_partition_reference_confirmation"]
    if int(cfg.get("maximum_batch_size", 0)) != 64:
        raise M26PopulationProductionV2Error("MapServer fallback batch-size drift")
    if int(cfg.get("crs_epsg", 0)) != 3395:
        raise M26PopulationProductionV2Error("MapServer fallback CRS drift")
    if cfg.get("accepted_pixel_field") != "Stretch.Pixel Value":
        raise M26PopulationProductionV2Error("MapServer fallback accepted-field drift")
    if float(amendment["quality_gates_unchanged"].get("minimum_valid_fraction_inside_geography", -1)) != 0.99:
        raise M26PopulationProductionV2Error("valid-fraction gate changed")
    for key in (
        "empty_statistics_global_semantics_authorized_without_partition_reference",
        "substantive_interpretation_authorized",
        "cross_component_temporal_aggregation_authorized",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if amendment.get(key) is not False:
            raise M26PopulationProductionV2Error(f"invalid amendment boundary: {key}")
    contribution = amendment["qualified_empty_partition_contribution"]
    if int(contribution.get("valid_source_value_count", -1)) != 0 or float(contribution.get("additive_sum_contribution", -1)) != 0.0:
        raise M26PopulationProductionV2Error("empty valid-set contribution drift")
    if contribution.get("imputation") is not False or contribution.get("must_not_be_labeled_population_zero") is not True:
        raise M26PopulationProductionV2Error("empty valid-set semantics drift")
    return amendment


def verify_amendment_evidence(amendment: dict[str, Any]) -> None:
    semantics = json.loads(SEMANTICS_ATTEMPT2.read_text(encoding="utf-8"))
    required = amendment["trigger_evidence"]
    if semantics.get("schema") != "ranah-observatory/milestone26-population-empty-stats-semantics-attempt2/v1":
        raise M26PopulationProductionV2Error("unexpected exact-cell semantics evidence schema")
    if semantics.get("decision") != required["required_attempt2_decision"]:
        raise M26PopulationProductionV2Error("exact-cell semantics decision drift")
    if semantics.get("exact_cell_no_valid_source_value_qualified") is not bool(required["required_exact_cell_qualified"]):
        raise M26PopulationProductionV2Error("exact-cell NoData qualification drift")
    if semantics.get("empty_statistics_global_semantics_qualified") is not False:
        raise M26PopulationProductionV2Error("exact-cell evidence improperly generalized empty semantics")

    scale = json.loads(MAP_SCALE.read_text(encoding="utf-8"))
    map_semantics = json.loads(MAP_SEMANTICS.read_text(encoding="utf-8"))
    cfg = amendment["empty_partition_reference_confirmation"]
    if scale.get("production_batch_transport_qualified") is not True or int(scale.get("qualified_production_batch_size", 0)) != int(cfg["maximum_batch_size"]):
        raise M26PopulationProductionV2Error("MapServer batch transport is not qualified for fallback")
    if map_semantics.get("semantic_binding", {}).get("accepted_field_name") != cfg["accepted_pixel_field"]:
        raise M26PopulationProductionV2Error("MapServer pixel semantics drift")


def is_exact_empty_statistics(payload: Any) -> bool:
    return isinstance(payload, dict) and set(payload) == {"statistics"} and payload.get("statistics") == []


def selected_native_centers(
    geography: dict[str, Any], partition: dict[str, Any], feature: dict[str, Any], source_meta: dict[str, Any]
) -> list[list[float]]:
    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    projected = shapely_transform(transformer.transform, shape(feature["geometry"]))
    bbox, width, height = base.stage1.aligned_window(projected.bounds, source_meta)
    frozen_bbox = [float(value) for value in geography["aligned_window_bbox"]]
    if width != int(geography["aligned_window_width"]) or height != int(geography["aligned_window_height"]):
        raise M26PopulationProductionV2Error(f"aligned window shape drift: {geography['geography_id']}")
    if any(abs(float(a) - float(b)) > 1e-6 for a, b in zip(bbox, frozen_bbox)):
        raise M26PopulationProductionV2Error(f"aligned window bbox drift: {geography['geography_id']}")

    full_mask = stats_geom.mask_for_geometry(projected, bbox, width, height)
    row0, row1 = int(partition["row0"]), int(partition["row1"])
    col0, col1 = int(partition["col0"]), int(partition["col1"])
    submask = full_mask[row0:row1, col0:col1]
    indices = np.argwhere(submask)
    expected = int(partition["selected_cell_count"])
    if len(indices) != expected:
        raise M26PopulationProductionV2Error(
            f"fallback exact-center count drift: {geography['geography_id']}/{partition['partition_index']} {len(indices)} != {expected}"
        )
    left, _bottom, _right, top = (float(value) for value in partition["bbox"])
    return [
        [left + (int(col) + 0.5) * 100.0, top - (int(row) + 0.5) * 100.0]
        for row, col in indices
    ]


def raw_geometry(result: dict[str, Any]) -> list[float] | None:
    geometry = result.get("geometry")
    if not isinstance(geometry, dict):
        return None
    x = map_multi.finite_number(geometry.get("x"))
    y = map_multi.finite_number(geometry.get("y"))
    if x is None or y is None:
        return None
    return [x, y]


def validate_nodata_batch(
    requested: list[list[float]], payload: dict[str, Any], *, field_name: str, tolerance: float
) -> dict[str, Any]:
    raw_results = payload.get("results") if isinstance(payload.get("results"), list) else []
    layer_results = [row for row in raw_results if isinstance(row, dict) and row.get("layerId") == 0]
    if len(raw_results) != len(layer_results) or len(layer_results) != len(requested):
        raise M26PopulationProductionV2Error(
            f"MapServer fallback raw-result count mismatch: raw={len(raw_results)} layer0={len(layer_results)} requested={len(requested)}"
        )

    unmatched = list(range(len(requested)))
    finite_values: list[float] = []
    nonfinite_field_values: list[str] = []
    for result in layer_results:
        point = raw_geometry(result)
        if point is None:
            raise M26PopulationProductionV2Error("MapServer fallback result missing finite point geometry")
        matched: int | None = None
        for index in unmatched:
            source = requested[index]
            if abs(float(source[0]) - point[0]) <= tolerance and abs(float(source[1]) - point[1]) <= tolerance:
                matched = index
                break
        if matched is None:
            raise M26PopulationProductionV2Error("MapServer fallback result geometry does not map to requested native center")
        unmatched.remove(matched)

        attributes = result.get("attributes")
        if not isinstance(attributes, dict) or field_name not in attributes:
            raise M26PopulationProductionV2Error("MapServer fallback result missing accepted pixel field")
        raw_value = attributes[field_name]
        finite = map_multi.finite_number(raw_value)
        if finite is not None:
            finite_values.append(finite)
        else:
            nonfinite_field_values.append(str(raw_value))

    if unmatched:
        raise M26PopulationProductionV2Error("MapServer fallback did not return one raw result for every requested center")
    if finite_values:
        raise M26PopulationProductionV2Error(
            f"transport disagreement: empty ImageServer statistics but MapServer returned {len(finite_values)} finite pixel values"
        )
    return {
        "requested_center_count": len(requested),
        "raw_result_count": len(raw_results),
        "finite_accepted_pixel_value_count": 0,
        "nonfinite_accepted_field_value_count": len(nonfinite_field_values),
        "all_result_geometries_one_to_one": True,
        "all_requested_centers_explicit_nonfinite": len(nonfinite_field_values) == len(requested),
        "nonfinite_value_labels": sorted(set(nonfinite_field_values)),
    }


def confirm_empty_partition(
    amendment: dict[str, Any], gid: str, partition_index: int, centers: list[list[float]]
) -> tuple[list[dict[str, Any]], int]:
    cfg = amendment["empty_partition_reference_confirmation"]
    service = str(cfg["mapserver_service"])
    field_name = str(cfg["accepted_pixel_field"])
    tolerance = float(cfg["result_geometry_tolerance_m"])
    batch_size = int(cfg["maximum_batch_size"])
    records: list[dict[str, Any]] = []
    total_bytes = 0

    for batch_index, start in enumerate(range(0, len(centers), batch_size), start=1):
        batch = centers[start : start + batch_size]
        url = map_scale.build_url(service, batch)
        response, payload, attempts_used = equiv.request_json_with_retries(url, timeout=30.0, attempts=3)
        body = response.get("body")
        if not isinstance(body, bytes):
            raise M26PopulationProductionV2Error("MapServer fallback response body is not bytes")
        validation = validate_nodata_batch(batch, payload, field_name=field_name, tolerance=tolerance)
        path = base.RAW_ROOT / gid / f"partition-{partition_index:04d}-mapserver-nodata-batch-{batch_index:04d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        total_bytes += len(body)
        records.append({
            "batch_index": batch_index,
            "requested_center_count": len(batch),
            "requested_url": url,
            "requested_url_length": len(url),
            "status": int(response["status"]),
            "content_type": str(response.get("content_type", "")),
            "attempts_used": attempts_used,
            "raw_path": path.relative_to(ROOT).as_posix(),
            "raw_sha256": hashlib.sha256(body).hexdigest(),
            "raw_bytes": len(body),
            "validation": validation,
        })
    if sum(int(row["requested_center_count"]) for row in records) != len(centers):
        raise M26PopulationProductionV2Error("MapServer fallback batch coverage mismatch")
    return records, total_bytes


def fetch_all_partitions_v2(contract: dict[str, Any], partitions: dict[str, Any]) -> None:
    amendment = load_amendment()
    verify_amendment_evidence(amendment)
    service = str(contract["source_transport"]["service"])
    url_gate = int(contract["partition_contract"]["maximum_encoded_get_url_length"])
    source_meta = base.stage1.source_metadata("inarisk_population_2020")
    features, _big_probe = base.stage1.load_qualified_big_features()
    feature_map = {str(row["geography_id"]): row for row in features}
    if len(feature_map) != 19:
        raise M26PopulationProductionV2Error("qualified BIG feature map is not exact 19")

    index_rows: list[dict[str, Any]] = []
    empty_partition_ids: list[str] = []
    fallback_response_count = 0
    fallback_total_bytes = 0
    base.RAW_ROOT.mkdir(parents=True, exist_ok=True)

    required = set(contract["source_transport"]["required_statistics_fields"])
    for geography in sorted(partitions["geographies"], key=lambda row: row["geography_id"]):
        gid = str(geography["geography_id"])
        feature = feature_map.get(gid)
        if feature is None:
            raise M26PopulationProductionV2Error(f"BIG feature missing for fallback-capable extraction: {gid}")
        for partition in sorted(geography["partitions"], key=lambda row: int(row["partition_index"])):
            partition_index = int(partition["partition_index"])
            selected_count = int(partition["selected_cell_count"])
            geometry = partition["candidate"]["arcgis_geometry"]
            url = stats_geom.stats_url(service, geometry)
            if len(url) > url_gate:
                raise M26PopulationProductionV2Error(f"partition URL exceeds locked gate: {gid}/{partition_index}")
            response, payload, attempts_used = equiv.request_json_with_retries(url, timeout=30.0, attempts=3)
            body = response.get("body")
            if not isinstance(body, bytes):
                raise M26PopulationProductionV2Error("statistics response body is not bytes")
            path = base.raw_path(gid, partition_index)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)

            row: dict[str, Any] = {
                "geography_id": gid,
                "partition_index": partition_index,
                "selected_cell_count": selected_count,
                "requested_url": url,
                "requested_url_length": len(url),
                "status": int(response["status"]),
                "content_type": str(response.get("content_type", "")),
                "attempts_used": attempts_used,
                "raw_path": path.relative_to(ROOT).as_posix(),
                "raw_sha256": hashlib.sha256(body).hexdigest(),
                "raw_bytes": len(body),
                "empty_statistics": False,
                "empty_statistics_reference_confirmed": False,
                "mapserver_fallback_responses": [],
            }

            if is_exact_empty_statistics(payload):
                centers = selected_native_centers(geography, partition, feature, source_meta)
                fallback, fallback_bytes = confirm_empty_partition(amendment, gid, partition_index, centers)
                row["empty_statistics"] = True
                row["empty_statistics_reference_confirmed"] = True
                row["mapserver_fallback_responses"] = fallback
                row["mapserver_fallback_response_count"] = len(fallback)
                row["mapserver_fallback_requested_center_count"] = len(centers)
                empty_partition_ids.append(f"{gid}/partition-{partition_index:04d}")
                fallback_response_count += len(fallback)
                fallback_total_bytes += fallback_bytes
            else:
                if not isinstance(payload, dict) or isinstance(payload.get("error"), dict):
                    raise M26PopulationProductionV2Error(f"nonstandard statistics payload: {gid}/{partition_index}")
                equiv.parse_statistics(payload, required)
            index_rows.append(row)

    expected = int(contract["partition_contract"]["partition_count_expected"])
    if len(index_rows) != expected:
        raise M26PopulationProductionV2Error(f"retrieval index count mismatch: {len(index_rows)} != {expected}")
    base.RETRIEVAL_INDEX.write_bytes(base.canonical_json_bytes({
        "schema": "ranah-observatory/milestone26-population-retrieval-index/v1",
        "source_id": contract["source_id"],
        "response_count": len(index_rows),
        "responses": index_rows,
        "production_amendment": {"path": AMENDMENT.relative_to(ROOT).as_posix(), "sha256": sha256_path(AMENDMENT)},
        "empty_statistics_partition_count": len(empty_partition_ids),
        "empty_statistics_partition_ids": empty_partition_ids,
        "mapserver_fallback_response_count": fallback_response_count,
        "mapserver_fallback_total_bytes": fallback_total_bytes,
    }))


def verify_fallback_records(retrieval_row: dict[str, Any]) -> None:
    fallback = retrieval_row.get("mapserver_fallback_responses")
    if not isinstance(fallback, list) or not fallback:
        raise M26PopulationProductionV2Error("empty statistics partition lacks frozen MapServer reference responses")
    requested_total = 0
    for record in fallback:
        path = ROOT / str(record["raw_path"])
        if not path.exists():
            raise M26PopulationProductionV2Error(f"missing MapServer fallback raw evidence: {path}")
        body = path.read_bytes()
        if hashlib.sha256(body).hexdigest() != record["raw_sha256"] or len(body) != int(record["raw_bytes"]):
            raise M26PopulationProductionV2Error(f"MapServer fallback raw evidence drift: {path}")
        validation = record.get("validation", {})
        requested = int(record["requested_center_count"])
        if validation.get("all_result_geometries_one_to_one") is not True:
            raise M26PopulationProductionV2Error("fallback geometry qualification missing")
        if validation.get("all_requested_centers_explicit_nonfinite") is not True:
            raise M26PopulationProductionV2Error("fallback did not explicitly qualify every requested center as nonfinite")
        if int(validation.get("finite_accepted_pixel_value_count", -1)) != 0:
            raise M26PopulationProductionV2Error("fallback contains finite accepted pixel value")
        if int(validation.get("raw_result_count", -1)) != requested:
            raise M26PopulationProductionV2Error("fallback raw-result count no longer matches requested centers")
        requested_total += requested
    if requested_total != int(retrieval_row.get("selected_cell_count", -1)):
        raise M26PopulationProductionV2Error("fallback reference did not exhaust the exact selected centers")


def parse_frozen_stats_v2(
    contract: dict[str, Any], retrieval_row: dict[str, Any], selected_cell_count: int
) -> dict[str, Any]:
    path = ROOT / str(retrieval_row["raw_path"])
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise M26PopulationProductionV2Error(f"frozen statistics response is not JSON: {path}") from exc
    if is_exact_empty_statistics(payload):
        if retrieval_row.get("empty_statistics") is not True or retrieval_row.get("empty_statistics_reference_confirmed") is not True:
            raise M26PopulationProductionV2Error("empty statistics partition is not reference-confirmed")
        if int(retrieval_row.get("selected_cell_count", -1)) != selected_cell_count:
            raise M26PopulationProductionV2Error("empty statistics selected-cell count drift")
        verify_fallback_records(retrieval_row)
        return {
            "count": 0,
            "sum": 0.0,
            "empty_valid_value_set": True,
            "imputed": False,
        }
    if retrieval_row.get("empty_statistics") is True:
        raise M26PopulationProductionV2Error("retrieval index labels a nonempty statistics response as empty")
    return ORIGINAL_PARSE_FROZEN_STATS(contract, retrieval_row, selected_cell_count)


def rewrite_transport_csv(path: Path, fieldnames: list[str], transport_label: str) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["transport"] = transport_label
    path.write_bytes(base.csv_bytes(fieldnames, rows))


def augment_outputs(manifest: dict[str, Any]) -> dict[str, Any]:
    retrieval = json.loads(base.RETRIEVAL_INDEX.read_text(encoding="utf-8"))
    empty_count = int(retrieval.get("empty_statistics_partition_count", 0))
    fallback_count = int(retrieval.get("mapserver_fallback_response_count", 0))
    fallback_bytes = int(retrieval.get("mapserver_fallback_total_bytes", 0))
    if empty_count <= 0:
        raise M26PopulationProductionV2Error("fallback-enabled production found no empty partition despite frozen trigger evidence")
    if fallback_count <= 0:
        raise M26PopulationProductionV2Error("empty partitions exist but no MapServer reference evidence was frozen")
    for row in retrieval["responses"]:
        if row.get("empty_statistics") is True:
            verify_fallback_records(row)

    rewrite_transport_csv(base.FRAME, base.FRAME_FIELDS, TRANSPORT_LABEL)
    rewrite_transport_csv(base.PROVENANCE, base.PROVENANCE_FIELDS, TRANSPORT_LABEL)
    manifest["transport"] = TRANSPORT_LABEL
    manifest["production_amendment"] = {"path": AMENDMENT.relative_to(ROOT).as_posix(), "sha256": sha256_path(AMENDMENT)}
    manifest["empty_stats_semantics_evidence"] = {
        "path": SEMANTICS_ATTEMPT2.relative_to(ROOT).as_posix(),
        "sha256": sha256_path(SEMANTICS_ATTEMPT2),
    }
    manifest["empty_statistics_partition_count"] = empty_count
    manifest["empty_statistics_partition_ids"] = retrieval["empty_statistics_partition_ids"]
    manifest["mapserver_nodata_confirmation_response_count"] = fallback_count
    manifest["mapserver_nodata_confirmation_total_bytes"] = fallback_bytes
    manifest["empty_statistics_partitions_all_reference_confirmed"] = True
    manifest["qualified_empty_partition_contribution_semantics"] = "empty_valid_value_set_additive_identity"
    manifest["empty_statistics_treated_as_population_zero"] = False
    manifest["empty_statistics_imputed"] = False
    manifest["raw_evidence_response_count"] = int(manifest["raw_response_count"]) + fallback_count
    manifest["raw_evidence_total_bytes"] = int(manifest["raw_response_total_bytes"]) + fallback_bytes
    manifest["outputs"]["component_frame_sha256"] = base.sha256_path(base.FRAME)
    manifest["outputs"]["provenance_frame_sha256"] = base.sha256_path(base.PROVENANCE)
    base.MANIFEST.write_bytes(base.canonical_json_bytes(manifest))
    return manifest


def install_amendment_transport() -> None:
    base.fetch_all_partitions = fetch_all_partitions_v2
    base.parse_frozen_stats = parse_frozen_stats_v2


def build(fetch_live: bool) -> dict[str, Any]:
    amendment = load_amendment()
    verify_amendment_evidence(amendment)
    install_amendment_transport()
    manifest = base.build(fetch_live=fetch_live)
    return augment_outputs(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build(fetch_live=args.fetch)
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "geography_count": manifest["geography_count"],
        "partition_count": manifest["partition_count"],
        "empty_statistics_partition_count": manifest["empty_statistics_partition_count"],
        "mapserver_nodata_confirmation_response_count": manifest["mapserver_nodata_confirmation_response_count"],
        "all_geographies_valid_fraction_pass": manifest["all_geographies_valid_fraction_pass"],
        "population_component_materialized": manifest["population_component_materialized"],
        "risk_synthesis_authorized": manifest["risk_synthesis_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
