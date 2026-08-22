#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts import materialize_milestone26_stage1_components as base
from scripts import materialize_milestone26_stage1_components_v3 as chunked

ROOT = Path(__file__).resolve().parents[1]
CHUNK_AMENDMENT_V2 = ROOT / "data/manifests/milestone26_stage1_chunk_transport_amendment_v2.json"


class M26ChunkV2Error(RuntimeError):
    pass


def load_chunk_amendment_v2() -> dict[str, Any]:
    payload = json.loads(CHUNK_AMENDMENT_V2.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/milestone26-stage1-chunk-transport-amendment/v2":
        raise M26ChunkV2Error("unexpected M26 chunk transport v2 schema")
    if payload.get("affected_source_ids") != list(base.SOURCE_IDS):
        raise M26ChunkV2Error("chunk transport v2 source set drift")
    if int(payload.get("maximum_tile_width_pixels", 0)) != 500 or int(payload.get("maximum_tile_height_pixels", 0)) != 500:
        raise M26ChunkV2Error("chunk transport v2 tile limit drift")
    if int(payload.get("tile_overlap_pixels", -1)) != 0 or int(payload.get("tile_gap_pixels", -1)) != 0:
        raise M26ChunkV2Error("chunk transport v2 overlap/gap contract drift")
    if int(payload.get("per_tile_crs_epsg", 0)) != 3395 or int(payload.get("per_tile_pixel_size_m", 0)) != 100:
        raise M26ChunkV2Error("chunk transport v2 source-grid contract drift")
    if payload.get("per_tile_resampling") != "nearest_neighbor":
        raise M26ChunkV2Error("chunk transport v2 resampling contract drift")
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
            raise M26ChunkV2Error(f"invalid chunk transport v2 boundary: {key}")
    if float(payload.get("minimum_valid_fraction_inside_polygon_unchanged", -1)) != 0.99:
        raise M26ChunkV2Error("chunk transport v2 changed the locked valid-coverage gate")
    chunked.nodata.load_nodata_amendment()
    return payload


def install_transport_v2() -> None:
    # Reuse the already tested v3 tiling/aggregation implementation while
    # substituting only the immutable transport amendment path and validator.
    chunked.CHUNK_AMENDMENT = CHUNK_AMENDMENT_V2
    chunked.load_chunk_amendment = load_chunk_amendment_v2


def build(fetch_live: bool) -> dict[str, Any]:
    install_transport_v2()
    return chunked.build(fetch_live=fetch_live)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    try:
        manifest = build(fetch_live=args.fetch)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        base.M26Stage1Error,
        chunked.M26ChunkError,
        M26ChunkV2Error,
    ) as exc:
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
