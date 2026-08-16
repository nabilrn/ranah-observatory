from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window, from_bounds
from shapely.geometry import box, shape
from shapely.ops import transform as shapely_transform
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from probe_big_sumbar_boundaries import (  # noqa: E402
    EXPECTED_EDITION as BIG_EDITION,
    big_crosswalk,
    canonical_sumbar_geographies,
    normalize_code,
    run_probe as run_big_probe,
)

CHIRPS_MONTHLY_COG_BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs"
CHIRPS_SOURCE_ID = "chirps_v3"
INDICATOR_ID = "annual_rainfall"
UNIT = "millimetres"
CLAIM_TYPE = "model_estimate"
METHOD_REVISION = "chirps-v3-final-monthly_fractional-area-v1"
WEIGHT_CRS = "EPSG:6933"
SOURCE_START_YEAR = 1981
SOURCE_END_YEAR = 2025
NODATA_THRESHOLD = -9000.0
MIN_VALID_AREA_FRACTION = 0.98

OBSERVATION_FIELDS = [
    "observation_id",
    "indicator_id",
    "geography_id",
    "time_start",
    "time_end",
    "frequency",
    "value_numeric",
    "unit",
    "claim_type",
    "provenance_id",
    "suppressed",
    "comparable",
    "methodology_version",
    "price_basis",
    "notes",
]

MONTHLY_DIAGNOSTIC_FIELDS = [
    "geography_id",
    "canonical_name",
    "source_permendagri_code",
    "year",
    "month",
    "spatial_mean_precipitation_mm",
    "valid_area_fraction",
    "valid_weight_area_m2",
    "polygon_weight_area_m2",
    "valid_pixel_intersections",
    "total_pixel_intersections",
    "source_url",
]

PROVENANCE_FIELDS = [
    "provenance_id",
    "source_id",
    "artifact_locator",
    "retrieved_at",
    "source_release",
    "checksum_sha256",
    "parser_revision",
    "transform_revision",
    "extraction_method",
    "notes",
]


@dataclass(frozen=True)
class GeographyWeights:
    geography_id: str
    canonical_name: str
    source_permendagri_code: str
    source_name: str
    rows: np.ndarray
    cols: np.ndarray
    areas_m2: np.ndarray
    polygon_area_m2: float


@dataclass(frozen=True)
class GridSignature:
    crs: str
    width: int
    height: int
    transform: tuple[float, ...]
    resolution: tuple[float, float]


def chirps_month_url(year: int, month: int) -> str:
    return f"{CHIRPS_MONTHLY_COG_BASE}/chirps-v3.0.{year:04d}.{month:02d}.cog"


def deterministic_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def gdal_env_options() -> dict[str, str]:
    return {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".cog",
        "GDAL_HTTP_MULTIRANGE": "YES",
        "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
        "GDAL_HTTP_MAX_RETRY": "4",
        "GDAL_HTTP_RETRY_DELAY": "1",
        "VSI_CACHE": "TRUE",
        "VSI_CACHE_SIZE": str(32 * 1024 * 1024),
    }


def grid_signature(dataset: rasterio.io.DatasetReader) -> GridSignature:
    if dataset.crs is None:
        raise ValueError("CHIRPS raster has no CRS")
    return GridSignature(
        crs=str(dataset.crs),
        width=dataset.width,
        height=dataset.height,
        transform=tuple(float(value) for value in dataset.transform),
        resolution=(float(dataset.res[0]), float(dataset.res[1])),
    )


def assert_grid_compatible(dataset: rasterio.io.DatasetReader, expected: GridSignature) -> None:
    actual = grid_signature(dataset)
    if actual != expected:
        raise ValueError(f"CHIRPS grid changed unexpectedly: expected={expected} actual={actual}")
    if actual.crs != "EPSG:4326":
        raise ValueError(f"CHIRPS grid CRS changed unexpectedly: {actual.crs}")
    if not math.isclose(actual.resolution[0], 0.05, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"CHIRPS x resolution changed unexpectedly: {actual.resolution[0]}")
    if not math.isclose(actual.resolution[1], 0.05, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"CHIRPS y resolution changed unexpectedly: {actual.resolution[1]}")


def load_and_select_big_features(raw_geojson: Path) -> list[dict[str, Any]]:
    payload = json.loads(raw_geojson.read_text(encoding="utf-8"))
    features = payload.get("features") if isinstance(payload, Mapping) else None
    if not isinstance(features, list):
        raise ValueError("BIG snapshot is not a GeoJSON FeatureCollection")

    crosswalk = big_crosswalk()
    canonical = canonical_sumbar_geographies()
    if len(crosswalk) != 19 or len(canonical) != 19:
        raise ValueError("BIG crosswalk and canonical geography registry must each contain 19 current Sumatera Barat units")

    selected: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    mapped_ids: set[str] = set()
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        properties = feature.get("properties") if isinstance(feature.get("properties"), Mapping) else {}
        code = normalize_code(properties.get("KDPKAB"))
        source_name = str(properties.get("WADMKK") or "").strip()
        if not code or not source_name:
            continue
        mapping = crosswalk.get(code)
        if mapping is None:
            raise ValueError(f"BIG source contains unmapped KDPKAB {code}: {source_name}")
        if code in seen_codes:
            raise ValueError(f"BIG source contains duplicate KDPKAB {code}")
        expected_name = mapping["source_name_expected"].strip()
        if source_name.casefold() != expected_name.casefold():
            raise ValueError(
                f"BIG source-name mismatch for {code}: expected {expected_name!r}, got {source_name!r}"
            )
        if str(properties.get("WADMPR") or "").strip().casefold() != "sumatera barat":
            raise ValueError(f"BIG selected feature {code} is outside Sumatera Barat")
        canonical_id = mapping["canonical_geography_id"]
        if canonical_id not in canonical:
            raise ValueError(f"BIG mapping {code} resolves outside current canonical Sumatera Barat: {canonical_id}")
        geometry = feature.get("geometry")
        geom = shape(geometry)
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"BIG geometry for {code} is invalid or non-polygonal")
        selected.append(
            {
                "feature": feature,
                "source_code": code,
                "source_name": source_name,
                "geography_id": canonical_id,
                "canonical_name": canonical[canonical_id]["canonical_name"],
            }
        )
        seen_codes.add(code)
        mapped_ids.add(canonical_id)

    if len(selected) != 19 or set(crosswalk) != seen_codes or set(canonical) != mapped_ids:
        raise ValueError(
            "BIG selected geometry does not map bijectively to the 19 current canonical Sumatera Barat geographies"
        )
    return sorted(selected, key=lambda item: item["geography_id"])


def compute_fractional_area_weights(
    selected_features: list[dict[str, Any]],
    dataset: rasterio.io.DatasetReader,
) -> tuple[list[GeographyWeights], Window]:
    if str(dataset.crs) != "EPSG:4326":
        raise ValueError(f"Expected EPSG:4326 CHIRPS grid, got {dataset.crs}")
    project = Transformer.from_crs("EPSG:4326", WEIGHT_CRS, always_xy=True).transform
    weights: list[GeographyWeights] = []

    for item in selected_features:
        geom = shape(item["feature"]["geometry"])
        projected_geom = shapely_transform(project, geom)
        polygon_area_m2 = float(projected_geom.area)
        if not math.isfinite(polygon_area_m2) or polygon_area_m2 <= 0:
            raise ValueError(f"Non-positive projected polygon area for {item['geography_id']}")

        minx, miny, maxx, maxy = geom.bounds
        candidate = from_bounds(minx, miny, maxx, maxy, dataset.transform)
        row_start = max(0, int(math.floor(candidate.row_off)) - 1)
        col_start = max(0, int(math.floor(candidate.col_off)) - 1)
        row_stop = min(dataset.height, int(math.ceil(candidate.row_off + candidate.height)) + 1)
        col_stop = min(dataset.width, int(math.ceil(candidate.col_off + candidate.width)) + 1)

        prepared = prep(geom)
        rows: list[int] = []
        cols: list[int] = []
        areas: list[float] = []
        for row in range(row_start, row_stop):
            y0 = dataset.transform.f + row * dataset.transform.e
            y1 = y0 + dataset.transform.e
            for col in range(col_start, col_stop):
                x0 = dataset.transform.c + col * dataset.transform.a
                x1 = x0 + dataset.transform.a
                cell = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                if not prepared.intersects(cell):
                    continue
                intersection = geom.intersection(cell)
                if intersection.is_empty:
                    continue
                area_m2 = float(shapely_transform(project, intersection).area)
                if not math.isfinite(area_m2) or area_m2 <= 0:
                    continue
                rows.append(row)
                cols.append(col)
                areas.append(area_m2)

        if not areas:
            raise ValueError(f"No CHIRPS grid intersections for {item['geography_id']}")
        area_ratio = sum(areas) / polygon_area_m2
        if not 0.995 <= area_ratio <= 1.005:
            raise ValueError(
                f"Fractional pixel intersections do not reconstruct polygon area for {item['geography_id']}: ratio={area_ratio}"
            )
        weights.append(
            GeographyWeights(
                geography_id=item["geography_id"],
                canonical_name=item["canonical_name"],
                source_permendagri_code=item["source_code"],
                source_name=item["source_name"],
                rows=np.asarray(rows, dtype=np.int32),
                cols=np.asarray(cols, dtype=np.int32),
                areas_m2=np.asarray(areas, dtype=np.float64),
                polygon_area_m2=polygon_area_m2,
            )
        )

    all_rows = np.concatenate([item.rows for item in weights])
    all_cols = np.concatenate([item.cols for item in weights])
    row_min = int(all_rows.min())
    row_max = int(all_rows.max())
    col_min = int(all_cols.min())
    col_max = int(all_cols.max())
    union_window = Window(
        col_off=col_min,
        row_off=row_min,
        width=col_max - col_min + 1,
        height=row_max - row_min + 1,
    )
    return weights, union_window


def weighted_month_value(
    array: np.ndarray,
    window: Window,
    item: GeographyWeights,
) -> tuple[float, float, float, int, int]:
    local_rows = item.rows - int(window.row_off)
    local_cols = item.cols - int(window.col_off)
    values = array[local_rows, local_cols].astype(np.float64, copy=False)
    valid = np.isfinite(values) & (values > NODATA_THRESHOLD) & (values >= 0.0)
    valid_count = int(valid.sum())
    total_count = int(values.size)
    if valid_count == 0:
        raise ValueError(f"No valid CHIRPS pixels for {item.geography_id}")
    valid_areas = item.areas_m2[valid]
    valid_area_m2 = float(valid_areas.sum())
    valid_area_fraction = valid_area_m2 / item.polygon_area_m2
    if valid_area_fraction < MIN_VALID_AREA_FRACTION:
        raise ValueError(
            f"CHIRPS valid area below threshold for {item.geography_id}: "
            f"{valid_area_fraction:.6f} < {MIN_VALID_AREA_FRACTION:.6f}"
        )
    value = float(np.average(values[valid], weights=valid_areas))
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid weighted CHIRPS precipitation for {item.geography_id}: {value}")
    return value, valid_area_fraction, valid_area_m2, valid_count, total_count


def process_month(
    year: int,
    month: int,
    expected_grid: GridSignature,
    weights: list[GeographyWeights],
    union_window: Window,
    raster_source: str | Path | None = None,
) -> list[dict[str, Any]]:
    source = str(raster_source) if raster_source is not None else chirps_month_url(year, month)
    with rasterio.Env(**gdal_env_options()):
        with rasterio.open(source) as dataset:
            assert_grid_compatible(dataset, expected_grid)
            array = dataset.read(1, window=union_window)

    rows: list[dict[str, Any]] = []
    for item in weights:
        value, coverage, valid_area_m2, valid_count, total_count = weighted_month_value(
            array, union_window, item
        )
        rows.append(
            {
                "geography_id": item.geography_id,
                "canonical_name": item.canonical_name,
                "source_permendagri_code": item.source_permendagri_code,
                "year": year,
                "month": month,
                "spatial_mean_precipitation_mm": round(value, 6),
                "valid_area_fraction": round(coverage, 9),
                "valid_weight_area_m2": round(valid_area_m2, 3),
                "polygon_weight_area_m2": round(item.polygon_area_m2, 3),
                "valid_pixel_intersections": valid_count,
                "total_pixel_intersections": total_count,
                "source_url": source,
            }
        )
    return rows


def build_annual_observations(
    monthly_rows: list[dict[str, Any]],
    start_year: int,
    end_year: int,
    provenance_id: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in monthly_rows:
        key = (str(row["geography_id"]), int(row["year"]))
        grouped.setdefault(key, []).append(row)

    expected_keys = {
        (geography_id, year)
        for geography_id in {str(row["geography_id"]) for row in monthly_rows}
        for year in range(start_year, end_year + 1)
    }
    if set(grouped) != expected_keys:
        missing = sorted(expected_keys - set(grouped))
        unexpected = sorted(set(grouped) - expected_keys)
        raise ValueError(f"Monthly aggregation key mismatch; missing={missing[:5]} unexpected={unexpected[:5]}")

    observations: list[dict[str, Any]] = []
    for (geography_id, year), rows in sorted(grouped.items()):
        rows = sorted(rows, key=lambda row: int(row["month"]))
        months = [int(row["month"]) for row in rows]
        if months != list(range(1, 13)):
            raise ValueError(f"Incomplete monthly coverage for {geography_id} {year}: {months}")
        annual_value = sum(float(row["spatial_mean_precipitation_mm"]) for row in rows)
        min_coverage = min(float(row["valid_area_fraction"]) for row in rows)
        observation_id = deterministic_id(
            "chirpsobs",
            INDICATOR_ID,
            geography_id,
            str(year),
            METHOD_REVISION,
            BIG_EDITION,
        )
        observations.append(
            {
                "observation_id": observation_id,
                "indicator_id": INDICATOR_ID,
                "geography_id": geography_id,
                "time_start": f"{year:04d}-01-01",
                "time_end": f"{year:04d}-12-31",
                "frequency": "annual",
                "value_numeric": round(annual_value, 3),
                "unit": UNIT,
                "claim_type": CLAIM_TYPE,
                "provenance_id": provenance_id,
                "suppressed": "false",
                "comparable": "true",
                "methodology_version": METHOD_REVISION,
                "price_basis": "",
                "notes": (
                    "source=CHIRPS v3 Final monthly; spatial_frame=current-boundary reconstruction "
                    f"using BIG {BIG_EDITION}; aggregation=sum of 12 fractional-area-weighted monthly "
                    f"means over valid CHIRPS land cells; minimum_monthly_valid_area_fraction={min_coverage:.6f}; "
                    "claim is model_estimate, not direct BMKG station observation."
                ),
            }
        )
    return observations


def validate_observations(observations: list[dict[str, Any]], start_year: int, end_year: int) -> None:
    expected_count = 19 * (end_year - start_year + 1)
    if len(observations) != expected_count:
        raise ValueError(f"Expected {expected_count} annual observations, got {len(observations)}")
    ids = [row["observation_id"] for row in observations]
    if len(ids) != len(set(ids)):
        raise ValueError("CHIRPS observation IDs are not unique")
    for row in observations:
        if row["indicator_id"] != INDICATOR_ID:
            raise ValueError("Unexpected indicator in CHIRPS annual output")
        if row["claim_type"] != CLAIM_TYPE:
            raise ValueError("CHIRPS annual output must remain model_estimate")
        value = float(row["value_numeric"])
        if not 500.0 <= value <= 10000.0:
            raise ValueError(
                f"Annual CHIRPS precipitation is outside broad Sumatera Barat plausibility guard: "
                f"{row['geography_id']} {row['time_start'][:4]} value={value}"
            )


def build_panel(
    start_year: int,
    end_year: int,
    output_dir: Path,
    geometry_geojson: Path | None = None,
    template_raster: str | Path | None = None,
) -> dict[str, Any]:
    if not SOURCE_START_YEAR <= start_year <= end_year <= SOURCE_END_YEAR:
        raise ValueError(
            f"Requested years must be within stable qualified range {SOURCE_START_YEAR}-{SOURCE_END_YEAR}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    geometry_path = geometry_geojson or output_dir / "big_sumbar_boundaries_june_2026.source.geojson"
    big_manifest: dict[str, Any] | None = None
    if geometry_geojson is None:
        big_manifest = run_big_probe(raw_output=geometry_path)
        if not big_manifest["conclusions"]["official_big_polygon_lane_qualified"]:
            raise ValueError("Live BIG geometry failed qualification gate")
    selected_features = load_and_select_big_features(geometry_path)

    first_source = str(template_raster) if template_raster is not None else chirps_month_url(start_year, 1)
    with rasterio.Env(**gdal_env_options()):
        with rasterio.open(first_source) as template:
            expected_grid = grid_signature(template)
            assert_grid_compatible(template, expected_grid)
            weights, union_window = compute_fractional_area_weights(selected_features, template)

    retrieved_at = datetime.now(timezone.utc).isoformat()
    provenance_id = deterministic_id(
        "chirpsprov",
        "CHIRPS-v3-Final-monthly",
        f"{start_year}-{end_year}",
        BIG_EDITION,
        METHOD_REVISION,
    )

    monthly_rows: list[dict[str, Any]] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            source_override: str | Path | None = None
            if template_raster is not None:
                if start_year != end_year or month != 1:
                    raise ValueError("template_raster override is only supported for a one-month test harness")
                source_override = template_raster
            month_rows = process_month(
                year,
                month,
                expected_grid,
                weights,
                union_window,
                raster_source=source_override,
            )
            monthly_rows.extend(month_rows)
            print(
                f"processed CHIRPS {year:04d}-{month:02d}: "
                f"{len(month_rows)} geographies",
                flush=True,
            )

    annual_observations = build_annual_observations(
        monthly_rows, start_year, end_year, provenance_id
    )
    validate_observations(annual_observations, start_year, end_year)

    observations_path = output_dir / "chirps-v3-annual-rainfall-current-boundaries.csv"
    monthly_path = output_dir / "chirps-v3-monthly-zonal-diagnostics.csv"
    provenance_path = output_dir / "chirps-v3-rainfall-provenance.csv"
    manifest_path = output_dir / "chirps-v3-rainfall-panel.manifest.json"

    write_csv(observations_path, OBSERVATION_FIELDS, annual_observations)
    write_csv(monthly_path, MONTHLY_DIAGNOSTIC_FIELDS, monthly_rows)

    provenance_row = {
        "provenance_id": provenance_id,
        "source_id": CHIRPS_SOURCE_ID,
        "artifact_locator": f"{CHIRPS_MONTHLY_COG_BASE}/chirps-v3.0.YYYY.MM.cog",
        "retrieved_at": retrieved_at,
        "source_release": "CHIRPS v3 Final monthly",
        "checksum_sha256": "",
        "parser_revision": "build_chirps_rainfall_panel.py",
        "transform_revision": METHOD_REVISION,
        "extraction_method": "derived",
        "notes": (
            f"Years {start_year}-{end_year}; BIG {BIG_EDITION} current polygon frame; "
            f"fractional pixel intersection areas computed in {WEIGHT_CRS}; source monthly COG "
            "values spatially averaged over valid land cells then summed across 12 months. "
            "Individual remote COG checksums are not materialized by range-read ingestion; "
            "source URLs, version, grid signature, diagnostics, and output checksums are retained."
        ),
    }
    write_csv(provenance_path, PROVENANCE_FIELDS, [provenance_row])

    values = [float(row["value_numeric"]) for row in annual_observations]
    coverages = [float(row["valid_area_fraction"]) for row in monthly_rows]
    manifest = {
        "generated_at": retrieved_at,
        "panel_version": 1,
        "indicator_id": INDICATOR_ID,
        "claim_type": CLAIM_TYPE,
        "unit": UNIT,
        "years": {"start": start_year, "end": end_year, "count": end_year - start_year + 1},
        "geography": {
            "count": 19,
            "spatial_frame": "current_boundary_reconstruction",
            "source": "Badan Informasi Geospasial",
            "source_edition": BIG_EDITION,
            "mapping": "BIG KDPKAB Permendagri/PUM -> explicit June 2026 crosswalk -> canonical geography_id",
            "raw_geojson_sha256": sha256_file(geometry_path),
        },
        "chirps": {
            "source": "CHIRPS v3 Final monthly",
            "monthly_cog_base": CHIRPS_MONTHLY_COG_BASE,
            "monthly_raster_count": (end_year - start_year + 1) * 12,
            "grid": {
                "crs": expected_grid.crs,
                "width": expected_grid.width,
                "height": expected_grid.height,
                "transform": list(expected_grid.transform),
                "resolution": list(expected_grid.resolution),
            },
            "nodata_rule": f"non-finite, negative, or <= {NODATA_THRESHOLD} excluded; valid area re-normalized",
        },
        "method": {
            "revision": METHOD_REVISION,
            "weight_crs": WEIGHT_CRS,
            "pixel_weighting": "fractional polygon-pixel intersection area",
            "monthly_statistic": "area-weighted spatial mean over valid CHIRPS land pixels",
            "annual_statistic": "sum of 12 monthly spatial means",
            "minimum_required_valid_area_fraction": MIN_VALID_AREA_FRACTION,
        },
        "quality": {
            "observation_count": len(annual_observations),
            "monthly_diagnostic_count": len(monthly_rows),
            "minimum_monthly_valid_area_fraction": min(coverages),
            "maximum_monthly_valid_area_fraction": max(coverages),
            "minimum_annual_rainfall_mm": min(values),
            "maximum_annual_rainfall_mm": max(values),
        },
        "outputs": {},
        "negative_guards": {
            "is_direct_station_observation": False,
            "uses_historical_boundary_geometry": False,
            "safe_to_interpret_big_june_2026_as_historical_boundary": False,
            "safe_to_equate_big_kdpkab_with_bps_code": False,
        },
        "big_live_probe": big_manifest,
    }
    for path in (observations_path, monthly_path, provenance_path):
        manifest["outputs"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build annual CHIRPS v3 rainfall model-estimate panel for current Sumatera Barat boundaries"
    )
    parser.add_argument("--start-year", type=int, default=SOURCE_START_YEAR)
    parser.add_argument("--end-year", type=int, default=SOURCE_END_YEAR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "processed" / "climate" / "chirps",
    )
    parser.add_argument(
        "--geometry-geojson",
        type=Path,
        help="Optional pre-qualified raw BIG GeoJSON snapshot; live BIG probe is used when omitted",
    )
    args = parser.parse_args()

    manifest = build_panel(
        start_year=args.start_year,
        end_year=args.end_year,
        output_dir=args.output_dir,
        geometry_geojson=args.geometry_geojson,
    )
    print(json.dumps(manifest["quality"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
