#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
from shapely import contains_xy
from shapely.geometry import shape

from scripts.probe_big_sumbar_boundaries import big_crosswalk, normalize_code, run_probe

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / "data/snapshots/usgs/milestone8/padang-2009/shakemap-grid.xml"
USGS_MANIFEST = ROOT / "data/manifests/milestone8_usgs_shakemap_probe.json"
RAW_BIG = ROOT / "data/snapshots/big/milestone8/big-june-2026-sumbar.geojson"
OUTPUT = ROOT / "data/analysis/quasi_causal/m8-shakemap-exposure-candidate.csv"
MANIFEST = ROOT / "data/manifests/milestone8_shakemap_exposure_candidate.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_shakemap_grid(path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    root = ET.parse(path).getroot()
    field_rows: list[tuple[int, str, str]] = []
    grid_spec: dict[str, str] = {}
    grid_text = ""
    for element in root.iter():
        name = localname(element.tag)
        if name == "grid_field":
            field_rows.append(
                (
                    int(element.attrib["index"]),
                    str(element.attrib["name"]).upper(),
                    str(element.attrib.get("units", "")),
                )
            )
        elif name == "grid_specification":
            grid_spec = dict(element.attrib)
        elif name == "grid_data":
            grid_text = element.text or ""

    field_rows.sort()
    if not field_rows or not grid_text.strip() or not grid_spec:
        raise RuntimeError("ShakeMap grid is missing fields, grid specification, or grid data")
    field_names = [name for _index, name, _units in field_rows]
    required = {"LON", "LAT", "PGA", "MMI"}
    if not required.issubset(field_names):
        raise RuntimeError(f"ShakeMap grid missing required fields: {sorted(required - set(field_names))}")

    values = np.fromstring(grid_text, sep=" ", dtype=float)
    width = len(field_rows)
    if values.size % width:
        raise RuntimeError(f"ShakeMap grid token count {values.size} is not divisible by field count {width}")
    matrix = values.reshape((-1, width))
    nlon = int(grid_spec["nlon"])
    nlat = int(grid_spec["nlat"])
    if matrix.shape[0] != nlon * nlat:
        raise RuntimeError(f"ShakeMap grid row count mismatch rows={matrix.shape[0]} expected={nlon*nlat}")

    arrays = {name: matrix[:, position] for position, name in enumerate(field_names)}
    units = {name: units for _index, name, units in field_rows}
    if units.get("PGA", "").casefold() not in {"pctg", "%g"}:
        raise RuntimeError(f"Unexpected PGA unit: {units.get('PGA')!r}")

    metadata: dict[str, Any] = {
        "field_names": field_names,
        "field_units": units,
        "grid_specification": grid_spec,
        "grid_row_count": int(matrix.shape[0]),
    }
    return arrays, metadata


def load_qualified_big_features() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    probe = run_probe(RAW_BIG)
    conclusions = probe.get("conclusions", {})
    if conclusions.get("official_big_polygon_lane_qualified") is not True:
        raise RuntimeError("BIG June 2026 polygon lane failed qualification")
    payload = json.loads(RAW_BIG.read_text(encoding="utf-8"))
    features = payload.get("features")
    if not isinstance(features, list):
        raise RuntimeError("BIG raw snapshot is not a GeoJSON feature collection")

    crosswalk = big_crosswalk()
    selected: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
        source_code = normalize_code(props.get("KDPKAB"))
        source_name = str(props.get("WADMKK") or "").strip()
        if not source_code or not source_name:
            continue
        mapping = crosswalk.get(source_code)
        if mapping is None:
            raise RuntimeError(f"BIG selected feature lacks qualified crosswalk: {source_code} {source_name}")
        selected.append(
            {
                "geography_id": mapping["canonical_geography_id"],
                "geography_name": source_name,
                "source_permendagri_code": source_code,
                "geometry": feature.get("geometry"),
            }
        )
    if len(selected) != 19 or len({row["geography_id"] for row in selected}) != 19:
        raise RuntimeError(f"Expected exact 19 qualified BIG geometries, got {len(selected)}")
    return selected, probe


def quantile(values: np.ndarray, q: float) -> float:
    return float(np.quantile(values, q, method="linear"))


def aggregate_feature(row: dict[str, Any], arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    geom = shape(row["geometry"])
    if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise RuntimeError(f"Invalid polygon geometry for {row['geography_id']}")
    lon = arrays["LON"]
    lat = arrays["LAT"]
    pga = arrays["PGA"]
    mmi = arrays["MMI"]
    minx, miny, maxx, maxy = geom.bounds
    bbox = (lon >= minx) & (lon <= maxx) & (lat >= miny) & (lat <= maxy)
    candidate_indices = np.flatnonzero(bbox)
    if candidate_indices.size == 0:
        raise RuntimeError(f"No ShakeMap grid points inside bounding box for {row['geography_id']}")
    inside_local = contains_xy(geom, lon[candidate_indices], lat[candidate_indices])
    indices = candidate_indices[np.asarray(inside_local, dtype=bool)]
    if indices.size == 0:
        raise RuntimeError(f"No ShakeMap grid-cell centers inside geometry for {row['geography_id']}")
    pga_values = pga[indices]
    mmi_values = mmi[indices]
    if not np.isfinite(pga_values).all() or not np.isfinite(mmi_values).all():
        raise RuntimeError(f"Non-finite ShakeMap exposure values for {row['geography_id']}")
    return {
        "geography_id": row["geography_id"],
        "geography_name": row["geography_name"],
        "source_permendagri_code": row["source_permendagri_code"],
        "grid_point_count": int(indices.size),
        "area_mean_pga_pct_g": float(np.mean(pga_values)),
        "area_median_pga_pct_g": float(np.median(pga_values)),
        "area_p90_pga_pct_g": quantile(pga_values, 0.90),
        "area_max_pga_pct_g": float(np.max(pga_values)),
        "area_mean_mmi": float(np.mean(mmi_values)),
        "area_max_mmi": float(np.max(mmi_values)),
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "geography_id",
        "geography_name",
        "source_permendagri_code",
        "grid_point_count",
        "area_mean_pga_pct_g",
        "area_median_pga_pct_g",
        "area_p90_pga_pct_g",
        "area_max_pga_pct_g",
        "area_mean_mmi",
        "area_max_mmi",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    if not GRID.exists() or not USGS_MANIFEST.exists():
        raise RuntimeError("Frozen USGS ShakeMap evidence is missing")
    usgs_manifest = json.loads(USGS_MANIFEST.read_text(encoding="utf-8"))
    if usgs_manifest.get("physical_exposure_candidate_frozen") is not True:
        raise RuntimeError("USGS ShakeMap candidate is not frozen")
    if sha256(GRID) != usgs_manifest.get("grid_sha256"):
        raise RuntimeError("Frozen ShakeMap grid SHA-256 does not match probe manifest")

    arrays, grid_metadata = parse_shakemap_grid(GRID)
    features, big_probe = load_qualified_big_features()
    rows = [aggregate_feature(row, arrays) for row in features]
    rows.sort(key=lambda row: row["geography_id"])
    if len(rows) != 19 or any(int(row["grid_point_count"]) <= 0 for row in rows):
        raise RuntimeError("ShakeMap exposure candidate does not cover exactly 19 geographies")
    write_csv(rows)

    pga_values = [float(row["area_mean_pga_pct_g"]) for row in rows]
    manifest = {
        "schema": "ranah-observatory/milestone8-shakemap-exposure-candidate/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "event_id": usgs_manifest.get("event_id"),
        "event_date": "2009-09-30",
        "primary_candidate": "area_mean_pga_pct_g",
        "primary_candidate_unit": "percent_g",
        "primary_candidate_selected_before_outcome_model_fit": True,
        "robustness_candidates": ["area_median_pga_pct_g", "area_p90_pga_pct_g", "area_max_pga_pct_g", "area_mean_mmi"],
        "geography_count": len(rows),
        "all_19_geographies_have_grid_support": True,
        "min_grid_point_count": min(int(row["grid_point_count"]) for row in rows),
        "max_grid_point_count": max(int(row["grid_point_count"]) for row in rows),
        "area_mean_pga_min": min(pga_values),
        "area_mean_pga_max": max(pga_values),
        "spatial_frame": "BIG June 2026 fixed-current-boundary polygons",
        "historical_boundary_continuity_claimed": False,
        "interpretation": "physical shaking exposure summarized over a fixed current-boundary spatial frame; not observed housing damage and not a historical-boundary reconstruction",
        "shakemap_grid_sha256": sha256(GRID),
        "big_raw_geojson_path": str(RAW_BIG.relative_to(ROOT)),
        "big_raw_geojson_sha256": sha256(RAW_BIG),
        "big_expected_edition": big_probe.get("expected_edition"),
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "design_amended": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
