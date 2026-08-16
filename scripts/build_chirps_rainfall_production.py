from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from scripts.build_chirps_rainfall_sample import (
    CHIRPS_COG_TEMPLATE,
    EXPECTED_BIG_EDITION,
    USER_AGENT,
    build_area_weights,
    clamp_window,
    cog_identity,
    fetch_big_geometries,
    sample_crosswalk,
    weighted_mean_with_coverage,
)

PRODUCTION_YEARS = tuple(range(1981, 2026))
MIN_VALID_AREA_FRACTION = 0.995
EXPECTED_GEOGRAPHY_COUNT = 19
EXPECTED_COG_COUNT = len(PRODUCTION_YEARS) * 12
EXPECTED_MONTHLY_ROWS = EXPECTED_GEOGRAPHY_COUNT * EXPECTED_COG_COUNT
EXPECTED_ANNUAL_ROWS = EXPECTED_GEOGRAPHY_COUNT * len(PRODUCTION_YEARS)


def annualize_monthly(monthly_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in monthly_rows:
        grouped[(str(row["geography_id"]), int(row["year"]))].append(row)

    annual_rows: list[dict[str, Any]] = []
    for (gid, year), rows in sorted(grouped.items()):
        if year not in PRODUCTION_YEARS:
            raise RuntimeError(f"Unexpected production year: {year}")
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
    coverage_values = np.array([float(row["valid_area_fraction"]) for row in monthly_rows], dtype=float)
    annual_values = np.array([float(row["annual_rainfall_mm"]) for row in annual_rows], dtype=float)
    min_coverage_row = min(monthly_rows, key=lambda row: float(row["valid_area_fraction"]))

    per_geography: dict[str, Any] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in annual_rows:
        grouped[str(row["geography_id"])].append(row)

    discontinuity_flags: list[dict[str, Any]] = []
    for gid, rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda row: int(row["year"]))
        values = np.array([float(row["annual_rainfall_mm"]) for row in rows], dtype=float)
        max_change = 0.0
        max_change_year_pair: list[int] | None = None
        for previous, current in zip(rows, rows[1:]):
            previous_value = float(previous["annual_rainfall_mm"])
            current_value = float(current["annual_rainfall_mm"])
            if previous_value <= 0:
                continue
            change = abs(current_value - previous_value) / previous_value
            if change > max_change:
                max_change = change
                max_change_year_pair = [int(previous["year"]), int(current["year"])]
        per_geography[gid] = {
            "geography_name": rows[0]["geography_name"],
            "min_annual_mm": round(float(values.min()), 6),
            "median_annual_mm": round(float(np.median(values)), 6),
            "max_annual_mm": round(float(values.max()), 6),
            "max_abs_yoy_fraction": round(max_change, 6),
            "max_abs_yoy_year_pair": max_change_year_pair,
        }
        if max_change >= 0.50:
            discontinuity_flags.append({
                "geography_id": gid,
                "geography_name": rows[0]["geography_name"],
                "max_abs_yoy_fraction": round(max_change, 6),
                "year_pair": max_change_year_pair,
            })

    yearly_iqr_flags: list[dict[str, Any]] = []
    for year in PRODUCTION_YEARS:
        rows = [row for row in annual_rows if int(row["year"]) == year]
        values = np.array([float(row["annual_rainfall_mm"]) for row in rows], dtype=float)
        q1, q3 = np.percentile(values, [25, 75])
        iqr = float(q3 - q1)
        lower = float(q1 - 1.5 * iqr)
        upper = float(q3 + 1.5 * iqr)
        for row in rows:
            value = float(row["annual_rainfall_mm"])
            if value < lower or value > upper:
                yearly_iqr_flags.append({
                    "year": year,
                    "geography_id": row["geography_id"],
                    "geography_name": row["geography_name"],
                    "annual_rainfall_mm": round(value, 6),
                    "lower_fence_mm": round(lower, 6),
                    "upper_fence_mm": round(upper, 6),
                })

    return {
        "coverage": {
            "minimum_valid_area_fraction": round(float(coverage_values.min()), 8),
            "p01_valid_area_fraction": round(float(np.percentile(coverage_values, 1)), 8),
            "p05_valid_area_fraction": round(float(np.percentile(coverage_values, 5)), 8),
            "median_valid_area_fraction": round(float(np.median(coverage_values)), 8),
            "production_threshold": MIN_VALID_AREA_FRACTION,
            "minimum_row": {
                "geography_id": min_coverage_row["geography_id"],
                "geography_name": min_coverage_row["geography_name"],
                "year": int(min_coverage_row["year"]),
                "month": int(min_coverage_row["month"]),
                "valid_area_fraction": float(min_coverage_row["valid_area_fraction"]),
            },
        },
        "annual_rainfall": {
            "minimum_mm": round(float(annual_values.min()), 6),
            "median_mm": round(float(np.median(annual_values)), 6),
            "maximum_mm": round(float(annual_values.max()), 6),
            "yearly_iqr_flags": yearly_iqr_flags,
            "iqr_flags_are_diagnostic_not_rejections": True,
            "per_geography": per_geography,
            "yoy_ge_50pct_flags": discontinuity_flags,
            "yoy_flags_are_diagnostic_not_rejections": True,
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


def run_production(output_dir: Path) -> dict[str, Any]:
    started = time.monotonic()
    crosswalk = sample_crosswalk()
    if len(crosswalk) != EXPECTED_GEOGRAPHY_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_GEOGRAPHY_COUNT} current geographies; got {len(crosswalk)}")
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
        for year in PRODUCTION_YEARS:
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
                        abs(abs(float(dataset.transform.a)) - 0.05) < 1e-7
                        and abs(abs(float(dataset.transform.e)) - 0.05) < 1e-7
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
                        if coverage < MIN_VALID_AREA_FRACTION:
                            raise RuntimeError(
                                f"Coverage below production threshold for {gid}/{year}-{month:02d}: "
                                f"{coverage:.8f} < {MIN_VALID_AREA_FRACTION:.8f}"
                            )
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
    if len(source_files) != EXPECTED_COG_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_COG_COUNT} source COGs; got {len(source_files)}")
    if len(monthly_rows) != EXPECTED_MONTHLY_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_MONTHLY_ROWS} monthly rows; got {len(monthly_rows)}")
    if len(annual_rows) != EXPECTED_ANNUAL_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_ANNUAL_ROWS} annual rows; got {len(annual_rows)}")

    diagnostics = build_diagnostics(monthly_rows, annual_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly_path = output_dir / "chirps_rainfall_production_monthly.csv"
    annual_path = output_dir / "chirps_rainfall_production_annual.csv"
    manifest_path = output_dir / "chirps_rainfall_production_manifest.json"
    write_csv(monthly_path, monthly_rows)
    write_csv(annual_path, annual_rows)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_dry_run_version": 1,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "scope": {
            "first_year": PRODUCTION_YEARS[0],
            "last_year": PRODUCTION_YEARS[-1],
            "year_count": len(PRODUCTION_YEARS),
            "geography_count": len(geography_ids),
            "source_cog_count": len(source_files),
            "monthly_row_count": len(monthly_rows),
            "annual_row_count": len(annual_rows),
            "not_canonical_materialization": True,
        },
        "method": {
            "monthly_statistic": "geodesic area-weighted mean of CHIRPS-valid intersecting grid-cell portions",
            "annual_statistic": "sum of 12 monthly polygon mean precipitation totals",
            "coverage_threshold": MIN_VALID_AREA_FRACTION,
            "coverage_threshold_basis": "bounded 1981/2000/2025 sample minimum was 0.99877921; 0.995 retains margin while failing material coverage loss",
            "claim_type": "model_estimate",
            "spatial_frame": "fixed_current_boundary_june_2026",
            "historical_boundary_continuity_claimed": False,
            "diagnostic_flags_are_not_auto_rejections": True,
        },
        "big_geometry": big_provenance,
        "chirps_grid": reference_grid,
        "chirps_source_files": source_files,
        "diagnostics": diagnostics,
        "gates": {
            "all_19_current_geographies_present": len(geography_ids) == EXPECTED_GEOGRAPHY_COUNT,
            "all_540_monthly_cogs_read": len(source_files) == EXPECTED_COG_COUNT,
            "all_10260_monthly_rows_present": len(monthly_rows) == EXPECTED_MONTHLY_ROWS,
            "all_855_annual_rows_present": len(annual_rows) == EXPECTED_ANNUAL_ROWS,
            "coverage_threshold_passed": diagnostics["coverage"]["minimum_valid_area_fraction"] >= MIN_VALID_AREA_FRACTION,
            "all_monthly_values_nonnegative": all(float(row["monthly_rainfall_mm"]) >= 0 for row in monthly_rows),
            "all_annual_values_positive": all(float(row["annual_rainfall_mm"]) > 0 for row in annual_rows),
            "all_rows_model_estimate": all(row["claim_type"] == "model_estimate" for row in monthly_rows + annual_rows),
            "all_rows_fixed_current_boundary": all(row["spatial_frame"] == "fixed_current_boundary_june_2026" for row in monthly_rows + annual_rows),
            "historical_boundary_continuity_not_claimed": True,
            "not_canonical_materialization": True,
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full 1981-2025 CHIRPS rainfall production dry-run")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/chirps-rainfall-production"))
    args = parser.parse_args()
    manifest = run_production(args.output_dir)
    summary = {
        "runtime_seconds": manifest["runtime_seconds"],
        "scope": manifest["scope"],
        "coverage": manifest["diagnostics"]["coverage"],
        "annual_rainfall_summary": {
            "minimum_mm": manifest["diagnostics"]["annual_rainfall"]["minimum_mm"],
            "median_mm": manifest["diagnostics"]["annual_rainfall"]["median_mm"],
            "maximum_mm": manifest["diagnostics"]["annual_rainfall"]["maximum_mm"],
            "yearly_iqr_flag_count": len(manifest["diagnostics"]["annual_rainfall"]["yearly_iqr_flags"]),
            "yoy_ge_50pct_flag_count": len(manifest["diagnostics"]["annual_rainfall"]["yoy_ge_50pct_flags"]),
        },
        "gates": manifest["gates"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
