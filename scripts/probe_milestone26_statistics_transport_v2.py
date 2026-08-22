#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Any

from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

from scripts import probe_milestone26_statistics_transport as base


class M26StatisticsTransportV2Error(RuntimeError):
    pass


def arcgis_polygon_xy(projected_geometry: Any) -> dict[str, Any]:
    """Serialize only planar XY coordinates for the ArcGIS polygon request.

    The qualified BIG boundary snapshot may carry a third coordinate ordinate.
    Stage 1 is explicitly planar EPSG:3395 analysis, so Z is not part of the
    spatial aggregation contract. Dropping only the third ordinate here keeps
    the same planar polygon while avoiding tuple-unpack failures.
    """
    polygons: list[Polygon]
    if isinstance(projected_geometry, Polygon):
        polygons = [projected_geometry]
    elif isinstance(projected_geometry, MultiPolygon):
        polygons = list(projected_geometry.geoms)
    else:
        raise M26StatisticsTransportV2Error(
            f"unsupported pilot geometry: {projected_geometry.geom_type}"
        )

    rings: list[list[list[float]]] = []
    for polygon in polygons:
        fixed = orient(polygon, sign=-1.0)
        rings.append([[float(coord[0]), float(coord[1])] for coord in fixed.exterior.coords])
        for interior in fixed.interiors:
            rings.append([[float(coord[0]), float(coord[1])] for coord in interior.coords])

    if not rings:
        raise M26StatisticsTransportV2Error("pilot polygon produced no ArcGIS rings")
    return {"rings": rings, "spatialReference": {"wkid": 3395}}


def run() -> dict[str, Any]:
    # Patch only the ArcGIS serialization adapter. All source qualification,
    # geometry-only pilot selection, native-grid TIFF reference statistics,
    # equivalence tolerances, and scientific claim boundaries remain exactly
    # those preregistered in the v1 probe.
    base.arcgis_polygon = arcgis_polygon_xy
    return base.run()


def main() -> int:
    try:
        payload = run()
    except Exception as exc:  # preserve fail-closed workflow behavior
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(
        {
            "pilot_geography_id": payload["pilot_geography_id"],
            "both_sources_equivalent": payload["both_sources_equivalent"],
            "statistics_transport_qualified_for_stage1": payload[
                "statistics_transport_qualified_for_stage1"
            ],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
