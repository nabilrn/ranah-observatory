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
REPRESENTATION_AMENDMENT_PATH = ROOT / "data/manifests/milestone26_dibi_geography_representation_amendment.json"


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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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
    try:
        code = int(error.get("code"))
    except (TypeError, ValueError):
        return False
    parts: list[str] = []
    if error.get("message") is not None:
        parts.append(str(error["message"]))
    details = error.get("details")
    if isinstance(details, list):
        parts.extend(str(item) for item in details)
    elif details is not None:
        parts.append(str(details))
    text = " ".join(parts).casefold()
    return code == 500 and ("not started" in text or ("service" in text and "started" in text))


def normalize_text(value: Any) -> str:
    return " ".join(str(value if value is not None else "").strip().upper().split())


def normalize_integral(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise DibiMaterializationError(f"{field} cannot be boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DibiMaterializationError(f"{field} is not numeric: {value!r}") from exc
    if not math.isfinite(number) or not number.is_integer():
        raise DibiMaterializationError(f"{field} must be finite integer-valued: {value!r}")
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


def query_url(service: str, layer_id: int, representation: dict[str, Any]) -> str:
    params = {
        "where": str(representation["where"]),
        "outFields": ",".join(str(field) for field in representation["out_fields"]),
        "returnGeometry": "true" if representation["return_geometry"] else "false",
        "f": str(representation["f"]),
    }
    return service.rstrip("/") + f"/{layer_id}/query?" + urllib.parse.urlencode(params)


def load_and_validate_contracts() -> tuple[
    dict[str, Any],
    dict[str, Any],
    Path,
    Path,
    Path,
    dict[str, Any],
]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    amendment = json.loads(REPRESENTATION_AMENDMENT_PATH.read_text(encoding="utf-8"))

    if contract.get("schema") != "ranah-observatory/milestone26-dibi-occurrence-production-contract/v1":
        raise DibiMaterializationError("unexpected DIBI production contract schema")
    if contract.get("contract_locked_before_cross_geography_numeric_extraction") is not True:
        raise DibiMaterializationError("DIBI production contract was not preregistered")
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
            raise DibiMaterializationError(f"base scientific boundary unexpectedly open: {flag}")

    numeric_contract = contract["numeric_fields"]
    if numeric_contract.get("retained_source_native_fields") != ["Total_basa", "Total_ba_1", "Total_keri"]:
        raise DibiMaterializationError("base DIBI numeric field set drift")
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
            raise DibiMaterializationError(f"base numeric transformation unexpectedly authorized: {flag}")

    if amendment.get("schema") != "ranah-observatory/milestone26-dibi-geography-representation-amendment/v1":
        raise DibiMaterializationError("unexpected DIBI geography representation amendment schema")
    if amendment.get("amendment_type") != "representation_only_geography_key_and_filter_correction":
        raise DibiMaterializationError("unexpected DIBI representation amendment type")
    if amendment.get("trigger", {}).get("numeric_outputs_committed_by_failed_run") is not False:
        raise DibiMaterializationError("representation amendment was not made before numeric output commitment")
    evidence = amendment.get("evidence", {})
    if evidence.get("numeric_occurrence_fields_requested_by_probe") is not False:
        raise DibiMaterializationError("representation probe requested occurrence fields")
    if evidence.get("numeric_occurrence_values_inspected_before_amendment") is not False:
        raise DibiMaterializationError("representation amendment was made after numeric occurrence inspection")
    for flag in (
        "source_family_changed",
        "source_endpoint_changed",
        "source_layer_changed",
        "coverage_changed",
        "component_class_changed",
        "claim_type_changed",
        "numeric_field_set_changed",
        "numeric_transformations_changed",
        "scientific_design_changed",
        "event_level_record_inference_authorized",
        "observed_impact_inference_authorized",
        "substantive_interpretation_authorized",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if amendment.get(flag) is not False:
            raise DibiMaterializationError(f"representation amendment changed scientific design: {flag}")

    probe_path = ROOT / str(evidence["identifier_only_probe"])
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("schema") != evidence["probe_schema"]:
        raise DibiMaterializationError("identifier-only probe schema drift")
    if probe.get("sumbar_candidate_count") != 19:
        raise DibiMaterializationError("identifier-only probe no longer proves exact 19 Sumbar candidates")
    if probe.get("numeric_occurrence_fields_requested") is not False:
        raise DibiMaterializationError("identifier-only probe requested occurrence fields")
    if probe.get("numeric_occurrence_values_inspected") is not False:
        raise DibiMaterializationError("identifier-only probe inspected occurrence values")

    corrected = amendment["corrected_representation"]
    expected_keys = {int(value) for value in corrected["expected_source_keys"]}
    probed_no_kab = {int(row["NO_KAB"]) for row in probe["sumbar_candidates"]}
    if probed_no_kab != expected_keys:
        raise DibiMaterializationError("corrected NO_KAB key set is not supported by frozen identifier-only evidence")
    if corrected.get("source_key") != "NO_KAB" or corrected.get("province_filter_field") != "NO_PROP":
        raise DibiMaterializationError("corrected geography representation drift")
    if int(corrected.get("province_filter_value")) != 13:
        raise DibiMaterializationError("corrected Sumbar province code drift")
    if corrected.get("province_name_required_normalized") != "SUMATERA BARAT":
        raise DibiMaterializationError("corrected province-name verification drift")
    if corrected.get("out_fields") != [
        "NO_PROP", "NO_KAB", "NAMA_PROP", "NAMA_KAB", "Total_basa", "Total_ba_1", "Total_keri"
    ]:
        raise DibiMaterializationError("corrected query field set drift")

    qualification_path = ROOT / str(contract["source_qualification"])
    with qualification_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    qualified = [row for row in rows if row.get("source_id") == contract["source_id"]]
    if len(qualified) != 1:
        raise DibiMaterializationError("DIBI source qualification row is not unique")
    if qualified[0].get("qualification_state") != "qualified_explicit_coverage_metadata":
        raise DibiMaterializationError("DIBI source qualification state drift")
    if qualified[0].get("numeric_extraction_authorized") != "True":
        raise DibiMaterializationError("DIBI source qualification does not authorize numeric extraction")

    transport_amendment_path = ROOT / str(contract["transport_amendment"])
    transport_amendment = json.loads(transport_amendment_path.read_text(encoding="utf-8"))
    transport = contract["source_transport"]
    if transport_amendment.get("preferred_endpoint") != transport["preferred_service"]:
        raise DibiMaterializationError("preferred endpoint drift")
    if transport_amendment.get("fallback_endpoint") != transport["fallback_service"]:
        raise DibiMaterializationError("fallback endpoint drift")
    if int(transport_amendment.get("fallback_layer_id")) != int(transport["qualified_layer_id"]):
        raise DibiMaterializationError("fallback layer drift")

    metadata_path = ROOT / str(contract["source_metadata"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    extra = metadata.get("extra")
    layer_record = extra.get(str(transport["qualified_layer_id"])) if isinstance(extra, dict) else None
    layer = layer_record.get("payload") if isinstance(layer_record, dict) else None
    if not isinstance(layer, dict) or layer.get("name") != transport["qualified_layer_name"]:
        raise DibiMaterializationError("frozen DIBI qualified layer drift")
    layer_fields = {
        str(item.get("name"))
        for item in layer.get("fields", [])
        if isinstance(item, dict) and item.get("name") is not None
    }
    required_fields = set(str(value) for value in corrected["out_fields"])
    if not required_fields.issubset(layer_fields):
        raise DibiMaterializationError(f"qualified layer missing corrected query fields: {sorted(required_fields-layer_fields)}")

    return contract, amendment, qualification_path, transport_amendment_path, metadata_path, transport_amendment


def acquire_raw(
    *,
    contract: dict[str, Any],
    representation_amendment: dict[str, Any],
    transport_amendment: dict[str, Any],
    qualification_path: Path,
    transport_amendment_path: Path,
    metadata_path: Path,
    mode: str,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    raw_root = ROOT / str(contract["output"]["raw_root"])
    raw_root.mkdir(parents=True, exist_ok=True)
    preferred_path = raw_root / "preferred-service-status.json"
    response_path = raw_root / "dibi-kabupaten-sumbar-2015-2024.json"
    sidecar_path = raw_root / "dibi-query.request.json"

    transport = contract["source_transport"]
    corrected = representation_amendment["corrected_representation"]
    preferred_url = str(transport["preferred_service"]).rstrip("/") + "?f=pjson"
    fallback_query_url = query_url(
        str(transport["fallback_service"]),
        int(transport["qualified_layer_id"]),
        corrected,
    )
    frozen_hashes = {
        "contract_sha256": sha256_path(CONTRACT_PATH),
        "representation_amendment_sha256": sha256_path(REPRESENTATION_AMENDMENT_PATH),
        "source_qualification_sha256": sha256_path(qualification_path),
        "transport_amendment_sha256": sha256_path(transport_amendment_path),
        "source_metadata_sha256": sha256_path(metadata_path),
    }

    if mode == "live":
        preferred_final, preferred_type, preferred_body = request_bytes(preferred_url)
        preferred_payload = load_json_bytes(preferred_body, "preferred DIBI service status")
        if not preferred_runtime_unavailable(preferred_payload):
            raise DibiMaterializationError(
                "preferred DIBI service no longer matches the frozen fallback trigger; contract review required"
            )
        preferred_path.write_bytes(preferred_body)

        final_url, content_type, body = request_bytes(fallback_query_url)
        response_payload = load_json_bytes(body, "corrected DIBI kabupaten query")
        if isinstance(response_payload.get("error"), dict):
            raise DibiMaterializationError(f"corrected DIBI query returned ArcGIS error: {response_payload['error']}")
        response_path.write_bytes(body)

        sidecar = {
            "schema": "ranah-observatory/milestone26-dibi-query-request/v2",
            "source_id": contract["source_id"],
            "preferred_status_requested_url": preferred_url,
            "preferred_status_final_url": preferred_final,
            "preferred_status_content_type": preferred_type,
            "preferred_status_path": rel(preferred_path),
            "preferred_status_sha256": sha256_bytes(preferred_body),
            "fallback_used": True,
            "fallback_query_requested_url": fallback_query_url,
            "fallback_query_final_url": final_url,
            "fallback_query_content_type": content_type,
            "fallback_layer_id": int(transport["qualified_layer_id"]),
            "fallback_layer_name": transport["qualified_layer_name"],
            "corrected_geography_source_key": corrected["source_key"],
            "corrected_province_filter": corrected["where"],
            "response_path": rel(response_path),
            "response_sha256": sha256_bytes(body),
            "response_bytes": len(body),
            "contract_path": rel(CONTRACT_PATH),
            "representation_amendment_path": rel(REPRESENTATION_AMENDMENT_PATH),
            "source_qualification_path": rel(qualification_path),
            "transport_amendment_path": rel(transport_amendment_path),
            "source_metadata_path": rel(metadata_path),
            **frozen_hashes,
        }
        write_json(sidecar_path, sidecar)
    else:
        for path in (preferred_path, response_path, sidecar_path):
            if not path.exists():
                raise DibiMaterializationError(f"offline DIBI evidence missing: {rel(path)}")
        if not preferred_runtime_unavailable(load_json_bytes(preferred_path.read_bytes(), "frozen preferred status")):
            raise DibiMaterializationError("frozen preferred-service evidence does not prove fallback trigger")
        response_payload = load_json_bytes(response_path.read_bytes(), "frozen corrected DIBI response")
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if sidecar.get("schema") != "ranah-observatory/milestone26-dibi-query-request/v2":
            raise DibiMaterializationError("unexpected DIBI request-sidecar schema")
        expected = {
            "fallback_query_requested_url": fallback_query_url,
            "corrected_geography_source_key": corrected["source_key"],
            "corrected_province_filter": corrected["where"],
            **frozen_hashes,
        }
        for key, value in expected.items():
            if sidecar.get(key) != value:
                raise DibiMaterializationError(f"offline DIBI sidecar drift: {key}")
        if sidecar.get("fallback_used") is not True:
            raise DibiMaterializationError("offline DIBI sidecar does not record fallback use")
        if sidecar.get("preferred_status_sha256") != sha256_path(preferred_path):
            raise DibiMaterializationError("offline preferred-service evidence checksum mismatch")
        if sidecar.get("response_sha256") != sha256_path(response_path):
            raise DibiMaterializationError("offline DIBI response checksum mismatch")
        if int(sidecar.get("response_bytes", -1)) != response_path.stat().st_size:
            raise DibiMaterializationError("offline DIBI response byte-count mismatch")

    return preferred_path, response_path, sidecar_path, response_payload


def parse_features(contract: dict[str, Any], amendment: dict[str, Any], response: dict[str, Any]) -> list[dict[str, Any]]:
    features = response.get("features")
    if not isinstance(features, list):
        raise DibiMaterializationError("DIBI response has no feature list")
    corrected = amendment["corrected_representation"]
    expected_count = int(corrected["expected_feature_count"])
    if len(features) != expected_count:
        raise DibiMaterializationError(f"corrected DIBI feature-count drift: {len(features)} != {expected_count}")

    expected_keys = {int(value) for value in corrected["expected_source_keys"]}
    numeric_fields = [str(value) for value in contract["numeric_fields"]["retained_source_native_fields"]]
    parsed: list[dict[str, Any]] = []
    seen: set[int] = set()
    for feature in features:
        attrs = feature.get("attributes") if isinstance(feature, dict) else None
        if not isinstance(attrs, dict):
            raise DibiMaterializationError("DIBI feature missing attributes")
        province_code = normalize_integral(attrs.get("NO_PROP"), "NO_PROP")
        if province_code != int(corrected["province_filter_value"]):
            raise DibiMaterializationError(f"unexpected province code in corrected DIBI response: {province_code}")
        if normalize_text(attrs.get("NAMA_PROP")) != corrected["province_name_required_normalized"]:
            raise DibiMaterializationError(f"province-name verification failed for attrs={attrs}")
        key = normalize_integral(attrs.get("NO_KAB"), "NO_KAB")
        if key in seen:
            raise DibiMaterializationError(f"duplicate NO_KAB in corrected DIBI response: {key}")
        if key not in expected_keys:
            raise DibiMaterializationError(f"unexpected corrected DIBI NO_KAB: {key}")
        seen.add(key)
        name = attrs.get("NAMA_KAB")
        if not isinstance(name, str) or not name.strip():
            raise DibiMaterializationError(f"missing NAMA_KAB for NO_KAB={key}")
        row: dict[str, Any] = {
            "NO_PROP": province_code,
            "NO_KAB": key,
            "NAMA_PROP": str(attrs["NAMA_PROP"]).strip(),
            "NAMA_KAB": name.strip(),
        }
        for field in numeric_fields:
            row[field] = validate_numeric(attrs.get(field), field, key)
        parsed.append(row)

    if seen != expected_keys:
        raise DibiMaterializationError(f"corrected DIBI key-set mismatch missing={sorted(expected_keys-seen)}")
    return sorted(parsed, key=lambda row: int(row["NO_KAB"]))


def build(mode: str) -> dict[str, Any]:
    contract, amendment, qualification_path, transport_amendment_path, metadata_path, transport_amendment = load_and_validate_contracts()
    preferred_path, response_path, sidecar_path, response_payload = acquire_raw(
        contract=contract,
        representation_amendment=amendment,
        transport_amendment=transport_amendment,
        qualification_path=qualification_path,
        transport_amendment_path=transport_amendment_path,
        metadata_path=metadata_path,
        mode=mode,
    )
    rows = parse_features(contract, amendment, response_payload)

    output = contract["output"]
    component_path = ROOT / str(output["component_frame"])
    provenance_path = ROOT / str(output["provenance_frame"])
    manifest_path = ROOT / str(output["manifest"])
    numeric_fields = [str(value) for value in contract["numeric_fields"]["retained_source_native_fields"]]

    component_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        key = int(row["NO_KAB"])
        component: dict[str, Any] = {
            "geography_id": f"idn.13.{key:04d}",
            "NO_PROP": int(row["NO_PROP"]),
            "NO_KAB": key,
            "NAMA_PROP": row["NAMA_PROP"],
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
                "NO_KAB": key,
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
                "representation_amendment_path": rel(REPRESENTATION_AMENDMENT_PATH),
                "representation_amendment_sha256": sha256_path(REPRESENTATION_AMENDMENT_PATH),
                "source_geography_key": "NO_KAB",
                "source_field_semantics_preserved_without_renaming": "true",
            }
        )

    component_fields = [
        "geography_id", "NO_PROP", "NO_KAB", "NAMA_PROP", "NAMA_KAB",
        "coverage_start_year", "coverage_end_year", *numeric_fields,
        "source_id", "component_class", "claim_type",
        "semantic_interpretation_of_abbreviated_field_names_authorized",
        "event_level_record_inference_authorized", "observed_impact_inference_authorized",
        "risk_synthesis_authorized",
    ]
    provenance_fields = [
        "geography_id", "NO_KAB", "source_record_order_after_local_sort",
        "raw_response_path", "raw_response_sha256", "request_sidecar_path",
        "request_sidecar_sha256", "preferred_service_status_path",
        "preferred_service_status_sha256", "transport_fallback_used",
        "qualified_layer_id", "qualified_layer_name", "representation_amendment_path",
        "representation_amendment_sha256", "source_geography_key",
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
        "exact_geography_key_set_pass": len(component_rows) == int(amendment["corrected_representation"]["expected_feature_count"]),
        "source_geography_key": "NO_KAB",
        "source_province_filter": "NO_PROP = 13",
        "representation_amendment_applied": True,
        "retained_source_native_numeric_fields": numeric_fields,
        "source_field_renaming_performed": False,
        "cross_field_sum_performed": False,
        "cross_field_ratio_performed": False,
        "annualization_performed": False,
        "imputation_performed": False,
        "semantic_interpretation_of_abbreviated_field_names_performed": False,
        "preferred_service_runtime_unavailable_evidence": {"path": rel(preferred_path), "sha256": sha256_path(preferred_path)},
        "transport_fallback_used": True,
        "transport_fallback_authorized": bool(transport_amendment["fallback_authorized_only_when_preferred_endpoint_reports_runtime_unavailable"]),
        "raw_response": {"path": rel(response_path), "sha256": sha256_path(response_path), "bytes": response_path.stat().st_size},
        "request_sidecar": {"path": rel(sidecar_path), "sha256": sha256_path(sidecar_path)},
        "contract": {"path": rel(CONTRACT_PATH), "sha256": sha256_path(CONTRACT_PATH)},
        "representation_amendment": {"path": rel(REPRESENTATION_AMENDMENT_PATH), "sha256": sha256_path(REPRESENTATION_AMENDMENT_PATH)},
        "source_qualification": {"path": rel(qualification_path), "sha256": sha256_path(qualification_path)},
        "transport_amendment": {"path": rel(transport_amendment_path), "sha256": sha256_path(transport_amendment_path)},
        "source_metadata": {"path": rel(metadata_path), "sha256": sha256_path(metadata_path)},
        "outputs": {
            "component_frame": rel(component_path),
            "component_frame_sha256": sha256_path(component_path),
            "provenance_frame": rel(provenance_path),
            "provenance_frame_sha256": sha256_path(provenance_path),
        },
        "offline_rebuild_required": bool(contract["reproducibility"]["offline_rebuild_required"]),
        "live_and_offline_outputs_must_be_byte_identical": bool(contract["reproducibility"]["live_and_offline_outputs_must_be_byte_identical"]),
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
    print(json.dumps({
        "mode": args.mode,
        "geography_count": manifest["geography_count"],
        "source_geography_key": manifest["source_geography_key"],
        "transport_fallback_used": manifest["transport_fallback_used"],
        "retained_source_native_numeric_fields": manifest["retained_source_native_numeric_fields"],
        "component_frame": manifest["outputs"]["component_frame"],
        "manifest": rel(ROOT / "data/manifests/milestone26_stage1_dibi_occurrence_context.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
