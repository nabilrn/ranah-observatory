from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce BIG boundary probe conclusions")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("geojson", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    conclusions = payload["conclusions"]
    geojson = payload["sumatera_barat_geojson"]
    errors: list[str] = []

    for key in (
        "official_big_polygon_lane_qualified",
        "current_sumbar_19_geographies_exactly_covered",
        "geometry_suitable_for_current_zonal_aggregation_candidate",
        "permendagri_kdpkab_crosswalk_required",
    ):
        if not conclusions.get(key):
            errors.append(f"expected {key}=true")

    for key in (
        "bps_fields_usable_as_live_join_key",
        "historical_boundary_continuity_established",
        "safe_to_project_current_boundaries_backward_without_harmonization",
    ):
        if conclusions.get(key):
            errors.append(f"expected {key}=false")

    if geojson.get("selected_kabkota_count") != 19:
        errors.append(
            f"expected selected_kabkota_count=19, got {geojson.get('selected_kabkota_count')!r}"
        )
    if geojson.get("source_kdbbps_nonblank_count") != 0:
        errors.append("expected live BIG KDBBPS values to remain blank for selected source response")
    if geojson.get("source_kdpbps_nonblank_count") != 0:
        errors.append("expected live BIG KDPBPS values to remain blank for selected source response")
    if geojson.get("missing_source_codes") or geojson.get("unexpected_source_codes"):
        errors.append("BIG Permendagri source-code footprint does not match crosswalk")
    if geojson.get("missing_canonical_geography_ids") or geojson.get(
        "unexpected_canonical_geography_ids"
    ):
        errors.append("BIG crosswalk does not resolve exactly to the canonical 19 geographies")
    if geojson.get("name_mismatches"):
        errors.append("BIG source names do not match the edition-specific crosswalk")

    if not args.geojson.exists() or args.geojson.stat().st_size <= 0:
        errors.append("raw BIG GeoJSON snapshot is missing or empty")

    if errors:
        print("BIG boundary probe gate FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "BIG boundary probe gate passed: 19 June 2026 Sumatera Barat polygons mapped "
        "through Permendagri KDPKAB; blank BPS fields not used."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
