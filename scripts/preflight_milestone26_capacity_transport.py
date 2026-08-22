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

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from scripts.build_milestone8_shakemap_exposure_candidate import load_qualified_big_features

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_capacity_production_contract.json"
SOURCE_META = ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_capacity_2021.json"
OUTPUT = ROOT / "data/manifests/milestone26_capacity_transport_preflight.json"


class CapacityPreflightError(RuntimeError):
    pass


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def request_bytes(url: str, retries: int = 3, timeout: float = 120.0) -> tuple[str, str, bytes]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if int(response.status) != 200:
                    raise CapacityPreflightError(f"HTTP {response.status}: {url}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()
        except (urllib.error.URLError, TimeoutError, CapacityPreflightError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)
    raise CapacityPreflightError(f"request failed after retries: {url}") from last_error


def is_tiff(body: bytes) -> bool:
    return body.startswith(b"II*\x00") or body.startswith(b"MM\x00*")


def aligned_window(bounds: tuple[float, float, float, float], meta: dict[str, Any], pixel: float) -> tuple[tuple[float, float, float, float], int, int]:
    minx, miny, maxx, maxy = bounds
    extent = meta["fullExtent"]
    origin_x = float(extent["xmin"])
    origin_y = float(extent["ymax"])
    col0 = math.floor((minx - origin_x) / pixel)
    col1 = math.ceil((maxx - origin_x) / pixel)
    row0 = math.floor((origin_y - maxy) / pixel)
    row1 = math.ceil((origin_y - miny) / pixel)
    width = int(col1 - col0)
    height = int(row1 - row0)
    if width <= 0 or height <= 0:
        raise CapacityPreflightError("non-positive aligned raster window")
    left = origin_x + col0 * pixel
    right = origin_x + col1 * pixel
    top = origin_y - row0 * pixel
    bottom = origin_y - row1 * pixel
    return (left, bottom, right, top), width, height


def export_url(service: str, bbox: tuple[float, float, float, float], width: int, height: int) -> str:
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
        "f": "image",
    }
    return service.rstrip("/") + "/exportImage?" + urllib.parse.urlencode(params)


def build(fetch_sample: bool) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-capacity-production-contract/v1":
        raise CapacityPreflightError("unexpected capacity production contract schema")
    if contract.get("capacity_component_materialization_authorized") is not True:
        raise CapacityPreflightError("capacity component materialization is not authorized")
    if contract.get("substantive_interpretation_authorized") is not False:
        raise CapacityPreflightError("substantive interpretation unexpectedly authorized")

    source_snapshot = json.loads(SOURCE_META.read_text(encoding="utf-8"))
    meta = source_snapshot.get("primary")
    if not isinstance(meta, dict):
        raise CapacityPreflightError("invalid frozen capacity ImageServer metadata")

    transport = contract["source_transport"]
    pixel = float(transport["native_pixel_size_m"])
    if int(meta["spatialReference"]["wkid"]) != int(transport["native_grid_crs_epsg"]):
        raise CapacityPreflightError("capacity CRS drift from frozen contract")
    if float(meta["pixelSizeX"]) != pixel or float(meta["pixelSizeY"]) != pixel:
        raise CapacityPreflightError("capacity native pixel size drift")
    if float(meta["minValues"][0]) != float(transport["frozen_valid_value_min"]):
        raise CapacityPreflightError("capacity minimum value drift")
    if float(meta["maxValues"][0]) != float(transport["frozen_valid_value_max"]):
        raise CapacityPreflightError("capacity maximum value drift")

    max_width = int(meta["maxImageWidth"])
    max_height = int(meta["maxImageHeight"])
    max_bytes = int(transport["single_file_max_bytes"])
    features, big_probe = load_qualified_big_features()
    if len(features) != int(contract["geography_count_expected"]):
        raise CapacityPreflightError("BIG geography count drift")

    transformer = Transformer.from_crs(4326, int(transport["native_grid_crs_epsg"]), always_xy=True)
    windows: list[dict[str, Any]] = []
    for feature in sorted(features, key=lambda row: row["geography_id"]):
        geom = shape(feature["geometry"])
        if geom.is_empty:
            raise CapacityPreflightError(f"empty BIG geometry: {feature['geography_id']}")
        projected = shapely_transform(transformer.transform, geom)
        bbox, width, height = aligned_window(projected.bounds, meta, pixel)
        if width > max_width or height > max_height:
            raise CapacityPreflightError(
                f"ImageServer export limit exceeded for {feature['geography_id']}: {width}x{height} > {max_width}x{max_height}"
            )
        windows.append(
            {
                "geography_id": feature["geography_id"],
                "geography_name": feature["geography_name"],
                "source_permendagri_code": feature["source_permendagri_code"],
                "bbox_native": [round(float(value), 6) for value in bbox],
                "width": width,
                "height": height,
                "native_cell_bbox_count": width * height,
                "uncompressed_f32_bytes": width * height * 4,
            }
        )

    representative = min(windows, key=lambda row: (row["native_cell_bbox_count"], row["geography_id"]))
    sample: dict[str, Any] = {
        "performed": False,
        "geography_id": representative["geography_id"],
        "geography_name": representative["geography_name"],
    }
    if fetch_sample:
        url = export_url(
            transport["service"],
            tuple(float(value) for value in representative["bbox_native"]),
            int(representative["width"]),
            int(representative["height"]),
        )
        final_url, content_type, body = request_bytes(url)
        if not is_tiff(body):
            preview = body[:300].decode("utf-8", errors="replace")
            raise CapacityPreflightError(f"representative export was not TIFF: {preview}")
        if len(body) >= max_bytes:
            raise CapacityPreflightError(f"representative TIFF exceeds frozen GitHub byte gate: {len(body)}")
        sample = {
            "performed": True,
            "geography_id": representative["geography_id"],
            "geography_name": representative["geography_name"],
            "requested_url": url,
            "final_url": final_url,
            "content_type": content_type,
            "raster_sha256": sha256_bytes(body),
            "raster_bytes": len(body),
            "within_single_file_byte_gate": True,
        }

    payload = {
        "schema": "ranah-observatory/milestone26-capacity-transport-preflight/v1",
        "milestone": 26,
        "stage": "stage1_capacity_transport_preflight",
        "source_id": contract["source_id"],
        "claim_type": contract["claim_type"],
        "reference_year": contract["reference_year"],
        "spatial_frame": contract["spatial_frame"],
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": sha256_path(CONTRACT)},
        "source_metadata": {"path": SOURCE_META.relative_to(ROOT).as_posix(), "sha256": sha256_path(SOURCE_META)},
        "big_boundary_probe_qualified": bool(big_probe.get("conclusions", {}).get("official_big_polygon_lane_qualified")),
        "geography_count": len(windows),
        "all_windows_within_imageserver_limits": True,
        "max_window_width": max(row["width"] for row in windows),
        "max_window_height": max(row["height"] for row in windows),
        "max_window_uncompressed_f32_bytes": max(row["uncompressed_f32_bytes"] for row in windows),
        "imageserver_limits": {"max_width": max_width, "max_height": max_height, "single_file_max_bytes": max_bytes},
        "representative_transport_sample": sample,
        "windows": windows,
        "capacity_component_materialized": False,
        "population_component_reextracted": False,
        "substantive_interpretation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight Milestone 26 InaRISK capacity exportImage transport")
    parser.add_argument("--fetch-sample", action="store_true", help="Fetch one smallest aligned geography TIFF as transport proof")
    args = parser.parse_args()
    payload = build(fetch_sample=args.fetch_sample)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": OUTPUT.relative_to(ROOT).as_posix(),
        "geography_count": payload["geography_count"],
        "max_window_width": payload["max_window_width"],
        "max_window_height": payload["max_window_height"],
        "representative_transport_sample": payload["representative_transport_sample"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
