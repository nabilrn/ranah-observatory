from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
EQUIVALENCE = ROOT / "data" / "validation" / "chirps" / "chirps-v3-2025-annual-monthly-equivalence.csv"

OBSERVATIONS = "chirps-v3-annual-rainfall-current-boundaries.csv"
DIAGNOSTICS = "chirps-v3-annual-zonal-diagnostics.csv"
SOURCE_ARTIFACTS = "chirps-v3-annual-source-artifacts.csv"
PROVENANCE = "chirps-v3-rainfall-provenance.csv"
MANIFEST = "chirps-v3-rainfall-panel.manifest.json"
GEOMETRY = "big_sumbar_boundaries_june_2026.source.geojson"

EXPECTED_INDICATOR = "annual_rainfall"
EXPECTED_UNIT = "millimetres"
EXPECTED_CLAIM = "model_estimate"
EXPECTED_METHOD = "chirps-v3-final-annual_fractional-area-v1"
EXPECTED_PROVENANCE_SOURCE = "chirps_v3"
EXPECTED_BIG_EDITION = "Juni 2026"
EXPECTED_EQUIVALENCE_REFERENCE = "data/validation/chirps/chirps-v3-2025-annual-monthly-equivalence.csv"
EXPECTED_EQUIVALENCE_ANNUAL_SHA = "e24f177b53c05eae36bf636b7ed42223948dce37350115ac157211f118b1e70c"
MIN_VALID_AREA_FRACTION = 0.98
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
        raise ValueError(
            f"canonical current Sumatera Barat geography count is {len(result)}, expected 19"
        )
    return result


def validate_equivalence_reference() -> tuple[list[str], float, float]:
    errors: list[str] = []
    rows = read_csv(EQUIVALENCE)
    canonical = current_sumbar_ids()
    ids = [row.get("geography_id", "") for row in rows]
    if len(rows) != 19 or set(ids) != canonical or len(ids) != len(set(ids)):
        errors.append("2025 annual-vs-monthly equivalence reference must cover exactly 19 canonical geographies")
    absolute_values: list[float] = []
    relative_values: list[float] = []
    for row in rows:
        try:
            absolute_values.append(float(row["absolute_difference_mm"]))
            relative_values.append(float(row["relative_difference_percent"]))
        except (KeyError, ValueError):
            errors.append("equivalence reference contains invalid difference values")
            break
    max_abs = max(absolute_values) if absolute_values else math.inf
    max_rel = max(relative_values) if relative_values else math.inf
    if max_abs >= 0.001:
        errors.append(f"annual-vs-monthly 2025 max absolute difference is too large: {max_abs}")
    if max_rel >= 0.0001:
        errors.append(f"annual-vs-monthly 2025 max relative difference is too large: {max_rel}")
    return errors, max_abs, max_rel


def validate(output_dir: Path) -> list[str]:
    errors: list[str] = []
    required = [OBSERVATIONS, DIAGNOSTICS, SOURCE_ARTIFACTS, PROVENANCE, MANIFEST, GEOMETRY]
    missing_files = [name for name in required if not (output_dir / name).is_file()]
    if missing_files:
        return [f"missing required panel files: {missing_files}"]

    equivalence_errors, equivalence_max_abs, equivalence_max_rel = validate_equivalence_reference()
    errors.extend(equivalence_errors)

    observations = read_csv(output_dir / OBSERVATIONS)
    diagnostics = read_csv(output_dir / DIAGNOSTICS)
    source_artifacts = read_csv(output_dir / SOURCE_ARTIFACTS)
    provenance = read_csv(output_dir / PROVENANCE)
    manifest = json.loads((output_dir / MANIFEST).read_text(encoding="utf-8"))
    canonical_ids = current_sumbar_ids()

    years = manifest.get("years", {})
    try:
        start_year = int(years["start"])
        end_year = int(years["end"])
        year_count = int(years["count"])
    except (KeyError, TypeError, ValueError):
        return errors + ["manifest years contract is invalid"]
    expected_years = set(range(start_year, end_year + 1))
    if start_year < 1981 or end_year > 2025 or start_year > end_year:
        errors.append(
            f"manifest year range {start_year}-{end_year} is outside qualified CHIRPS range 1981-2025"
        )
    if year_count != len(expected_years):
        errors.append("manifest year count does not match start/end range")

    expected_row_count = 19 * year_count
    if len(observations) != expected_row_count:
        errors.append(
            f"annual observation count is {len(observations)}, expected {expected_row_count}"
        )
    if len(diagnostics) != expected_row_count:
        errors.append(
            f"annual diagnostic count is {len(diagnostics)}, expected {expected_row_count}"
        )
    if len(source_artifacts) != year_count:
        errors.append(
            f"annual source-artifact count is {len(source_artifacts)}, expected {year_count}"
        )

    source_by_year: dict[int, dict[str, str]] = {}
    for row in source_artifacts:
        try:
            year = int(row.get("year", ""))
            byte_count = int(row.get("bytes", ""))
        except ValueError:
            errors.append("annual source-artifact row contains invalid year or byte count")
            continue
        if year in source_by_year:
            errors.append(f"duplicate source artifact for year {year}")
        source_by_year[year] = row
        if year not in expected_years:
            errors.append(f"source artifact year {year} is outside manifest range")
        url = row.get("source_url", "")
        expected_url = (
            "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs/"
            f"chirps-v3.0.{year:04d}.tif"
        )
        if url != expected_url:
            errors.append(f"unexpected annual CHIRPS source URL for {year}: {url!r}")
        sha = row.get("sha256", "")
        if not SHA256_RE.fullmatch(sha):
            errors.append(f"invalid SHA-256 for CHIRPS annual source {year}")
        if byte_count <= 1_000_000:
            errors.append(f"CHIRPS annual source {year} is implausibly small: {byte_count} bytes")
        if not row.get("retrieved_at", ""):
            errors.append(f"source artifact {year} is missing retrieved_at")
    if set(source_by_year) != expected_years:
        missing = sorted(expected_years - set(source_by_year))
        unexpected = sorted(set(source_by_year) - expected_years)
        errors.append(f"source-artifact year coverage mismatch; missing={missing} unexpected={unexpected}")

    diagnostic_by_key: dict[tuple[str, int], dict[str, str]] = {}
    coverage_values: list[float] = []
    rainfall_values: list[float] = []
    for row in diagnostics:
        geography_id = row.get("geography_id", "")
        if geography_id not in canonical_ids:
            errors.append(f"annual diagnostic uses noncanonical geography {geography_id!r}")
            continue
        try:
            year = int(row.get("year", ""))
            rainfall = float(row.get("annual_rainfall_mm", ""))
            coverage = float(row.get("valid_area_fraction", ""))
            valid_area = float(row.get("valid_weight_area_m2", ""))
            polygon_area = float(row.get("polygon_weight_area_m2", ""))
            valid_pixels = int(row.get("valid_pixel_intersections", ""))
            total_pixels = int(row.get("total_pixel_intersections", ""))
            source_bytes = int(row.get("source_bytes", ""))
        except ValueError:
            errors.append(f"invalid annual diagnostic numeric fields for geography {geography_id}")
            continue
        key = (geography_id, year)
        if key in diagnostic_by_key:
            errors.append(f"duplicate annual diagnostic key {key}")
        diagnostic_by_key[key] = row
        if year not in expected_years:
            errors.append(f"annual diagnostic year {year} is outside manifest range")
        if not math.isfinite(rainfall) or not 500.0 <= rainfall <= 10000.0:
            errors.append(f"annual rainfall is outside plausibility guard for {geography_id} {year}: {rainfall}")
        if not MIN_VALID_AREA_FRACTION <= coverage <= 1.001:
            errors.append(f"invalid valid-area fraction for {geography_id} {year}: {coverage}")
        if not 0 < valid_area <= polygon_area * 1.001:
            errors.append(f"invalid area accounting for {geography_id} {year}")
        if not 0 < valid_pixels <= total_pixels:
            errors.append(f"invalid pixel accounting for {geography_id} {year}")
        coverage_values.append(coverage)
        rainfall_values.append(rainfall)
        source = source_by_year.get(year)
        if source:
            if row.get("source_url") != source.get("source_url"):
                errors.append(f"diagnostic/source URL mismatch for {geography_id} {year}")
            if row.get("source_sha256") != source.get("sha256"):
                errors.append(f"diagnostic/source SHA mismatch for {geography_id} {year}")
            if source_bytes != int(source.get("bytes", "0")):
                errors.append(f"diagnostic/source byte-count mismatch for {geography_id} {year}")

    expected_keys = {
        (geography_id, year)
        for geography_id in canonical_ids
        for year in expected_years
    }
    if set(diagnostic_by_key) != expected_keys:
        missing = sorted(expected_keys - set(diagnostic_by_key))
        unexpected = sorted(set(diagnostic_by_key) - expected_keys)
        errors.append(
            f"annual diagnostic geography-year coverage mismatch; missing={missing[:5]} unexpected={unexpected[:5]}"
        )

    observation_ids: set[str] = set()
    observation_keys: set[tuple[str, int]] = set()
    provenance_ids: set[str] = set()
    for row in observations:
        observation_id = row.get("observation_id", "")
        if not observation_id:
            errors.append("annual observation contains blank observation_id")
        elif observation_id in observation_ids:
            errors.append(f"duplicate annual observation_id {observation_id}")
        observation_ids.add(observation_id)
        geography_id = row.get("geography_id", "")
        if geography_id not in canonical_ids:
            errors.append(f"annual observation uses noncanonical geography {geography_id!r}")
            continue
        try:
            year = int(row.get("time_start", "")[:4])
            value = float(row.get("value_numeric", ""))
        except ValueError:
            errors.append(f"invalid annual observation year/value for geography {geography_id}")
            continue
        key = (geography_id, year)
        if key in observation_keys:
            errors.append(f"duplicate annual observation geography-year key {key}")
        observation_keys.add(key)
        if row.get("time_start") != f"{year:04d}-01-01" or row.get("time_end") != f"{year:04d}-12-31":
            errors.append(f"annual time bounds are not calendar-year bounds for {geography_id} {year}")
        if row.get("frequency") != "annual":
            errors.append(f"unexpected frequency for {geography_id} {year}: {row.get('frequency')!r}")
        if row.get("indicator_id") != EXPECTED_INDICATOR:
            errors.append(f"unexpected indicator for {geography_id} {year}")
        if row.get("unit") != EXPECTED_UNIT:
            errors.append(f"unexpected unit for {geography_id} {year}")
        if row.get("claim_type") != EXPECTED_CLAIM:
            errors.append(f"CHIRPS row must remain model_estimate for {geography_id} {year}")
        if row.get("methodology_version") != EXPECTED_METHOD:
            errors.append(f"unexpected methodology version for {geography_id} {year}")
        if row.get("suppressed") != "false" or row.get("comparable") != "true":
            errors.append(f"unexpected suppression/comparability flags for {geography_id} {year}")
        notes = row.get("notes", "")
        for phrase in (
            "CHIRPS v3 Final annual",
            "current-boundary reconstruction",
            "model_estimate",
            f"BIG {EXPECTED_BIG_EDITION}",
        ):
            if phrase not in notes:
                errors.append(f"annual observation notes missing {phrase!r} for {geography_id} {year}")
        diagnostic = diagnostic_by_key.get(key)
        if diagnostic:
            diagnostic_value = float(diagnostic["annual_rainfall_mm"])
            if not math.isclose(value, round(diagnostic_value, 3), rel_tol=0.0, abs_tol=0.0005):
                errors.append(f"observation/diagnostic rainfall mismatch for {geography_id} {year}")
        provenance_id = row.get("provenance_id", "")
        if provenance_id:
            provenance_ids.add(provenance_id)
        else:
            errors.append(f"annual observation has blank provenance_id for {geography_id} {year}")
    if observation_keys != expected_keys:
        missing = sorted(expected_keys - observation_keys)
        unexpected = sorted(observation_keys - expected_keys)
        errors.append(
            f"annual observation geography-year coverage mismatch; missing={missing[:5]} unexpected={unexpected[:5]}"
        )

    if len(provenance) != 1:
        errors.append(f"expected one panel provenance row, found {len(provenance)}")
    else:
        prov = provenance[0]
        if prov.get("source_id") != EXPECTED_PROVENANCE_SOURCE:
            errors.append(f"unexpected provenance source_id {prov.get('source_id')!r}")
        if prov.get("source_release") != "CHIRPS v3 Final annual":
            errors.append("provenance source_release must remain CHIRPS v3 Final annual")
        if prov.get("extraction_method") != "derived":
            errors.append("CHIRPS panel provenance extraction_method must remain derived")
        if prov.get("transform_revision") != EXPECTED_METHOD:
            errors.append("CHIRPS panel provenance transform revision changed")
        if prov.get("provenance_id", "") not in provenance_ids or len(provenance_ids) != 1:
            errors.append("annual observation provenance IDs do not resolve uniquely to panel provenance")
        if "annual/global/tifs/chirps-v3.0.YYYY.tif" not in prov.get("artifact_locator", ""):
            errors.append("panel provenance must retain annual CHIRPS TIFF artifact pattern")
        if prov.get("checksum_sha256") != sha256_file(output_dir / SOURCE_ARTIFACTS):
            errors.append("provenance checksum must equal source-artifact manifest SHA-256")

    if manifest.get("panel_version") != 2:
        errors.append("manifest panel_version must be 2 for annual-source materialization")
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
    if geography.get("raw_geojson_sha256") != sha256_file(output_dir / GEOMETRY):
        errors.append("manifest BIG raw GeoJSON checksum does not match output")

    chirps = manifest.get("chirps", {})
    if chirps.get("source") != "CHIRPS v3 Final annual":
        errors.append("manifest CHIRPS source must remain Final annual")
    if chirps.get("annual_raster_count") != year_count:
        errors.append("manifest annual_raster_count does not match year range")
    if chirps.get("annual_tif_base") != "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/annual/global/tifs":
        errors.append("manifest annual_tif_base changed")
    transport = chirps.get("transport", {})
    if transport.get("mode") != "sequential_full_download":
        errors.append("manifest transport mode must remain sequential_full_download")
    if transport.get("source_level_sha256") is not True:
        errors.append("manifest must retain source-level SHA-256 for annual TIFFs")
    try:
        delay = float(transport.get("polite_inter_request_delay_seconds"))
    except (TypeError, ValueError):
        errors.append("manifest inter-request delay is invalid")
    else:
        if delay < 1.0:
            errors.append("annual bulk transport must retain at least a 1-second inter-request delay")

    method = manifest.get("method", {})
    if method.get("revision") != EXPECTED_METHOD:
        errors.append("manifest method revision changed")
    if method.get("weight_crs") != "EPSG:6933":
        errors.append("manifest weight CRS must remain EPSG:6933")
    if method.get("pixel_weighting") != "fractional polygon-pixel intersection area":
        errors.append("manifest pixel weighting changed")
    if method.get("annual_statistic") != "area-weighted spatial mean of official CHIRPS annual precipitation raster":
        errors.append("manifest annual statistic changed")
    try:
        manifest_min_coverage = float(method.get("minimum_required_valid_area_fraction"))
    except (TypeError, ValueError):
        errors.append("manifest minimum valid-area fraction is invalid")
    else:
        if not math.isclose(manifest_min_coverage, MIN_VALID_AREA_FRACTION, abs_tol=1e-12):
            errors.append("manifest minimum valid-area fraction changed")

    equivalence = manifest.get("cross_granularity_validation", {})
    if equivalence.get("reference") != EXPECTED_EQUIVALENCE_REFERENCE:
        errors.append("manifest annual-vs-monthly equivalence reference changed")
    if equivalence.get("year") != 2025:
        errors.append("manifest equivalence year must remain 2025")
    if equivalence.get("annual_tif_sha256") != EXPECTED_EQUIVALENCE_ANNUAL_SHA:
        errors.append("manifest 2025 annual TIFF equivalence checksum changed")
    try:
        manifest_eq_abs = float(equivalence.get("max_absolute_difference_mm"))
        manifest_eq_rel = float(equivalence.get("max_relative_difference_percent"))
    except (TypeError, ValueError):
        errors.append("manifest equivalence metrics are invalid")
    else:
        if not math.isclose(manifest_eq_abs, equivalence_max_abs, rel_tol=0.0, abs_tol=1e-9):
            errors.append("manifest max absolute equivalence difference does not match evidence table")
        if not math.isclose(manifest_eq_rel, equivalence_max_rel, rel_tol=0.0, abs_tol=1e-12):
            errors.append("manifest max relative equivalence difference does not match evidence table")

    quality = manifest.get("quality", {})
    if quality.get("observation_count") != expected_row_count:
        errors.append("manifest observation_count does not match panel size")
    if quality.get("annual_diagnostic_count") != expected_row_count:
        errors.append("manifest annual_diagnostic_count does not match panel size")
    if quality.get("source_artifact_count") != year_count:
        errors.append("manifest source_artifact_count does not match year count")
    if coverage_values:
        if not math.isclose(
            float(quality.get("minimum_valid_area_fraction")),
            min(coverage_values),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            errors.append("manifest minimum valid-area fraction does not match diagnostics")
        if not math.isclose(
            float(quality.get("maximum_valid_area_fraction")),
            max(coverage_values),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            errors.append("manifest maximum valid-area fraction does not match diagnostics")
    if rainfall_values:
        if not math.isclose(
            float(quality.get("minimum_annual_rainfall_mm")),
            min(round(value, 3) for value in rainfall_values),
            rel_tol=0.0,
            abs_tol=0.001,
        ):
            errors.append("manifest minimum annual rainfall does not match observations")
        if not math.isclose(
            float(quality.get("maximum_annual_rainfall_mm")),
            max(round(value, 3) for value in rainfall_values),
            rel_tol=0.0,
            abs_tol=0.001,
        ):
            errors.append("manifest maximum annual rainfall does not match observations")

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
    for name in (OBSERVATIONS, DIAGNOSTICS, SOURCE_ARTIFACTS, PROVENANCE):
        recorded = outputs.get(name, {})
        path = output_dir / name
        if recorded.get("bytes") != path.stat().st_size:
            errors.append(f"manifest byte size mismatch for {name}")
        if recorded.get("sha256") != sha256_file(path):
            errors.append(f"manifest SHA-256 mismatch for {name}")

    if start_year == 1981 and end_year == 2025:
        if expected_row_count != 855 or year_count != 45:
            errors.append("full qualified CHIRPS panel cardinality contract changed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate materialized CHIRPS annual rainfall panel"
    )
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
