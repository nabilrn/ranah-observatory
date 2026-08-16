from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
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

CHIRPS_ANNUAL_TIF_BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs"
CHIRPS_SOURCE_ID = "chirps_v3"
INDICATOR_ID = "annual_rainfall"
UNIT = "millimetres"
CLAIM_TYPE = "model_estimate"
METHOD_REVISION = "chirps-v3-final-annual_fractional-area-v1"
WEIGHT_CRS = "EPSG:6933"
SOURCE_START_YEAR = 1981
SOURCE_END_YEAR = 2025
NODATA_THRESHOLD = -9000.0
MIN_VALID_AREA_FRACTION = 0.98
DOWNLOAD_ATTEMPTS = 5
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
POLITE_DELAY_SECONDS = 2.0
USER_AGENT = "ranah-observatory/0.1 (+https://github.com/nabilrn/ranah-observatory)"

EQUIVALENCE_REFERENCE = "data/validation/chirps/chirps-v3-2025-annual-monthly-equivalence.csv"
EQUIVALENCE_YEAR = 2025
EQUIVALENCE_MAX_ABS_MM = 0.000460631
EQUIVALENCE_MAX_RELATIVE_PERCENT = 0.000013209810
EQUIVALENCE_ANNUAL_TIF_SHA256 = "e24f177b53c05eae36bf636b7ed42223948dce37350115ac157211f118b1e70c"

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

ANNUAL_DIAGNOSTIC_FIELDS = [
    "geography_id",
    "canonical_name",
    "source_permendagri_code",
    "year",
    "annual_rainfall_mm",
    "valid_area_fraction",
    "valid_weight_area_m2",
    "polygon_weight_area_m2",
    "valid_pixel_intersections",
    "total_pixel_intersections",
    "source_url",
    "source_sha256",
    "source_bytes",
]

SOURCE_ARTIFACT_FIELDS = [
    "year",
    "source_url",
    "retrieved_at",
    "bytes",
    "sha256",
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


def chirps_annual_url(year: int) -> str:
    return f"{CHIRPS_ANNUAL_TIF_BASE}/chirps-v3.0.{year:04d}.tif"


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


def _download_backoff_seconds(attempt: int, status: int | None = None) -> float:
    if status in {403, 429}:
        return float(min(15 * attempt, 60))
    return float(min(2 ** (attempt - 1), 16))


def download_annual_tif(source: str, target: Path) -> tuple[str, int]:
    last_error: BaseException | None = None
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        digest = hashlib.sha256()
        bytes_written = 0
        try:
            request = urllib.request.Request(
                source,
                headers={
                    "Accept": "image/tiff,application/octet-stream,*/*",
                    "User-Agent": USER_AGENT,
                    "Connection": "close",
                },
            )
            with urllib.request.urlopen(request, timeout=180.0) as response:
                status = int(getattr(response, "status", 200))
                if status != 200:
                    raise OSError(f"unexpected HTTP status {status}")
                expected_length_raw = response.headers.get("Content-Length")
                expected_length = int(expected_length_raw) if expected_length_raw and expected_length_raw.isdigit() else None
                with target.open("wb") as handle:
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
                        if not chunk:
                            break
                        handle.write(chunk)
                        digest.update(chunk)
                        bytes_written += len(chunk)
            if bytes_written <= 0:
                raise OSError("downloaded CHIRPS annual TIFF is empty")
            if expected_length is not None and bytes_written != expected_length:
                raise OSError(
                    f"download length mismatch: expected {expected_length} bytes, got {bytes_written}"
                )
            with target.open("rb") as handle:
                prefix = handle.read(4)
            if prefix not in {b"II*\x00", b"MM\x00*"}:
                raise OSError(f"downloaded object is not a TIFF: prefix={prefix!r}")
            return digest.hexdigest(), bytes_written
        except urllib.error.HTTPError as exc:
            last_error = exc
            target.unlink(missing_ok=True)
            status = exc.code
            if attempt < DOWNLOAD_ATTEMPTS:
                delay = _download_backoff_seconds(attempt, status)
                print(
                    f"annual TIFF HTTP {status} for {source} on attempt {attempt}/{DOWNLOAD_ATTEMPTS}; "
                    f"retrying in {delay:.0f}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(delay)
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            target.unlink(missing_ok=True)
            if attempt < DOWNLOAD_ATTEMPTS:
                delay = _download_backoff_seconds(attempt)
                print(
                    f"annual TIFF download failed for {source} on attempt {attempt}/{DOWNLOAD_ATTEMPTS}: "
                    f"{exc}; retrying in {delay:.0f}s",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(delay)
    raise RuntimeError(
        f"CHIRPS annual TIFF download failed after {DOWNLOAD_ATTEMPTS} attempts for {source}: {last_error}"
    )


def load_and_select_big_features(raw_geojson: Path) -> list[dict[str, Any]]:
    payload = json.loads(raw_geojson.read_text(encoding="utf-8"))
    features = payload.get("features") if isinstance(payload, Mapping) else None
    if not isinstance(features, list):
        raise ValueError("BIG snapshot is not a GeoJSON FeatureCollection")

    crosswalk = big_crosswalk()
    canonical = canonical_sumbar_geographies()
    if len(crosswalk) != 19 or len(canonical) != 19:
        raise ValueError(
            "BIG crosswalk and canonical geography registry must each contain 19 current Sumatera Barat units"
        )

    selected: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    mapped_ids: set[str] = set()
    for feature in features:
        if not isinstance(feature, Mapping):
            continue
        properties = (
            feature.get("properties")
            if isinstance(feature.get("properties"), Mapping)
            else {}
        )
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
            raise ValueError(
                f"BIG mapping {code} resolves outside current canonical Sumatera Barat: {canonical_id}"
            )
        geom = shape(feature.get("geometry"))
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
        row_stop = min(
            dataset.height,
            int(math.ceil(candidate.row_off + candidate.height)) + 1,
        )
        col_stop = min(
            dataset.width,
            int(math.ceil(candidate.col_off + candidate.width)) + 1,
        )

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
                cell = box(
                    min(x0, x1),
                    min(y0, y1),
                    max(x0, x1),
                    max(y0, y1),
                )
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
                f"Fractional pixel intersections do not reconstruct polygon area for "
                f"{item['geography_id']}: ratio={area_ratio}"
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


def weighted_raster_value(
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


def build_observation(
    diagnostic: Mapping[str, Any],
    provenance_id: str,
) -> dict[str, Any]:
    geography_id = str(diagnostic["geography_id"])
    year = int(diagnostic["year"])
    value = float(diagnostic["annual_rainfall_mm"])
    coverage = float(diagnostic["valid_area_fraction"])
    observation_id = deterministic_id(
        "chirpsobs",
        INDICATOR_ID,
        geography_id,
        str(year),
        METHOD_REVISION,
        BIG_EDITION,
    )
    return {
        "observation_id": observation_id,
        "indicator_id": INDICATOR_ID,
        "geography_id": geography_id,
        "time_start": f"{year:04d}-01-01",
        "time_end": f"{year:04d}-12-31",
        "frequency": "annual",
        "value_numeric": round(value, 3),
        "unit": UNIT,
        "claim_type": CLAIM_TYPE,
        "provenance_id": provenance_id,
        "suppressed": "false",
        "comparable": "true",
        "methodology_version": METHOD_REVISION,
        "price_basis": "",
        "notes": (
            "source=CHIRPS v3 Final annual; spatial_frame=current-boundary reconstruction "
            f"using BIG {BIG_EDITION}; aggregation=fractional-area-weighted spatial mean of "
            f"official annual precipitation raster over valid CHIRPS land cells; "
            f"valid_area_fraction={coverage:.6f}; claim is model_estimate, not direct BMKG "
            "station observation."
        ),
    }


def validate_observations(
    observations: list[dict[str, Any]],
    start_year: int,
    end_year: int,
) -> None:
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


def _prepare_geometry(
    output_dir: Path,
    geometry_geojson: Path | None,
) -> tuple[Path, dict[str, Any] | None]:
    output_geometry = output_dir / "big_sumbar_boundaries_june_2026.source.geojson"
    if geometry_geojson is None:
        big_manifest = run_big_probe(raw_output=output_geometry)
        if not big_manifest["conclusions"]["official_big_polygon_lane_qualified"]:
            raise ValueError("Live BIG geometry failed qualification gate")
        return output_geometry, big_manifest

    source = geometry_geojson.resolve()
    destination = output_geometry.resolve()
    if source != destination:
        shutil.copyfile(source, destination)
    return output_geometry, None


def build_panel(
    start_year: int,
    end_year: int,
    output_dir: Path,
    geometry_geojson: Path | None = None,
) -> dict[str, Any]:
    if not SOURCE_START_YEAR <= start_year <= end_year <= SOURCE_END_YEAR:
        raise ValueError(
            f"Requested years must be within stable qualified range "
            f"{SOURCE_START_YEAR}-{SOURCE_END_YEAR}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    geometry_path, big_manifest = _prepare_geometry(output_dir, geometry_geojson)
    selected_features = load_and_select_big_features(geometry_path)

    retrieved_at = datetime.now(timezone.utc).isoformat()
    provenance_id = deterministic_id(
        "chirpsprov",
        "CHIRPS-v3-Final-annual",
        f"{start_year}-{end_year}",
        BIG_EDITION,
        METHOD_REVISION,
    )

    diagnostics: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    source_artifacts: list[dict[str, Any]] = []
    expected_grid: GridSignature | None = None
    weights: list[GeographyWeights] | None = None
    union_window: Window | None = None

    with tempfile.TemporaryDirectory(prefix="chirps-annual-") as temp_dir:
        temp_root = Path(temp_dir)
        for index, year in enumerate(range(start_year, end_year + 1)):
            source_url = chirps_annual_url(year)
            local_tif = temp_root / f"chirps-v3.0.{year:04d}.tif"
            source_sha256, source_bytes = download_annual_tif(source_url, local_tif)
            year_retrieved_at = datetime.now(timezone.utc).isoformat()

            with rasterio.open(local_tif) as dataset:
                if expected_grid is None:
                    expected_grid = grid_signature(dataset)
                    assert_grid_compatible(dataset, expected_grid)
                    weights, union_window = compute_fractional_area_weights(
                        selected_features, dataset
                    )
                else:
                    assert_grid_compatible(dataset, expected_grid)
                if weights is None or union_window is None:
                    raise RuntimeError("CHIRPS spatial weights were not initialized")
                array = dataset.read(1, window=union_window)

            source_artifacts.append(
                {
                    "year": year,
                    "source_url": source_url,
                    "retrieved_at": year_retrieved_at,
                    "bytes": source_bytes,
                    "sha256": source_sha256,
                }
            )

            for item in weights:
                value, coverage, valid_area_m2, valid_count, total_count = weighted_raster_value(
                    array, union_window, item
                )
                diagnostic = {
                    "geography_id": item.geography_id,
                    "canonical_name": item.canonical_name,
                    "source_permendagri_code": item.source_permendagri_code,
                    "year": year,
                    "annual_rainfall_mm": round(value, 6),
                    "valid_area_fraction": round(coverage, 9),
                    "valid_weight_area_m2": round(valid_area_m2, 3),
                    "polygon_weight_area_m2": round(item.polygon_area_m2, 3),
                    "valid_pixel_intersections": valid_count,
                    "total_pixel_intersections": total_count,
                    "source_url": source_url,
                    "source_sha256": source_sha256,
                    "source_bytes": source_bytes,
                }
                diagnostics.append(diagnostic)
                observations.append(build_observation(diagnostic, provenance_id))

            print(
                f"processed CHIRPS annual {year}: {len(weights)} geographies; "
                f"source_bytes={source_bytes} sha256={source_sha256[:12]}...",
                flush=True,
            )
            local_tif.unlink(missing_ok=True)
            if index < (end_year - start_year):
                time.sleep(POLITE_DELAY_SECONDS)

    if expected_grid is None:
        raise RuntimeError("No CHIRPS annual rasters were processed")
    validate_observations(observations, start_year, end_year)

    observations_path = output_dir / "chirps-v3-annual-rainfall-current-boundaries.csv"
    diagnostics_path = output_dir / "chirps-v3-annual-zonal-diagnostics.csv"
    source_artifacts_path = output_dir / "chirps-v3-annual-source-artifacts.csv"
    provenance_path = output_dir / "chirps-v3-rainfall-provenance.csv"
    manifest_path = output_dir / "chirps-v3-rainfall-panel.manifest.json"

    write_csv(observations_path, OBSERVATION_FIELDS, observations)
    write_csv(diagnostics_path, ANNUAL_DIAGNOSTIC_FIELDS, diagnostics)
    write_csv(source_artifacts_path, SOURCE_ARTIFACT_FIELDS, source_artifacts)

    provenance_row = {
        "provenance_id": provenance_id,
        "source_id": CHIRPS_SOURCE_ID,
        "artifact_locator": f"{CHIRPS_ANNUAL_TIF_BASE}/chirps-v3.0.YYYY.tif",
        "retrieved_at": retrieved_at,
        "source_release": "CHIRPS v3 Final annual",
        "checksum_sha256": sha256_file(source_artifacts_path),
        "parser_revision": "build_chirps_rainfall_panel.py",
        "transform_revision": METHOD_REVISION,
        "extraction_method": "derived",
        "notes": (
            f"Years {start_year}-{end_year}; BIG {BIG_EDITION} current polygon frame; "
            f"fractional pixel intersection areas computed in {WEIGHT_CRS}; official CHIRPS v3 "
            "Final annual TIFFs downloaded sequentially with source-level SHA-256 checksums and "
            f"a {POLITE_DELAY_SECONDS:.1f}s inter-request delay; each annual raster is spatially "
            "averaged over valid land cells. Direct annual-raster aggregation was validated against "
            f"the 2025 sum-of-monthly-COGs implementation with maximum absolute difference "
            f"{EQUIVALENCE_MAX_ABS_MM:.9f} mm."
        ),
    }
    write_csv(provenance_path, PROVENANCE_FIELDS, [provenance_row])

    values = [float(row["value_numeric"]) for row in observations]
    coverages = [float(row["valid_area_fraction"]) for row in diagnostics]
    manifest = {
        "generated_at": retrieved_at,
        "panel_version": 2,
        "indicator_id": INDICATOR_ID,
        "claim_type": CLAIM_TYPE,
        "unit": UNIT,
        "years": {
            "start": start_year,
            "end": end_year,
            "count": end_year - start_year + 1,
        },
        "geography": {
            "count": 19,
            "spatial_frame": "current_boundary_reconstruction",
            "source": "Badan Informasi Geospasial",
            "source_edition": BIG_EDITION,
            "mapping": (
                "BIG KDPKAB Permendagri/PUM -> explicit June 2026 crosswalk -> "
                "canonical geography_id"
            ),
            "raw_geojson_sha256": sha256_file(geometry_path),
        },
        "chirps": {
            "source": "CHIRPS v3 Final annual",
            "annual_tif_base": CHIRPS_ANNUAL_TIF_BASE,
            "annual_raster_count": end_year - start_year + 1,
            "grid": {
                "crs": expected_grid.crs,
                "width": expected_grid.width,
                "height": expected_grid.height,
                "transform": list(expected_grid.transform),
                "resolution": list(expected_grid.resolution),
            },
            "nodata_rule": (
                f"non-finite, negative, or <= {NODATA_THRESHOLD} excluded; "
                "valid area re-normalized"
            ),
            "transport": {
                "mode": "sequential_full_download",
                "download_attempts": DOWNLOAD_ATTEMPTS,
                "polite_inter_request_delay_seconds": POLITE_DELAY_SECONDS,
                "source_level_sha256": True,
            },
        },
        "method": {
            "revision": METHOD_REVISION,
            "weight_crs": WEIGHT_CRS,
            "pixel_weighting": "fractional polygon-pixel intersection area",
            "annual_statistic": (
                "area-weighted spatial mean of official CHIRPS annual precipitation raster"
            ),
            "minimum_required_valid_area_fraction": MIN_VALID_AREA_FRACTION,
        },
        "cross_granularity_validation": {
            "reference": EQUIVALENCE_REFERENCE,
            "year": EQUIVALENCE_YEAR,
            "annual_tif_sha256": EQUIVALENCE_ANNUAL_TIF_SHA256,
            "max_absolute_difference_mm": EQUIVALENCE_MAX_ABS_MM,
            "max_relative_difference_percent": EQUIVALENCE_MAX_RELATIVE_PERCENT,
            "interpretation": (
                "official annual TIFF zonal means are numerically equivalent to the previously "
                "validated sum of twelve monthly COG zonal means within floating-point rounding"
            ),
        },
        "quality": {
            "observation_count": len(observations),
            "annual_diagnostic_count": len(diagnostics),
            "source_artifact_count": len(source_artifacts),
            "minimum_valid_area_fraction": min(coverages),
            "maximum_valid_area_fraction": max(coverages),
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
    for path in (
        observations_path,
        diagnostics_path,
        source_artifacts_path,
        provenance_path,
    ):
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
        description=(
            "Build annual CHIRPS v3 rainfall model-estimate panel for current "
            "Sumatera Barat boundaries"
        )
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
        help=(
            "Optional pre-qualified raw BIG GeoJSON snapshot; live BIG probe is used when omitted"
        ),
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
