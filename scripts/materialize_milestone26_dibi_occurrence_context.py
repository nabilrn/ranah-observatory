#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data/manifests/milestone26_dibi_occurrence_production_contract.json"


class DibiMaterializationError(RuntimeError):
    pass


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def request_bytes(url: str, retries: int = 3, timeout: float = 120.0) -> tuple[str, str, bytes]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if int(response.status) != 200:
                    raise DibiMaterializationError(f"HTTP {response.status}: {url}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()
        except (urllib.error.URLError, TimeoutError, DibiMaterializationError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)
    raise DibiMaterializationError(f"request failed after retries: {url}") from last_error


def load_json_bytes(body: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = body[:300].decode("utf-8", errors="replace")
        raise DibiMaterializationError(f"{label} is not valid JSON: {preview}") from exc
    if not isinstance(payload, dict):
        raise DibiMaterializationError(f"{label} JSON root must be an object")
    return payload


def preferred_runtime_unavailable(payload: dict[str, Any]) -> bool:
    error = payload.get("error")
    if not isinstance(error, dict):
        return False
    code = error.get("code")
    texts: list[str] = []
    message = error.get("message")
    if message is not None:
        texts.append(str(message))
    details = error.get("details")
    if isinstance(details, list):
        texts.extend(str(item) for item in details)
    elif details is not None:
        texts.append(str(details))
    combined = " ".join(texts).casefold()
    return int(code) == 500 and ("not started" in combined or "service" in combined and "started" in combined)


def normalize_geo_key(value: Any) -> int:
    if isinstance(value, bool):
        raise DibiMaterializationError(f"invalid boolean id_kab_bps: {value!r}")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError as exc:
            raise DibiMaterializationError(f"invalid id_kab_bps: {value!r}") from exc
    else:
        raise DibiMaterializationError(f"invalid id_kab_bps type: {type(value).__name__}")
    if not math.isfinite(number) or not number.is_integer():
        raise DibiMaterializationError(f"id_kab_bps must be a finite integer-valued key: {value!r}")
    return int(number)


def validate_numeric(value: Any, field: str, geography_key: int) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DibiMaterializationError(f"{field} for {geography_key} is not numeric: {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise DibiMaterializationError(f"{field} for {geography_key} is non-finite")
    if number < 0:
        raise DibiMaterializationError(f"{field} for {geography_key} is negative: {value!r}")
    return value


def csv_numeric(value: int | float) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def query_url(service: str, layer_id: int, contract: dict[str, Any]) -> str:
    query = contract["query_contract"]
    params = {
        "where": str(query["where"]),
        "outFields": ",".join(str(field) for field in query["out_fields"]),
        "returnGeometry": "true" if query["return_geometry"] else "false",
        "f": str(query["f"]),
    }
    return service.rstrip("/") + f"/{layer_id}/query?" + urllib.parse.urlencode(params)


def validate_contract(contract: dict[str, Any]) -> tuple[Path, dict[str, Any], Path, dict[str, Any], Path]:
    if contract.get("schema") != "ranah-observatory/milestone26-dibi-occurrence-production-contract/v1":
        raise DibiMaterializationError("unexpected DIBI production contract schema")
    if contract.get("contract_locked_before_cross_geography_numeric_extraction") is not True:
        raise DibiMaterializationError("DIBI contract was not locked before numeric extraction")
    if contract.get("numeric_materialization_authorized") is not True:
        raise DibiMaterializationError("DIBI numeric materialization is not authorized")
    for flag in (
        "event_level_record_inference_authorized",
        "observed_impact_inference_authorized",
        "substantive_interpretation_authorized",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(flag) is not False:
            raise DibiMaterializationError(f"scientific boundary unexpectedly open: {flag}")

    if contract["coverage"].get("annual_disaggregation_authorized") is not False:
        raise DibiMaterializationError("annual disaggregation unexpectedly authorized")
    numeric_contract = contract["numeric_fields"]
    for flag in (
        "integer_coercion_authorized",
        "source_field_renaming_authorized",
        "cross_field_sum_authorized",
        "cross_field_ratio_authorized",
        "annualization_authorized",
        "imputation_authorized",
        "semantic_interpretation_of_abbreviated_field_names_authorized",
    ):
        if numeric_contract.get(flag) is not False:
            raise DibiMaterializationError(f"numeric transformation unexpectedly authorized: {flag}")

    qualification_path = ROOT / str(contract["source_qualification"])
    with qualification_path.open(newline="", encoding="utf-8") as handle:
        qualification_rows = list(csv.DictReader(handle))
    matches = [row for row in qualification_rows if row.get("source_id") == contract["source_id"]]
    if len(matches) != 1:
        raise DibiMaterializationError("DIBI source qualification row is not unique")
    q = matches[0]
    if q.get("qualification_state") != "qualified_explicit_coverage_metadata":
        raise DibiMaterializationError("DIBI source qualification state drift")
    if q.get("numeric_extraction_authorized") != "True":
        raise DibiMaterializationError("DIBI source qualification does not authorize numeric extraction")

    amendment_path = ROOT / str(contract["transport_amendment"])
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    if amendment.get("schema") != "ranah-observatory/milestone26-dibi-transport-amendment/v1":
        raise DibiMaterializationError("unexpected DIBI transport amendment schema")
    if amendment.get("source_id") != contract["source_id"]:
        raise DibiMaterializationError("DIBI transport amendment source drift")
    transport = contract["source_transport"]
    if amendment.get("preferred_endpoint") != transport["preferred_service"]:
        raise DibiMaterializationError("preferred DIBI endpoint drift")
    if amendment.get("fallback_endpoint") != transport["fallback_service"]:
        raise DibiMaterializationError("fallback DIBI endpoint drift")
    if int(amendment.get("fallback_layer_id")) != int(transport["qualified_layer_id"]):
        raise DibiMaterializationError("DIBI fallback layer-id drift")
    if amendment.get("fallback_layer_name") != transport["qualified_layer_name"]:
        raise DibiMaterializationError("DIBI fallback layer-name drift")
    if amendment.get("numeric_values_promoted_by_amendment") is not False:
        raise DibiMaterializationError("transport amendment unexpectedly promoted numeric values")

    metadata_path = ROOT / str(contract["source_metadata"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    extra = metadata.get("extra")
    layer_record = extra.get(str(transport["qualified_layer_id"])) if isinstance(extra, dict) else None
    layer_payload = layer_record.get("payload") if isinstance(layer_record, dict) else None
    if not isinstance(layer_payload, dict):
        raise DibiMaterializationError("frozen DIBI source metadata lacks qualified layer payload")
    if layer_payload.get("name") != transport["qualified_layer_name"]:
        raise DibiMaterializationError("frozen DIBI qualified layer name drift")
    fields = {
        str(item.get("name"))
        for item in layer_payload.get("fields", [])
        if isinstance(item, dict) and item.get("name") is not None
    }
    required_fields = set(str(value) for value in contract["query_contract"]["out_fields"])
    if not required_fields.issubset(fields):
        raise DibiMaterializationError(f"frozen DIBI layer missing fields: {sorted(required_fields - fields)}")

    return qualification_path, q, amendment_path, amendment, metadata_path


def acquire_raw(
    contract: dict[str, Any],
    mode: str,
    qualification_path: Path,
    amendment_path: Path,
    metadata_path: Path,
) -> tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]:
    output = contract["output"]
    raw_root = ROOT / str(output["raw_root"])
    raw_root.mkdir(parents=True, exist_ok=True)
    preferred_path = raw_root / "preferred-service-status.json"
    response_path = raw_root / "dibi-kabupaten-sumbar-2015-2024.json"
    sidecar_path = raw_root / "dibi-query.request.json"

    transport = contract["source_transport"]
    preferred_url = str(transport["preferred_service"]).rstrip("/") + "?f=pjson"
    fallback_query_url = query_url(
        str(transport["fallback_service"]),
        int(transport["qualified_layer_id"]),
        contract,
    )
    contract_sha = sha256_path(CONTRACT_PATH)
    qualification_sha = sha256_path(qualification_path)
    amendment_sha = sha256_path(amendment_path)
    metadata_sha = sha256_path(metadata_path)

    if mode == "live":
        preferred_final_url, preferred_content_type, preferred_body = request_bytes(preferred_url)
        preferred_payload = load_json_bytes(preferred_body, "preferred DIBI service status")
        if not preferred_runtime_unavailable(preferred_payload):
            raise DibiMaterializationError(
                "preferred DIBI service no longer reports the preregistered runtime-unavailable state; contract review required before extraction"
            )
        preferred_path.write_bytes(preferred_body)

        final_url, content_type, body = request_bytes(fallback_query_url)
        response_payload = load_json_bytes(body, "fallback DIBI kabupaten query")
        if isinstance(response_payload.get("error"), dict):
            raise DibiMaterializationError(f"fallback DIBI query returned ArcGIS error: {response_payload['error']}")
        response_path.write_bytes(body)

        sidecar = {
            "schema": "ranah-observatory/milestone26-dibi-query-request/v1",
            "source_id": contract["source_id"],
            "preferred_status_requested_url": preferred_url,
            "preferred_status_final_url": preferred_final_url,
            "preferred_status_content_type": preferred_content_type,
            "preferred_status_path": rel(preferred_path),
            "preferred_status_sha256": sha256_bytes(preferred_body),
            "fallback_used": True,
            "fallback_query_requested_url": fallback_query_url,
            "fallback_query_final_url": final_url,
            "fallback_query_content_type": content_type,
            "fallback_layer_id": int(transport["qualified_layer_id"]),
            "fallback_layer_name": transport["qualified_layer_name"],
            "response_path": rel(response_path),
            "response_sha256": sha256_bytes(body),
            "response_bytes": len(body),
            "contract_path": rel(CONTRACT_PATH),
            "contract_sha256": contract_sha,
            "source_qualification_path": rel(qualification_path),
            "source_qualification_sha256": qualification_sha,
            "transport_amendment_path": rel(amendment_path),
            "transport_amendment_sha256": amendment_sha,
            "source_metadata_path": rel(metadata_path),
            "source_metadata_sha256": metadata_sha,
        }
        write_json(sidecar_path, sidecar)
    else:
        for path in (preferred_path, response_path, sidecar_path):
            if not path.exists():
                raise DibiMaterializationError(f"offline DIBI evidence missing: {rel(path)}")
        preferred_body = preferred_path.read_bytes()
        preferred_payload = load_json_bytes(preferred_body, "frozen preferred DIBI service status")
        if not preferred_runtime_unavailable(preferred_payload):
            raise DibiMaterializationError("frozen preferred-service evidence does not prove runtime unavailability")
        body = response_path.read_bytes()
        response_payload = load_json_bytes(body, "frozen fallback DIBI response")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if sidecar.get("schema") != "ranah-observatory/milestone26-dibi-query-request/v1":
            raise DibiMaterializationError("unexpected frozen DIBI request-sidecar schema")
        expected = {
            "preferred_status_requested_url": preferred_url,
            "fallback_query_requested_url": fallback_query_url,
            "contract_sha256": contract_sha,
            "source_qualification_sha256": qualification_sha,
            "transport_amendment_sha256": amendment_sha,
            "source_metadata_sha256": metadata_sha,
        }
        for key, value in expected.items():
            if sidecar.get(key) != value:
                raise DibiMaterializationError(f"offline DIBI sidecar drift: {key}")
        if sidecar.get("fallback_used") is not True:
            raise DibiMaterializationError("offline DIBI sidecar does not record authorized fallback use")
        if sidecar.get("preferred_status_sha256") != sha256_path(preferred_path):
            raise DibiMaterializationError("offline preferred-service evidence checksum mismatch")
        if sidecar.get("response_sha256") != sha256_path(response_path):
            raise DibiMaterializationError("offline DIBI query response checksum mismatch")
        if int(sidecar.get("response_bytes", -1)) != response_path.stat().st_size:
            raise DibiMaterializationError("offline DIBI query response byte-count mismatch")

    return preferred_path, response_path, sidecar_path, sidecar, response_payload


def parse_features(contract: dict[str, Any], response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    features = response_payload.get("features")
    if not isinstance(features, list):
        raise DibiMaterializationError("DIBI response has no feature list")
    expected_count = int(contract["query_contract"]["expected_feature_count"])
    if len(features) != expected_count:
        raise DibiMaterializationError(f"DIBI feature-count drift: {len(features)} != {expected_count}")

    expected_keys = {int(value) for value in contract["geography_contract"]["expected_source_keys"]}
    numeric_fields = [str(value) for value in contract["numeric_fields"]["retained_source_native_fields"]]
    parsed: list[dict[str, Any]] = []
    seen: set[int] = set()
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("attributes"), dict):
            raise DibiMaterializationError("DIBI feature missing attributes object")
        attrs = feature["attributes"]
        key = normalize_geo_key(attrs.get("id_kab_bps"))
        if key in seen:
            raise DibiMaterializationError(f"duplicate DIBI id_kab_bps: {key}")
        seen.add(key)
        if key not in expected_keys:
            raise DibiMaterializationError(f"unexpected DIBI geography key: {key}")
        name = attrs.get("NAMA_KAB")
        if not isinstance(name, str) or not name.strip():
            raise DibiMaterializationError(f"missing DIBI NAMA_KAB for {key}")
        row: dict[str, Any] = {
            "id_kab_bps": key,
            "NAMA_KAB": name.strip(),
        }
        for field in numeric_fields:
            row[field] = validate_numeric(attrs.get(field), field, key)
        parsed.append(row)

    if seen != expected_keys:
        raise DibiMaterializationError(
            f"DIBI geography-key set mismatch missing={sorted(expected_keys-seen)} extra={sorted(seen-expected_keys)}"
        )
    return sorted(parsed, key=lambda row: int(row["id_kab_bps"]))


def build(mode: str) -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    qualification_path, _qualification, amendment_path, amendment, metadata_path = validate_contract(contract)
    preferred_path, response_path, sidecar_path, sidecar, response_payload = acquire_raw(
        contract,
        mode,
        qualification_path,
        amendment_path,
        metadata_path,
    )
    rows = parse_features(contract, response_payload)

    output = contract["output"]
    component_path = ROOT / str(output["component_frame"])
    provenance_path = ROOT / str(output["provenance_frame"])
    manifest_path = ROOT / str(output["manifest"])
    numeric_fields = [str(value) for value in contract["numeric_fields"]["retained_source_native_fields"]]

    component_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        key = int(row["id_kab_bps"])
        component: dict[str, Any] = {
            "geography_id": f"idn.13.{key:04d}",
            "id_kab_bps": key,
            "NAMA_KAB": row["NAMA_KAB"],
            "coverage_start_year": int(contract["coverage"]["declared_start_year"]),
            "coverage_end_year": int(contract["coverage"]["declared_end_year"]),
        }
        for field in numeric_fields:
            component[field] = csv_numeric(row[field])
        component.update(
            {
                "source_id": contract["source_id"],
                "component_class": contract["component_class"],
                "claim_type": contract["claim_type"],
                "semantic_interpretation_of_abbreviated_field_names_authorized": "false",
                "event_level_record_inference_authorized": "false",
                "observed_impact_inference_authorized": "false",
                "risk_synthesis_authorized": "false",
            }
        )
        component_rows.append(component)
        provenance_rows.append(
            {
                "geography_id": component["geography_id"],
                "id_kab_bps": key,
                "source_record_order_after_local_sort": index,
                "raw_response_path": rel(response_path),
                "raw_response_sha256": sha256_path(response_path),
                "request_sidecar_path": rel(sidecar_path),
                "request_sidecar_sha256": sha256_path(sidecar_path),
                "preferred_service_status_path": rel(preferred_path),
                "preferred_service_status_sha256": sha256_path(preferred_path),
                "transport_fallback_used": "true",
                "qualified_layer_id": int(contract["source_transport"]["qualified_layer_id"]),
                "qualified_layer_name": contract["source_transport"]["qualified_layer_name"],
                "source_field_semantics_preserved_without_renaming": "true",
            }
        )

    component_fields = [
        "geography_id",
        "id_kab_bps",
        "NAMA_KAB",
        "coverage_start_year",
        "coverage_end_year",
        *numeric_fields,
        "source_id",
        "component_class",
        "claim_type",
        "semantic_interpretation_of_abbreviated_field_names_authorized",
        "event_level_record_inference_authorized",
        "observed_impact_inference_authorized",
        "risk_synthesis_authorized",
    ]
    provenance_fields = [
        "geography_id",
        "id_kab_bps",
        "source_record_order_after_local_sort",
        "raw_response_path",
        "raw_response_sha256",
        "request_sidecar_path",
        "request_sidecar_sha256",
        "preferred_service_status_path",
        "preferred_service_status_sha256",
        "transport_fallback_used",
        "qualified_layer_id",
        "qualified_layer_name",
        "source_field_semantics_preserved_without_renaming",
    ]
    write_csv(component_path, component_fields, component_rows)
    write_csv(provenance_path, provenance_fields, provenance_rows)

    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-dibi-occurrence-context/v1",
        "milestone": 26,
        "stage": "stage1_dibi_recorded_occurrence_context_materialization",
        "source_id": contract["source_id"],
        "component_class": contract["component_class"],
        "claim_type": contract["claim_type"],
        "coverage": contract["coverage"],
        "geography_count": len(component_rows),
        "observation_count": len(component_rows),
        "exact_geography_key_set_pass": len(component_rows) == int(contract["geography_count_expected"]),
        "retained_source_native_numeric_fields": numeric_fields,
        "source_field_renaming_performed": False,
        "cross_field_sum_performed": False,
        "cross_field_ratio_performed": False,
        "annualization_performed": False,
        "imputation_performed": False,
        "semantic_interpretation_of_abbreviated_field_names_performed": False,
        "preferred_service_runtime_unavailable_evidence": {
            "path": rel(preferred_path),
            "sha256": sha256_path(preferred_path),
        },
        "transport_fallback_used": True,
        "transport_fallback_authorized": bool(
            amendment["fallback_authorized_only_when_preferred_endpoint_reports_runtime_unavailable"]
        ),
        "raw_response": {
            "path": rel(response_path),
            "sha256": sha256_path(response_path),
            "bytes": response_path.stat().st_size,
        },
        "request_sidecar": {
            "path": rel(sidecar_path),
            "sha256": sha256_path(sidecar_path),
        },
        "contract": {"path": rel(CONTRACT_PATH), "sha256": sha256_path(CONTRACT_PATH)},
        "source_qualification": {"path": rel(qualification_path), "sha256": sha256_path(qualification_path)},
        "transport_amendment": {"path": rel(amendment_path), "sha256": sha256_path(amendment_path)},
        "source_metadata": {"path": rel(metadata_path), "sha256": sha256_path(metadata_path)},
        "outputs": {
            "component_frame": rel(component_path),
            "component_frame_sha256": sha256_path(component_path),
            "provenance_frame": rel(provenance_path),
            "provenance_frame_sha256": sha256_path(provenance_path),
        },
        "offline_rebuild_required": bool(contract["reproducibility"]["offline_rebuild_required"]),
        "live_and_offline_outputs_must_be_byte_identical": bool(
            contract["reproducibility"]["live_and_offline_outputs_must_be_byte_identical"]
        ),
        "event_level_record_inference_performed": False,
        "observed_impact_inference_performed": False,
        "substantive_interpretation_performed": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "stage1_complete": False,
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize Milestone 26 DIBI 2015-2024 kabupaten occurrence/context fields")
    parser.add_argument("--mode", choices=("live", "offline"), default="offline")
    args = parser.parse_args()
    manifest = build(args.mode)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "geography_count": manifest["geography_count"],
                "transport_fallback_used": manifest["transport_fallback_used"],
                "retained_source_native_numeric_fields": manifest["retained_source_native_numeric_fields"],
                "component_frame": manifest["outputs"]["component_frame"],
                "manifest": rel(ROOT / "data/manifests/milestone26_stage1_dibi_occurrence_context.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
