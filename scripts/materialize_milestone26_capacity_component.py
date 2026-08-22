#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from shapely.geometry import mapping, shape
from shapely.ops import transform as shapely_transform

from scripts.build_milestone8_shakemap_exposure_candidate import load_qualified_big_features

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data/manifests/milestone26_capacity_production_contract.json"
PREFLIGHT_PATH = ROOT / "data/manifests/milestone26_capacity_transport_preflight.json"
NODATA_AMENDMENT_PATH = ROOT / "data/manifests/milestone26_stage1_nodata_transport_amendment.json"


class CapacityMaterializationError(RuntimeError):
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


def request_bytes(url: str, retries: int = 3, timeout: float = 180.0) -> tuple[str, str, bytes]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)",
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if int(response.status) != 200:
                    raise CapacityMaterializationError(f"HTTP {response.status}: {url}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()
        except (urllib.error.URLError, TimeoutError, CapacityMaterializationError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)
    raise CapacityMaterializationError(f"request failed after retries: {url}") from last_error


def is_tiff(body: bytes) -> bool:
    return body.startswith(b"II*\x00") or body.startswith(b"MM\x00*")


def normalize_html_text(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def normalize_phrase(value: str) -> str:
    return " ".join(html.unescape(value).split())


def aligned_window(
    bounds: tuple[float, float, float, float],
    source_meta: dict[str, Any],
    pixel_size: float,
) -> tuple[tuple[float, float, float, float], int, int]:
    minx, miny, maxx, maxy = bounds
    extent = source_meta["fullExtent"]
    origin_x = float(extent["xmin"])
    origin_y = float(extent["ymax"])

    col0 = math.floor((minx - origin_x) / pixel_size)
    col1 = math.ceil((maxx - origin_x) / pixel_size)
    row0 = math.floor((origin_y - maxy) / pixel_size)
    row1 = math.ceil((origin_y - miny) / pixel_size)

    width = int(col1 - col0)
    height = int(row1 - row0)
    if width <= 0 or height <= 0:
        raise CapacityMaterializationError("non-positive aligned raster window")

    left = origin_x + col0 * pixel_size
    right = origin_x + col1 * pixel_size
    top = origin_y - row0 * pixel_size
    bottom = origin_y - row1 * pixel_size
    return (left, bottom, right, top), width, height


def export_url(
    service: str,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    epsg: int,
) -> str:
    params = {
        "bbox": ",".join(f"{value:.6f}" for value in bbox),
        "bboxSR": str(epsg),
        "size": f"{width},{height}",
        "imageSR": str(epsg),
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_NearestNeighbor",
        "compression": "LZ77",
        "returnSquarePixels": "true",
        "f": "image",
    }
    return service.rstrip("/") + "/exportImage?" + urllib.parse.urlencode(params)


def source_metadata(contract: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = ROOT / str(contract["source_metadata"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    primary = payload.get("primary")
    if not isinstance(primary, dict):
        raise CapacityMaterializationError("frozen capacity metadata has no primary ImageServer payload")
    return path, primary


def validate_contract(
    contract: dict[str, Any],
    preflight: dict[str, Any],
    nodata_amendment: dict[str, Any],
    source_meta: dict[str, Any],
) -> None:
    if contract.get("schema") != "ranah-observatory/milestone26-capacity-production-contract/v1":
        raise CapacityMaterializationError("unexpected capacity production contract schema")
    if contract.get("contract_locked_before_cross_geography_numeric_extraction") is not True:
        raise CapacityMaterializationError("capacity contract was not locked before numeric extraction")
    if contract.get("capacity_component_materialization_authorized") is not True:
        raise CapacityMaterializationError("capacity component materialization is not authorized")
    if contract.get("cross_geography_numeric_source_extraction_authorized") is not True:
        raise CapacityMaterializationError("cross-geography numeric extraction is not authorized")
    if contract.get("population_component_reextraction_authorized") is not False:
        raise CapacityMaterializationError("population re-extraction unexpectedly authorized")
    for flag in (
        "substantive_interpretation_authorized",
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(flag) is not False:
            raise CapacityMaterializationError(f"scientific boundary unexpectedly open: {flag}")

    if preflight.get("schema") != "ranah-observatory/milestone26-capacity-transport-preflight/v1":
        raise CapacityMaterializationError("capacity preflight is missing or has unexpected schema")
    if preflight.get("geography_count") != int(contract["geography_count_expected"]):
        raise CapacityMaterializationError("capacity preflight geography count drift")
    if preflight.get("all_windows_within_imageserver_limits") is not True:
        raise CapacityMaterializationError("capacity preflight did not clear ImageServer limits")
    if preflight.get("representative_transport_sample", {}).get("within_single_file_byte_gate") is not True:
        raise CapacityMaterializationError("capacity preflight did not clear representative byte gate")

    if nodata_amendment.get("schema") != "ranah-observatory/milestone26-stage1-nodata-transport-amendment/v1":
        raise CapacityMaterializationError("unexpected NoData transport amendment schema")
    if contract["source_id"] not in nodata_amendment.get("affected_source_ids", []):
        raise CapacityMaterializationError("capacity source is not covered by the frozen NoData amendment")
    if float(nodata_amendment["minimum_valid_fraction_inside_polygon_unchanged"]) != float(
        contract["aggregation"]["minimum_valid_fraction_inside_geography"]
    ):
        raise CapacityMaterializationError("NoData amendment changed the pre-locked valid-fraction gate")
    if nodata_amendment.get("aggregation_semantics_changed") is not False:
        raise CapacityMaterializationError("NoData amendment unexpectedly changed aggregation semantics")

    transport = contract["source_transport"]
    epsg = int(transport["native_grid_crs_epsg"])
    pixel = float(transport["native_pixel_size_m"])
    if int(source_meta["spatialReference"]["wkid"]) != epsg:
        raise CapacityMaterializationError("capacity source CRS drift")
    if float(source_meta["pixelSizeX"]) != pixel or float(source_meta["pixelSizeY"]) != pixel:
        raise CapacityMaterializationError("capacity source native pixel-size drift")
    if float(source_meta["minValues"][0]) != float(transport["frozen_valid_value_min"]):
        raise CapacityMaterializationError("capacity source minimum-value drift")
    if float(source_meta["maxValues"][0]) != float(transport["frozen_valid_value_max"]):
        raise CapacityMaterializationError("capacity source maximum-value drift")


def fetch_or_verify_semantic_evidence(contract: dict[str, Any], mode: str) -> tuple[Path, str]:
    evidence = contract["semantic_evidence"]
    path = ROOT / str(evidence["frozen_path"])
    required = normalize_phrase(str(evidence["required_phrase"]))

    if mode == "live":
        _final_url, _content_type, body = request_bytes(str(evidence["url"]), timeout=120.0)
        normalized = normalize_html_text(body)
        if required not in normalized:
            raise CapacityMaterializationError("capacity semantic evidence no longer contains the frozen index-scale phrase")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    else:
        if not path.exists():
            raise CapacityMaterializationError(f"offline semantic evidence missing: {rel(path)}")
        body = path.read_bytes()
        normalized = normalize_html_text(body)
        if required not in normalized:
            raise CapacityMaterializationError("frozen semantic evidence fails required phrase check")

    return path, sha256_path(path)


def raster_stem(geography_id: str) -> str:
    return geography_id.replace(".", "-").replace("/", "-")


def acquire_raster(
    *,
    mode: str,
    geography: dict[str, Any],
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    contract: dict[str, Any],
    contract_sha: str,
    source_metadata_path: Path,
    source_metadata_sha: str,
    semantic_path: Path,
    semantic_sha: str,
) -> tuple[Path, Path, dict[str, Any]]:
    raw_root = ROOT / str(contract["output"]["raw_root"])
    raw_root.mkdir(parents=True, exist_ok=True)
    stem = raster_stem(str(geography["geography_id"]))
    raster_path = raw_root / f"{stem}.tif"
    sidecar_path = raw_root / f"{stem}.request.json"

    transport = contract["source_transport"]
    epsg = int(transport["native_grid_crs_epsg"])
    requested = export_url(str(transport["service"]), bbox, width, height, epsg)

    if mode == "live":
        final_url, content_type, body = request_bytes(requested)
        if not is_tiff(body):
            preview = body[:300].decode("utf-8", errors="replace")
            raise CapacityMaterializationError(
                f"{geography['geography_id']} export did not return TIFF: {preview}"
            )
        if len(body) >= int(transport["single_file_max_bytes"]):
            raise CapacityMaterializationError(
                f"{geography['geography_id']} raster exceeds frozen single-file byte gate: {len(body)}"
            )
        raster_path.write_bytes(body)
        raster_sha = sha256_bytes(body)
        sidecar = {
            "schema": "ranah-observatory/milestone26-capacity-raster-request/v1",
            "source_id": contract["source_id"],
            "geography_id": geography["geography_id"],
            "geography_name": geography["geography_name"],
            "source_permendagri_code": geography["source_permendagri_code"],
            "requested_url": requested,
            "final_url": final_url,
            "content_type": content_type,
            "bbox_native": [round(float(value), 6) for value in bbox],
            "width": width,
            "height": height,
            "native_grid_crs_epsg": epsg,
            "native_pixel_size_m": float(transport["native_pixel_size_m"]),
            "format": transport["format"],
            "pixel_type": transport["pixel_type"],
            "compression": transport["compression"],
            "interpolation": transport["interpolation"],
            "raster_path": rel(raster_path),
            "raster_sha256": raster_sha,
            "raster_bytes": len(body),
            "contract_path": rel(CONTRACT_PATH),
            "contract_sha256": contract_sha,
            "source_metadata_path": rel(source_metadata_path),
            "source_metadata_sha256": source_metadata_sha,
            "semantic_evidence_path": rel(semantic_path),
            "semantic_evidence_sha256": semantic_sha,
        }
        write_json(sidecar_path, sidecar)
    else:
        if not raster_path.exists() or not sidecar_path.exists():
            raise CapacityMaterializationError(
                f"offline raw evidence missing for {geography['geography_id']}"
            )
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if sidecar.get("schema") != "ranah-observatory/milestone26-capacity-raster-request/v1":
            raise CapacityMaterializationError(f"unexpected sidecar schema: {rel(sidecar_path)}")
        if sidecar.get("geography_id") != geography["geography_id"]:
            raise CapacityMaterializationError(f"sidecar geography mismatch: {rel(sidecar_path)}")
        if sidecar.get("requested_url") != requested:
            raise CapacityMaterializationError(f"offline request contract drift: {geography['geography_id']}")
        if sidecar.get("contract_sha256") != contract_sha:
            raise CapacityMaterializationError(f"offline contract checksum drift: {geography['geography_id']}")
        if sidecar.get("source_metadata_sha256") != source_metadata_sha:
            raise CapacityMaterializationError(f"offline source metadata checksum drift: {geography['geography_id']}")
        if sidecar.get("semantic_evidence_sha256") != semantic_sha:
            raise CapacityMaterializationError(f"offline semantic evidence checksum drift: {geography['geography_id']}")
        raster_sha = sha256_path(raster_path)
        if sidecar.get("raster_sha256") != raster_sha:
            raise CapacityMaterializationError(f"offline raster checksum mismatch: {geography['geography_id']}")
        if int(sidecar.get("raster_bytes", -1)) != raster_path.stat().st_size:
            raise CapacityMaterializationError(f"offline raster byte-count mismatch: {geography['geography_id']}")

    return raster_path, sidecar_path, sidecar


def aggregate_raster(
    *,
    raster_path: Path,
    projected_geometry: Any,
    expected_width: int,
    expected_height: int,
    contract: dict[str, Any],
) -> dict[str, Any]:
    transport = contract["source_transport"]
    aggregation = contract["aggregation"]
    epsg = int(transport["native_grid_crs_epsg"])
    pixel_size = float(transport["native_pixel_size_m"])
    valid_min = float(transport["frozen_valid_value_min"])
    valid_max = float(transport["frozen_valid_value_max"])

    with rasterio.open(raster_path) as src:
        if src.count != 1:
            raise CapacityMaterializationError(f"expected one-band capacity raster: {rel(raster_path)}")
        if src.width != expected_width or src.height != expected_height:
            raise CapacityMaterializationError(
                f"raster dimensions drift for {rel(raster_path)}: {src.width}x{src.height} != {expected_width}x{expected_height}"
            )
        if src.crs is None or src.crs.to_epsg() != epsg:
            raise CapacityMaterializationError(f"raster CRS drift for {rel(raster_path)}: {src.crs}")
        if not math.isclose(abs(float(src.transform.a)), pixel_size, rel_tol=0.0, abs_tol=1e-6):
            raise CapacityMaterializationError(f"raster x pixel-size drift: {rel(raster_path)}")
        if not math.isclose(abs(float(src.transform.e)), pixel_size, rel_tol=0.0, abs_tol=1e-6):
            raise CapacityMaterializationError(f"raster y pixel-size drift: {rel(raster_path)}")

        values = src.read(1).astype(np.float64, copy=False)
        inside = geometry_mask(
            [mapping(projected_geometry)],
            out_shape=(src.height, src.width),
            transform=src.transform,
            invert=True,
            all_touched=bool(aggregation["all_touched"]),
        )
        inside_count = int(np.count_nonzero(inside))
        if inside_count <= 0:
            raise CapacityMaterializationError(f"no native grid-cell centers inside boundary: {rel(raster_path)}")

        candidates = values[inside]
        valid = np.isfinite(candidates)
        if src.nodata is not None and math.isfinite(float(src.nodata)):
            valid &= candidates != float(src.nodata)
        valid &= candidates >= valid_min
        valid &= candidates <= valid_max
        valid_values = candidates[valid]
        valid_count = int(valid_values.size)
        valid_fraction = valid_count / inside_count
        minimum = float(aggregation["minimum_valid_fraction_inside_geography"])
        if valid_fraction < minimum:
            raise CapacityMaterializationError(
                f"valid coverage gate failed for {rel(raster_path)}: {valid_fraction:.12f} < {minimum:.12f}"
            )
        if valid_count <= 0:
            raise CapacityMaterializationError(f"no valid capacity cells: {rel(raster_path)}")

        mean_value = float(np.mean(valid_values, dtype=np.float64))
        if not (valid_min <= mean_value <= valid_max):
            raise CapacityMaterializationError(f"capacity mean outside frozen source range: {rel(raster_path)}")

        return {
            "inside_native_cell_count": inside_count,
            "valid_native_cell_count": valid_count,
            "invalid_native_cell_count": inside_count - valid_count,
            "capacity_valid_fraction": valid_fraction,
            "capacity_index_2021_mean": mean_value,
            "dataset_nodata": None if src.nodata is None else float(src.nodata),
        }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build(mode: str) -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    nodata_amendment = json.loads(NODATA_AMENDMENT_PATH.read_text(encoding="utf-8"))
    source_metadata_path, source_meta = source_metadata(contract)
    validate_contract(contract, preflight, nodata_amendment, source_meta)

    contract_sha = sha256_path(CONTRACT_PATH)
    preflight_sha = sha256_path(PREFLIGHT_PATH)
    nodata_sha = sha256_path(NODATA_AMENDMENT_PATH)
    source_metadata_sha = sha256_path(source_metadata_path)
    semantic_path, semantic_sha = fetch_or_verify_semantic_evidence(contract, mode)

    features, big_probe = load_qualified_big_features()
    expected_geographies = int(contract["geography_count_expected"])
    if len(features) != expected_geographies:
        raise CapacityMaterializationError(f"expected {expected_geographies} BIG geographies, got {len(features)}")

    transport = contract["source_transport"]
    aggregation = contract["aggregation"]
    output = contract["output"]
    epsg = int(transport["native_grid_crs_epsg"])
    pixel_size = float(transport["native_pixel_size_m"])
    max_width = int(source_meta["maxImageWidth"])
    max_height = int(source_meta["maxImageHeight"])
    decimal_places = int(output["primary_value_decimal_places"])
    transformer = Transformer.from_crs(4326, epsg, always_xy=True)

    component_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    raw_evidence: list[dict[str, Any]] = []

    for geography in sorted(features, key=lambda row: row["geography_id"]):
        geom = shape(geography["geometry"])
        if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise CapacityMaterializationError(f"invalid BIG geometry: {geography['geography_id']}")
        projected = shapely_transform(transformer.transform, geom)
        bbox, width, height = aligned_window(projected.bounds, source_meta, pixel_size)
        if width > max_width or height > max_height:
            raise CapacityMaterializationError(
                f"ImageServer dimension gate failed for {geography['geography_id']}: {width}x{height}"
            )

        raster_path, sidecar_path, sidecar = acquire_raster(
            mode=mode,
            geography=geography,
            bbox=bbox,
            width=width,
            height=height,
            contract=contract,
            contract_sha=contract_sha,
            source_metadata_path=source_metadata_path,
            source_metadata_sha=source_metadata_sha,
            semantic_path=semantic_path,
            semantic_sha=semantic_sha,
        )
        stats = aggregate_raster(
            raster_path=raster_path,
            projected_geometry=projected,
            expected_width=width,
            expected_height=height,
            contract=contract,
        )

        component_rows.append(
            {
                "geography_id": geography["geography_id"],
                "geography_name": geography["geography_name"],
                "source_permendagri_code": geography["source_permendagri_code"],
                "reference_year": int(contract["reference_year"]),
                aggregation["primary_value_field"]: f"{stats['capacity_index_2021_mean']:.{decimal_places}f}",
                "capacity_valid_fraction": f"{stats['capacity_valid_fraction']:.9f}",
                "inside_native_cell_count": stats["inside_native_cell_count"],
                "valid_native_cell_count": stats["valid_native_cell_count"],
                "invalid_native_cell_count": stats["invalid_native_cell_count"],
                "claim_type": contract["claim_type"],
                "component_class": contract["component_class"],
                "source_id": contract["source_id"],
                "spatial_frame": contract["spatial_frame"],
                "substantive_interpretation_authorized": "false",
                "risk_synthesis_authorized": "false",
            }
        )
        provenance_rows.append(
            {
                "geography_id": geography["geography_id"],
                "raw_raster_path": rel(raster_path),
                "raw_raster_sha256": sha256_path(raster_path),
                "raw_request_sidecar_path": rel(sidecar_path),
                "raw_request_sidecar_sha256": sha256_path(sidecar_path),
                "raster_bytes": raster_path.stat().st_size,
                "raster_width": width,
                "raster_height": height,
                "native_grid_crs_epsg": epsg,
                "native_pixel_size_m": f"{pixel_size:.0f}",
                "aggregation_estimand": aggregation["estimand"],
                "boundary_rule": aggregation["boundary_rule"],
                "validity_rule": nodata_amendment["validity_rule"],
                "capacity_valid_fraction": f"{stats['capacity_valid_fraction']:.9f}",
                "semantic_evidence_path": rel(semantic_path),
                "semantic_evidence_sha256": semantic_sha,
            }
        )
        raw_evidence.append(
            {
                "geography_id": geography["geography_id"],
                "raster_path": rel(raster_path),
                "raster_sha256": sidecar["raster_sha256"],
                "raster_bytes": int(sidecar["raster_bytes"]),
                "request_sidecar_path": rel(sidecar_path),
                "request_sidecar_sha256": sha256_path(sidecar_path),
            }
        )

    component_path = ROOT / str(output["component_frame"])
    provenance_path = ROOT / str(output["provenance_frame"])
    manifest_path = ROOT / str(output["manifest"])

    component_fields = [
        "geography_id",
        "geography_name",
        "source_permendagri_code",
        "reference_year",
        aggregation["primary_value_field"],
        "capacity_valid_fraction",
        "inside_native_cell_count",
        "valid_native_cell_count",
        "invalid_native_cell_count",
        "claim_type",
        "component_class",
        "source_id",
        "spatial_frame",
        "substantive_interpretation_authorized",
        "risk_synthesis_authorized",
    ]
    provenance_fields = [
        "geography_id",
        "raw_raster_path",
        "raw_raster_sha256",
        "raw_request_sidecar_path",
        "raw_request_sidecar_sha256",
        "raster_bytes",
        "raster_width",
        "raster_height",
        "native_grid_crs_epsg",
        "native_pixel_size_m",
        "aggregation_estimand",
        "boundary_rule",
        "validity_rule",
        "capacity_valid_fraction",
        "semantic_evidence_path",
        "semantic_evidence_sha256",
    ]
    write_csv(component_path, component_fields, component_rows)
    write_csv(provenance_path, provenance_fields, provenance_rows)

    valid_fractions = [float(row["capacity_valid_fraction"]) for row in component_rows]
    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-capacity-component/v1",
        "milestone": 26,
        "stage": "stage1_capacity_component_materialization",
        "source_id": contract["source_id"],
        "component_class": contract["component_class"],
        "claim_type": contract["claim_type"],
        "reference_year": int(contract["reference_year"]),
        "spatial_frame": contract["spatial_frame"],
        "geography_count": len(component_rows),
        "observation_count": len(component_rows),
        "capacity_component_materialized": len(component_rows) == expected_geographies,
        "population_component_reextracted": False,
        "aggregation_estimand": aggregation["estimand"],
        "boundary_rule": aggregation["boundary_rule"],
        "minimum_valid_fraction_required": float(aggregation["minimum_valid_fraction_inside_geography"]),
        "minimum_valid_fraction_observed": min(valid_fractions),
        "all_geographies_valid_fraction_pass": all(
            value >= float(aggregation["minimum_valid_fraction_inside_geography"])
            for value in valid_fractions
        ),
        "inside_native_cell_count": sum(int(row["inside_native_cell_count"]) for row in component_rows),
        "valid_native_cell_count": sum(int(row["valid_native_cell_count"]) for row in component_rows),
        "invalid_native_cell_count": sum(int(row["invalid_native_cell_count"]) for row in component_rows),
        "raw_raster_count": len(raw_evidence),
        "raw_request_sidecar_count": len(raw_evidence),
        "raw_evidence": raw_evidence,
        "contract": {"path": rel(CONTRACT_PATH), "sha256": contract_sha},
        "transport_preflight": {"path": rel(PREFLIGHT_PATH), "sha256": preflight_sha},
        "nodata_transport_amendment": {"path": rel(NODATA_AMENDMENT_PATH), "sha256": nodata_sha},
        "source_metadata": {"path": rel(source_metadata_path), "sha256": source_metadata_sha},
        "semantic_evidence": {
            "path": rel(semantic_path),
            "sha256": semantic_sha,
            "role": contract["semantic_evidence"]["evidence_role"],
        },
        "big_boundary_probe_qualified": bool(
            big_probe.get("conclusions", {}).get("official_big_polygon_lane_qualified")
        ),
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
    parser = argparse.ArgumentParser(description="Materialize Milestone 26 InaRISK capacity 2021 component")
    parser.add_argument("--mode", choices=("live", "offline"), default="offline")
    args = parser.parse_args()
    manifest = build(args.mode)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "geography_count": manifest["geography_count"],
                "capacity_component_materialized": manifest["capacity_component_materialized"],
                "minimum_valid_fraction_observed": manifest["minimum_valid_fraction_observed"],
                "raw_raster_count": manifest["raw_raster_count"],
                "component_frame": manifest["outputs"]["component_frame"],
                "manifest": rel(ROOT / "data/manifests/milestone26_stage1_capacity_component.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
