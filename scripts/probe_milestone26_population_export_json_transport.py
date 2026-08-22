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

import rasterio

from scripts import materialize_milestone26_stage1_components as stage1
from scripts import probe_milestone26_statistics_transport as stats_v1

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_export_json_transport_contract.json"
OUT_DIR = ROOT / "data/processed/bnpb/m26_population_export_json_transport"
OUT_MANIFEST = ROOT / "data/manifests/milestone26_population_export_json_transport.json"
SOURCE_ID = "inarisk_population_2020"


class M26PopulationExportJSONError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-population-export-json-transport-contract/v1":
        raise M26PopulationExportJSONError("unexpected export JSON transport contract schema")
    if payload.get("locked_before_live_probe") is not True or payload.get("source_id") != SOURCE_ID:
        raise M26PopulationExportJSONError("export JSON transport contract drift")
    for key in (
        "numeric_aggregation_authorized",
        "substantive_value_promotion_authorized",
        "equivalence_decision_authorized",
        "pilot_selection_changed",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "cross_geography_numeric_extraction_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26PopulationExportJSONError(f"invalid export JSON boundary: {key}")
    return payload


def request_once(url: str, timeout: float) -> dict[str, Any]:
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
                "Accept": "application/json,image/tiff,*/*",
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


def build_request() -> tuple[str, dict[str, Any]]:
    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    urls = stage1.registry_urls()
    features, big_probe = stage1.load_qualified_big_features()
    capacity_meta = stage1.source_metadata("inarisk_capacity_2021")
    pilot_feature, projected, _cbbox, _cwidth, _cheight = stats_v1.select_geometry_only_pilot(features, capacity_meta)
    population_meta = stage1.source_metadata(SOURCE_ID)
    bbox, width, height = stage1.aligned_window(projected.bounds, population_meta)
    params = {
        "bbox": ",".join(f"{value:.6f}" for value in bbox),
        "bboxSR": "3395",
        "size": f"{width},{height}",
        "imageSR": "3395",
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_NearestNeighbor",
        "compression": "LZ77",
        "returnSquarePixels": "true",
        "f": "json",
    }
    url = urls[SOURCE_ID].rstrip("/") + "/exportImage?" + urllib.parse.urlencode(params)
    context = {
        "pilot_geography_id": pilot_feature["geography_id"],
        "pilot_geography_name": pilot_feature["geography_name"],
        "bbox_native": list(bbox),
        "width": width,
        "height": height,
        "pixel_size_m": 100,
        "crs_epsg": 3395,
        "big_expected_edition": big_probe.get("expected_edition"),
    }
    return url, context


def inspect_tiff(path: Path, expected_width: int, expected_height: int) -> dict[str, Any]:
    with rasterio.open(path) as dataset:
        epsg = dataset.crs.to_epsg() if dataset.crs is not None else None
        result = {
            "driver": dataset.driver,
            "count": dataset.count,
            "width": dataset.width,
            "height": dataset.height,
            "crs_epsg": epsg,
            "pixel_size_x": float(dataset.transform.a),
            "pixel_size_y_abs": abs(float(dataset.transform.e)),
            "nodata": dataset.nodata,
        }
    result["metadata_gate_passed"] = (
        result["driver"] == "GTiff"
        and result["count"] == 1
        and result["width"] == expected_width
        and result["height"] == expected_height
        and result["crs_epsg"] == 3395
        and abs(result["pixel_size_x"] - 100.0) <= 1e-6
        and abs(result["pixel_size_y_abs"] - 100.0) <= 1e-6
    )
    return result


def run() -> dict[str, Any]:
    contract = load_contract()
    request_url, context = build_request()
    timeout = float(contract["href_follow"]["timeout_seconds"])
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    export_response = request_once(request_url, timeout)
    export_body = export_response.pop("body")
    export_path = OUT_DIR / "export-response.body"
    export_path.write_bytes(export_body)
    export_record = {
        **export_response,
        "requested_url": request_url,
        "requested_url_length": len(request_url),
        "body_path": export_path.relative_to(ROOT).as_posix(),
        "body_bytes": len(export_body),
        "body_sha256": sha256_bytes(export_body),
        "json_parseable": False,
        "arcgis_error_present": False,
        "href_present": False,
        "reported_width": None,
        "reported_height": None,
        "reported_extent_present": False,
    }

    href: str | None = None
    if export_response["status"] == 200 and export_response["exception_class"] is None:
        try:
            payload = json.loads(export_body.decode("utf-8"))
            export_record["json_parseable"] = isinstance(payload, dict)
            if isinstance(payload, dict):
                export_record["arcgis_error_present"] = isinstance(payload.get("error"), dict)
                href = payload.get("href") if isinstance(payload.get("href"), str) else None
                export_record["href_present"] = href is not None
                export_record["reported_width"] = payload.get("width")
                export_record["reported_height"] = payload.get("height")
                export_record["reported_extent_present"] = isinstance(payload.get("extent"), dict)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

    dimensions_match = (
        export_record["reported_width"] == context["width"]
        and export_record["reported_height"] == context["height"]
        and export_record["reported_extent_present"] is True
    )
    export_record["response_contract_gate_passed"] = (
        export_record["status"] == 200
        and export_record["json_parseable"] is True
        and export_record["arcgis_error_present"] is False
        and export_record["href_present"] is True
        and dimensions_match
    )

    href_record: dict[str, Any] | None = None
    tiff_metadata: dict[str, Any] | None = None
    if href is not None:
        href_response = request_once(href, timeout)
        href_body = href_response.pop("body")
        href_path = OUT_DIR / "exported-image.tif"
        href_path.write_bytes(href_body)
        href_record = {
            **href_response,
            "href": href,
            "body_path": href_path.relative_to(ROOT).as_posix(),
            "body_bytes": len(href_body),
            "body_sha256": sha256_bytes(href_body),
            "tiff_magic": stage1.is_tiff(href_body),
        }
        if href_record["status"] == 200 and href_record["tiff_magic"] and len(href_body) < 95_000_000:
            try:
                tiff_metadata = inspect_tiff(href_path, context["width"], context["height"])
            except Exception as exc:
                tiff_metadata = {"metadata_gate_passed": False, "inspection_error": f"{type(exc).__name__}: {exc}"}

    transport_success = bool(
        export_record["response_contract_gate_passed"]
        and href_record is not None
        and href_record["status"] == 200
        and href_record["exception_class"] is None
        and href_record["tiff_magic"] is True
        and tiff_metadata is not None
        and tiff_metadata.get("metadata_gate_passed") is True
    )

    manifest = {
        "schema": "ranah-observatory/milestone26-population-export-json-transport/v1",
        "milestone": 26,
        "stage": "stage1_transport_diagnostic",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "source_id": SOURCE_ID,
        "pilot": context,
        "export_json_response": export_record,
        "href_response": href_record,
        "tiff_metadata": tiff_metadata,
        "transport_success": transport_success,
        "numeric_aggregation_performed": False,
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
        manifest = run()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "transport_success": manifest["transport_success"],
        "export_status": manifest["export_json_response"]["status"],
        "export_exception": manifest["export_json_response"]["exception_class"],
        "href_present": manifest["export_json_response"]["href_present"],
        "href_status": manifest["href_response"]["status"] if manifest["href_response"] else None,
        "href_exception": manifest["href_response"]["exception_class"] if manifest["href_response"] else None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
