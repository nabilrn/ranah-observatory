#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
AMENDMENT_PATH = ROOT / "data/manifests/milestone26_dibi_transport_amendment.json"
SOURCE_METADATA_PATH = ROOT / "data/processed/bnpb/m26_source_qualification/dibi_kabupaten_hidromet_2015_2024.json"
RAW_ROOT = ROOT / "data/processed/bnpb/m26_dibi_geography_probe"
RAW_PATH = RAW_ROOT / "identifier-only-kabupaten.json"
PREFERRED_STATUS_PATH = RAW_ROOT / "preferred-service-status.json"
REQUEST_SIDECAR_PATH = RAW_ROOT / "identifier-only-query.request.json"
MANIFEST_PATH = ROOT / "data/manifests/milestone26_dibi_geography_representation_probe.json"

IDENTIFIER_FIELDS = ["id_kab_bps", "NAMA_KAB", "NAMA_PROP", "KABKOTA", "NO_PROP", "NO_KAB"]
FORBIDDEN_NUMERIC_OCCURRENCE_FIELDS = ["Total_basa", "Total_ba_1", "Total_keri"]


class DibiGeographyProbeError(RuntimeError):
    pass


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
                    raise DibiGeographyProbeError(f"HTTP {response.status}: {url}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()
        except (urllib.error.URLError, TimeoutError, DibiGeographyProbeError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)
    raise DibiGeographyProbeError(f"request failed after retries: {url}") from last_error


def load_json_bytes(body: bytes, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        preview = body[:300].decode("utf-8", errors="replace")
        raise DibiGeographyProbeError(f"{label} is not valid JSON: {preview}") from exc
    if not isinstance(payload, dict):
        raise DibiGeographyProbeError(f"{label} JSON root must be an object")
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
        parts.extend(str(value) for value in details)
    elif details is not None:
        parts.append(str(details))
    text = " ".join(parts).casefold()
    return code == 500 and ("not started" in text or ("service" in text and "started" in text))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def numeric_equal(value: Any, expected: int) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number == float(expected)


def validate_source_metadata(amendment: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    if amendment.get("schema") != "ranah-observatory/milestone26-dibi-transport-amendment/v1":
        raise DibiGeographyProbeError("unexpected DIBI transport amendment schema")
    if amendment.get("source_id") != "dibi_kabupaten_hidromet_2015_2024":
        raise DibiGeographyProbeError("unexpected DIBI source id")
    extra = metadata.get("extra")
    layer_record = extra.get(str(amendment["fallback_layer_id"])) if isinstance(extra, dict) else None
    layer = layer_record.get("payload") if isinstance(layer_record, dict) else None
    if not isinstance(layer, dict):
        raise DibiGeographyProbeError("frozen DIBI metadata lacks fallback layer payload")
    if int(layer.get("id")) != int(amendment["fallback_layer_id"]):
        raise DibiGeographyProbeError("fallback layer id drift")
    if layer.get("name") != amendment["fallback_layer_name"]:
        raise DibiGeographyProbeError("fallback layer name drift")
    fields = {
        str(item.get("name"))
        for item in layer.get("fields", [])
        if isinstance(item, dict) and item.get("name") is not None
    }
    missing = [field for field in IDENTIFIER_FIELDS if field not in fields]
    if missing:
        raise DibiGeographyProbeError(f"identifier-only probe fields missing from frozen layer metadata: {missing}")
    if any(field in IDENTIFIER_FIELDS for field in FORBIDDEN_NUMERIC_OCCURRENCE_FIELDS):
        raise DibiGeographyProbeError("numeric occurrence field leaked into identifier-only field list")
    return layer


def query_url(service: str, layer_id: int) -> str:
    params = {
        "where": "1=1",
        "outFields": ",".join(IDENTIFIER_FIELDS),
        "returnGeometry": "false",
        "f": "json",
    }
    return service.rstrip("/") + f"/{layer_id}/query?" + urllib.parse.urlencode(params)


def sorted_identifier_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("error"), dict):
        raise DibiGeographyProbeError(f"identifier-only query returned ArcGIS error: {payload['error']}")
    features = payload.get("features")
    if not isinstance(features, list):
        raise DibiGeographyProbeError("identifier-only query has no feature list")
    rows: list[dict[str, Any]] = []
    for feature in features:
        attrs = feature.get("attributes") if isinstance(feature, dict) else None
        if not isinstance(attrs, dict):
            raise DibiGeographyProbeError("identifier-only feature lacks attributes")
        if any(field in attrs for field in FORBIDDEN_NUMERIC_OCCURRENCE_FIELDS):
            raise DibiGeographyProbeError("numeric occurrence field unexpectedly returned by identifier-only query")
        rows.append({field: attrs.get(field) for field in IDENTIFIER_FIELDS})
    return sorted(
        rows,
        key=lambda row: (
            normalize_text(row.get("NAMA_PROP")),
            normalize_text(row.get("NAMA_KAB")),
            str(row.get("id_kab_bps")),
        ),
    )


def is_sumbar_candidate(row: dict[str, Any]) -> bool:
    province_name = normalize_text(row.get("NAMA_PROP"))
    return province_name == "SUMATERA BARAT" or numeric_equal(row.get("NO_PROP"), 13)


def compact_value_set(rows: list[dict[str, Any]], field: str) -> list[Any]:
    values: list[Any] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(field)
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            values.append(value)
    return values


def build(mode: str) -> dict[str, Any]:
    amendment = json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))
    metadata = json.loads(SOURCE_METADATA_PATH.read_text(encoding="utf-8"))
    layer = validate_source_metadata(amendment, metadata)

    preferred_url = amendment["preferred_endpoint"].rstrip("/") + "?f=pjson"
    fallback_url = query_url(amendment["fallback_endpoint"], int(amendment["fallback_layer_id"]))

    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    if mode == "live":
        preferred_final, preferred_type, preferred_body = request_bytes(preferred_url)
        preferred_payload = load_json_bytes(preferred_body, "preferred DIBI service status")
        if not preferred_runtime_unavailable(preferred_payload):
            raise DibiGeographyProbeError(
                "preferred DIBI endpoint no longer matches the frozen runtime-unavailable fallback trigger"
            )
        PREFERRED_STATUS_PATH.write_bytes(preferred_body)

        final_url, content_type, raw_body = request_bytes(fallback_url)
        raw_payload = load_json_bytes(raw_body, "identifier-only DIBI query")
        RAW_PATH.write_bytes(raw_body)
        sidecar = {
            "schema": "ranah-observatory/milestone26-dibi-geography-probe-request/v1",
            "source_id": amendment["source_id"],
            "preferred_status_requested_url": preferred_url,
            "preferred_status_final_url": preferred_final,
            "preferred_status_content_type": preferred_type,
            "preferred_status_path": rel(PREFERRED_STATUS_PATH),
            "preferred_status_sha256": sha256_bytes(preferred_body),
            "fallback_query_requested_url": fallback_url,
            "fallback_query_final_url": final_url,
            "fallback_query_content_type": content_type,
            "fallback_layer_id": int(amendment["fallback_layer_id"]),
            "fallback_layer_name": amendment["fallback_layer_name"],
            "requested_fields": IDENTIFIER_FIELDS,
            "forbidden_numeric_occurrence_fields": FORBIDDEN_NUMERIC_OCCURRENCE_FIELDS,
            "numeric_occurrence_fields_requested": False,
            "raw_path": rel(RAW_PATH),
            "raw_sha256": sha256_bytes(raw_body),
            "raw_bytes": len(raw_body),
            "transport_amendment_path": rel(AMENDMENT_PATH),
            "transport_amendment_sha256": sha256_path(AMENDMENT_PATH),
            "source_metadata_path": rel(SOURCE_METADATA_PATH),
            "source_metadata_sha256": sha256_path(SOURCE_METADATA_PATH),
        }
        write_json(REQUEST_SIDECAR_PATH, sidecar)
    else:
        for path in (PREFERRED_STATUS_PATH, RAW_PATH, REQUEST_SIDECAR_PATH):
            if not path.exists():
                raise DibiGeographyProbeError(f"offline geography-probe evidence missing: {rel(path)}")
        preferred_body = PREFERRED_STATUS_PATH.read_bytes()
        if not preferred_runtime_unavailable(load_json_bytes(preferred_body, "frozen preferred status")):
            raise DibiGeographyProbeError("frozen preferred-service status no longer proves fallback trigger")
        raw_body = RAW_PATH.read_bytes()
        raw_payload = load_json_bytes(raw_body, "frozen identifier-only query")
        sidecar = json.loads(REQUEST_SIDECAR_PATH.read_text(encoding="utf-8"))
        if sidecar.get("numeric_occurrence_fields_requested") is not False:
            raise DibiGeographyProbeError("frozen geography probe sidecar requested numeric occurrence fields")
        if sidecar.get("requested_fields") != IDENTIFIER_FIELDS:
            raise DibiGeographyProbeError("frozen geography probe requested-field drift")
        if sidecar.get("fallback_query_requested_url") != fallback_url:
            raise DibiGeographyProbeError("frozen geography probe query drift")
        if sidecar.get("raw_sha256") != sha256_path(RAW_PATH):
            raise DibiGeographyProbeError("frozen identifier-only response checksum mismatch")
        if sidecar.get("preferred_status_sha256") != sha256_path(PREFERRED_STATUS_PATH):
            raise DibiGeographyProbeError("frozen preferred status checksum mismatch")
        if sidecar.get("transport_amendment_sha256") != sha256_path(AMENDMENT_PATH):
            raise DibiGeographyProbeError("transport amendment checksum drift")
        if sidecar.get("source_metadata_sha256") != sha256_path(SOURCE_METADATA_PATH):
            raise DibiGeographyProbeError("source metadata checksum drift")

    rows = sorted_identifier_rows(raw_payload)
    candidates = [row for row in rows if is_sumbar_candidate(row)]
    candidate_ids = compact_value_set(candidates, "id_kab_bps")
    candidate_names = compact_value_set(candidates, "NAMA_KAB")

    payload = {
        "schema": "ranah-observatory/milestone26-dibi-geography-representation-probe/v1",
        "milestone": 26,
        "stage": "representation_only_probe_before_dibi_numeric_contract_amendment",
        "source_id": amendment["source_id"],
        "fallback_layer_id": int(amendment["fallback_layer_id"]),
        "fallback_layer_name": amendment["fallback_layer_name"],
        "layer_max_record_count": int(layer.get("maxRecordCount", 0)),
        "identifier_fields_requested": IDENTIFIER_FIELDS,
        "numeric_occurrence_fields_forbidden": FORBIDDEN_NUMERIC_OCCURRENCE_FIELDS,
        "numeric_occurrence_fields_requested": False,
        "all_feature_count": len(rows),
        "sumbar_candidate_rule": "NAMA_PROP normalized equals SUMATERA BARAT OR NO_PROP numerically equals 13",
        "sumbar_candidate_count": len(candidates),
        "sumbar_candidate_id_kab_bps_values": candidate_ids,
        "sumbar_candidate_nama_kab_values": candidate_names,
        "sumbar_candidates": candidates,
        "representation_contract_amendment_required": True,
        "numeric_occurrence_values_inspected": False,
        "numeric_occurrence_values_promoted": False,
        "event_level_record_inference_performed": False,
        "observed_impact_inference_performed": False,
        "substantive_interpretation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "raw_identifier_response": {
            "path": rel(RAW_PATH),
            "sha256": sha256_path(RAW_PATH),
            "bytes": RAW_PATH.stat().st_size,
        },
        "preferred_service_status": {
            "path": rel(PREFERRED_STATUS_PATH),
            "sha256": sha256_path(PREFERRED_STATUS_PATH),
        },
        "request_sidecar": {
            "path": rel(REQUEST_SIDECAR_PATH),
            "sha256": sha256_path(REQUEST_SIDECAR_PATH),
        },
        "transport_amendment": {"path": rel(AMENDMENT_PATH), "sha256": sha256_path(AMENDMENT_PATH)},
        "source_metadata": {"path": rel(SOURCE_METADATA_PATH), "sha256": sha256_path(SOURCE_METADATA_PATH)},
    }
    write_json(MANIFEST_PATH, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe DIBI kabupaten geography representation without occurrence values")
    parser.add_argument("--mode", choices=("live", "offline"), default="offline")
    args = parser.parse_args()
    payload = build(args.mode)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "all_feature_count": payload["all_feature_count"],
                "sumbar_candidate_count": payload["sumbar_candidate_count"],
                "sumbar_candidate_id_kab_bps_values": payload["sumbar_candidate_id_kab_bps_values"],
                "numeric_occurrence_fields_requested": payload["numeric_occurrence_fields_requested"],
                "manifest": rel(MANIFEST_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
