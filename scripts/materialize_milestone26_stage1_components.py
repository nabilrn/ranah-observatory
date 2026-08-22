#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import math
import re
import sys
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
CONTRACT = ROOT / "data/manifests/milestone26_stage1_aggregation_contract.json"
STAGE0 = ROOT / "data/manifests/milestone26_source_qualification.json"
REGISTRY = ROOT / "data/registries/m26-bnpb-source-candidates.csv"
RAW_ROOT = ROOT / "data/processed/bnpb/m26_component_extraction"
OUT = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage1-component-frame.csv"
PROVENANCE = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage1-component-provenance.csv"
MANIFEST = ROOT / "data/manifests/milestone26_stage1_components.json"

SOURCE_IDS = ("inarisk_capacity_2021", "inarisk_population_2020")
SOURCE_META_SNAPSHOT = {
    "inarisk_capacity_2021": ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_capacity_2021.json",
    "inarisk_population_2020": ROOT / "data/processed/bnpb/m26_source_qualification/inarisk_population_2020.json",
}
SEMANTIC_PATHS = {
    "capacity": RAW_ROOT / "semantic/capacity-index-scale.html",
    "population": RAW_ROOT / "semantic/population-grid-cell-semantics.html",
}

FRAME_FIELDS = [
    "geography_id",
    "geography_name",
    "source_permendagri_code",
    "spatial_frame",
    "capacity_reference_year",
    "capacity_index_2021_mean",
    "capacity_inside_pixel_count",
    "capacity_valid_pixel_count",
    "capacity_valid_fraction",
    "population_reference_year",
    "population_exposure_proxy_2020_persons",
    "population_inside_pixel_count",
    "population_valid_pixel_count",
    "population_valid_fraction",
    "cross_component_temporal_aggregation_authorized",
    "risk_synthesis_authorized",
]
PROVENANCE_FIELDS = [
    "provenance_id",
    "source_id",
    "component_class",
    "geography_id",
    "reference_year",
    "aggregation",
    "source_service_url",
    "export_request_url",
    "raster_path",
    "raster_sha256",
    "raster_bytes",
    "source_metadata_path",
    "source_metadata_sha256",
    "semantic_evidence_path",
    "semantic_evidence_sha256",
    "bbox_native",
    "width",
    "height",
    "pixel_size_m",
    "crs_epsg",
    "boundary_rule",
    "resampling",
]


class M26Stage1Error(RuntimeError):
    pass


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(fields: list[str], rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fields})
    return buffer.getvalue().encode("utf-8")


def normalize_text(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def normalize_phrase(value: str) -> str:
    text = html.unescape(value).replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().casefold()


def load_contract() -> dict[str, Any]:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage1-aggregation-contract/v1":
        raise M26Stage1Error("unexpected Stage 1 contract schema")
    if payload.get("contract_locked_before_cross_geography_numeric_extraction") is not True:
        raise M26Stage1Error("Stage 1 aggregation contract was not pre-locked")
    if payload.get("authorized_source_ids") != list(SOURCE_IDS):
        raise M26Stage1Error("Stage 1 authorized source set drift")
    if payload.get("held_source_ids") != ["dibi_kabupaten_hidromet_2015_2024"]:
        raise M26Stage1Error("Stage 1 held source set drift")
    if payload["dibi_2015_2024"].get("numeric_extraction_authorized_in_stage1") is not False:
        raise M26Stage1Error("opaque DIBI values must remain held")
    for key in (
        "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26Stage1Error(f"Stage 1 forbidden authorization enabled: {key}")
    return payload


def load_stage0() -> dict[str, Any]:
    payload = json.loads(STAGE0.read_text(encoding="utf-8"))
    if payload.get("stage0_complete") is not True or payload.get("expected_qualification_states_match") is not True:
        raise M26Stage1Error("M26 Stage 0 is not fully qualified")
    qualified = payload.get("qualified_numeric_source_ids", [])
    for source_id in SOURCE_IDS:
        if source_id not in qualified:
            raise M26Stage1Error(f"Stage 1 source was not numeric-qualified in Stage 0: {source_id}")
    if payload.get("hazard_vulnerability_numeric_extraction_authorized") is not False:
        raise M26Stage1Error("hazard/vulnerability extraction unexpectedly authorized")
    return payload


def verify_stage0_snapshot_hashes(stage0: dict[str, Any]) -> dict[str, str]:
    expected = {item["source_id"]: item for item in stage0.get("snapshots", [])}
    hashes: dict[str, str] = {}
    for source_id, path in SOURCE_META_SNAPSHOT.items():
        if source_id not in expected:
            raise M26Stage1Error(f"missing Stage 0 snapshot manifest entry: {source_id}")
        digest = sha256_path(path)
        if digest != expected[source_id]["sha256"]:
            raise M26Stage1Error(f"Stage 0 snapshot SHA mismatch: {source_id}")
        hashes[source_id] = digest
    return hashes


def registry_urls() -> dict[str, str]:
    with REGISTRY.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {str(row["source_id"]): str(row["source_url"]) for row in rows}
    for source_id in SOURCE_IDS:
        if not result.get(source_id):
            raise M26Stage1Error(f"missing source URL in registry: {source_id}")
    return result


def request_bytes(url: str, *, retries: int = 3, timeout: float = 90.0) -> tuple[str, str, bytes]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if int(response.status) != 200:
                    raise M26Stage1Error(f"HTTP {response.status}: {url}")
                return str(response.geturl()), str(response.headers.get("Content-Type", "")), response.read()
        except (urllib.error.URLError, TimeoutError, M26Stage1Error) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(1.0 * (2**attempt))
    raise M26Stage1Error(f"request failed after retries: {url}") from last_error


def freeze_semantic_evidence(contract: dict[str, Any], fetch_live: bool) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for role, spec in contract["semantic_evidence"].items():
        path = SEMANTIC_PATHS[role]
        if fetch_live:
            _final_url, content_type, body = request_bytes(spec["url"])
            if "html" not in content_type.casefold() and not body.lstrip().lower().startswith(b"<"):
                raise M26Stage1Error(f"semantic evidence is not HTML: {role}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        if not path.exists():
            raise M26Stage1Error(f"semantic evidence snapshot missing: {role}")
        body = path.read_bytes()
        normalized = normalize_text(body)
        for phrase in spec["required_phrases"]:
            if normalize_phrase(phrase) not in normalized:
                raise M26Stage1Error(f"required semantic phrase not found for {role}: {phrase!r}")
        result[role] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_bytes(body),
            "source_url": spec["url"],
            "evidence_role": spec["evidence_role"],
        }
    return result


def source_metadata(source_id: str) -> dict[str, Any]:
    payload = json.loads(SOURCE_META_SNAPSHOT[source_id].read_text(encoding="utf-8"))
    primary = payload.get("primary")
    if not isinstance(primary, dict):
        raise M26Stage1Error(f"invalid Stage 0 ImageServer snapshot: {source_id}")
    if int(primary.get("bandCount", 0)) != 1 or int(primary.get("spatialReference", {}).get("wkid", 0)) != 3395:
        raise M26Stage1Error(f"unexpected raster contract for {source_id}")
    if float(primary.get("pixelSizeX", 0)) != 100.0 or float(primary.get("pixelSizeY", 0)) != 100.0:
        raise M26Stage1Error(f"unexpected native pixel size for {source_id}")
    return primary


def aligned_window(bounds: tuple[float, float, float, float], meta: dict[str, Any]) -> tuple[tuple[float, float, float, float], int, int]:
    minx, miny, maxx, maxy = bounds
    extent = meta["fullExtent"]
    origin_x = float(extent["xmin"])
    origin_y = float(extent["ymax"])
    pixel = 100.0
    col0 = math.floor((minx - origin_x) / pixel)
    col1 = math.ceil((maxx - origin_x) / pixel)
    row0 = math.floor((origin_y - maxy) / pixel)
    row1 = math.ceil((origin_y - miny) / pixel)
    width = int(col1 - col0)
    height = int(row1 - row0)
    if width <= 0 or height <= 0:
        raise M26Stage1Error("non-positive aligned raster window")
    if width > int(meta.get("maxImageWidth", 0)) or height > int(meta.get("maxImageHeight", 0)):
        raise M26Stage1Error(f"aligned raster window exceeds ImageServer export limits: {width}x{height}")
    left = origin_x + col0 * pixel
    right = origin_x + col1 * pixel
    top = origin_y - row0 * pixel
    bottom = origin_y - row1 * pixel
    return (left, bottom, right, top), width, height


def export_url(base: str, bbox: tuple[float, float, float, float], width: int, height: int) -> str:
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
    return base.rstrip("/") + "/exportImage?" + urllib.parse.urlencode(params)


def is_tiff(body: bytes) -> bool:
    return body.startswith(b"II*\x00") or body.startswith(b"MM\x00*")


def sidecar_path(raster_path: Path) -> Path:
    return raster_path.with_suffix(".json")


def ensure_raster(
    source_id: str,
    base_url: str,
    geography_id: str,
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    source_meta_sha: str,
    semantic: dict[str, str],
    fetch_live: bool,
) -> tuple[Path, dict[str, Any]]:
    folder = RAW_ROOT / source_id
    raster_path = folder / f"{geography_id}.tif"
    meta_path = sidecar_path(raster_path)
    url = export_url(base_url, bbox, width, height)
    if fetch_live:
        final_url, content_type, body = request_bytes(url)
        if not is_tiff(body):
            preview = body[:500].decode("utf-8", errors="replace")
            raise M26Stage1Error(f"ImageServer export is not TIFF for {source_id}/{geography_id}: {preview}")
        if len(body) >= 95_000_000:
            raise M26Stage1Error(f"single frozen raster is too large for GitHub: {source_id}/{geography_id}")
        folder.mkdir(parents=True, exist_ok=True)
        raster_path.write_bytes(body)
        sidecar = {
            "schema": "ranah-observatory/milestone26-stage1-raster-source/v1",
            "source_id": source_id,
            "geography_id": geography_id,
            "requested_url": url,
            "final_url": final_url,
            "content_type": content_type,
            "bbox_native": list(bbox),
            "width": width,
            "height": height,
            "pixel_size_m": 100,
            "crs_epsg": 3395,
            "resampling": "nearest_neighbor",
            "raster_sha256": sha256_bytes(body),
            "raster_bytes": len(body),
            "source_metadata_sha256": source_meta_sha,
            "semantic_evidence_sha256": semantic["sha256"],
        }
        meta_path.write_bytes(canonical_json_bytes(sidecar))
    if not raster_path.exists() or not meta_path.exists():
        raise M26Stage1Error(f"frozen raster/sidecar missing: {source_id}/{geography_id}")
    sidecar = json.loads(meta_path.read_text(encoding="utf-8"))
    if sidecar.get("requested_url") != url:
        raise M26Stage1Error(f"frozen raster request contract drift: {source_id}/{geography_id}")
    digest = sha256_path(raster_path)
    if digest != sidecar.get("raster_sha256"):
        raise M26Stage1Error(f"frozen raster SHA mismatch: {source_id}/{geography_id}")
    if sidecar.get("source_metadata_sha256") != source_meta_sha or sidecar.get("semantic_evidence_sha256") != semantic["sha256"]:
        raise M26Stage1Error(f"frozen raster evidence binding mismatch: {source_id}/{geography_id}")
    return raster_path, sidecar


def valid_mask(values: np.ndarray, inside: np.ndarray, nodata: float | None) -> np.ndarray:
    valid = inside & np.isfinite(values)
    if nodata is not None and math.isfinite(float(nodata)):
        valid &= values != float(nodata)
    return valid


def aggregate_component(source_id: str, raster_path: Path, projected_geometry: Any, minimum_fraction: float) -> dict[str, Any]:
    with rasterio.open(raster_path) as dataset:
        if dataset.count != 1 or dataset.crs is None or dataset.crs.to_epsg() != 3395:
            raise M26Stage1Error(f"unexpected frozen raster CRS/bands: {raster_path}")
        if abs(float(dataset.transform.a) - 100.0) > 1e-6 or abs(abs(float(dataset.transform.e)) - 100.0) > 1e-6:
            raise M26Stage1Error(f"frozen raster is not native 100 m grid: {raster_path}")
        values = dataset.read(1).astype(np.float64, copy=False)
        inside = geometry_mask(
            [mapping(projected_geometry)],
            out_shape=(dataset.height, dataset.width),
            transform=dataset.transform,
            invert=True,
            all_touched=False,
        )
        inside_count = int(np.count_nonzero(inside))
        if inside_count <= 0:
            raise M26Stage1Error(f"no raster cell centers inside geometry: {raster_path}")
        valid = valid_mask(values, inside, dataset.nodata)
        valid_count = int(np.count_nonzero(valid))
        fraction = valid_count / inside_count
        if fraction < minimum_fraction:
            raise M26Stage1Error(f"valid raster fraction below gate for {raster_path}: {fraction}")
        selected = values[valid]
        if source_id == "inarisk_capacity_2021":
            if np.any(selected < 0.0) or np.any(selected > 1.0):
                raise M26Stage1Error(f"capacity pixel outside locked 0-1 range: {raster_path}")
            value = float(np.mean(selected, dtype=np.float64))
        elif source_id == "inarisk_population_2020":
            if np.any(selected < 0.0):
                raise M26Stage1Error(f"negative population grid value: {raster_path}")
            value = float(np.sum(selected, dtype=np.float64))
        else:
            raise M26Stage1Error(f"unauthorized Stage 1 source: {source_id}")
        if not math.isfinite(value):
            raise M26Stage1Error(f"non-finite component aggregate: {raster_path}")
        return {
            "value": value,
            "inside_pixel_count": inside_count,
            "valid_pixel_count": valid_count,
            "valid_fraction": fraction,
        }


def stable_provenance_id(source_id: str, geography_id: str, raster_sha: str, contract_sha: str) -> str:
    token = f"{source_id}|{geography_id}|{raster_sha}|{contract_sha}"
    return "m26prov_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def build(fetch_live: bool) -> dict[str, Any]:
    contract = load_contract()
    stage0 = load_stage0()
    source_meta_hashes = verify_stage0_snapshot_hashes(stage0)
    source_urls = registry_urls()
    semantic = freeze_semantic_evidence(contract, fetch_live)
    contract_sha = sha256_path(CONTRACT)
    minimum_fraction = float(contract["quality_gates"]["minimum_valid_fraction_inside_polygon"])

    features, big_probe = load_qualified_big_features()
    features.sort(key=lambda row: row["geography_id"])
    if len(features) != 19 or len({row["geography_id"] for row in features}) != 19:
        raise M26Stage1Error("fixed BIG geography frame is not exact 19")

    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    source_meta = {source_id: source_metadata(source_id) for source_id in SOURCE_IDS}
    frame_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    raw_objects: list[dict[str, Any]] = []

    semantic_role = {"inarisk_capacity_2021": "capacity", "inarisk_population_2020": "population"}
    component_class = {"inarisk_capacity_2021": "capacity", "inarisk_population_2020": "exposure"}
    reference_year = {"inarisk_capacity_2021": 2021, "inarisk_population_2020": 2020}
    aggregation = {
        "inarisk_capacity_2021": "mean_of_valid_native_grid_cells_with_centers_inside_fixed_boundary",
        "inarisk_population_2020": "sum_of_nonnegative_native_grid_cell_person_values_with_centers_inside_fixed_boundary",
    }

    for feature in features:
        geom = shape(feature["geometry"])
        if geom.is_empty:
            raise M26Stage1Error(f"empty BIG geometry: {feature['geography_id']}")
        projected = shapely_transform(transformer.transform, geom)
        component_results: dict[str, dict[str, Any]] = {}
        for source_id in SOURCE_IDS:
            bbox, width, height = aligned_window(projected.bounds, source_meta[source_id])
            role = semantic_role[source_id]
            raster_path, sidecar = ensure_raster(
                source_id,
                source_urls[source_id],
                feature["geography_id"],
                bbox,
                width,
                height,
                source_meta_hashes[source_id],
                semantic[role],
                fetch_live,
            )
            aggregate = aggregate_component(source_id, raster_path, projected, minimum_fraction)
            component_results[source_id] = {**aggregate, "sidecar": sidecar, "raster_path": raster_path}
            raster_sha = sidecar["raster_sha256"]
            provenance_rows.append({
                "provenance_id": stable_provenance_id(source_id, feature["geography_id"], raster_sha, contract_sha),
                "source_id": source_id,
                "component_class": component_class[source_id],
                "geography_id": feature["geography_id"],
                "reference_year": reference_year[source_id],
                "aggregation": aggregation[source_id],
                "source_service_url": source_urls[source_id],
                "export_request_url": sidecar["requested_url"],
                "raster_path": raster_path.relative_to(ROOT).as_posix(),
                "raster_sha256": raster_sha,
                "raster_bytes": sidecar["raster_bytes"],
                "source_metadata_path": SOURCE_META_SNAPSHOT[source_id].relative_to(ROOT).as_posix(),
                "source_metadata_sha256": source_meta_hashes[source_id],
                "semantic_evidence_path": semantic[role]["path"],
                "semantic_evidence_sha256": semantic[role]["sha256"],
                "bbox_native": ",".join(f"{float(v):.6f}" for v in sidecar["bbox_native"]),
                "width": sidecar["width"],
                "height": sidecar["height"],
                "pixel_size_m": 100,
                "crs_epsg": 3395,
                "boundary_rule": "pixel_center_inside_polygon",
                "resampling": "nearest_neighbor",
            })
            raw_objects.append({
                "source_id": source_id,
                "geography_id": feature["geography_id"],
                "path": raster_path.relative_to(ROOT).as_posix(),
                "sha256": raster_sha,
                "bytes": int(sidecar["raster_bytes"]),
            })

        capacity = component_results["inarisk_capacity_2021"]
        population = component_results["inarisk_population_2020"]
        frame_rows.append({
            "geography_id": feature["geography_id"],
            "geography_name": feature["geography_name"],
            "source_permendagri_code": feature["source_permendagri_code"],
            "spatial_frame": "BIG_June_2026_fixed_current_boundary",
            "capacity_reference_year": 2021,
            "capacity_index_2021_mean": f"{capacity['value']:.9f}",
            "capacity_inside_pixel_count": capacity["inside_pixel_count"],
            "capacity_valid_pixel_count": capacity["valid_pixel_count"],
            "capacity_valid_fraction": f"{capacity['valid_fraction']:.9f}",
            "population_reference_year": 2020,
            "population_exposure_proxy_2020_persons": f"{population['value']:.6f}",
            "population_inside_pixel_count": population["inside_pixel_count"],
            "population_valid_pixel_count": population["valid_pixel_count"],
            "population_valid_fraction": f"{population['valid_fraction']:.9f}",
            "cross_component_temporal_aggregation_authorized": "false",
            "risk_synthesis_authorized": "false",
        })

    frame_rows.sort(key=lambda row: row["geography_id"])
    provenance_rows.sort(key=lambda row: (row["source_id"], row["geography_id"]))
    raw_objects.sort(key=lambda row: (row["source_id"], row["geography_id"]))
    if len(frame_rows) != 19 or len(provenance_rows) != 38 or len(raw_objects) != 38:
        raise M26Stage1Error("unexpected Stage 1 output cardinality")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(csv_bytes(FRAME_FIELDS, frame_rows))
    PROVENANCE.write_bytes(csv_bytes(PROVENANCE_FIELDS, provenance_rows))

    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-components/v1",
        "milestone": 26,
        "stage": 1,
        "stage1_complete": True,
        "geography_count": 19,
        "component_count": 2,
        "observation_count": 38,
        "provenance_count": 38,
        "authorized_source_ids": list(SOURCE_IDS),
        "held_source_ids": ["dibi_kabupaten_hidromet_2015_2024"],
        "capacity_reference_year": 2021,
        "population_reference_year": 2020,
        "spatial_frame": "BIG_June_2026_fixed_current_boundary",
        "aggregation_contract": {
            "path": CONTRACT.relative_to(ROOT).as_posix(),
            "sha256": contract_sha,
        },
        "stage0_qualification": {
            "path": STAGE0.relative_to(ROOT).as_posix(),
            "sha256": sha256_path(STAGE0),
        },
        "semantic_evidence": semantic,
        "big_expected_edition": big_probe.get("expected_edition"),
        "raw_raster_count": 38,
        "raw_raster_total_bytes": sum(int(item["bytes"]) for item in raw_objects),
        "raw_rasters": raw_objects,
        "outputs": {
            "component_frame": {"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha256_path(OUT)},
            "provenance": {"path": PROVENANCE.relative_to(ROOT).as_posix(), "sha256": sha256_path(PROVENANCE)},
        },
        "dibi_numeric_extraction_performed": False,
        "hazard_vulnerability_numeric_extraction_performed": False,
        "event_impact_panel_materialized": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "completion_claim": "two independently qualified disaster-risk components summarized on the fixed current-boundary frame; no composite risk score",
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_bytes(canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="fetch and freeze live Stage 1 source rasters and semantic evidence")
    args = parser.parse_args()
    try:
        manifest = build(fetch_live=args.fetch)
    except (OSError, ValueError, json.JSONDecodeError, M26Stage1Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "stage1_complete": manifest["stage1_complete"],
        "geography_count": manifest["geography_count"],
        "observation_count": manifest["observation_count"],
        "raw_raster_total_bytes": manifest["raw_raster_total_bytes"],
        "risk_synthesis_authorized": manifest["risk_synthesis_authorized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
