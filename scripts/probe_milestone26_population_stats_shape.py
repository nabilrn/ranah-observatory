#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

from scripts import build_milestone26_population_stats_geometry as stats_geom
from scripts import probe_milestone26_population_mapserver_multipoint as map_multi

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_stats_shape_diagnostic_contract.json"
PARTITIONS = ROOT / "data/manifests/milestone26_population_stats_partitions.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_stats_shape_diagnostic"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_stats_shape_diagnostic.json"


class M26PopulationStatsShapeError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-stats-shape-diagnostic-contract/v1":
        raise M26PopulationStatsShapeError("unexpected shape diagnostic contract schema")
    if contract.get("locked_before_live_shape_diagnostic") is not True:
        raise M26PopulationStatsShapeError("shape diagnostic was not locked before live probing")
    if contract.get("source_id") != "inarisk_population_2020":
        raise M26PopulationStatsShapeError("shape diagnostic source drift")
    if int(contract.get("partition_count_maximum", 0)) != 420:
        raise M26PopulationStatsShapeError("shape diagnostic partition ceiling drift")
    if contract.get("stop_rule") != "stop_immediately_after_first_nonstandard_statistics_shape":
        raise M26PopulationStatsShapeError("shape diagnostic stop rule drift")
    for key in (
        "numeric_aggregates_computed",
        "cross_geography_component_values_materialized",
        "substantive_values_promoted",
        "stage1_population_production_extraction_authorized_by_this_diagnostic",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise M26PopulationStatsShapeError(f"invalid diagnostic boundary: {key}")
    return contract


def load_partitions(contract: dict[str, Any]) -> dict[str, Any]:
    partitions = json.loads(PARTITIONS.read_text(encoding="utf-8"))
    if partitions.get("schema") != "ranah-observatory/milestone26-population-stats-partitions/v1":
        raise M26PopulationStatsShapeError("unexpected partition manifest schema")
    if partitions.get("geography_count") != 19:
        raise M26PopulationStatsShapeError("partition geography count drift")
    if partitions.get("total_partition_count") != int(contract["partition_count_maximum"]):
        raise M26PopulationStatsShapeError("partition count drift")
    if partitions.get("all_partition_cell_counts_exact") is not True:
        raise M26PopulationStatsShapeError("partition selected-cell counts are not exact")
    if partitions.get("all_partition_urls_within_gate") is not True:
        raise M26PopulationStatsShapeError("partition URLs are not frozen URI-safe")
    return partitions


def classify_payload(payload: Any, required_fields: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "classification": "transport_or_arcgis_error",
            "statistics_present": False,
            "statistics_type": None,
            "statistics_length": None,
            "missing_required_fields": [],
        }
    if isinstance(payload.get("error"), dict):
        return {
            "classification": "transport_or_arcgis_error",
            "statistics_present": "statistics" in payload,
            "statistics_type": type(payload.get("statistics")).__name__ if "statistics" in payload else None,
            "statistics_length": len(payload["statistics"]) if isinstance(payload.get("statistics"), list) else None,
            "missing_required_fields": [],
        }
    if "statistics" not in payload:
        return {
            "classification": "missing_statistics",
            "statistics_present": False,
            "statistics_type": None,
            "statistics_length": None,
            "missing_required_fields": [],
        }
    statistics = payload.get("statistics")
    if not isinstance(statistics, list):
        return {
            "classification": "statistics_not_list",
            "statistics_present": True,
            "statistics_type": type(statistics).__name__,
            "statistics_length": None,
            "missing_required_fields": [],
        }
    if len(statistics) == 0:
        return {
            "classification": "empty_statistics",
            "statistics_present": True,
            "statistics_type": "list",
            "statistics_length": 0,
            "missing_required_fields": [],
        }
    if len(statistics) != 1:
        return {
            "classification": "multiple_statistics",
            "statistics_present": True,
            "statistics_type": "list",
            "statistics_length": len(statistics),
            "missing_required_fields": [],
        }
    item = statistics[0]
    if not isinstance(item, dict):
        return {
            "classification": "statistics_item_not_object",
            "statistics_present": True,
            "statistics_type": "list",
            "statistics_length": 1,
            "missing_required_fields": [],
        }
    missing = sorted(required_fields - set(item))
    if missing:
        return {
            "classification": "missing_required_fields",
            "statistics_present": True,
            "statistics_type": "list",
            "statistics_length": 1,
            "missing_required_fields": missing,
        }
    return {
        "classification": "standard",
        "statistics_present": True,
        "statistics_type": "list",
        "statistics_length": 1,
        "missing_required_fields": [],
    }


def request_for_shape(url: str, required_fields: set[str], attempts: int = 3, timeout: float = 30.0) -> tuple[dict[str, Any], bytes, dict[str, Any], int]:
    last_response: dict[str, Any] | None = None
    last_body = b""
    last_shape: dict[str, Any] | None = None
    for attempt in range(1, attempts + 1):
        response = map_multi.request_once(url, timeout=timeout)
        body = response.pop("body")
        if not isinstance(body, bytes):
            body = b""
        payload = map_multi.parse_json(body)
        shape = classify_payload(payload, required_fields)
        transport_ok = response.get("status") == 200 and response.get("exception_class") is None and isinstance(payload, dict)
        arcgis_error = bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict))
        response["json_parseable"] = isinstance(payload, dict)
        response["arcgis_error_present"] = arcgis_error
        if transport_ok and not arcgis_error:
            return response, body, shape, attempt
        last_response, last_body, last_shape = response, body, shape
        if attempt < attempts:
            time.sleep(float(2 ** (attempt - 1)))
    assert last_response is not None and last_shape is not None
    return last_response, last_body, last_shape, attempts


def iter_frozen_partitions(partitions: dict[str, Any]):
    for geography in sorted(partitions["geographies"], key=lambda row: str(row["geography_id"])):
        for partition in sorted(geography["partitions"], key=lambda row: int(row["partition_index"])):
            yield geography, partition


def run() -> dict[str, Any]:
    contract = load_contract()
    partitions = load_partitions(contract)
    required_fields = set(contract["standard_shape_contract"]["required_fields"])
    service = str(contract["source_service"])
    standard_count = 0
    checked_count = 0
    first_nonstandard: dict[str, Any] | None = None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for geography, partition in iter_frozen_partitions(partitions):
        checked_count += 1
        gid = str(geography["geography_id"])
        partition_index = int(partition["partition_index"])
        selected_cell_count = int(partition["selected_cell_count"])
        url = stats_geom.stats_url(service, partition["candidate"]["arcgis_geometry"])
        response, body, shape, attempts_used = request_for_shape(url, required_fields)
        if shape["classification"] == "standard":
            standard_count += 1
            continue

        raw_path = OUT_DIR / "first-nonstandard-response.json"
        raw_path.write_bytes(body)
        first_nonstandard = {
            "scan_position": checked_count,
            "geography_id": gid,
            "geography_name": geography.get("geography_name"),
            "source_permendagri_code": geography.get("source_permendagri_code"),
            "partition_index": partition_index,
            "selected_cell_count": selected_cell_count,
            "classification": shape["classification"],
            "statistics_present": shape["statistics_present"],
            "statistics_type": shape["statistics_type"],
            "statistics_length": shape["statistics_length"],
            "missing_required_fields": shape["missing_required_fields"],
            "requested_url_length": len(url),
            "attempts_used": attempts_used,
            "response_status": response.get("status"),
            "response_content_type": response.get("content_type"),
            "response_json_parseable": response.get("json_parseable"),
            "response_arcgis_error_present": response.get("arcgis_error_present"),
            "response_exception_class": response.get("exception_class"),
            "raw_response_path": raw_path.relative_to(ROOT).as_posix(),
            "raw_response_sha256": sha256_bytes(body),
            "raw_response_bytes": len(body),
        }
        break

    manifest = {
        "schema": "ranah-observatory/milestone26-population-stats-shape-diagnostic/v1",
        "milestone": 26,
        "stage": "stage1_transport_shape_diagnostic",
        "contract": {
            "path": CONTRACT.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        },
        "partition_manifest": {
            "path": PARTITIONS.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(PARTITIONS.read_bytes()).hexdigest(),
        },
        "scan_order": contract["scan_order"],
        "checked_partition_count": checked_count,
        "standard_shape_partition_count_before_first_nonstandard": standard_count,
        "first_nonstandard_found": first_nonstandard is not None,
        "first_nonstandard": first_nonstandard,
        "standard_response_numeric_values_recorded": False,
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
    except (OSError, ValueError, KeyError, json.JSONDecodeError, M26PopulationStatsShapeError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    first = manifest["first_nonstandard"]
    print(json.dumps({
        "checked_partition_count": manifest["checked_partition_count"],
        "standard_shape_partition_count_before_first_nonstandard": manifest["standard_shape_partition_count_before_first_nonstandard"],
        "first_nonstandard_found": manifest["first_nonstandard_found"],
        "first_nonstandard_geography_id": None if first is None else first["geography_id"],
        "first_nonstandard_partition_index": None if first is None else first["partition_index"],
        "first_nonstandard_classification": None if first is None else first["classification"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
