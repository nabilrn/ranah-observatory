#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import Transformer
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from shapely.geometry import mapping, shape
from shapely.ops import transform as shapely_transform

from scripts import materialize_milestone26_stage1_components as stage1

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone26_population_mapserver_workload_contract.json"
SCALE = ROOT / "data/manifests/milestone26_population_mapserver_scale.json"
OUT = ROOT / "data/manifests/milestone26_population_mapserver_workload.json"


class M26PopulationWorkloadError(RuntimeError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-population-mapserver-workload-contract/v1":
        raise M26PopulationWorkloadError("unexpected workload contract schema")
    if contract.get("locked_before_workload_computation") is not True:
        raise M26PopulationWorkloadError("workload contract not locked")
    if contract.get("qualified_batch_size") != 64 or contract.get("diagnostic_headroom_batch_size") != 128:
        raise M26PopulationWorkloadError("workload batch sizes drifted")
    for key in (
        "stage1_population_aggregation_authorized",
        "numeric_source_value_extraction_authorized",
        "substantive_value_promotion_authorized",
        "cross_geography_numeric_source_extraction_authorized",
        "aggregation_semantics_changed",
        "source_family_changed",
        "minimum_valid_fraction_changed",
        "risk_synthesis_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise M26PopulationWorkloadError(f"invalid workload boundary: {key}")
    return contract


def inside_cell_count(projected_geometry: Any, bbox: tuple[float, float, float, float], width: int, height: int) -> int:
    left, _bottom, _right, top = bbox
    transform = from_origin(left, top, 100.0, 100.0)
    inside = geometry_mask(
        [mapping(projected_geometry)],
        out_shape=(height, width),
        transform=transform,
        invert=True,
        all_touched=False,
    )
    return int(np.count_nonzero(inside))


def build() -> dict[str, Any]:
    contract = load_contract()
    scale = json.loads(SCALE.read_text(encoding="utf-8"))
    if scale.get("production_batch_transport_qualified") is not True or scale.get("qualified_production_batch_size") != 64:
        raise M26PopulationWorkloadError("batch-64 transport is not qualified")

    stage0 = stage1.load_stage0()
    stage1.verify_stage0_snapshot_hashes(stage0)
    meta = stage1.source_metadata("inarisk_population_2020")
    features, big_probe = stage1.load_qualified_big_features()
    if len(features) != 19 or len({row["geography_id"] for row in features}) != 19:
        raise M26PopulationWorkloadError("BIG frame is not exact 19 geographies")

    transformer = Transformer.from_crs(4326, 3395, always_xy=True)
    rows: list[dict[str, Any]] = []
    for feature in sorted(features, key=lambda row: row["geography_id"]):
        geom = shape(feature["geometry"])
        if geom.is_empty:
            raise M26PopulationWorkloadError(f"empty geometry: {feature['geography_id']}")
        projected = shapely_transform(transformer.transform, geom)
        bbox, width, height = stage1.aligned_window(projected.bounds, meta)
        inside = inside_cell_count(projected, bbox, width, height)
        if inside <= 0:
            raise M26PopulationWorkloadError(f"no native centers inside {feature['geography_id']}")
        rows.append({
            "geography_id": feature["geography_id"],
            "geography_name": feature["geography_name"],
            "source_permendagri_code": feature["source_permendagri_code"],
            "aligned_window_width": width,
            "aligned_window_height": height,
            "aligned_window_pixel_count": width * height,
            "inside_boundary_native_cell_count": inside,
            "batch64_request_count_ceiling": math.ceil(inside / 64),
            "batch128_request_count_ceiling": math.ceil(inside / 128),
        })

    total_inside = sum(row["inside_boundary_native_cell_count"] for row in rows)
    total_64 = sum(row["batch64_request_count_ceiling"] for row in rows)
    total_128 = sum(row["batch128_request_count_ceiling"] for row in rows)
    padang_panjang = next(row for row in rows if row["geography_id"] == "idn.13.1374")

    manifest = {
        "schema": "ranah-observatory/milestone26-population-mapserver-workload/v1",
        "milestone": 26,
        "stage": "stage1_transport_qualification",
        "contract": {"path": CONTRACT.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest()},
        "scale_evidence": {"path": SCALE.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(SCALE.read_bytes()).hexdigest()},
        "big_expected_edition": big_probe.get("expected_edition"),
        "geography_count": len(rows),
        "batch64_qualified": True,
        "headroom128_observed_pass": bool(scale.get("headroom_128_observed_pass")),
        "geographies": rows,
        "padang_panjang_pilot_workload": padang_panjang,
        "totals": {
            "inside_boundary_native_cell_count": total_inside,
            "batch64_request_count_ceiling": total_64,
            "batch128_request_count_ceiling": total_128,
        },
        "source_values_accessed": False,
        "numeric_source_value_extraction_performed": False,
        "stage1_population_aggregation_authorized": False,
        "substantive_value_promotion_performed": False,
        "aggregation_semantics_changed": False,
        "source_family_changed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT.write_bytes(canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    try:
        manifest = build()
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "geography_count": manifest["geography_count"],
        "padang_panjang": manifest["padang_panjang_pilot_workload"],
        "totals": manifest["totals"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
