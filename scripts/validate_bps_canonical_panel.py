#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

EXPECTED_SERIES_ROWS = {
    "labor_tpt_regency": 160,
    "labor_tpak_regency": 160,
    "hdi_expected_schooling": 160,
    "hdi_mean_schooling": 160,
    "hdi_life_expectancy_lfsp2020": 120,
    "poverty_headcount_regency": 160,
    "real_grdp_growth_regency": 160,
}
EXPECTED_INDICATORS = {
    "unemployment_rate",
    "labor_force_participation",
    "expected_years_schooling",
    "mean_years_schooling",
    "life_expectancy",
    "poverty_rate",
    "real_grdp_growth",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(directory: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    observations_path = directory / "bps-canonical-observations.csv"
    provenance_path = directory / "bps-canonical-provenance.csv"
    manifest_path = directory / "bps-canonical-panel.manifest.json"

    for path in (observations_path, provenance_path, manifest_path):
        if not path.is_file():
            errors.append(f"missing canonical panel artifact: {path.name}")
    if errors:
        return errors, {"observations": 0, "provenance": 0, "indicators": 0, "geographies": 0}

    observations = _read_csv(observations_path)
    provenance = _read_csv(provenance_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema") != "ranah-observatory/bps-canonical-panel/v1":
        errors.append("unexpected canonical panel manifest schema")
    if manifest.get("source_id") != "bps_webapi":
        errors.append("canonical panel source_id must be bps_webapi")
    if manifest.get("observation_count") != 1080 or len(observations) != 1080:
        errors.append(
            f"expected 1080 canonical observations, manifest={manifest.get('observation_count')} csv={len(observations)}"
        )
    if manifest.get("provenance_count") != 54 or len(provenance) != 54:
        errors.append(
            f"expected 54 provenance records, manifest={manifest.get('provenance_count')} csv={len(provenance)}"
        )
    if manifest.get("canonical_series_count") != 7:
        errors.append("canonical panel must contain exactly 7 promoted source series")
    if manifest.get("held_series") != ["internet_person_5plus"]:
        errors.append("person-level internet source must be the only held series")
    if manifest.get("series_rows") != EXPECTED_SERIES_ROWS:
        errors.append(f"canonical series row counts differ from reviewed contract: {manifest.get('series_rows')!r}")
    if manifest.get("observations_sha256") != _sha256(observations_path):
        errors.append("canonical observation checksum mismatch")
    if manifest.get("provenance_sha256") != _sha256(provenance_path):
        errors.append("canonical provenance checksum mismatch")

    observation_ids = [row["observation_id"] for row in observations]
    if len(observation_ids) != len(set(observation_ids)):
        errors.append("canonical observation IDs are not unique")
    provenance_ids = [row["provenance_id"] for row in provenance]
    if len(provenance_ids) != len(set(provenance_ids)):
        errors.append("canonical provenance IDs are not unique")
    provenance_set = set(provenance_ids)
    unresolved = sorted({row["provenance_id"] for row in observations} - provenance_set)
    if unresolved:
        errors.append(f"canonical observations reference missing provenance IDs: {unresolved[:5]}")

    indicators = {row["indicator_id"] for row in observations}
    if indicators != EXPECTED_INDICATORS:
        errors.append(f"canonical indicator membership changed: {sorted(indicators)}")
    if any(row["indicator_id"] == "internet_access" for row in observations):
        errors.append("held person-level internet source leaked into canonical observations")

    geographies = {row["geography_id"] for row in observations}
    if len(geographies) != 20:
        errors.append(f"canonical observations must cover 20 Sumatera Barat geographies, found {len(geographies)}")

    units_by_indicator: dict[str, set[str]] = {}
    for row in observations:
        units_by_indicator.setdefault(row["indicator_id"], set()).add(row["unit"])
        if row["claim_type"] != "observed":
            errors.append(f"{row['observation_id']}: canonical BPS value must retain claim_type=observed")
        if row["suppressed"] != "false":
            errors.append(f"{row['observation_id']}: unexpected suppression flag")
        try:
            float(row["value_numeric"])
        except ValueError:
            errors.append(f"{row['observation_id']}: value_numeric is not numeric")

    for indicator in {"unemployment_rate", "labor_force_participation", "poverty_rate", "real_grdp_growth"}:
        if units_by_indicator.get(indicator) != {"percent"}:
            errors.append(f"{indicator}: canonical unit must be percent")
    for indicator in {"expected_years_schooling", "mean_years_schooling", "life_expectancy"}:
        if units_by_indicator.get(indicator) != {"years"}:
            errors.append(f"{indicator}: canonical unit must be years")

    for row in observations:
        year = int(row["time_start"][:4])
        indicator = row["indicator_id"]
        if indicator in {"unemployment_rate", "labor_force_participation"}:
            if row["time_start"] != f"{year}-08-01" or row["time_end"] != f"{year}-08-31":
                errors.append(f"{row['observation_id']}: labor observation must use August reference month")
            if row["comparable"]:
                errors.append(
                    f"{row['observation_id']}: labor cross-regime comparability must remain unresolved pending weighting lineage"
                )
        elif indicator in {"expected_years_schooling", "mean_years_schooling", "poverty_rate"}:
            if row["time_start"] != f"{year}-03-01" or row["time_end"] != f"{year}-03-31":
                errors.append(f"{row['observation_id']}: Susenas-derived observation must use March reference month")
            if row["comparable"] != "true":
                errors.append(f"{row['observation_id']}: expected comparable=true")
        elif indicator in {"life_expectancy", "real_grdp_growth"}:
            if row["time_start"] != f"{year}-01-01" or row["time_end"] != f"{year}-12-31":
                errors.append(f"{row['observation_id']}: annual observation has incorrect calendar-year bounds")
            if row["comparable"] != "true":
                errors.append(f"{row['observation_id']}: expected comparable=true")

        if indicator == "life_expectancy" and "LF-SP2020" not in row["methodology_version"]:
            errors.append(f"{row['observation_id']}: life expectancy must retain LF-SP2020 methodology version")
        if indicator == "real_grdp_growth":
            if row["price_basis"] != "constant_2010":
                errors.append(f"{row['observation_id']}: GRDP growth must retain constant_2010 price basis")
            notes = row["notes"]
            if year == 2024 and "release_status=very_provisional" not in notes:
                errors.append(f"{row['observation_id']}: missing 2024 GRDP provisional flag")
            if year == 2025 and "release_status=very_very_provisional" not in notes:
                errors.append(f"{row['observation_id']}: missing 2025 GRDP provisional flag")

    if Counter(row["indicator_id"] for row in observations)["life_expectancy"] != 120:
        errors.append("life expectancy canonical family must contain 120 observations (20 geographies x 6 years)")

    for row in provenance:
        if row["source_id"] != "bps_webapi":
            errors.append(f"{row['provenance_id']}: unexpected source_id")
        if row["extraction_method"] != "api":
            errors.append(f"{row['provenance_id']}: extraction_method must be api")
        if not row["artifact_locator"].startswith("bps-webapi://domain/1300/var/"):
            errors.append(f"{row['provenance_id']}: malformed BPS artifact locator")
        if len(row["checksum_sha256"]) != 64:
            errors.append(f"{row['provenance_id']}: snapshot checksum is not SHA-256 length")
        try:
            int(row["checksum_sha256"], 16)
        except ValueError:
            errors.append(f"{row['provenance_id']}: snapshot checksum is not hexadecimal")
        if not row["source_release"]:
            errors.append(f"{row['provenance_id']}: BPS source last_update is required")

    return errors, {
        "observations": len(observations),
        "provenance": len(provenance),
        "indicators": len(indicators),
        "geographies": len(geographies),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the generated evidence-qualified BPS canonical panel.")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        errors, counts = validate(args.directory)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BPS canonical panel validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS canonical panel validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS canonical panel validation passed: "
        f"{counts['observations']} observations, {counts['provenance']} provenance records, "
        f"{counts['indicators']} indicators, {counts['geographies']} geographies."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
