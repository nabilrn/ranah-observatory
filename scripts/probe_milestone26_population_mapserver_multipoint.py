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
CONTRACT = ROOT / "data/manifests/milestone26_population_mapserver_multipoint_contract.json"
SEMANTICS = ROOT / "data/manifests/milestone26_population_mapserver_pixel_semantics_amendment.json"
IDENTITY = ROOT / "data/manifests/milestone26_population_mapserver_identity.json"
IMAGE_EVIDENCE = ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_population_2020.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_mapserver_multipoint"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_mapserver_multipoint.json"


class M26PopulationMultipointError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_locked_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    image = json.loads(IMAGE_EVIDENCE.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-mapserver-multipoint-contract/v1":
        raise M26PopulationMultipointError("unexpected multipoint contract schema")
    if contract.get("locked_before_live_probe") is not True:
        raise M26PopulationMultipointError("multipoint contract is not locked")
    if semantics.get("locked_before_multipoint_probe") is not True:
        raise M26PopulationMultipointError("pixel semantic amendment is not locked")
    if semantics.get("semantic_binding", {}).get("accepted_field_name") != "Stretch.Pixel Value":
        raise M26PopulationMultipointError("unexpected accepted pixel field")
    if identity.get("identity_gates", {}).get("all_identity_gates_passed") is not True:
        raise M26PopulationMultipointError("MapServer identity gate is not qualified")
    if identity.get("same_dataset_transport_candidate_qualified") is not True:
        raise M26PopulationMultipointError("same-dataset transport candidate is not qualified")
    for payload in (contract, semantics):
        for key in (
            "numeric_aggregation_authorized",
            "substantive_value_promotion_authorized",
            "cross_geography_numeric_extraction_authorized",
            "aggregation_semantics_changed",
            "source_family_changed",
            "minimum_valid_fraction_changed",
            "risk_synthesis_authorized",
            "statistical_model_fit_authorized",
            "causal_claim_authorized",
            "monetary_wasted_potential_estimate_authorized",
        ):
            if payload.get(key) is not False:
                raise M26PopulationMultipointError(f"invalid locked boundary: {key}")
    return contract, semantics, identity, image


def request_once(url: str, timeout: float = 30.0) -> dict[str, Any]:
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


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def extract_pixel_result(result: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    if result.get("layerId") != 0:
        return None
    attrs = result.get("attributes")
    if not isinstance(attrs, dict) or field_name not in attrs:
        return None
    value = finite_number(attrs[field_name])
    if value is None:
        return None
    geometry = result.get("geometry") if isinstance(result.get("geometry"), dict) else None
    point = None
    if geometry is not None:
        x = finite_number(geometry.get("x"))
        y = finite_number(geometry.get("y"))
        if x is not None and y is not None:
            point = [x, y]
    return {"value": value, "geometry": point, "field": field_name}


def one_to_one_geometry_match(input_points: list[list[float]], results: list[dict[str, Any]], tolerance: float) -> bool:
    result_points = [row.get("geometry") for row in results]
    if any(not isinstance(point, list) or len(point) != 2 for point in result_points):
        return False
    unmatched = list(range(len(result_points)))
    for source in input_points:
        matched_index = None
        for index in unmatched:
            target = result_points[index]
            if abs(float(source[0]) - float(target[0])) <= tolerance and abs(float(source[1]) - float(target[1])) <= tolerance:
                matched_index = index
                break
        if matched_index is None:
            return False
        unmatched.remove(matched_index)
    return not unmatched


def run() -> dict[str, Any]:
    contract, semantics, identity, image = load_locked_inputs()
    base_x = float(identity["pilot"]["center_x"])
    base_y = float(identity["pilot"]["center_y"])
    offsets = contract["pilot_rule"]["points"]
    points = [[base_x + float(dx), base_y + float(dy)] for dx, dy in offsets]
    geometry = {"points": points, "spatialReference": {"wkid": 3395}}
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    mapserver = str(contract["candidate_mapserver"]).rstrip("/")
    params = {
        "geometry": json.dumps(geometry, separators=(",", ":")),
        "geometryType": "esriGeometryMultipoint",
        "sr": "3395",
        "layers": "all:0",
        "tolerance": "1",
        "mapExtent": f"{min(xs)-100:.6f},{min(ys)-100:.6f},{max(xs)+100:.6f},{max(ys)+100:.6f}",
        "imageDisplay": "400,400,96",
        "returnGeometry": "true",
        "f": "json",
    }
    url = mapserver + "/identify?" + urllib.parse.urlencode(params)
    response = request_once(url)
    body = response.pop("body")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body_path = OUT_DIR / "multipoint-identify.body"
    body_path.write_bytes(body)
    payload = parse_json(body)
    response_record = {
        **response,
        "requested_url": url,
        "requested_url_length": len(url),
        "body_path": body_path.relative_to(ROOT).as_posix(),
        "body_bytes": len(body),
        "body_sha256": sha256_bytes(body),
        "json_parseable": payload is not None,
        "arcgis_error_present": bool(isinstance(payload, dict) and isinstance(payload.get("error"), dict)),
    }

    field_name = semantics["semantic_binding"]["accepted_field_name"]
    raw_results = payload.get("results") if isinstance(payload, dict) and isinstance(payload.get("results"), list) else []
    parsed_results = [candidate for row in raw_results if isinstance(row, dict) and (candidate := extract_pixel_result(row, field_name)) is not None]
    image_meta = image.get("primary") if isinstance(image.get("primary"), dict) else {}
    min_value = float(image_meta["minValues"][0])
    max_value = float(image_meta["maxValues"][0])
    range_match = bool(parsed_results and all(min_value <= row["value"] <= max_value for row in parsed_results))
    result_count_match = len(parsed_results) == len(points) == int(contract["pilot_rule"]["point_count"])
    geometry_match = one_to_one_geometry_match(points, parsed_results, float(contract["qualification_gates"]["one_to_one_result_geometry_match_to_input_points_within_meters"]))
    transport_ok = bool(response_record["status"] == 200 and response_record["exception_class"] is None and not response_record["arcgis_error_present"])
    multipoint_qualified = bool(transport_ok and result_count_match and range_match and geometry_match)

    manifest = {
        "schema": "ranah-observatory/milestone26-population-mapserver-multipoint/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "semantic_amendment": {"path": SEMANTICS.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(SEMANTICS.read_bytes()).hexdigest()},
        "identity_evidence": {"path": IDENTITY.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(IDENTITY.read_bytes()).hexdigest()},
        "input_points": points,
        "input_point_count": len(points),
        "accepted_pixel_field": field_name,
        "frozen_valid_range": [min_value, max_value],
        "response": response_record,
        "raw_result_count": len(raw_results),
        "parsed_pixel_result_count": len(parsed_results),
        "diagnostic_pixel_results": parsed_results,
        "gates": {
            "transport_ok": transport_ok,
            "result_count_match": result_count_match,
            "all_values_inside_frozen_range": range_match,
            "one_to_one_result_geometry_match": geometry_match,
            "multipoint_batch_transport_qualified": multipoint_qualified,
        },
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
        "transport_ok": manifest["gates"]["transport_ok"],
        "raw_result_count": manifest["raw_result_count"],
        "parsed_pixel_result_count": manifest["parsed_pixel_result_count"],
        "result_count_match": manifest["gates"]["result_count_match"],
        "geometry_match": manifest["gates"]["one_to_one_result_geometry_match"],
        "multipoint_batch_transport_qualified": manifest["gates"]["multipoint_batch_transport_qualified"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
