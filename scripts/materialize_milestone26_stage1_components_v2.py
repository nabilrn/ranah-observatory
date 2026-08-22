#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from shapely.geometry import mapping

from scripts import materialize_milestone26_stage1_components as base

ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "data/manifests/milestone26_stage1_nodata_transport_amendment.json"

# Re-export stable helpers for focused tests and downstream read-only reproducibility.
load_contract = base.load_contract
load_stage0 = base.load_stage0
normalize_text = base.normalize_text
normalize_phrase = base.normalize_phrase
aligned_window = base.aligned_window
export_url = base.export_url
canonical_json_bytes = base.canonical_json_bytes
M26Stage1Error = base.M26Stage1Error
STAGE0 = base.STAGE0
MANIFEST = base.MANIFEST


def load_nodata_amendment() -> dict[str, Any]:
    payload = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage1-nodata-transport-amendment/v1":
        raise M26Stage1Error("unexpected Stage 1 NoData amendment schema")
    if payload.get("affected_source_ids") != list(base.SOURCE_IDS):
        raise M26Stage1Error("Stage 1 NoData amendment source set drift")
    if payload.get("minimum_valid_fraction_inside_polygon_unchanged") != 0.99:
        raise M26Stage1Error("Stage 1 NoData amendment changed the coverage gate")
    for key in (
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
            raise M26Stage1Error(f"invalid Stage 1 NoData amendment boundary: {key}")

    for source_id in base.SOURCE_IDS:
        spec = payload["source_range_binding"][source_id]
        meta_path = ROOT / spec["metadata_path"]
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))["primary"]
        declared_min = float(metadata["minValues"][0])
        declared_max = float(metadata["maxValues"][0])
        if declared_min != float(spec["declared_min"]) or declared_max != float(spec["declared_max"]):
            raise M26Stage1Error(f"NoData amendment source range does not match frozen ImageServer metadata: {source_id}")
    return payload


def source_valid_range(source_id: str) -> tuple[float, float]:
    payload = load_nodata_amendment()
    spec = payload["source_range_binding"][source_id]
    return float(spec["declared_min"]), float(spec["declared_max"])


def aggregate_component(source_id: str, raster_path: Path, projected_geometry: Any, minimum_fraction: float) -> dict[str, Any]:
    if source_id not in base.SOURCE_IDS:
        raise M26Stage1Error(f"unauthorized Stage 1 source: {source_id}")
    declared_min, declared_max = source_valid_range(source_id)
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

        finite_inside = inside & np.isfinite(values)
        if dataset.nodata is not None and math.isfinite(float(dataset.nodata)):
            finite_inside &= values != float(dataset.nodata)
        valid = finite_inside & (values >= declared_min) & (values <= declared_max)
        transport_invalid_count = int(np.count_nonzero(finite_inside & ~valid))
        valid_count = int(np.count_nonzero(valid))
        fraction = valid_count / inside_count
        if fraction < minimum_fraction:
            raise M26Stage1Error(
                f"valid raster fraction below locked gate for {raster_path}: "
                f"valid={valid_count} inside={inside_count} fraction={fraction:.9f} "
                f"transport_invalid={transport_invalid_count} declared_range=[{declared_min},{declared_max}]"
            )
        selected = values[valid]
        if source_id == "inarisk_capacity_2021":
            value = float(np.mean(selected, dtype=np.float64))
        else:
            value = float(np.sum(selected, dtype=np.float64))
        if not math.isfinite(value):
            raise M26Stage1Error(f"non-finite component aggregate: {raster_path}")
        return {
            "value": value,
            "inside_pixel_count": inside_count,
            "valid_pixel_count": valid_count,
            "valid_fraction": fraction,
            "transport_invalid_pixel_count": transport_invalid_count,
            "declared_source_min": declared_min,
            "declared_source_max": declared_max,
        }


_original_build = base.build


def build(fetch_live: bool) -> dict[str, Any]:
    amendment = load_nodata_amendment()
    base.aggregate_component = aggregate_component
    manifest = _original_build(fetch_live)
    manifest["nodata_transport_amendment"] = {
        "path": AMENDMENT.relative_to(ROOT).as_posix(),
        "sha256": base.sha256_path(AMENDMENT),
        "validity_rule": amendment["validity_rule"],
    }
    MANIFEST.write_bytes(canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
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
