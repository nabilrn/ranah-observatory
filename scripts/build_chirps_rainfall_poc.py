from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import rasterio
from pyproj import Geod
from rasterio.windows import Window, from_bounds
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry

ROOT = Path(__file__).resolve().parents[1]
BIG_CROSSWALK = ROOT / "data" / "registries" / "big_geography_map.csv"
BIG_LAYER_URL = "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_KABKOTA_AR/MapServer/0"
CHIRPS_COG_TEMPLATE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/chirps-v3.0.{year:04d}.{month:02d}.cog"
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
EXPECTED_BIG_EDITION = "Juni 2026"
POC_YEAR = 1981
POC_GEOGRAPHY_IDS = (
    "idn.13.1371",  # Padang: city
    "idn.13.1307",  # Agam: mainland regency
    "idn.13.1301",  # Kepulauan Mentawai: island regency
)
GEOD = Geod(ellps="WGS84")


def normalize_code(value: Any) -> str:
    return "".join(character for character in str(value or "") if character.isdigit())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def poc_crosswalk(path: Path = BIG_CROSSWALK) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    selected = {
        row["canonical_geography_id"]: row
        for row in rows
        if row["canonical_geography_id"] in POC_GEOGRAPHY_IDS
        and row["source_edition"] == EXPECTED_BIG_EDITION
        and row["mapping_status"] == "qualified_current_crosswalk"
    }
    if set(selected) != set(POC_GEOGRAPHY_IDS):
        missing = sorted(set(POC_GEOGRAPHY_IDS) - set(selected))
        raise RuntimeError(f"PoC BIG crosswalk incomplete; missing={missing}")
    return selected


def build_big_query_url() -> str:
    params = {
        "where": "WADMPR='Sumatera Barat'",
        "outFields": "OBJECTID,KDPKAB,WADMKK,WADMPR,METADATA",
        "returnGeometry": "true",
        "returnZ": "false",
        "returnM": "false",
        "outSR": "4326",
        "orderByFields": "OBJECTID ASC",
        "f": "geojson",
    }
    return f"{BIG_LAYER_URL}/query?{urllib.parse.urlencode(params)}"


def fetch_bytes(url: str, *, range_header: str | None = None, timeout: float = 60.0) -> tuple[bytes, Mapping[str, str], int]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,application/geo+json,application/octet-stream,*/*"}
    if range_header:
        headers["Range"] = range_header
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        response_headers = {key.lower(): value for key, value in response.headers.items()}
        return body, response_headers, int(getattr(response, "status", 200))


def fetch_big_geometries(crosswalk: Mapping[str, Mapping[str, str]]) -> tuple[dict[str, BaseGeometry], dict[str, Any]]:
    url = build_big_query_url()
    body, headers, status = fetch_bytes(url)
    if status != 200:
        raise RuntimeError(f"BIG query failed with HTTP {status}")
    payload = json.loads(body.decode("utf-8-sig"))
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise RuntimeError("BIG response is not a GeoJSON FeatureCollection")

    source_to_canonical = {
        row["source_code_normalized"]: canonical_id
        for canonical_id, row in crosswalk.items()
    }
    selected: dict[str, BaseGeometry] = {}
    source_names: dict[str, str] = {}
    for feature in payload["features"]:
        properties = feature.get("properties") or {}
        source_code = normalize_code(properties.get("KDPKAB"))
        canonical_id = source_to_canonical.get(source_code)
        if not canonical_id:
            continue
        if str(properties.get("WADMPR") or "").strip().casefold() != "sumatera barat":
            raise RuntimeError(f"Unexpected province for {canonical_id}")
        expected_name = str(crosswalk[canonical_id]["source_name_expected"]).strip()
        actual_name = str(properties.get("WADMKK") or "").strip()
        if actual_name.casefold() != expected_name.casefold():
            raise RuntimeError(f"BIG name mismatch for {canonical_id}: {actual_name!r} != {expected_name!r}")
        geometry = shape(feature.get("geometry"))
        if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError(f"Invalid polygonal geometry for {canonical_id}")
        if not geometry.is_valid:
            raise RuntimeError(f"BIG geometry is topologically invalid for {canonical_id}")
        if canonical_id in selected:
            raise RuntimeError(f"Duplicate BIG feature for {canonical_id}")
        selected[canonical_id] = geometry
        source_names[canonical_id] = actual_name

    if set(selected) != set(crosswalk):
        missing = sorted(set(crosswalk) - set(selected))
        raise RuntimeError(f"BIG PoC geometry selection incomplete; missing={missing}")

    provenance = {
        "url": url,
        "http_status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "etag": headers.get("etag", ""),
        "last_modified": headers.get("last-modified", ""),
        "source_edition": EXPECTED_BIG_EDITION,
        "canonical_ids": sorted(selected),
        "source_names": source_names,
    }
    return selected, provenance


def cog_identity(url: str) -> dict[str, Any]:
    body, headers, status = fetch_bytes(url, range_header="bytes=0-16383")
    return {
        "url": url,
        "http_status": status,
        "bytes_read": len(body),
        "content_range": headers.get("content-range", ""),
        "content_length": headers.get("content-length", ""),
        "etag": headers.get("etag", ""),
        "last_modified": headers.get("last-modified", ""),
        "prefix_sha256": hashlib.sha256(body).hexdigest(),
        "is_tiff": body.startswith(b"II*\x00") or body.startswith(b"MM\x00*"),
    }


def clamp_window(bounds: tuple[float, float, float, float], dataset: rasterio.io.DatasetReader) -> Window:
    raw = from_bounds(*bounds, transform=dataset.transform)
    col0 = max(0, math.floor(raw.col_off))
    row0 = max(0, math.floor(raw.row_off))
    col1 = min(dataset.width, math.ceil(raw.col_off + raw.width))
    row1 = min(dataset.height, math.ceil(raw.row_off + raw.height))
    if col1 <= col0 or row1 <= row0:
        raise RuntimeError("Requested geometry does not overlap CHIRPS raster")
    return Window(col0, row0, col1 - col0, row1 - row0)


def geodesic_area(geometry: BaseGeometry) -> float:
    if geometry.is_empty:
        return 0.0
    area, _ = GEOD.geometry_area_perimeter(geometry)
    return abs(float(area))


def build_area_weights(
    geometry: BaseGeometry,
    transform: rasterio.Affine,
    height: int,
    width: int,
) -> list[tuple[int, int, float]]:
    weights: list[tuple[int, int, float]] = []
    for row in range(height):
        for col in range(width):
            x0, y0 = transform * (col, row)
            x1, y1 = transform * (col + 1, row + 1)
            cell = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            if not geometry.intersects(cell):
                continue
            intersection = geometry.intersection(cell)
            area = geodesic_area(intersection)
            if area > 0:
                weights.append((row, col, area))
    if not weights:
        raise RuntimeError("Polygon has no positive-area overlap with raster window")
    return weights


def weighted_mean_with_coverage(
    values: np.ndarray,
    weights: Iterable[tuple[int, int, float]],
    nodata: float | None,
) -> tuple[float, float, int]:
    numerator = 0.0
    valid_area = 0.0
    total_area = 0.0
    valid_cells = 0
    for row, col, area in weights:
        total_area += area
        value = float(values[row, col])
        valid = math.isfinite(value) and (nodata is None or not math.isclose(value, float(nodata), rel_tol=0.0, abs_tol=1e-8))
        if not valid:
            continue
        if value < 0:
            raise RuntimeError(f"Negative CHIRPS rainfall value encountered: {value}")
        numerator += value * area
        valid_area += area
        valid_cells += 1
    if valid_area <= 0:
        raise RuntimeError("No valid CHIRPS land pixels overlap polygon")
    return numerator / valid_area, valid_area / total_area, valid_cells


def annualize_monthly(monthly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in monthly_rows:
        grouped[str(row["geography_id"])].append(row)
    annual_rows: list[dict[str, Any]] = []
    for geography_id, rows in sorted(grouped.items()):
        months = sorted(int(row["month"]) for row in rows)
        if months != list(range(1, 13)):
            raise RuntimeError(f"Annualization requires exactly months 1..12 for {geography_id}; got {months}")
        years = {int(row["year"]) for row in rows}
        if years != {POC_YEAR}:
            raise RuntimeError(f"Unexpected PoC year for {geography_id}: {sorted(years)}")
        annual_rows.append(
            {
                "geography_id": geography_id,
                "geography_name": rows[0]["geography_name"],
                "year": POC_YEAR,
                "annual_rainfall_mm": round(sum(float(row["monthly_rainfall_mm"]) for row in rows), 6),
                "months_complete": 12,
                "min_valid_area_fraction": round(min(float(row["valid_area_fraction"]) for row in rows), 8),
                "claim_type": "model_estimate",
                "spatial_frame": "fixed_current_boundary_june_2026",
                "source_product": "CHIRPS v3 Final monthly",
                "geometry_source": "BIG BATAS_KABKOTA_AR",
                "geometry_source_edition": EXPECTED_BIG_EDITION,
            }
        )
    return annual_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"Refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_poc(output_dir: Path) -> dict[str, Any]:
    crosswalk = poc_crosswalk()
    geometries, big_provenance = fetch_big_geometries(crosswalk)
    combined_bounds = (
        min(geometry.bounds[0] for geometry in geometries.values()),
        min(geometry.bounds[1] for geometry in geometries.values()),
        max(geometry.bounds[2] for geometry in geometries.values()),
        max(geometry.bounds[3] for geometry in geometries.values()),
    )

    monthly_rows: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    area_weights: dict[str, list[tuple[int, int, float]]] | None = None
    reference_grid: dict[str, Any] | None = None

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".cog",
        GDAL_HTTP_USERAGENT=USER_AGENT,
    ):
        for month in range(1, 13):
            url = CHIRPS_COG_TEMPLATE.format(year=POC_YEAR, month=month)
            identity = cog_identity(url)
            if identity["http_status"] not in {200, 206} or not identity["is_tiff"]:
                raise RuntimeError(f"CHIRPS COG identity probe failed: {identity}")
            source_files.append(identity)

            with rasterio.open(url) as dataset:
                if dataset.count != 1:
                    raise RuntimeError(f"Expected single-band CHIRPS raster, got {dataset.count}")
                if dataset.crs is None or dataset.crs.to_epsg() != 4326:
                    raise RuntimeError(f"Expected CHIRPS EPSG:4326, got {dataset.crs}")
                if not (math.isclose(abs(dataset.transform.a), 0.05, abs_tol=1e-7) and math.isclose(abs(dataset.transform.e), 0.05, abs_tol=1e-7)):
                    raise RuntimeError(f"Unexpected CHIRPS grid resolution: {dataset.transform}")
                window = clamp_window(combined_bounds, dataset)
                window_transform = dataset.window_transform(window)
                values = dataset.read(1, window=window)
                grid_contract = {
                    "crs": dataset.crs.to_string(),
                    "pixel_width_degrees": abs(float(dataset.transform.a)),
                    "pixel_height_degrees": abs(float(dataset.transform.e)),
                    "dtype": str(dataset.dtypes[0]),
                    "nodata": dataset.nodata,
                    "window": {
                        "col_off": int(window.col_off),
                        "row_off": int(window.row_off),
                        "width": int(window.width),
                        "height": int(window.height),
                    },
                }
                if reference_grid is None:
                    reference_grid = grid_contract
                    area_weights = {
                        geography_id: build_area_weights(geometry, window_transform, values.shape[0], values.shape[1])
                        for geography_id, geometry in geometries.items()
                    }
                else:
                    comparable = {key: grid_contract[key] for key in ("crs", "pixel_width_degrees", "pixel_height_degrees", "window")}
                    reference_comparable = {key: reference_grid[key] for key in comparable}
                    if comparable != reference_comparable:
                        raise RuntimeError(f"CHIRPS monthly grid drift detected in {POC_YEAR}-{month:02d}")
                assert area_weights is not None
                for geography_id in POC_GEOGRAPHY_IDS:
                    rainfall, coverage, valid_cells = weighted_mean_with_coverage(values, area_weights[geography_id], dataset.nodata)
                    monthly_rows.append(
                        {
                            "geography_id": geography_id,
                            "geography_name": crosswalk[geography_id]["canonical_name"],
                            "year": POC_YEAR,
                            "month": month,
                            "monthly_rainfall_mm": round(rainfall, 6),
                            "valid_area_fraction": round(coverage, 8),
                            "valid_intersecting_cells": valid_cells,
                            "claim_type": "model_estimate",
                            "spatial_frame": "fixed_current_boundary_june_2026",
                            "source_product": "CHIRPS v3 Final monthly",
                        }
                    )

    annual_rows = annualize_monthly(monthly_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly_path = output_dir / "chirps_rainfall_poc_monthly.csv"
    annual_path = output_dir / "chirps_rainfall_poc_annual.csv"
    manifest_path = output_dir / "chirps_rainfall_poc_manifest.json"
    write_csv(monthly_path, monthly_rows)
    write_csv(annual_path, annual_rows)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "poc_version": 1,
        "scope": {
            "year": POC_YEAR,
            "geography_ids": list(POC_GEOGRAPHY_IDS),
            "geography_count": len(POC_GEOGRAPHY_IDS),
            "monthly_row_count": len(monthly_rows),
            "annual_row_count": len(annual_rows),
            "not_canonical_materialization": True,
        },
        "method": {
            "monthly_statistic": "geodesic area-weighted mean of CHIRPS-valid intersecting grid-cell portions",
            "annual_statistic": "sum of 12 monthly polygon mean precipitation totals",
            "nodata_rule": "exclude nodata/non-finite cells from numerator and valid-area denominator; never treat nodata as zero",
            "coastline_rule": "report valid_area_fraction; CHIRPS-valid land overlap defines each monthly mean",
            "claim_type": "model_estimate",
            "spatial_frame": "fixed current BIG June 2026 boundaries backcast onto 1981 climate raster",
            "historical_boundary_continuity_claimed": False,
        },
        "big_geometry": big_provenance,
        "chirps_grid": reference_grid,
        "chirps_source_files": source_files,
        "outputs": {
            "monthly_csv": str(monthly_path),
            "annual_csv": str(annual_path),
        },
        "gates": {
            "exactly_3_geographies": len(annual_rows) == 3,
            "exactly_36_monthly_rows": len(monthly_rows) == 36,
            "all_annual_rows_complete": all(row["months_complete"] == 12 for row in annual_rows),
            "all_claims_model_estimate": all(row["claim_type"] == "model_estimate" for row in monthly_rows + annual_rows),
            "no_historical_boundary_claim": True,
            "all_annual_rainfall_positive": all(float(row["annual_rainfall_mm"]) > 0 for row in annual_rows),
            "all_monthly_coverage_positive": all(float(row["valid_area_fraction"]) > 0 for row in monthly_rows),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a bounded CHIRPS/BIG rainfall zonal-aggregation proof of concept")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/chirps-rainfall-poc"))
    args = parser.parse_args()
    manifest = run_poc(args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
