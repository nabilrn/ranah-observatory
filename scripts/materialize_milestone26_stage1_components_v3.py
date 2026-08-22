#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import geometry_mask
from shapely.geometry import mapping, shape
from shapely.ops import transform as shapely_transform

from scripts import materialize_milestone26_stage1_components as base
from scripts import materialize_milestone26_stage1_components_v2 as nodata

ROOT = Path(__file__).resolve().parents[1]
CHUNK_AMENDMENT = ROOT / "data/manifests/milestone26_stage1_chunk_transport_amendment.json"
NODATA_AMENDMENT = ROOT / "data/manifests/milestone26_stage1_nodata_transport_amendment.json"

FRAME_FIELDS = base.FRAME_FIELDS
PROVENANCE_FIELDS = [
    "provenance_id",
    "source_id",
    "component_class",
    "geography_id",
    "reference_year",
    "aggregation",
    "source_service_url",
    "bundle_manifest_path",
    "bundle_manifest_sha256",
    "tile_count",
    "tile_total_bytes",
    "source_metadata_path",
    "source_metadata_sha256",
    "semantic_evidence_path",
    "semantic_evidence_sha256",
    "geography_bbox_native",
    "geography_width",
    "geography_height",
    "pixel_size_m",
    "crs_epsg",
    "boundary_rule",
    "resampling",
]


class M26ChunkError(RuntimeError):
    pass


def load_chunk_amendment() -> dict[str, Any]:
    payload = json.loads(CHUNK_AMENDMENT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage1-chunk-transport-amendment/v1":
        raise M26ChunkError("unexpected M26 chunk amendment schema")
    if payload.get("affected_source_ids") != list(base.SOURCE_IDS):
        raise M26ChunkError("chunk amendment source set drift")
    if int(payload.get("maximum_tile_width_pixels", 0)) != 1500 or int(payload.get("maximum_tile_height_pixels", 0)) != 1500:
        raise M26ChunkError("chunk amendment tile limit drift")
    for key in (
        "downsampling_authorized",
        "upsampling_authorized",
        "aggregation_semantics_changed",
        "cross_geography_substantive_values_inspected_before_amendment",
        "outcome_or_model_results_inspected",
        "source_family_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if payload.get(key) is not False:
            raise M26ChunkError(f"invalid chunk amendment boundary: {key}")
    if float(payload.get("minimum_valid_fraction_inside_polygon_unchanged", -1)) != 0.99:
        raise M26ChunkError("chunk amendment changed the locked coverage gate")
    nodata.load_nodata_amendment()
    return payload


def tile_specs(
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    max_width: int,
    max_height: int,
) -> list[dict[str, Any]]:
    if width <= 0 or height <= 0 or max_width <= 0 or max_height <= 0:
        raise M26ChunkError("invalid chunk dimensions")
    left, bottom, right, top = bbox
    pixel_x = (right - left) / width
    pixel_y = (top - bottom) / height
    if abs(pixel_x - 100.0) > 1e-6 or abs(pixel_y - 100.0) > 1e-6:
        raise M26ChunkError(f"chunk source window is not exact native 100 m grid: {pixel_x}, {pixel_y}")
    specs: list[dict[str, Any]] = []
    index = 0
    for row0 in range(0, height, max_height):
        row1 = min(row0 + max_height, height)
        for col0 in range(0, width, max_width):
            col1 = min(col0 + max_width, width)
            tile_left = left + col0 * 100.0
            tile_right = left + col1 * 100.0
            tile_top = top - row0 * 100.0
            tile_bottom = top - row1 * 100.0
            specs.append(
                {
                    "tile_index": index,
                    "row0": row0,
                    "row1": row1,
                    "col0": col0,
                    "col1": col1,
                    "width": col1 - col0,
                    "height": row1 - row0,
                    "bbox": (tile_left, tile_bottom, tile_right, tile_top),
                }
            )
            index += 1
    area_pixels = sum(int(item["width"]) * int(item["height"]) for item in specs)
    if area_pixels != width * height:
        raise M26ChunkError("chunk coverage has gap or overlap")
    return specs


def _tile_folder(source_id: str, geography_id: str) -> Path:
    return base.RAW_ROOT / source_id / geography_id


def _tile_paths(source_id: str, geography_id: str, tile_index: int) -> tuple[Path, Path]:
    folder = _tile_folder(source_id, geography_id)
    stem = f"tile-{tile_index:03d}"
    return folder / f"{stem}.tif", folder / f"{stem}.json"


def ensure_tile(
    source_id: str,
    base_url: str,
    geography_id: str,
    spec: dict[str, Any],
    source_meta_sha: str,
    semantic: dict[str, str],
    fetch_live: bool,
) -> tuple[Path, dict[str, Any]]:
    raster_path, sidecar_path = _tile_paths(source_id, geography_id, int(spec["tile_index"]))
    url = base.export_url(base_url, tuple(spec["bbox"]), int(spec["width"]), int(spec["height"]))
    if fetch_live:
        final_url, content_type, body = base.request_bytes(url, retries=5, timeout=90.0)
        if not base.is_tiff(body):
            preview = body[:500].decode("utf-8", errors="replace")
            raise M26ChunkError(f"ImageServer tile is not TIFF for {source_id}/{geography_id}: {preview}")
        if len(body) >= 95_000_000:
            raise M26ChunkError(f"single frozen tile exceeds GitHub file limit: {source_id}/{geography_id}")
        raster_path.parent.mkdir(parents=True, exist_ok=True)
        raster_path.write_bytes(body)
        sidecar = {
            "schema": "ranah-observatory/milestone26-stage1-raster-tile/v1",
            "source_id": source_id,
            "geography_id": geography_id,
            "tile_index": int(spec["tile_index"]),
            "row0": int(spec["row0"]),
            "row1": int(spec["row1"]),
            "col0": int(spec["col0"]),
            "col1": int(spec["col1"]),
            "requested_url": url,
            "final_url": final_url,
            "content_type": content_type,
            "bbox_native": list(spec["bbox"]),
            "width": int(spec["width"]),
            "height": int(spec["height"]),
            "pixel_size_m": 100,
            "crs_epsg": 3395,
            "resampling": "nearest_neighbor",
            "raster_sha256": base.sha256_bytes(body),
            "raster_bytes": len(body),
            "source_metadata_sha256": source_meta_sha,
            "semantic_evidence_sha256": semantic["sha256"],
        }
        sidecar_path.write_bytes(base.canonical_json_bytes(sidecar))
    if not raster_path.exists() or not sidecar_path.exists():
        raise M26ChunkError(f"frozen raster tile missing: {source_id}/{geography_id}/{spec['tile_index']}")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if sidecar.get("requested_url") != url:
        raise M26ChunkError(f"frozen tile request drift: {source_id}/{geography_id}/{spec['tile_index']}")
    digest = base.sha256_path(raster_path)
    if digest != sidecar.get("raster_sha256"):
        raise M26ChunkError(f"frozen tile SHA mismatch: {source_id}/{geography_id}/{spec['tile_index']}")
    if sidecar.get("source_metadata_sha256") != source_meta_sha or sidecar.get("semantic_evidence_sha256") != semantic["sha256"]:
        raise M26ChunkError(f"frozen tile evidence binding mismatch: {source_id}/{geography_id}/{spec['tile_index']}")
    return raster_path, sidecar


def tile_statistics(source_id: str, raster_path: Path, projected_geometry: Any) -> dict[str, Any]:
    declared_min, declared_max = nodata.source_valid_range(source_id)
    with rasterio.open(raster_path) as dataset:
        if dataset.count != 1 or dataset.crs is None or dataset.crs.to_epsg() != 3395:
            raise M26ChunkError(f"unexpected tile CRS/bands: {raster_path}")
        if abs(float(dataset.transform.a) - 100.0) > 1e-6 or abs(abs(float(dataset.transform.e)) - 100.0) > 1e-6:
            raise M26ChunkError(f"tile is not native 100 m grid: {raster_path}")
        values = dataset.read(1).astype(np.float64, copy=False)
        inside = geometry_mask(
            [mapping(projected_geometry)],
            out_shape=(dataset.height, dataset.width),
            transform=dataset.transform,
            invert=True,
            all_touched=False,
        )
        inside_count = int(np.count_nonzero(inside))
        if inside_count == 0:
            return {
                "inside_count": 0,
                "valid_count": 0,
                "transport_invalid_count": 0,
                "value_sum": 0.0,
            }
        candidate = inside & np.isfinite(values)
        if dataset.nodata is not None and math.isfinite(float(dataset.nodata)):
            candidate &= values != float(dataset.nodata)
        valid = candidate & (values >= declared_min) & (values <= declared_max)
        transport_invalid_count = int(np.count_nonzero(candidate & ~valid))
        selected = values[valid]
        value_sum = float(np.sum(selected, dtype=np.float64)) if selected.size else 0.0
        if not math.isfinite(value_sum):
            raise M26ChunkError(f"non-finite tile aggregate: {raster_path}")
        return {
            "inside_count": inside_count,
            "valid_count": int(selected.size),
            "transport_invalid_count": transport_invalid_count,
            "value_sum": value_sum,
        }


def combine_statistics(source_id: str, stats: list[dict[str, Any]], minimum_fraction: float) -> dict[str, Any]:
    inside = sum(int(item["inside_count"]) for item in stats)
    valid = sum(int(item["valid_count"]) for item in stats)
    invalid = sum(int(item["transport_invalid_count"]) for item in stats)
    value_sum = math.fsum(float(item["value_sum"]) for item in stats)
    if inside <= 0:
        raise M26ChunkError("chunked geography has no pixel centers inside polygon")
    fraction = valid / inside
    if fraction < minimum_fraction:
        raise M26ChunkError(
            f"chunked valid fraction below locked gate: valid={valid} inside={inside} "
            f"fraction={fraction:.9f} transport_invalid={invalid}"
        )
    if source_id == "inarisk_capacity_2021":
        if valid <= 0:
            raise M26ChunkError("capacity has no valid native-grid cells")
        value = value_sum / valid
    elif source_id == "inarisk_population_2020":
        value = value_sum
    else:
        raise M26ChunkError(f"unauthorized chunked source: {source_id}")
    if not math.isfinite(value):
        raise M26ChunkError("non-finite combined component aggregate")
    return {
        "value": value,
        "inside_pixel_count": inside,
        "valid_pixel_count": valid,
        "valid_fraction": fraction,
        "transport_invalid_pixel_count": invalid,
    }


def bundle_manifest(
    source_id: str,
    geography_id: str,
    geography_bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    tile_records: list[dict[str, Any]],
    source_meta_sha: str,
    semantic_sha: str,
) -> tuple[Path, str]:
    path = _tile_folder(source_id, geography_id) / "bundle.json"
    payload = {
        "schema": "ranah-observatory/milestone26-stage1-raster-bundle/v1",
        "source_id": source_id,
        "geography_id": geography_id,
        "geography_bbox_native": list(geography_bbox),
        "geography_width": width,
        "geography_height": height,
        "pixel_size_m": 100,
        "crs_epsg": 3395,
        "source_metadata_sha256": source_meta_sha,
        "semantic_evidence_sha256": semantic_sha,
        "chunk_transport_amendment_sha256": base.sha256_path(CHUNK_AMENDMENT),
        "nodata_transport_amendment_sha256": base.sha256_path(NODATA_AMENDMENT),
        "tile_count": len(tile_records),
        "tile_total_bytes": sum(int(item["bytes"]) for item in tile_records),
        "tiles": tile_records,
    }
    path.write_bytes(base.canonical_json_bytes(payload))
    return path, base.sha256_path(path)


def stable_provenance_id(source_id: str, geography_id: str, bundle_sha: str, contract_sha: str) -> str:
    token = f"{source_id}|{geography_id}|{bundle_sha}|{contract_sha}"
    return "m26prov_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def build(fetch_live: bool) -> dict[str, Any]:
    amendment = load_chunk_amendment()
    contract = base.load_contract()
    stage0 = base.load_stage0()
    source_meta_hashes = base.verify_stage0_snapshot_hashes(stage0)
    source_urls = base.registry_urls()
    semantic = base.freeze_semantic_evidence(contract, fetch_live)
    contract_sha = base.sha256_path(base.CONTRACT)
    minimum_fraction = float(contract["quality_gates"]["minimum_valid_fraction_inside_polygon"])
    max_width = int(amendment["maximum_tile_width_pixels"])
    max_height = int(amendment["maximum_tile_height_pixels"])

    features, big_probe = base.load_qualified_big_features()
    features.sort(key=lambda row: row["geography_id"])
    if len(features) != 19 or len({row["geography_id"] for row in features}) != 19:
        raise M26ChunkError("fixed BIG geography frame is not exact 19")

    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    source_meta = {source_id: base.source_metadata(source_id) for source_id in base.SOURCE_IDS}
    semantic_role = {"inarisk_capacity_2021": "capacity", "inarisk_population_2020": "population"}
    component_class = {"inarisk_capacity_2021": "capacity", "inarisk_population_2020": "exposure"}
    reference_year = {"inarisk_capacity_2021": 2021, "inarisk_population_2020": 2020}
    aggregation = {
        "inarisk_capacity_2021": "mean_of_valid_native_grid_cells_with_centers_inside_fixed_boundary",
        "inarisk_population_2020": "sum_of_nonnegative_native_grid_cell_person_values_with_centers_inside_fixed_boundary",
    }

    frame_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    raw_tiles: list[dict[str, Any]] = []
    bundle_records: list[dict[str, Any]] = []

    for feature in features:
        geom = shape(feature["geometry"])
        projected = shapely_transform(transformer.transform, geom)
        results: dict[str, dict[str, Any]] = {}
        for source_id in base.SOURCE_IDS:
            geography_bbox, geography_width, geography_height = base.aligned_window(projected.bounds, source_meta[source_id])
            specs = tile_specs(geography_bbox, geography_width, geography_height, max_width, max_height)
            stats: list[dict[str, Any]] = []
            tile_records: list[dict[str, Any]] = []
            role = semantic_role[source_id]
            for spec in specs:
                raster_path, sidecar = ensure_tile(
                    source_id,
                    source_urls[source_id],
                    feature["geography_id"],
                    spec,
                    source_meta_hashes[source_id],
                    semantic[role],
                    fetch_live,
                )
                stats.append(tile_statistics(source_id, raster_path, projected))
                relative = raster_path.relative_to(ROOT).as_posix()
                record = {
                    "tile_index": int(spec["tile_index"]),
                    "row0": int(spec["row0"]),
                    "row1": int(spec["row1"]),
                    "col0": int(spec["col0"]),
                    "col1": int(spec["col1"]),
                    "bbox_native": list(spec["bbox"]),
                    "width": int(spec["width"]),
                    "height": int(spec["height"]),
                    "path": relative,
                    "sidecar_path": base.sidecar_path(raster_path).relative_to(ROOT).as_posix(),
                    "sha256": sidecar["raster_sha256"],
                    "bytes": int(sidecar["raster_bytes"]),
                }
                tile_records.append(record)
                raw_tiles.append({"source_id": source_id, "geography_id": feature["geography_id"], **record})
            combined = combine_statistics(source_id, stats, minimum_fraction)
            results[source_id] = combined
            bundle_path, bundle_sha = bundle_manifest(
                source_id,
                feature["geography_id"],
                geography_bbox,
                geography_width,
                geography_height,
                tile_records,
                source_meta_hashes[source_id],
                semantic[role]["sha256"],
            )
            bundle_records.append(
                {
                    "source_id": source_id,
                    "geography_id": feature["geography_id"],
                    "path": bundle_path.relative_to(ROOT).as_posix(),
                    "sha256": bundle_sha,
                    "tile_count": len(tile_records),
                    "tile_total_bytes": sum(int(item["bytes"]) for item in tile_records),
                }
            )
            provenance_rows.append(
                {
                    "provenance_id": stable_provenance_id(source_id, feature["geography_id"], bundle_sha, contract_sha),
                    "source_id": source_id,
                    "component_class": component_class[source_id],
                    "geography_id": feature["geography_id"],
                    "reference_year": reference_year[source_id],
                    "aggregation": aggregation[source_id],
                    "source_service_url": source_urls[source_id],
                    "bundle_manifest_path": bundle_path.relative_to(ROOT).as_posix(),
                    "bundle_manifest_sha256": bundle_sha,
                    "tile_count": len(tile_records),
                    "tile_total_bytes": sum(int(item["bytes"]) for item in tile_records),
                    "source_metadata_path": base.SOURCE_META_SNAPSHOT[source_id].relative_to(ROOT).as_posix(),
                    "source_metadata_sha256": source_meta_hashes[source_id],
                    "semantic_evidence_path": semantic[role]["path"],
                    "semantic_evidence_sha256": semantic[role]["sha256"],
                    "geography_bbox_native": ",".join(f"{float(v):.6f}" for v in geography_bbox),
                    "geography_width": geography_width,
                    "geography_height": geography_height,
                    "pixel_size_m": 100,
                    "crs_epsg": 3395,
                    "boundary_rule": "pixel_center_inside_polygon",
                    "resampling": "nearest_neighbor",
                }
            )

        capacity = results["inarisk_capacity_2021"]
        population = results["inarisk_population_2020"]
        frame_rows.append(
            {
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
            }
        )

    frame_rows.sort(key=lambda row: row["geography_id"])
    provenance_rows.sort(key=lambda row: (row["source_id"], row["geography_id"]))
    raw_tiles.sort(key=lambda row: (row["source_id"], row["geography_id"], int(row["tile_index"])))
    bundle_records.sort(key=lambda row: (row["source_id"], row["geography_id"]))
    if len(frame_rows) != 19 or len(provenance_rows) != 38 or len(bundle_records) != 38 or len(raw_tiles) < 38:
        raise M26ChunkError("unexpected chunked Stage 1 cardinality")

    base.OUT.parent.mkdir(parents=True, exist_ok=True)
    base.OUT.write_bytes(base.csv_bytes(FRAME_FIELDS, frame_rows))
    base.PROVENANCE.write_bytes(base.csv_bytes(PROVENANCE_FIELDS, provenance_rows))

    manifest = {
        "schema": "ranah-observatory/milestone26-stage1-components/v2",
        "milestone": 26,
        "stage": 1,
        "stage1_complete": True,
        "geography_count": 19,
        "component_count": 2,
        "observation_count": 38,
        "provenance_count": 38,
        "authorized_source_ids": list(base.SOURCE_IDS),
        "held_source_ids": ["dibi_kabupaten_hidromet_2015_2024"],
        "capacity_reference_year": 2021,
        "population_reference_year": 2020,
        "spatial_frame": "BIG_June_2026_fixed_current_boundary",
        "aggregation_contract": {"path": base.CONTRACT.relative_to(ROOT).as_posix(), "sha256": contract_sha},
        "stage0_qualification": {"path": base.STAGE0.relative_to(ROOT).as_posix(), "sha256": base.sha256_path(base.STAGE0)},
        "nodata_transport_amendment": {"path": NODATA_AMENDMENT.relative_to(ROOT).as_posix(), "sha256": base.sha256_path(NODATA_AMENDMENT)},
        "chunk_transport_amendment": {"path": CHUNK_AMENDMENT.relative_to(ROOT).as_posix(), "sha256": base.sha256_path(CHUNK_AMENDMENT)},
        "semantic_evidence": semantic,
        "big_expected_edition": big_probe.get("expected_edition"),
        "bundle_count": 38,
        "bundles": bundle_records,
        "raw_raster_tile_count": len(raw_tiles),
        "raw_raster_total_bytes": sum(int(item["bytes"]) for item in raw_tiles),
        "raw_raster_tiles": raw_tiles,
        "outputs": {
            "component_frame": {"path": base.OUT.relative_to(ROOT).as_posix(), "sha256": base.sha256_path(base.OUT)},
            "provenance": {"path": base.PROVENANCE.relative_to(ROOT).as_posix(), "sha256": base.sha256_path(base.PROVENANCE)},
        },
        "dibi_numeric_extraction_performed": False,
        "hazard_vulnerability_numeric_extraction_performed": False,
        "event_impact_panel_materialized": False,
        "cross_component_temporal_aggregation_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "completion_claim": "two independently qualified disaster-risk components summarized on the fixed current-boundary frame using native-grid chunk transport; no composite risk score",
    }
    base.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    base.MANIFEST.write_bytes(base.canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build(fetch_live=args.fetch)
    except (OSError, ValueError, json.JSONDecodeError, base.M26Stage1Error, M26ChunkError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "stage1_complete": manifest["stage1_complete"],
                "geography_count": manifest["geography_count"],
                "observation_count": manifest["observation_count"],
                "raw_raster_tile_count": manifest["raw_raster_tile_count"],
                "raw_raster_total_bytes": manifest["raw_raster_total_bytes"],
                "risk_synthesis_authorized": manifest["risk_synthesis_authorized"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
