#!/usr/bin/env python3
"""Run DEMNAS topography materialization against the normalized BIG boundary.

The tracked boundary is intentionally normalized by
``acquire_sumbar_public_disaster_sources.py`` to the properties ``name``,
``province``, and ``kdpkab``.  The underlying DEMNAS materializer originally
expected the source-native ArcGIS field names.  This adapter makes that schema
boundary explicit while retaining the materializer's raster, validation, and
output contracts unchanged.
"""

from __future__ import annotations

import json
from typing import Any

import materialize_demnas_sumbar_topography as demnas


def load_normalized_boundaries(crosswalk: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    payload = json.loads(demnas.BOUNDARY_PATH.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise RuntimeError("BIG boundary is not a GeoJSON FeatureCollection")

    features = payload["features"]
    if len(features) != 19:
        raise RuntimeError(f"expected 19 BIG boundary features, got {len(features)}")

    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for feature in features:
        properties = feature.get("properties") or {}
        code = demnas.normalize_code(properties.get("kdpkab"))
        province = demnas.normalize_text(properties.get("province"))
        source_name = demnas.normalize_text(properties.get("name"))

        if province.casefold() != "sumatera barat":
            raise RuntimeError(f"unexpected BIG province for {code}: {province!r}")
        if code not in crosswalk:
            raise RuntimeError(f"boundary code missing from crosswalk: {code!r}")

        expected_name = demnas.normalize_text(crosswalk[code]["source_name_expected"])
        if source_name.casefold() != expected_name.casefold():
            raise RuntimeError(
                f"BIG boundary name mismatch for {code}: {source_name!r} != {expected_name!r}"
            )
        if code in seen:
            raise RuntimeError(f"duplicate BIG boundary code: {code}")

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError(
                f"unsupported BIG boundary geometry for {code}: {(geometry or {}).get('type')!r}"
            )

        seen.add(code)
        output.append(
            {
                "source_code": code,
                "source_name": source_name,
                "canonical_geography_id": crosswalk[code]["canonical_geography_id"],
                "canonical_name": crosswalk[code]["canonical_name"],
                "geometry": geometry,
            }
        )

    if seen != set(crosswalk):
        missing = sorted(set(crosswalk) - seen)
        extra = sorted(seen - set(crosswalk))
        raise RuntimeError(f"BIG boundary/crosswalk coverage mismatch: missing={missing} extra={extra}")
    return output


def main() -> None:
    demnas.load_boundaries = load_normalized_boundaries
    demnas.main()


if __name__ == "__main__":
    main()
