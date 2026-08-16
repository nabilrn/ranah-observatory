from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"

OBSERVATIONS = "chirps-v3-annual-rainfall-current-boundaries.csv"
MONTHLY = "chirps-v3-monthly-zonal-diagnostics.csv"
PROVENANCE = "chirps-v3-rainfall-provenance.csv"
MANIFEST = "chirps-v3-rainfall-panel.manifest.json"
GEOMETRY = "big_sumbar_boundaries_june_2026.source.geojson"

EXPECTED_INDICATOR = "annual_rainfall"
EXPECTED_UNIT = "millimetres"
EXPECTED_CLAIM = "model_estimate"
EXPECTED_METHOD = "chirps-v3-final-monthly_fractional-area-v1"
EXPECTED_PROVENANCE_SOURCE = "chirps_v3"
EXPECTED_BIG_EDITION = "Juni 2026"
MIN_VALID_AREA_FRACTION = 0.98


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_sumbar_ids() -> set[str]:
    rows = read_csv(GEOGRAPHIES)
    result = {
        row["geography_id"]
        for row in rows
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    }
    if len(result) != 19:
        raise ValueError(f"canonical current Sumatera Barat geography count is {len(result)}, expected 19")
    return result


def validate(output_dir: Path) -> list[str]:
    errors: list[str] = []
    required = [OBSERVATIONS, MONTHLY, PROVENANCE, MANIFEST, GEOMETRY]
    missing_files = [name for name in required if not (output_dir / name).is_file()]
    if missing_files:
        return [f"missing required panel files: {missing_files}"]

    observations = read_csv(output_dir / OBSERVATIONS)
    monthly = read_csv(output_dir / MONTHLY)
    provenance = read_csv(output_dir / PROVENANCE)
    manifest = json.loads((output_dir / MANIFEST).read_text(encoding="utf-8"))
    canonical_ids = current_sumbar_ids()

    years = manifest.get("years", {})
    try:
        start_year = int(years["start"])
        end_year = int(years["end"])
        year_count = int(years["count"])
    except (KeyError, TypeError, ValueError):
        return ["manifest years contract is invalid"]
    expected_years = set(range(start_year, end_year + 1))
    if start_year < 1981 or end_year > 2025 or start_year > end_year:
        errors.append(f"manifest year range {start_year}-{end_year} is outside qualified CHIRPS range 1981-2025")
    if year_count != len(expected_years):
        errors.append("manifest year count does not match start/end range")

    expected_observation_count = 19 * year_count
    expected_monthly_count = expected_observation_count * 12
    if len(observations) != expected_observation_count:
        errors.append(
            f"annual observation count is {len(observations)}, expected {expected_observation_count}"
        )
    if len(monthly) != expected_monthly_count:
        errors.append(
            f"monthly diagnostic count is {len(monthly)}, expected {expected_monthly_count}"
        )

    observation_ids = [row.get("observation_id", "") for row in observations]
    if any(not value for value in observation_ids):
        errors.append("annual observations contain blank observation_id")
    if len(observation_ids) != len(set(observation_ids)):
        errors.append("annual observation_id values are not unique")

    annual_keys: list[tuple[str, int]] = []
    provenance_ids: set[str] = set()
    for row in observations:
        geography_id = row.get("geography_id", "")
        if geography_id not in canonical_ids:
            errors.append(f"annual observation uses noncanonical geography {geography_id!r}")
            continue
        try:
            year = int(row.get("time_start", "")[:4])
        except ValueError:
            errors.append(f"invalid annual time_start {row.get('time_start')!r}")
            continue
        annual_keys.append((geography_id, year))
        if year not in expected_years:
            errors.append(f"annual observation year {year} is outside manifest range")
        if row.get("time_start") != f"{year:04d}-01-01" or row.get("time_end") != f"{year:04d}-12-31":
            errors.append(f"annual time bounds are not calendar-year bounds for {geography_id} {year}")
        if row.get("frequency") != "annual":
            errors.append(f"unexpected frequency for {geography_id} {year}: {row.get('frequency')!r}")
        if row.get("indicator_id") != EXPECTED_INDICATOR:
            errors.append(f"unexpected indicator for {geography_id} {year}: {row.get('indicator_id')!r}")
        if row.get("unit") != EXPECTED_UNIT:
            errors.append(f"unexpected unit for {geography_id} {year}: {row.get('unit')!r}")
        if row.get("claim_type") != EXPECTED_CLAIM:
            errors.append(f"CHIRPS row must remain model_estimate for {geography_id} {year}")
        if row.get("methodology_version") != EXPECTED_METHOD:
            errors.append(f"unexpected methodology version for {geography_id} {year}")
        if row.get("suppressed") != "false":
            errors.append(f"CHIRPS annual observation unexpectedly suppressed for {geography_id} {year}")
        if row.get("comparable") != "true":
            errors.append(f"CHIRPS current-boundary series must be internally marked comparable for {geography_id} {year}")
        notes = row.get("notes", "")
        for phrase in (
            "current-boundary reconstruction",
            "model_estimate",
            f"BIG {EXPECTED_BIG_EDITION}",
        ):
            if phrase not in notes:
                errors.append(f"annual observation notes missing {phrase!r} for {geography_id} {year}")
        try:
            value = float(row.get("value_numeric", ""))
        except ValueError:
            errors.append(f"annual rainfall is not numeric for {geography_id} {year}")
        else:
            if not math.isfinite(value) or not 500.0 <= value <= 10000.0:
                errors.append(f"annual rainfall is outside broad plausibility guard for {geography_id} {year}: {value}")
        provenance_id = row.get("provenance_id", "")
        if provenance_id:
            provenance_ids.add(provenance_id)
        else:
            errors.append(f"annual observation has blank provenance_id for {geography_id} {year}")

    expected_annual_keys = {
        (geography_id, year) for geography_id in canonical_ids for year in expected_years
    }
    if len(annual_keys) != len(set(annual_keys)):
        errors.append("duplicate geography-year keys exist in annual observations")
    if set(annual_keys) != expected_annual_keys:
        missing = sorted(expected_annual_keys - set(annual_keys))
        unexpected = sorted(set(annual_keys) - expected_annual_keys)
        errors.append(f"annual geography-year coverage mismatch; missing={missing[:5]} unexpected={unexpected[:5]}")

    monthly_keys: list[tuple[str, int, int]] = []
    coverage_values: list[float] = []
    for row in monthly:
        geography_id = row.get("geography_id", "")
        if geography_id not in canonical_ids:
            errors.append(f"monthly diagnostic uses noncanonical geography {geography_id!r}")
            continue
        try:
            year = int(row.get("year", ""))
            month = int(row.get("month", ""))
            value = float(row.get("spatial_mean_precipitation_mm", ""))
            coverage = float(row.get("valid_area_fraction", ""))
            valid_area = float(row.get("valid_weight_area_m2", ""))
            polygon_area = float(row.get("polygon_weight_area_m2", ""))
            valid_pixels = int(row.get("valid_pixel_intersections", ""))
            total_pixels = int(row.get("total_pixel_intersections", ""))
        except ValueError:
            errors.append(f"invalid monthly numeric fields for geography {geography_id}")
            continue
        monthly_keys.append((geography_id, year, month))
        if year not in expected_years or month not in range(1, 13):
            errors.append(f"monthly diagnostic has out-of-range period {geography_id} {year}-{month:02d}")
        if not math.isfinite(value) or value < 0:
            errors.append(f"invalid monthly rainfall value for {geography_id} {year}-{month:02d}: {value}")
        if not MIN_VALID_AREA_FRACTION <= coverage <= 1.001:
            errors.append(f"invalid monthly valid-area fraction for {geography_id} {year}-{month:02d}: {coverage}")
        coverage_values.append(coverage)
        if not 0 < valid_area <= polygon_area * 1.001:
            errors.append(f"invalid monthly area accounting for {geography_id} {year}-{month:02d}")
        if not 0 < valid_pixels <= total_pixels:
            errors.append(f"invalid monthly pixel accounting for {geography_id} {year}-{month:02d}")
        source_url = row.get("source_url", "")
        expected_suffix = f"chirps-v3.0.{year:04d}.{month:02d}.cog"
        if not source_url.startswith("https://data.chc.ucsb.edu/") or not source_url.endswith(expected_suffix):
            errors.append(f"unexpected CHIRPS source URL for {geography_id} {year}-{month:02d}")

    expected_monthly_keys = {
        (geography_id, year, month)
        for geography_id in canonical_ids
        for year in expected_years
        for month in range(1, 13)
    }
    if len(monthly_keys) != len(set(monthly_keys)):
        errors.append("duplicate geography-year-month keys exist in monthly diagnostics")
    if set(monthly_keys) != expected_monthly_keys:
        missing = sorted(expected_monthly_keys - set(monthly_keys))
        unexpected = sorted(set(monthly_keys) - expected_monthly_keys)
        errors.append(f"monthly geography-period coverage mismatch; missing={missing[:5]} unexpected={unexpected[:5]}")

    if len(provenance) != 1:
        errors.append(f"expected one panel provenance row, found {len(provenance)}")
    else:
        prov = provenance[0]
        if prov.get("source_id") != EXPECTED_PROVENANCE_SOURCE:
            errors.append(f"unexpected provenance source_id {prov.get('source_id')!r}")
        if prov.get("extraction_method") != "derived":
            errors.append("CHIRPS panel provenance extraction_method must remain derived")
        if prov.get("transform_revision") != EXPECTED_METHOD:
            errors.append("CHIRPS panel provenance transform revision changed")
        if prov.get("provenance_id", "") not in provenance_ids:
            errors.append("annual observation provenance_id does not resolve to panel provenance")
        if len(provenance_ids) != 1:
            errors.append(f"annual observations reference {len(provenance_ids)} provenance IDs, expected one")
        if "YYYY.MM.cog" not in prov.get("artifact_locator", ""):
            errors.append("panel provenance must retain monthly CHIRPS COG artifact pattern")

    if manifest.get("indicator_id") != EXPECTED_INDICATOR:
        errors.append("manifest indicator_id changed")
    if manifest.get("claim_type") != EXPECTED_CLAIM:
        errors.append("manifest claim_type must remain model_estimate")
    if manifest.get("unit") != EXPECTED_UNIT:
        errors.append("manifest unit changed")

    geography = manifest.get("geography", {})
    if geography.get("count") != 19:
        errors.append("manifest geography count must remain 19")
    if geography.get("spatial_frame") != "current_boundary_reconstruction":
        errors.append("manifest spatial frame must remain current_boundary_reconstruction")
    if geography.get("source_edition") != EXPECTED_BIG_EDITION:
        errors.append("manifest BIG source edition changed")
    geometry_sha = geography.get("raw_geojson_sha256")
    if geometry_sha != sha256_file(output_dir / GEOMETRY):
        errors.append("manifest BIG raw GeoJSON checksum does not match output")

    method = manifest.get("method", {})
    if method.get("revision") != EXPECTED_METHOD:
        errors.append("manifest method revision changed")
    if method.get("weight_crs") != "EPSG:6933":
        errors.append("manifest weight CRS must remain EPSG:6933")
    if method.get("pixel_weighting") != "fractional polygon-pixel intersection area":
        errors.append("manifest pixel weighting changed")
    if method.get("annual_statistic") != "sum of 12 monthly spatial means":
        errors.append("manifest annual statistic changed")
    try:
        manifest_min_coverage = float(method.get("minimum_required_valid_area_fraction"))
    except (TypeError, ValueError):
        errors.append("manifest minimum valid-area fraction is invalid")
    else:
        if not math.isclose(manifest_min_coverage, MIN_VALID_AREA_FRACTION, abs_tol=1e-12):
            errors.append("manifest minimum valid-area fraction changed")

    quality = manifest.get("quality", {})
    if quality.get("observation_count") != expected_observation_count:
        errors.append("manifest observation_count does not match expected panel size")
    if quality.get("monthly_diagnostic_count") != expected_monthly_count:
        errors.append("manifest monthly_diagnostic_count does not match expected panel size")
    if coverage_values:
        try:
            manifest_min = float(quality.get("minimum_monthly_valid_area_fraction"))
            manifest_max = float(quality.get("maximum_monthly_valid_area_fraction"))
        except (TypeError, ValueError):
            errors.append("manifest monthly coverage extrema are invalid")
        else:
            if not math.isclose(manifest_min, min(coverage_values), rel_tol=0.0, abs_tol=1e-9):
                errors.append("manifest minimum monthly valid-area fraction does not match diagnostics")
            if not math.isclose(manifest_max, max(coverage_values), rel_tol=0.0, abs_tol=1e-9):
                errors.append("manifest maximum monthly valid-area fraction does not match diagnostics")

    negative = manifest.get("negative_guards", {})
    for key in (
        "is_direct_station_observation",
        "uses_historical_boundary_geometry",
        "safe_to_interpret_big_june_2026_as_historical_boundary",
        "safe_to_equate_big_kdpkab_with_bps_code",
    ):
        if negative.get(key) is not False:
            errors.append(f"manifest negative guard {key} must remain false")

    outputs = manifest.get("outputs", {})
    for name in (OBSERVATIONS, MONTHLY, PROVENANCE):
        recorded = outputs.get(name, {})
        path = output_dir / name
        if recorded.get("bytes") != path.stat().st_size:
            errors.append(f"manifest byte size mismatch for {name}")
        if recorded.get("sha256") != sha256_file(path):
            errors.append(f"manifest SHA-256 mismatch for {name}")

    if start_year == 1981 and end_year == 2025:
        if expected_observation_count != 855 or expected_monthly_count != 10260:
            errors.append("full qualified CHIRPS panel cardinality contract changed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate materialized CHIRPS annual rainfall panel")
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    try:
        errors = validate(args.output_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CHIRPS rainfall panel validation FAILED: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("CHIRPS rainfall panel validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("CHIRPS rainfall panel validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
