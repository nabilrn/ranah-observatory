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
    errors: list[str] = []

    for key in (
        "official_big_polygon_lane_qualified",
        "current_sumbar_19_geographies_exactly_covered",
        "geometry_suitable_for_current_zonal_aggregation_candidate",
    ):
        if not conclusions.get(key):
            errors.append(f"expected {key}=true")

    for key in (
        "historical_boundary_continuity_established",
        "safe_to_project_current_boundaries_backward_without_harmonization",
    ):
        if conclusions.get(key):
            errors.append(f"expected {key}=false")

    if not args.geojson.exists() or args.geojson.stat().st_size <= 0:
        errors.append("raw BIG GeoJSON snapshot is missing or empty")

    if errors:
        print("BIG boundary probe gate FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("BIG boundary probe gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
