from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
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
EXPECTED_BIG_EDITION = "Juni 2026"
CHIRPS_MISSING_SENTINEL = -9999.0
SAMPLE_YEARS = (1981, 2000, 2025)
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"
GEOD = Geod(ellps="WGS84")


def normalize_code(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def sample_crosswalk(path: Path = BIG_CROSSWALK) -> dict[str, dict[str, str]]:
    selected = {
        row["canonical_geography_id"]: row
        for row in read_csv(path)
        if row["source_edition"] == EXPECTED_BIG_EDITION
        and row["mapping_status"] == "qualified_current_crosswalk"
        and row["source_system"] == "Permendagri"
    }
    if len(selected) != 19:
        raise RuntimeError(f"Expected exactly 19 qualified current BIG mappings; got {len(selected)}")
    if len({row["source_code_normalized"] for row in selected.values()}) != 19:
        raise RuntimeError("BIG sample crosswalk source codes are not unique")
    return selected


def fetch_bytes(url: str, range_header: str | None = None, timeout: float = 60.0) -> tuple[bytes, dict[str, str], int]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,application/geo+json,application/octet-stream,*/*",
    }
    if range_header:
        headers["Range"] = range_header
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return (
            response.read(),
            {k.lower(): v for k, v in response.headers.items()},
            int(getattr(response, "status", 200)),
        )


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


def fetch_big_geometries(crosswalk: Mapping[str, Mapping[str, str]]) -> tuple[dict[str, BaseGeometry], dict[str, Any]]:
    url = build_big_query_url()
    body, headers, status = fetch_bytes(url)
    if status != 200:
        raise RuntimeError(f"BIG query failed with HTTP {status}")
    payload = json.loads(body.decode("utf-8-sig"))
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise RuntimeError("BIG response is not a GeoJSON FeatureCollection")

    source_to_canonical = {row["source_code_normalized"]: gid for gid, row in crosswalk.items()}
    selected: dict[str, BaseGeometry] = {}
    source_names: dict[str, str] = {}
    for feature in payload["features"]:
        props = feature.get("properties") or {}
        gid = source_to_canonical.get(normalize_code(props.get("KDPKAB")))
        if not gid:
            continue
        if str(props.get("WADMPR") or "").strip().casefold() != "sumatera barat":
            raise RuntimeError(f"Unexpected BIG province for {gid}")
        actual_name = str(props.get("WADMKK") or "").strip()
        expected_name = str(crosswalk[gid]["source_name_expected"])
        if actual_name.casefold() != expected_name.casefold():
            raise RuntimeError(f"BIG name mismatch for {gid}: {actual_name!r} != {expected_name!r}")
        geometry = shape(feature.get("geometry"))
        if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"} or not geometry.is_valid:
            raise RuntimeError(f"Invalid BIG geometry for {gid}")
        if gid in selected:
            raise RuntimeError(f"Duplicate BIG geometry for {gid}")
        selected[gid] = geometry
        source_names[gid] = actual_name

    if set(selected) != set(crosswalk):
        missing = sorted(set(crosswalk) - set(selected))
        unexpected = sorted(set(selected) - set(crosswalk))
        raise RuntimeError(f"BIG geometry selection mismatch; missing={missing}; unexpected={unexpected}")

    return selected, {
        "url": url,
        "http_status": status,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "etag": headers.get("etag", ""),
        "last_modified": headers.get("last-modified", ""),
        "source_edition": EXPECTED_BIG_EDITION,
        "canonical_ids": sorted(selected),
        "source_names": dict(sorted(source_names.items())),
    }


def cog_identity(url: str) -> dict[str, Any]:
    body, headers, status = fetch_bytes(url, "bytes=0-16383")
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
        raise RuntimeError("BIG geometry does not overlap CHIRPS raster")
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
            area = geodesic_area(geometry.intersection(cell))
            if area > 0:
                weights.append((row, col, area))
    if not weights:
        raise RuntimeError("Polygon has no positive-area raster overlap")
    return weights


def weighted_mean_with_coverage(
    values: np.ndarray,
    weights: Iterable[tuple[int, int, float]],
    nodata: float | None,
) -> tuple[float, float, int]:
    numerator = valid_area = total_area = 0.0
    valid_cells = 0
    for row, col, area in weights:
        total_area += area
        value = float(values[row, col])
        declared_nodata = nodata is not None and math.isclose(value, float(nodata), rel_tol=0.0, abs_tol=1e-8)
        chirps_missing = math.isclose(value, CHIRPS_MISSING_SENTINEL, rel_tol=0.0, abs_tol=1e-8)
        if not math.isfinite(value) or declared_nodata or chirps_missing:
            continue
        if value < 0:
            raise RuntimeError(f"Unexpected negative CHIRPS rainfall value: {value}")
        numerator += value * area
        valid_area += area
        valid_cells += 1
    if valid_area <= 0:
        raise RuntimeError("No valid CHIRPS land pixels overlap polygon")
    return numerator / valid_area, valid_area / total_area, valid_cells


def annualize_monthly(
    monthly_rows: list[dict[str, Any]],
    years: Iterable[int] = SAMPLE_YEARS,
) -> list[dict[str, Any]]:
    expected_years = set(int(year) for year in years)
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in monthly_rows:
        grouped[(str(row["geography_id"]), int(row["year"]))].append(row)

    annual_rows: list[dict[str, Any]] = []
    for (gid, year), rows in sorted(grouped.items()):
        if year not in expected_years:
            raise RuntimeError(f"Unexpected sample year: {year}")
        months = sorted(int(row["month"]) for row in rows)
        if months != list(range(1, 13)):
            raise RuntimeError(f"Annualization requires months 1..12 exactly once for {gid}/{year}; got {months}")
        annual_rows.append({
            "geography_id": gid,
            "geography_name": rows[0]["geography_name"],
            "year": year,
            "annual_rainfall_mm": round(sum(float(row["monthly_rainfall_mm"]) for row in rows), 6),
            "months_complete": 12,
            "min_valid_area_fraction": round(min(float(row["valid_area_fraction"]) for row in rows), 8),
            "mean_valid_area_fraction": round(float(np.mean([float(row["valid_area_fraction"]) for row in rows])), 8),
            "claim_type": "model_estimate",
            "spatial_frame": "fixed_current_boundary_june_2026",
            "source_product": "CHIRPS v3 Final monthly",
            "geometry_source": "BIG BATAS_KABKOTA_AR",
            "geometry_source_edition": EXPECTED_BIG_EDITION,
        })
    return annual_rows


def build_diagnostics(monthly_rows: list[dict[str, Any]], annual_rows: list[dict[str, Any]]) -> dict[str, Any]:
    coverage = np.array([float(row["valid_area_fraction"]) for row in monthly_rows], dtype=float)
    rainfall = np.array([float(row["annual_rainfall_mm"]) for row in annual_rows], dtype=float)

    by_year: dict[str, Any] = {}
    for year in SAMPLE_YEARS:
        rows = [row for row in annual_rows if int(row["year"]) == year]
        values = np.array([float(row["annual_rainfall_mm"]) for row in rows], dtype=float)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = float(q3 - q1)
        lower = float(q1 - 1.5 * iqr)
        upper = float(q3 + 1.5 * iqr)
        flags = [
            {
                "geography_id": row["geography_id"],
                "geography_name": row["geography_name"],
                "annual_rainfall_mm": row["annual_rainfall_mm"],
            }
            for row in rows
            if float(row["annual_rainfall_mm"]) < lower or float(row["annual_rainfall_mm"]) > upper
        ]
        by_year[str(year)] = {
            "min_mm": round(float(values.min()), 6),
            "median_mm": round(float(np.median(values)), 6),
            "max_mm": round(float(values.max()), 6),
            "iqr_lower_fence_mm": round(lower, 6),
            "iqr_upper_fence_mm": round(upper, 6),
            "iqr_flags": flags,
        }

    min_row = min(monthly_rows, key=lambda row: float(row["valid_area_fraction"]))
    return {
        "coverage": {
            "minimum_valid_area_fraction": round(float(coverage.min()), 8),
            "p05_valid_area_fraction": round(float(np.percentile(coverage, 5)), 8),
            "median_valid_area_fraction": round(float(np.median(coverage)), 8),
            "minimum_row": {
                "geography_id": min_row["geography_id"],
                "geography_name": min_row["geography_name"],
                "year": int(min_row["year"]),
                "month": int(min_row["month"]),
                "valid_area_fraction": float(min_row["valid_area_fraction"]),
            },
        },
        "annual_rainfall": {
            "minimum_mm": round(float(rainfall.min()), 6),
            "median_mm": round(float(np.median(rainfall)), 6),
            "maximum_mm": round(float(rainfall.max()), 6),
            "by_year": by_year,
            "iqr_flags_are_diagnostic_not_rejections": True,
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"Refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_sample(output_dir: Path) -> dict[str, Any]:
    started = time.monotonic()
    crosswalk = sample_crosswalk()
    geometries, big_provenance = fetch_big_geometries(crosswalk)
    geography_ids = tuple(sorted(geometries))
    bounds = (
        min(g.bounds[0] for g in geometries.values()),
        min(g.bounds[1] for g in geometries.values()),
        max(g.bounds[2] for g in geometries.values()),
        max(g.bounds[3] for g in geometries.values()),
    )

    monthly_rows: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    weights: dict[str, list[tuple[int, int, float]]] | None = None
    reference_grid: dict[str, Any] | None = None

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".cog",
        GDAL_HTTP_USERAGENT=USER_AGENT,
    ):
        for year in SAMPLE_YEARS:
            for month in range(1, 13):
                url = CHIRPS_COG_TEMPLATE.format(year=year, month=month)
                identity = cog_identity(url)
                if identity["http_status"] not in {200, 206} or not identity["is_tiff"]:
                    raise RuntimeError(f"CHIRPS transport probe failed for {year}-{month:02d}: {identity}")
                source_files.append(identity)

                with rasterio.open(url) as dataset:
                    if dataset.count != 1 or dataset.crs is None or dataset.crs.to_epsg() != 4326:
                        raise RuntimeError(f"Unexpected CHIRPS band/CRS contract for {year}-{month:02d}")
                    if not (
                        math.isclose(abs(dataset.transform.a), 0.05, abs_tol=1e-7)
                        and math.isclose(abs(dataset.transform.e), 0.05, abs_tol=1e-7)
                    ):
                        raise RuntimeError(f"Unexpected CHIRPS grid resolution for {year}-{month:02d}")

                    window = clamp_window(bounds, dataset)
                    transform = dataset.window_transform(window)
                    values = dataset.read(1, window=window)
                    grid = {
                        "crs": dataset.crs.to_string(),
                        "pixel_width_degrees": abs(float(dataset.transform.a)),
                        "pixel_height_degrees": abs(float(dataset.transform.e)),
                        "dtype": str(dataset.dtypes[0]),
                        "nodata": dataset.nodata,
                        "explicit_missing_sentinel": CHIRPS_MISSING_SENTINEL,
                        "window": {
                            "col_off": int(window.col_off),
                            "row_off": int(window.row_off),
                            "width": int(window.width),
                            "height": int(window.height),
                        },
                    }
                    comparable = {k: grid[k] for k in ("crs", "pixel_width_degrees", "pixel_height_degrees", "window")}
                    if reference_grid is None:
                        reference_grid = grid
                        weights = {
                            gid: build_area_weights(geometry, transform, *values.shape)
                            for gid, geometry in geometries.items()
                        }
                    else:
                        reference_comparable = {k: reference_grid[k] for k in comparable}
                        if comparable != reference_comparable:
                            raise RuntimeError(f"CHIRPS grid drift detected in {year}-{month:02d}")

                    assert weights is not None
                    for gid in geography_ids:
                        rainfall, coverage, valid_cells = weighted_mean_with_coverage(values, weights[gid], dataset.nodata)
                        monthly_rows.append({
                            "geography_id": gid,
                            "geography_name": crosswalk[gid]["canonical_name"],
                            "year": year,
                            "month": month,
                            "monthly_rainfall_mm": round(rainfall, 6),
                            "valid_area_fraction": round(coverage, 8),
                            "valid_intersecting_cells": valid_cells,
                            "claim_type": "model_estimate",
                            "spatial_frame": "fixed_current_boundary_june_2026",
                            "source_product": "CHIRPS v3 Final monthly",
                        })

    annual_rows = annualize_monthly(monthly_rows)
    expected_monthly = len(SAMPLE_YEARS) * 12 * 19
    expected_annual = len(SAMPLE_YEARS) * 19
    if len(monthly_rows) != expected_monthly or len(annual_rows) != expected_annual:
        raise RuntimeError(
            f"Sample row-count contract failed: monthly={len(monthly_rows)}/{expected_monthly}; "
            f"annual={len(annual_rows)}/{expected_annual}"
        )

    diagnostics = build_diagnostics(monthly_rows, annual_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly_path = output_dir / "chirps_rainfall_sample_monthly.csv"
    annual_path = output_dir / "chirps_rainfall_sample_annual.csv"
    manifest_path = output_dir / "chirps_rainfall_sample_manifest.json"
    write_csv(monthly_path, monthly_rows)
    write_csv(annual_path, annual_rows)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_version": 1,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "scope": {
            "years": list(SAMPLE_YEARS),
            "geography_ids": list(geography_ids),
            "geography_count": len(geography_ids),
            "source_cog_count": len(source_files),
            "monthly_row_count": len(monthly_rows),
            "annual_row_count": len(annual_rows),
            "not_canonical_materialization": True,
        },
        "method": {
            "monthly_statistic": "geodesic area-weighted mean of CHIRPS-valid intersecting grid-cell portions",
            "annual_statistic": "sum of 12 monthly polygon mean precipitation totals",
            "nodata_rule": "exclude GDAL nodata, explicit CHIRPS -9999 missing sentinel, and non-finite cells; never treat missing as zero",
            "coastline_rule": "report valid_area_fraction for every geography-month",
            "claim_type": "model_estimate",
            "spatial_frame": "fixed_current_boundary_june_2026",
            "historical_boundary_continuity_claimed": False,
            "outlier_rule": "IQR flags are descriptive diagnostics only and never auto-reject valid source values",
        },
        "big_geometry": big_provenance,
        "chirps_grid": reference_grid,
        "chirps_source_files": source_files,
        "diagnostics": diagnostics,
        "gates": {
            "all_19_current_geographies_present": len(geography_ids) == 19,
            "all_36_sample_cogs_read": len(source_files) == 36,
            "all_684_monthly_rows_present": len(monthly_rows) == 684,
            "all_57_annual_rows_present": len(annual_rows) == 57,
            "all_monthly_values_nonnegative": all(float(row["monthly_rainfall_mm"]) >= 0 for row in monthly_rows),
            "all_annual_values_positive": all(float(row["annual_rainfall_mm"]) > 0 for row in annual_rows),
            "all_monthly_rows_model_estimate": all(row["claim_type"] == "model_estimate" for row in monthly_rows),
            "all_annual_rows_model_estimate": all(row["claim_type"] == "model_estimate" for row in annual_rows),
            "all_rows_fixed_current_boundary": all(row["spatial_frame"] == "fixed_current_boundary_june_2026" for row in monthly_rows + annual_rows),
            "all_monthly_rows_have_valid_overlap": all(float(row["valid_area_fraction"]) > 0 for row in monthly_rows),
            "grid_contract_stable_across_sample": True,
            "historical_boundary_continuity_not_claimed": True,
            "not_canonical_materialization": True,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded 19-geography x 3-year CHIRPS rainfall sample")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/chirps-rainfall-sample"))
    args = parser.parse_args()
    print(json.dumps(run_sample(args.output_dir), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
