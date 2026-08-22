#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from scripts import probe_milestone26_population_empty_stats_semantics as attempt1
from scripts import probe_milestone26_population_mapserver_multipoint as map_multi
from scripts import probe_milestone26_population_mapserver_scale as map_scale
from scripts import probe_milestone26_population_stats_shape as shape_probe
from scripts import build_milestone26_population_stats_geometry as stats_geom

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_empty_stats_semantics_attempt2_contract.json"
PRIOR = ROOT / "data/manifests/milestone26_population_empty_stats_semantics.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_empty_stats_semantics_attempt2"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_empty_stats_semantics_attempt2.json"


class M26PopulationEmptyStatsAttempt2Error(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-empty-stats-semantics-attempt2-contract/v1":
        raise M26PopulationEmptyStatsAttempt2Error("unexpected attempt-2 contract schema")
    if contract.get("locked_before_live_probe") is not True:
        raise M26PopulationEmptyStatsAttempt2Error("attempt-2 contract is not locked")
    target = contract.get("target", {})
    if target.get("geography_id") != "idn.13.1377" or int(target.get("partition_index", 0)) != 1 or int(target.get("selected_cell_count", 0)) != 1:
        raise M26PopulationEmptyStatsAttempt2Error("attempt-2 target drift")
    gate = contract.get("recovery_gate", {})
    if int(gate.get("repeat_count_per_service", 0)) != 2 or int(gate.get("required_status", 0)) != 200:
        raise M26PopulationEmptyStatsAttempt2Error("recovery gate drift")
    semantic = contract.get("semantic_probe", {})
    if int(semantic.get("image_server_repeat_count", 0)) != 3 or int(semantic.get("mapserver_repeat_count", 0)) != 3:
        raise M26PopulationEmptyStatsAttempt2Error("semantic repeat plan drift")
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
            raise M26PopulationEmptyStatsAttempt2Error(f"invalid attempt-2 boundary: {key}")
    return contract


def verify_prior_attempt(contract: dict[str, Any]) -> dict[str, Any]:
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    expected = contract["prior_attempt"]
    if prior.get("schema") != "ranah-observatory/milestone26-population-empty-stats-semantics/v1":
        raise M26PopulationEmptyStatsAttempt2Error("unexpected prior-attempt schema")
    if prior.get("decision") != expected["required_decision"]:
        raise M26PopulationEmptyStatsAttempt2Error("prior-attempt decision drift")
    image_statuses = [row.get("response", {}).get("status") for row in prior.get("image_server_repeats", [])]
    map_statuses = [row.get("response", {}).get("status") for row in prior.get("mapserver_repeats", [])]
    if image_statuses != expected["required_image_server_http_statuses"]:
        raise M26PopulationEmptyStatsAttempt2Error("prior ImageServer outage evidence drift")
    if map_statuses != expected["required_mapserver_http_statuses"]:
        raise M26PopulationEmptyStatsAttempt2Error("prior MapServer outage evidence drift")
    if prior.get("stage1_population_production_extraction_authorized") is not False:
        raise M26PopulationEmptyStatsAttempt2Error("prior attempt unexpectedly authorized production")
    return prior


def freeze(prefix: str, repeat: int, response: dict[str, Any], body: bytes) -> dict[str, Any]:
    path = OUT_DIR / f"{prefix}-repeat-{repeat}.json"
    path.write_bytes(body)
    return {
        **response,
        "raw_path": path.relative_to(ROOT).as_posix(),
        "raw_bytes": len(body),
        "raw_sha256": hashlib.sha256(body).hexdigest(),
    }


def probe_recovery_service(name: str, url: str, repeat_count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for repeat in range(1, repeat_count + 1):
        response = map_multi.request_once(url, timeout=30.0)
        body = response.pop("body")
        if not isinstance(body, bytes):
            body = b""
        payload = map_multi.parse_json(body)
        arcgis_error = bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict))
        transport_ok = bool(
            response.get("status") == 200
            and response.get("exception_class") is None
            and isinstance(payload, dict)
            and not arcgis_error
        )
        rows.append({
            "service": name,
            "repeat": repeat,
            "transport_ok": transport_ok,
            "json_object": isinstance(payload, dict),
            "arcgis_error_present": arcgis_error,
            "response": freeze(f"recovery-{name}", repeat, response, body),
        })
    return rows


def recovery_gate_passed(rows: list[dict[str, Any]], repeat_count: int) -> bool:
    image = [row for row in rows if row.get("service") == "image-server"]
    map_rows = [row for row in rows if row.get("service") == "mapserver"]
    return bool(
        len(image) == repeat_count
        and len(map_rows) == repeat_count
        and all(row.get("transport_ok") is True for row in image + map_rows)
    )


def probe_image_semantics(contract1: dict[str, Any], partition: dict[str, Any], repeat_count: int) -> list[dict[str, Any]]:
    required_fields = {"count", "sum", "mean", "min", "max", "skipX", "skipY"}
    geometry = partition["candidate"]["arcgis_geometry"]
    url = stats_geom.stats_url(str(contract1["image_server_repeat_probe"]["service"]), geometry)
    rows: list[dict[str, Any]] = []
    for repeat in range(1, repeat_count + 1):
        response = map_multi.request_once(url, timeout=30.0)
        body = response.pop("body")
        if not isinstance(body, bytes):
            body = b""
        payload = map_multi.parse_json(body)
        arcgis_error = bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict))
        classification = shape_probe.classify_payload(payload, required_fields)
        transport_ok = bool(
            response.get("status") == 200
            and response.get("exception_class") is None
            and isinstance(payload, dict)
            and not arcgis_error
        )
        rows.append({
            "repeat": repeat,
            "transport_ok": transport_ok,
            "arcgis_error_present": arcgis_error,
            "classification": classification["classification"],
            "statistics_length": classification["statistics_length"],
            "requested_url_length": len(url),
            "response": freeze("semantic-image-server", repeat, response, body),
        })
    return rows


def probe_map_semantics(contract1: dict[str, Any], center: list[float], repeat_count: int) -> list[dict[str, Any]]:
    cfg = contract1["mapserver_reference_probe"]
    field_name = str(cfg["accepted_pixel_field"])
    tolerance = float(cfg["result_geometry_tolerance_m"])
    url = map_scale.build_url(str(cfg["service"]), [center])
    rows: list[dict[str, Any]] = []
    for repeat in range(1, repeat_count + 1):
        response = map_multi.request_once(url, timeout=30.0)
        body = response.pop("body")
        if not isinstance(body, bytes):
            body = b""
        payload = map_multi.parse_json(body)
        arcgis_error = bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict))
        transport_ok = bool(
            response.get("status") == 200
            and response.get("exception_class") is None
            and isinstance(payload, dict)
            and not arcgis_error
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
        rows.append({
            "repeat": repeat,
            "transport_ok": transport_ok,
            "arcgis_error_present": arcgis_error,
            "raw_result_count": len(raw_results),
            "finite_accepted_pixel_value_count": len(parsed),
            "accepted_result_geometry_matches_exact_center": geometry_match,
            "requested_url_length": len(url),
            "response": freeze("semantic-mapserver", repeat, response, body),
        })
    return rows


def run() -> dict[str, Any]:
    contract = load_contract()
    prior = verify_prior_attempt(contract)
    contract1 = attempt1.load_contract()
    _diagnostic, partitions, _identity, _semantics, _scale = attempt1.load_frozen_inputs(contract1)
    geography, partition = attempt1.target_partition(partitions, contract1)
    center, center_evidence = attempt1.derive_exact_native_center(partition)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gate_cfg = contract["recovery_gate"]
    repeat_count = int(gate_cfg["repeat_count_per_service"])
    recovery_rows = []
    recovery_rows.extend(probe_recovery_service("image-server", str(gate_cfg["image_server_metadata_url"]), repeat_count))
    recovery_rows.extend(probe_recovery_service("mapserver", str(gate_cfg["mapserver_metadata_url"]), repeat_count))
    recovered = recovery_gate_passed(recovery_rows, repeat_count)

    image_rows: list[dict[str, Any]] = []
    map_rows: list[dict[str, Any]] = []
    if recovered:
        image_rows = probe_image_semantics(contract1, partition, int(contract["semantic_probe"]["image_server_repeat_count"]))
        map_rows = probe_map_semantics(contract1, center, int(contract["semantic_probe"]["mapserver_repeat_count"]))
        decision = attempt1.decide(image_rows, map_rows)
    else:
        decision = "service_not_recovered"

    if decision not in contract["attempt2_decisions"]:
        raise M26PopulationEmptyStatsAttempt2Error(f"unexpected attempt-2 decision: {decision}")

    manifest = {
        "schema": "ranah-observatory/milestone26-population-empty-stats-semantics-attempt2/v1",
        "milestone": 26,
        "stage": "stage1_transport_semantics_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": sha256_path(CONTRACT)},
        "prior_attempt": {"path": PRIOR.relative_to(ROOT).as_posix(), "sha256": sha256_path(PRIOR), "decision": prior["decision"]},
        "target": {
            "geography_id": geography["geography_id"],
            "geography_name": geography["geography_name"],
            "source_permendagri_code": geography["source_permendagri_code"],
            "partition_index": int(partition["partition_index"]),
            "selected_cell_count": int(partition["selected_cell_count"]),
            "native_center_epsg3395": center,
            "center_derivation": center_evidence,
        },
        "recovery_gate": {
            "repeat_count_per_service": repeat_count,
            "responses": recovery_rows,
            "all_repeats_both_services_passed": recovered,
        },
        "semantic_probe_performed": recovered,
        "image_server_repeats": image_rows,
        "mapserver_repeats": map_rows,
        "decision": decision,
        "exact_cell_no_valid_source_value_qualified": decision == "deterministic_no_valid_source_value_for_exact_native_cell",
        "transient_empty_statistics_observed": decision == "transient_image_server_empty_statistics",
        "transport_disagreement_observed": decision == "transport_disagreement",
        "diagnostic_inconclusive": decision in {"service_not_recovered", "inconclusive"},
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
    except (OSError, ValueError, KeyError, json.JSONDecodeError, M26PopulationEmptyStatsAttempt2Error) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "recovery_gate_passed": manifest["recovery_gate"]["all_repeats_both_services_passed"],
        "semantic_probe_performed": manifest["semantic_probe_performed"],
        "decision": manifest["decision"],
        "image_server_classes": [row["classification"] for row in manifest["image_server_repeats"]],
        "mapserver_valid_counts": [row["finite_accepted_pixel_value_count"] for row in manifest["mapserver_repeats"]],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
