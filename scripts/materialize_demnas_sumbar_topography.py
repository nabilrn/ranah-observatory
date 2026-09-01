#!/usr/bin/env python3
"""Materialize coarse Sumatera Barat topography context from BIG DEMNAS.

The official DEMNAS ImageServer is sampled onto a deliberately coarser
analysis grid (~0.005 degree, roughly 0.5 km near the equator).  This is for
regional kabupaten/kota context only; it must not be represented as a local
hazard, engineering, or native-resolution DEM product.

Raw TIFF bytes are written below data/raw (gitignored).  Only district-level
summary CSV and a reproducibility/validation manifest are committed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "data/processed/geography/sumbar-big-kabkota.geojson"
CROSSWALK_PATH = ROOT / "data/registries/big_geography_map.csv"
RAW_DIR = ROOT / "data/raw/demnas"
RAW_TIFF = RAW_DIR / "sumbar-regional-grid-0.005deg.tif"
OUT_DIR = ROOT / "data/processed/geography/demnas_topography"
OUTPUT_CSV = OUT_DIR / "sumbar-kabkota-topography-context.csv"
MANIFEST = ROOT / "data/manifests/sumbar_demnas_topography.json"

SERVICE_URL = "https://geoservices.big.go.id/raster/rest/services/DEMNAS/DEM_Indonesia/ImageServer"
ANALYSIS_PIXEL_DEGREES = 0.005
BBOX_BUFFER_DEGREES = 0.01
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"
MAX_TIFF_BYTES = 40 * 1024 * 1024
EXPECTED_NATIVE_PIXEL_DEGREES = 7.498500299940011e-5


def normalize_code(value: Any) -> str:
    text = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(text) == 3:
        text = "0" + text
    return text


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_bytes(url: str, *, timeout: int = 120, max_bytes: int | None = None) -> tuple[bytes, dict[str, str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        final_url = response.geturl()
        declared = response.headers.get("Content-Length")
        if max_bytes is not None and declared:
            try:
                if int(declared) > max_bytes:
                    raise RuntimeError(f"response too large: {declared} > {max_bytes}")
            except ValueError:
                pass
        if max_bytes is None:
            data = response.read()
        else:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise RuntimeError(f"response exceeded limit of {max_bytes} bytes")
        return data, headers, final_url


def request_json(url: str) -> tuple[dict[str, Any], bytes, str]:
    raw, _, final_url = request_bytes(url, timeout=60, max_bytes=5 * 1024 * 1024)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON payload from {url}")
    return payload, raw, final_url


def load_crosswalk() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with CROSSWALK_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            code = normalize_code(row.get("source_code_normalized"))
            if not code or code in rows:
                raise RuntimeError(f"invalid/duplicate BIG crosswalk code: {code!r}")
            if row.get("mapping_status") != "qualified_current_crosswalk":
                raise RuntimeError(f"unqualified BIG crosswalk row: {code}")
            rows[code] = row
    if len(rows) != 19:
        raise RuntimeError(f"expected 19 BIG geography crosswalk rows, got {len(rows)}")
    return rows


def load_boundaries(crosswalk: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    payload = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise RuntimeError("BIG boundary is not a GeoJSON FeatureCollection")
    features = payload["features"]
    if len(features) != 19:
        raise RuntimeError(f"expected 19 BIG boundary features, got {len(features)}")

    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for feature in features:
        properties = feature.get("properties") or {}
        code = normalize_code(properties.get("KDPKAB"))
        province = normalize_text(properties.get("WADMPR"))
        source_name = normalize_text(properties.get("WADMKK"))
        if province.casefold() != "sumatera barat":
            raise RuntimeError(f"unexpected BIG province for {code}: {province!r}")
        if code not in crosswalk:
            raise RuntimeError(f"boundary code missing from crosswalk: {code}")
        expected_name = normalize_text(crosswalk[code]["source_name_expected"])
        if source_name.casefold() != expected_name.casefold():
            raise RuntimeError(f"BIG boundary name mismatch for {code}: {source_name!r} != {expected_name!r}")
        if code in seen:
            raise RuntimeError(f"duplicate BIG boundary code: {code}")
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError(f"unsupported BIG boundary geometry for {code}: {(geometry or {}).get('type')!r}")
        seen.add(code)
        output.append({
            "source_code": code,
            "source_name": source_name,
            "canonical_geography_id": crosswalk[code]["canonical_geography_id"],
            "canonical_name": crosswalk[code]["canonical_name"],
            "geometry": geometry,
        })
    if seen != set(crosswalk):
        raise RuntimeError("BIG boundary/crosswalk coverage mismatch")
    return output


def iter_positions(value: Any):
    if isinstance(value, (list, tuple)):
        if len(value) >= 2 and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value[:2]):
            yield float(value[0]), float(value[1])
            return
        for item in value:
            yield from iter_positions(item)


def geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points = list(iter_positions(geometry.get("coordinates")))
    if not points:
        raise RuntimeError("boundary geometry has no coordinates")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def union_bbox(features: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    boxes = [geometry_bbox(item["geometry"]) for item in features]
    return (
        min(box[0] for box in boxes) - BBOX_BUFFER_DEGREES,
        min(box[1] for box in boxes) - BBOX_BUFFER_DEGREES,
        max(box[2] for box in boxes) + BBOX_BUFFER_DEGREES,
        max(box[3] for box in boxes) + BBOX_BUFFER_DEGREES,
    )


def validate_service() -> dict[str, Any]:
    payload, raw, final_url = request_json(f"{SERVICE_URL}?f=pjson")
    if payload.get("name") != "DEMNAS/DEM_Indonesia":
        raise RuntimeError(f"unexpected DEMNAS service name: {payload.get('name')!r}")
    spatial_reference = (payload.get("spatialReference") or {}).get("wkid")
    if spatial_reference != 4326:
        raise RuntimeError(f"unexpected DEMNAS spatial reference: {spatial_reference!r}")
    if payload.get("bandCount") != 1 or payload.get("pixelType") != "F32":
        raise RuntimeError(f"unexpected DEMNAS raster contract: bandCount={payload.get('bandCount')} pixelType={payload.get('pixelType')}")
    pixel_size = float(payload.get("pixelSizeX"))
    if abs(pixel_size - EXPECTED_NATIVE_PIXEL_DEGREES) > 1e-9:
        raise RuntimeError(f"DEMNAS native pixel size changed: {pixel_size}")
    if int(payload.get("maxImageWidth") or 0) < 1000 or int(payload.get("maxImageHeight") or 0) < 1000:
        raise RuntimeError("DEMNAS export-image service dimensions are unexpectedly small")
    copyright_text = normalize_text(payload.get("copyrightText"))
    if "badan informasi geospasial" not in copyright_text.casefold():
        raise RuntimeError(f"unexpected DEMNAS copyright: {copyright_text!r}")
    return {
        "name": payload.get("name"),
        "description": payload.get("description"),
        "extent": payload.get("extent"),
        "spatial_reference": spatial_reference,
        "native_pixel_degrees": pixel_size,
        "band_count": payload.get("bandCount"),
        "pixel_type": payload.get("pixelType"),
        "min_values": payload.get("minValues"),
        "max_values": payload.get("maxValues"),
        "default_resampling_method": payload.get("defaultResamplingMethod"),
        "max_image_width": payload.get("maxImageWidth"),
        "max_image_height": payload.get("maxImageHeight"),
        "copyright": copyright_text,
        "service_metadata_url": final_url,
        "service_metadata_sha256": sha256_bytes(raw),
    }


def export_dem(bbox: tuple[float, float, float, float], service: dict[str, Any]) -> tuple[np.ndarray, dict[str, Any]]:
    xmin, ymin, xmax, ymax = bbox
    width = max(2, math.ceil((xmax - xmin) / ANALYSIS_PIXEL_DEGREES))
    height = max(2, math.ceil((ymax - ymin) / ANALYSIS_PIXEL_DEGREES))
    if width > int(service["max_image_width"]) or height > int(service["max_image_height"]):
        raise RuntimeError(f"requested DEMNAS analysis grid exceeds service limits: {width}x{height}")

    params = {
        "bbox": f"{xmin:.8f},{ymin:.8f},{xmax:.8f},{ymax:.8f}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{width},{height}",
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }
    url = f"{SERVICE_URL}/exportImage?{urllib.parse.urlencode(params)}"
    raw, headers, final_url = request_bytes(url, timeout=180, max_bytes=MAX_TIFF_BYTES)
    if len(raw) < 100:
        raise RuntimeError(f"DEMNAS export unexpectedly small: {len(raw)} bytes")
    if raw[:2] not in {b"II", b"MM"}:
        preview = raw[:200].decode("utf-8", errors="replace")
        raise RuntimeError(f"DEMNAS export is not TIFF: {preview!r}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RAW_TIFF.write_bytes(raw)
    array = np.asarray(tifffile.imread(RAW_TIFF), dtype=np.float64)
    array = np.squeeze(array)
    if array.ndim != 2 or array.shape != (height, width):
        raise RuntimeError(f"unexpected DEMNAS TIFF shape: {array.shape}, expected {(height, width)}")
    valid = np.isfinite(array) & (array >= -200) & (array <= 9000)
    if valid.sum() < array.size * 0.2:
        raise RuntimeError(f"too few valid DEMNAS cells: {int(valid.sum())}/{array.size}")
    array[~valid] = np.nan

    return array, {
        "request_url": url,
        "resolved_url": final_url,
        "request_parameters": params,
        "content_type": headers.get("content-type"),
        "width": width,
        "height": height,
        "raw_tiff_path": RAW_TIFF.relative_to(ROOT).as_posix(),
        "raw_tiff_committed": False,
        "raw_tiff_bytes": len(raw),
        "raw_tiff_sha256": sha256_bytes(raw),
        "valid_cell_count": int(valid.sum()),
        "total_cell_count": int(array.size),
    }


def ring_mask(x: np.ndarray, y: np.ndarray, ring: list[list[float]]) -> np.ndarray:
    if len(ring) < 4:
        raise RuntimeError("invalid polygon ring with fewer than four positions")
    inside = np.zeros(x.shape, dtype=bool)
    xj, yj = float(ring[-1][0]), float(ring[-1][1])
    for position in ring:
        xi, yi = float(position[0]), float(position[1])
        crossing = ((yi > y) != (yj > y))
        denominator = yj - yi
        if denominator != 0:
            x_intersection = (xj - xi) * (y - yi) / denominator + xi
            inside ^= crossing & (x < x_intersection)
        xj, yj = xi, yi
    return inside


def polygon_mask(x: np.ndarray, y: np.ndarray, polygon: list[list[list[float]]]) -> np.ndarray:
    if not polygon:
        raise RuntimeError("empty polygon coordinates")
    mask = ring_mask(x, y, polygon[0])
    for hole in polygon[1:]:
        mask &= ~ring_mask(x, y, hole)
    return mask


def geometry_mask(x: np.ndarray, y: np.ndarray, geometry: dict[str, Any]) -> np.ndarray:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geom_type == "Polygon":
        return polygon_mask(x, y, coordinates)
    if geom_type == "MultiPolygon":
        mask = np.zeros(x.shape, dtype=bool)
        for polygon in coordinates:
            mask |= polygon_mask(x, y, polygon)
        return mask
    raise RuntimeError(f"unsupported geometry type: {geom_type!r}")


def percentile(values: np.ndarray, q: float) -> float:
    return float(np.nanpercentile(values, q))


def rounded(value: float) -> str:
    return f"{value:.2f}"


def summarize(features: list[dict[str, Any]], bbox: tuple[float, float, float, float], elevation: np.ndarray) -> list[dict[str, str]]:
    xmin, ymin, xmax, ymax = bbox
    height, width = elevation.shape
    pixel_x = (xmax - xmin) / width
    pixel_y = (ymax - ymin) / height
    lon = xmin + (np.arange(width) + 0.5) * pixel_x
    lat = ymax - (np.arange(height) + 0.5) * pixel_y

    # np.gradient uses row 0 at the north edge.  Latitude-dependent east-west
    # spacing prevents an avoidable degree-to-metre distortion.
    dy_m = 111_320.0 * pixel_y
    dx_m = 111_320.0 * np.cos(np.deg2rad(lat))[:, None] * pixel_x
    grad_row, grad_col = np.gradient(elevation, dy_m, axis=(0, 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        grad_x = grad_col / np.where(dx_m == 0, np.nan, 1.0)
        slope = np.degrees(np.arctan(np.sqrt(grad_x * grad_x + grad_row * grad_row)))
    slope[~np.isfinite(elevation)] = np.nan

    outputs: list[dict[str, str]] = []
    for feature in features:
        bxmin, bymin, bxmax, bymax = geometry_bbox(feature["geometry"])
        col_idx = np.where((lon >= bxmin) & (lon <= bxmax))[0]
        row_idx = np.where((lat >= bymin) & (lat <= bymax))[0]
        if not len(col_idx) or not len(row_idx):
            raise RuntimeError(f"no DEM grid cells overlap boundary bbox: {feature['canonical_name']}")
        sub_lon, sub_lat = np.meshgrid(lon[col_idx], lat[row_idx])
        mask = geometry_mask(sub_lon, sub_lat, feature["geometry"])
        sub_elevation = elevation[np.ix_(row_idx, col_idx)]
        sub_slope = slope[np.ix_(row_idx, col_idx)]
        valid_mask = mask & np.isfinite(sub_elevation) & np.isfinite(sub_slope)
        if valid_mask.sum() < 5:
            raise RuntimeError(f"too few valid DEM cells for {feature['canonical_name']}: {int(valid_mask.sum())}")
        elev_values = sub_elevation[valid_mask]
        slope_values = sub_slope[valid_mask]
        outputs.append({
            "geography_id": feature["canonical_geography_id"],
            "geography_name": feature["canonical_name"],
            "source_kdpkab": feature["source_code"],
            "source_name": feature["source_name"],
            "analysis_grid_cell_count": str(int(valid_mask.sum())),
            "elevation_mean_m": rounded(float(np.nanmean(elev_values))),
            "elevation_median_m": rounded(float(np.nanmedian(elev_values))),
            "elevation_p10_m": rounded(percentile(elev_values, 10)),
            "elevation_p90_m": rounded(percentile(elev_values, 90)),
            "elevation_min_m": rounded(float(np.nanmin(elev_values))),
            "elevation_max_m": rounded(float(np.nanmax(elev_values))),
            "slope_mean_deg_generalized": rounded(float(np.nanmean(slope_values))),
            "slope_median_deg_generalized": rounded(float(np.nanmedian(slope_values))),
            "slope_p90_deg_generalized": rounded(percentile(slope_values, 90)),
        })
    outputs.sort(key=lambda item: item["geography_id"])
    return outputs


def main() -> None:
    crosswalk = load_crosswalk()
    boundaries = load_boundaries(crosswalk)
    bbox = union_bbox(boundaries)
    service = validate_service()
    elevation, export = export_dem(bbox, service)
    rows = summarize(boundaries, bbox, elevation)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0])
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    result = {
        "schema": "ranah-observatory/demnas-sumbar-topography-context/v1",
        "source": {
            "provider": "Badan Informasi Geospasial",
            "product": "DEMNAS",
            "service": SERVICE_URL,
            "service_contract": service,
        },
        "analysis_contract": {
            "purpose": "regional kabupaten/kota topography context for Ranah Observatory",
            "native_resolution_preserved": False,
            "analysis_pixel_degrees_target": ANALYSIS_PIXEL_DEGREES,
            "analysis_grid_label": "coarse regional grid, roughly 0.5 km near the equator",
            "slope_is_generalized": True,
            "safe_for_local_hazard_mapping": False,
            "safe_for_engineering_design": False,
            "causal_claim_by_itself": False,
            "boundary_source": BOUNDARY_PATH.relative_to(ROOT).as_posix(),
            "boundary_sha256": sha256_path(BOUNDARY_PATH),
            "crosswalk_source": CROSSWALK_PATH.relative_to(ROOT).as_posix(),
            "crosswalk_sha256": sha256_path(CROSSWALK_PATH),
            "boundary_edition": "Juni 2026",
            "district_count": len(rows),
            "bbox_wgs84": [round(value, 8) for value in bbox],
        },
        "export": export,
        "output": {
            "path": OUTPUT_CSV.relative_to(ROOT).as_posix(),
            "sha256": sha256_path(OUTPUT_CSV),
            "row_count": len(rows),
        },
        "missing_values_inferred": False,
        "geography_inferred": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "district_count": len(rows),
        "grid": f"{export['width']}x{export['height']}",
        "valid_cells": export["valid_cell_count"],
        "raw_tiff_bytes": export["raw_tiff_bytes"],
        "output": OUTPUT_CSV.relative_to(ROOT).as_posix(),
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
