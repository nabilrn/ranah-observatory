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

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_mapserver_identity_contract.json"
IMAGE_EVIDENCE = ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_population_2020.json"
PILOT_EVIDENCE = ROOT / "data/manifests/milestone26_population_export_json_transport.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_mapserver_identity"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_mapserver_identity.json"


class M26PopulationMapServerError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-population-mapserver-identity-contract/v1":
        raise M26PopulationMapServerError("unexpected MapServer identity contract schema")
    if payload.get("locked_before_live_probe") is not True:
        raise M26PopulationMapServerError("MapServer identity contract is not locked")
    for key in (
        "numeric_aggregation_authorized",
        "substantive_value_promotion_authorized",
        "cross_geography_numeric_extraction_authorized",
        "pilot_selection_changed",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26PopulationMapServerError(f"invalid locked boundary: {key}")
    return payload


def request_once(url: str, timeout: float = 20.0) -> dict[str, Any]:
    started = time.monotonic()
    body = b""
    status: int | None = None
    content_type = ""
    final_url = url
    exception_class: str | None = None
    exception_message: str | None = None
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            final_url = str(response.geturl())
            content_type = str(response.headers.get("Content-Type", ""))
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        final_url = str(exc.geturl())
        content_type = str(exc.headers.get("Content-Type", "")) if exc.headers else ""
        try:
            body = exc.read()
        except Exception:
            body = b""
        exception_class = type(exc).__name__
        exception_message = str(exc)
    except Exception as exc:
        exception_class = type(exc).__name__
        exception_message = str(exc)
    return {
        "status": status,
        "content_type": content_type,
        "final_url": final_url,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "exception_class": exception_class,
        "exception_message": exception_message,
        "body": body,
    }


def parse_json(body: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def extent_tuple(payload: dict[str, Any] | None) -> tuple[float, float, float, float] | None:
    if not isinstance(payload, dict):
        return None
    extent = payload.get("fullExtent") if isinstance(payload.get("fullExtent"), dict) else payload.get("extent")
    if not isinstance(extent, dict):
        return None
    try:
        return tuple(float(extent[key]) for key in ("xmin", "ymin", "xmax", "ymax"))  # type: ignore[return-value]
    except (KeyError, TypeError, ValueError):
        return None


def extent_matches(left: tuple[float, ...] | None, right: tuple[float, ...] | None, tolerance: float) -> bool:
    return bool(left and right and len(left) == 4 and len(right) == 4 and all(abs(a - b) <= tolerance for a, b in zip(left, right)))


def wkid(payload: dict[str, Any] | None) -> int | None:
    if not isinstance(payload, dict):
        return None
    sr = payload.get("spatialReference")
    if not isinstance(sr, dict) and isinstance(payload.get("extent"), dict):
        sr = payload["extent"].get("spatialReference")
    if not isinstance(sr, dict) and isinstance(payload.get("fullExtent"), dict):
        sr = payload["fullExtent"].get("spatialReference")
    if not isinstance(sr, dict):
        return None
    value = sr.get("latestWkid", sr.get("wkid"))
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def raw_pixel_candidate(identify_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(identify_payload, dict):
        return None
    results = identify_payload.get("results")
    if not isinstance(results, list):
        return None
    for result in results:
        if not isinstance(result, dict) or result.get("layerId") != 0:
            continue
        display = str(result.get("displayFieldName") or "").strip().casefold()
        value = parse_number(result.get("value"))
        if display in {"pixel value", "pixel_value"} and value is not None:
            return {"field": result.get("displayFieldName"), "value": value, "location": "result.value"}
        attrs = result.get("attributes")
        if isinstance(attrs, dict):
            for key, candidate in attrs.items():
                normalized = str(key).strip().casefold().replace("_", " ")
                if normalized != "pixel value":
                    continue
                value = parse_number(candidate)
                if value is not None:
                    return {"field": str(key), "value": value, "location": "result.attributes"}
    return None


def frozen_reference() -> tuple[dict[str, Any], dict[str, Any]]:
    image = json.loads(IMAGE_EVIDENCE.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT_EVIDENCE.read_text(encoding="utf-8"))
    return image, pilot


def save_response(name: str, response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    body = response.pop("body")
    path = OUT_DIR / f"{name}.body"
    path.write_bytes(body)
    payload = parse_json(body)
    record = {
        **response,
        "body_path": path.relative_to(ROOT).as_posix(),
        "body_bytes": len(body),
        "body_sha256": sha256_bytes(body),
        "json_parseable": payload is not None,
        "arcgis_error_present": bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict)),
    }
    return record, payload


def run() -> dict[str, Any]:
    contract = load_contract()
    image_evidence, pilot_evidence = frozen_reference()
    image_meta = image_evidence.get("primary") if isinstance(image_evidence.get("primary"), dict) else {}
    image_extent = extent_tuple(image_meta)
    image_wkid = wkid(image_meta)
    image_title = str(image_evidence.get("extra", {}).get("info/iteminfo", {}).get("payload", {}).get("title") or "")

    bbox = pilot_evidence["pilot"]["bbox_native"]
    xmin, ymin, xmax, ymax = (float(value) for value in bbox)
    x = (xmin + xmax) / 2.0
    y = (ymin + ymax) / 2.0
    mapserver = str(contract["candidate_mapserver"]).rstrip("/")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    service_record, service_payload = save_response("mapserver-service", request_once(mapserver + "?f=pjson"))
    layer_record, layer_payload = save_response("mapserver-layer-0", request_once(mapserver + "/0?f=pjson"))

    params = {
        "geometry": f"{x:.6f},{y:.6f}",
        "geometryType": "esriGeometryPoint",
        "sr": "3395",
        "layers": "all:0",
        "tolerance": "1",
        "mapExtent": f"{x-100:.6f},{y-100:.6f},{x+100:.6f},{y+100:.6f}",
        "imageDisplay": "200,200,96",
        "returnGeometry": "false",
        "f": "json",
    }
    identify_url = mapserver + "/identify?" + urllib.parse.urlencode(params)
    identify_record, identify_payload = save_response("mapserver-identify", request_once(identify_url, timeout=30.0))

    service_layers = service_payload.get("layers") if isinstance(service_payload, dict) else None
    service_layer_match = bool(
        isinstance(service_layers, list)
        and any(isinstance(row, dict) and row.get("id") == 0 and row.get("name") == contract["required_layer_name"] for row in service_layers)
    )
    title_match = bool(isinstance(layer_payload, dict) and layer_payload.get("name") == contract["required_layer_name"] and image_title == contract["required_layer_name"])
    type_match = bool(isinstance(layer_payload, dict) and layer_payload.get("type") == contract["required_layer_type"])
    candidate_wkid = wkid(layer_payload) or wkid(service_payload)
    crs_match = candidate_wkid == int(contract["required_crs_epsg"]) == image_wkid
    candidate_extent = extent_tuple(layer_payload) or extent_tuple(service_payload)
    extent_match = extent_matches(candidate_extent, image_extent, float(contract["extent_absolute_tolerance_m"]))
    official_host_match = urllib.parse.urlparse(mapserver).hostname == "gis.bnpb.go.id"
    identity_gate_passed = all((official_host_match, service_layer_match, title_match, type_match, crs_match, extent_match))

    pixel = raw_pixel_candidate(identify_payload)
    identify_transport_success = bool(identify_record["status"] == 200 and identify_record["exception_class"] is None and not identify_record["arcgis_error_present"])
    raw_pixel_surface_observed = bool(identity_gate_passed and identify_transport_success and pixel is not None)

    manifest = {
        "schema": "ranah-observatory/milestone26-population-mapserver-identity/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "source_id": contract["source_id"],
        "candidate_mapserver": mapserver,
        "frozen_image_server_reference": {
            "path": IMAGE_EVIDENCE.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(IMAGE_EVIDENCE.read_bytes()).hexdigest(),
            "title": image_title,
            "crs_epsg": image_wkid,
            "full_extent": list(image_extent) if image_extent else None,
        },
        "pilot": {"geography_id": pilot_evidence["pilot"]["pilot_geography_id"], "center_x": x, "center_y": y, "selection_changed": False},
        "responses": {"service": service_record, "layer_0": layer_record, "identify": identify_record},
        "identity_gates": {
            "official_bnpb_same_host": official_host_match,
            "service_layer_name_match": service_layer_match,
            "exact_layer_title_match": title_match,
            "raster_layer_type_match": type_match,
            "crs_match": crs_match,
            "full_extent_match": extent_match,
            "all_identity_gates_passed": identity_gate_passed,
        },
        "candidate_layer": {
            "title": layer_payload.get("name") if isinstance(layer_payload, dict) else None,
            "type": layer_payload.get("type") if isinstance(layer_payload, dict) else None,
            "crs_epsg": candidate_wkid,
            "extent": list(candidate_extent) if candidate_extent else None,
        },
        "identify_transport_success": identify_transport_success,
        "raw_pixel_candidate": pixel,
        "raw_pixel_surface_observed": raw_pixel_surface_observed,
        "same_dataset_transport_candidate_qualified": identity_gate_passed,
        "stage1_population_aggregation_authorized": False,
        "numeric_aggregation_performed": False,
        "substantive_value_promotion_performed": False,
        "cross_geography_numeric_extraction_performed": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
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
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "identity_gate_passed": manifest["identity_gates"]["all_identity_gates_passed"],
        "identify_transport_success": manifest["identify_transport_success"],
        "raw_pixel_surface_observed": manifest["raw_pixel_surface_observed"],
        "stage1_population_aggregation_authorized": manifest["stage1_population_aggregation_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
