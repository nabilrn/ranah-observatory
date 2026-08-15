#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "manifests" / "bps_expansion_baseline.json"
SERIES = ROOT / "data" / "registries" / "bps_expansion_series.csv"

EXPECTED_COUNTS = {
    "source_row_count": 726,
    "canonical_observation_count": 574,
    "held_source_native_count": 152,
    "canonical_provenance_count": 36,
}
EXPECTED_SOURCE_ROWS = {
    "underemployment_regency": 140,
    "inequality_gini": 160,
    "agriculture_share_adhb": 120,
    "manufacturing_share_adhb": 120,
    "rice_yield_ksa": 160,
    "export_value_port_loading": 6,
    "population_sp2020": 20,
}
EXPECTED_CANONICAL_ROWS = {
    "underemployment_regency": 140,
    "inequality_gini": 8,
    "agriculture_share_adhb": 120,
    "manufacturing_share_adhb": 120,
    "rice_yield_ksa": 160,
    "export_value_port_loading": 6,
    "population_sp2020": 20,
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    series = {row["expansion_series_id"]: row for row in _read_csv(SERIES)}

    if baseline.get("schema") != "ranah-observatory/bps-expansion-baseline/v1":
        errors.append("unexpected expansion baseline schema")
    if baseline.get("source_id") != "bps_webapi" or baseline.get("domain") != "1300":
        errors.append("expansion baseline must identify BPS WebAPI domain 1300")
    for field, expected in EXPECTED_COUNTS.items():
        if baseline.get(field) != expected:
            errors.append(f"baseline {field}={baseline.get(field)!r}, expected {expected}")
    for field in (
        "semantic_fingerprint_sha256",
        "reviewed_source_panel_sha256",
        "reviewed_canonical_observations_sha256",
        "reviewed_canonical_provenance_sha256",
        "reviewed_held_source_native_sha256",
    ):
        if not _sha256(baseline.get(field)):
            errors.append(f"baseline {field} is not a valid SHA-256")
    if set(baseline.get("semantic_fingerprint_excludes", [])) != {
        "retrieved_at_utc", "source_snapshot", "source_snapshot_sha256"
    }:
        errors.append("expansion semantic fingerprint exclusions changed unexpectedly")

    baseline_series_raw = baseline.get("series")
    if not isinstance(baseline_series_raw, list):
        errors.append("baseline series must be a list")
        baseline_series_raw = []
    baseline_series = {
        str(item.get("expansion_series_id", "")): item
        for item in baseline_series_raw
        if isinstance(item, dict) and item.get("expansion_series_id")
    }
    if set(baseline_series) != set(series):
        errors.append(
            f"baseline/registry series mismatch: baseline={sorted(baseline_series)} registry={sorted(series)}"
        )

    for series_id, config in series.items():
        item = baseline_series.get(series_id)
        if item is None:
            continue
        expected = {
            "bps_var_id": int(config["bps_var_id"]),
            "period_start": int(config["target_start_year"]),
            "period_end": int(config["target_end_year"]),
            "source_rows": EXPECTED_SOURCE_ROWS[series_id],
            "canonical_rows": EXPECTED_CANONICAL_ROWS[series_id],
            "held_rows": 152 if series_id == "inequality_gini" else 0,
        }
        for field, expected_value in expected.items():
            if item.get(field) != expected_value:
                errors.append(
                    f"{series_id}: baseline {field}={item.get(field)!r}, expected {expected_value!r}"
                )
        if not isinstance(item.get("source_last_update"), str) or not item.get("source_last_update", "").strip():
            errors.append(f"{series_id}: source_last_update is required")

    acquisition = baseline.get("acquisition")
    if not isinstance(acquisition, dict):
        errors.append("baseline acquisition provenance is required")
    else:
        if acquisition.get("workflow") != "BPS Structural Expansion Harvest":
            errors.append("unexpected expansion acquisition workflow")
        if not isinstance(acquisition.get("workflow_run_id"), int) or acquisition.get("workflow_run_id", 0) <= 0:
            errors.append("expansion workflow_run_id must be a positive integer")
        if not isinstance(acquisition.get("artifact_id"), int) or acquisition.get("artifact_id", 0) <= 0:
            errors.append("expansion artifact_id must be a positive integer")
        if not _sha256(acquisition.get("artifact_digest_sha256")):
            errors.append("expansion artifact_digest_sha256 must be a valid SHA-256")
        if not acquisition.get("review_note"):
            errors.append("expansion baseline requires a review note")

    return errors, {
        "series": len(baseline_series),
        "source": int(baseline.get("source_row_count", 0) or 0),
        "canonical": int(baseline.get("canonical_observation_count", 0) or 0),
        "held": int(baseline.get("held_source_native_count", 0) or 0),
    }


def main() -> int:
    try:
        errors, counts = validate()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BPS expansion baseline validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS expansion baseline validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS expansion baseline validation passed: "
        f"{counts['series']} series, {counts['source']} source rows, "
        f"{counts['canonical']} canonical, {counts['held']} held."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
