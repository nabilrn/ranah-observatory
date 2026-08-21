#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from scripts import materialize_milestone26_stage1_components as stage1
from scripts import probe_milestone26_statistics_transport as stats_v1
from scripts import probe_milestone26_statistics_transport_v2 as stats_v2
from scripts import probe_milestone26_statistics_transport_v3 as stats_v3

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_transport_capability_diagnostic_contract.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_transport_capability_diagnostic"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_transport_capability_diagnostic.json"
SOURCE_ID = "inarisk_population_2020"


class M26PopulationTransportDiagnosticError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-population-transport-capability-diagnostic-contract/v1":
        raise M26PopulationTransportDiagnosticError("unexpected diagnostic contract schema")
    if payload.get("locked_before_live_capability_probe") is not True:
        raise M26PopulationTransportDiagnosticError("diagnostic contract was not pre-locked")
    if payload.get("source_id") != SOURCE_ID:
        raise M26PopulationTransportDiagnosticError("diagnostic source drift")
    for key in (
        "substantive_value_promotion_authorized",
        "equivalence_decision_authorized",
        "aggregation_semantics_changed",
        "source_family_changed",
        "cross_geography_numeric_extraction_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26PopulationTransportDiagnosticError(f"invalid diagnostic boundary: {key}")
    return payload


def json_surface(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"json_parseable": False, "json_top_level_keys": [], "arcgis_error_present": False, "arcgis_error_code": None}
    if not isinstance(payload, dict):
        return {"json_parseable": True, "json_top_level_keys": [], "arcgis_error_present": False, "arcgis_error_code": None}
    error = payload.get("error")
    return {
        "json_parseable": True,
        "json_top_level_keys": sorted(str(key) for key in payload.keys()),
        "arcgis_error_present": isinstance(error, dict),
        "arcgis_error_code": error.get("code") if isinstance(error, dict) else None,
    }


def request_diagnostic(name: str, endpoint: str, params: dict[str, str], timeout: float) -> dict[str, Any]:
    url = endpoint + "?" + urllib.parse.urlencode(params)
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

    elapsed = time.monotonic() - started
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body_path = OUT_DIR / f"{name}.body"
    body_path.write_bytes(body)
    surface = json_surface(body)
    return {
        "operation": name,
        "requested_url_length": len(url),
        "final_url": final_url,
        "http_status": status,
        "content_type": content_type,
        "elapsed_seconds": round(elapsed, 6),
        "exception_class": exception_class,
        "exception_message": exception_message,
        "response_body_path": body_path.relative_to(ROOT).as_posix(),
        "response_body_bytes": len(body),
        "response_body_sha256": sha256_bytes(body),
        "error_body_preview": body[:500].decode("utf-8", errors="replace") if status is not None and status >= 400 else "",
        **surface,
        "transport_success": status == 200 and not surface["arcgis_error_present"] and exception_class is None,
    }


def build_requests() -> tuple[str, dict[str, tuple[str, dict[str, str]]], dict[str, Any]]:
    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    source_urls = stage1.registry_urls()
    service = source_urls[SOURCE_ID]
    features, big_probe = stage1.load_qualified_big_features()
    capacity_meta = stage1.source_metadata("inarisk_capacity_2021")
    pilot_feature, projected, _bbox, _width, _height = stats_v1.select_geometry_only_pilot(features, capacity_meta)
    source_meta = stage1.source_metadata(SOURCE_ID)
    bbox, width, height = stage1.aligned_window(projected.bounds, source_meta)
    centers = sorted(stats_v3.grid_centers_inside_polygon(projected, bbox, width, height), key=lambda point: (point[0], point[1]))
    point = centers[0]
    point_geometry = {"x": point[0], "y": point[1], "spatialReference": {"wkid": 3395}}
    polygon_geometry = stats_v2.arcgis_polygon_xy(projected)

    requests = {
        "computeStatisticsHistograms": (
            service.rstrip("/") + "/computeStatisticsHistograms",
            {
                "geometry": json.dumps(polygon_geometry, separators=(",", ":")),
                "geometryType": "esriGeometryPolygon",
                "pixelSize": "100,100",
                "processAsMultidimensional": "false",
                "f": "json",
            },
        ),
        "getSamples": (
            service.rstrip("/") + "/getSamples",
            {
                "geometry": json.dumps(point_geometry, separators=(",", ":")),
                "geometryType": "esriGeometryPoint",
                "pixelSize": "100,100",
                "interpolation": "RSP_NearestNeighbor",
                "returnFirstValueOnly": "true",
                "f": "json",
            },
        ),
        "identify": (
            service.rstrip("/") + "/identify",
            {
                "geometry": json.dumps(point_geometry, separators=(",", ":")),
                "geometryType": "esriGeometryPoint",
                "pixelSize": "100,100",
                "returnGeometry": "false",
                "returnCatalogItems": "false",
                "returnPixelValues": "false",
                "processAsMultidimensional": "false",
                "f": "json",
            },
        ),
    }
    pilot = {
        "geography_id": pilot_feature["geography_id"],
        "geography_name": pilot_feature["geography_name"],
        "population_aligned_window": {"bbox_native": list(bbox), "width": width, "height": height},
        "diagnostic_point": point,
        "native_center_count_inside_pilot": len(centers),
        "big_expected_edition": big_probe.get("expected_edition"),
    }
    return service, requests, pilot


def run() -> dict[str, Any]:
    contract = load_contract()
    service, requests, pilot = build_requests()
    timeout = float(contract["timeout_seconds"])
    outcomes = {
        name: request_diagnostic(name, endpoint, params, timeout)
        for name, (endpoint, params) in requests.items()
    }
    manifest = {
        "schema": "ranah-observatory/milestone26-population-transport-capability-diagnostic/v1",
        "milestone": 26,
        "stage": "stage1_transport_diagnostic",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "source_id": SOURCE_ID,
        "service_url": service,
        "pilot": pilot,
        "operation_outcomes": outcomes,
        "operation_count": len(outcomes),
        "substantive_value_promotion_performed": False,
        "equivalence_decision_performed": False,
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
        payload = run()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({name: {"status": item["http_status"], "success": item["transport_success"], "exception": item["exception_class"]} for name, item in payload["operation_outcomes"].items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
