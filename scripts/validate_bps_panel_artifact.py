#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "data" / "manifests" / "bps_panel_baseline.json"
PANEL_REGISTRY = ROOT / "data" / "registries" / "bps_panel_series.csv"
GEOGRAPHY_MAP = ROOT / "data" / "registries" / "bps_panel_geography_map.csv"


def _read_csv(path: Path) -> list[dict[str, str]]:
    import csv

    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _is_sha256(value: object) -> bool:
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
    registry = _read_csv(PANEL_REGISTRY)
    geography_map = _read_csv(GEOGRAPHY_MAP)

    if baseline.get("schema") != "ranah-observatory/bps-panel-baseline/v1":
        errors.append("unexpected BPS panel baseline schema")
    if baseline.get("source_id") != "bps_webapi" or baseline.get("domain") != "1300":
        errors.append("baseline must identify BPS WebAPI domain 1300")
    if not _is_sha256(baseline.get("panel_csv_sha256")):
        errors.append("baseline panel_csv_sha256 is not a valid SHA-256")
    if not _is_sha256(baseline.get("semantic_fingerprint_sha256")):
        errors.append("baseline semantic_fingerprint_sha256 is not a valid SHA-256")

    expected_excludes = {"retrieved_at_utc", "source_snapshot", "source_snapshot_sha256"}
    if set(baseline.get("semantic_fingerprint_excludes", [])) != expected_excludes:
        errors.append("semantic fingerprint volatile-field exclusions changed unexpectedly")

    if baseline.get("series_count") != len(registry):
        errors.append("baseline series_count does not match bps_panel_series.csv")
    if baseline.get("row_count") != 1240:
        errors.append("first BPS panel baseline must contain 1240 source-native rows")
    if baseline.get("canonical_geography_count") != 20:
        errors.append("first BPS panel baseline must cover 20 canonical Sumatera Barat geographies")

    mapping_counts = baseline.get("geography_mapping_counts")
    if mapping_counts != {
        "qualified_current_code": 1178,
        "qualified_source_aggregate_alias": 62,
    }:
        errors.append("baseline geography mapping counts differ from qualified first-panel contract")

    baseline_series = baseline.get("series")
    if not isinstance(baseline_series, list):
        errors.append("baseline series must be a list")
        baseline_series = []
    by_id = {
        str(row.get("panel_series_id", "")): row
        for row in baseline_series
        if isinstance(row, dict)
    }
    if len(by_id) != len(baseline_series):
        errors.append("baseline contains duplicate or invalid panel_series_id values")

    expected_total_rows = 0
    for config in registry:
        series_id = config["panel_series_id"]
        row = by_id.get(series_id)
        if row is None:
            errors.append(f"baseline missing panel series {series_id}")
            continue
        expected_rows = (int(config["target_end_year"]) - int(config["target_start_year"]) + 1) * 20
        expected_total_rows += expected_rows
        expected = {
            "indicator_id": config["indicator_id"],
            "bps_var_id": int(config["bps_var_id"]),
            "selected_turvar_id": int(config["selected_turvar_id"]),
            "period_start": int(config["target_start_year"]),
            "period_end": int(config["target_end_year"]),
            "rows": expected_rows,
            "canonical_promotion_status": config["canonical_promotion_status"],
        }
        for field, expected_value in expected.items():
            if row.get(field) != expected_value:
                errors.append(
                    f"{series_id}: baseline {field}={row.get(field)!r}, expected {expected_value!r}"
                )
        last_update = row.get("source_last_update")
        if not isinstance(last_update, str) or not last_update.strip():
            errors.append(f"{series_id}: source_last_update is required in frozen baseline")

    if expected_total_rows != baseline.get("row_count"):
        errors.append(
            f"registry-derived row count {expected_total_rows} does not match baseline row_count {baseline.get('row_count')}"
        )

    if len(geography_map) != 21:
        errors.append("first-panel geography map must contain 19 local codes plus two province aliases")

    acquisition = baseline.get("acquisition")
    if not isinstance(acquisition, dict):
        errors.append("baseline acquisition provenance is required")
    else:
        if acquisition.get("workflow") != "BPS Normalized Panel Harvest":
            errors.append("unexpected baseline acquisition workflow")
        if not isinstance(acquisition.get("workflow_run_id"), int):
            errors.append("baseline workflow_run_id must be an integer")
        if not isinstance(acquisition.get("artifact_id"), int):
            errors.append("baseline artifact_id must be an integer")
        artifact_digest = acquisition.get("artifact_digest")
        if not isinstance(artifact_digest, str) or not artifact_digest.startswith("sha256:") or not _is_sha256(artifact_digest[7:]):
            errors.append("baseline artifact_digest must be a sha256: digest")
        head_sha = acquisition.get("head_sha")
        if not isinstance(head_sha, str) or len(head_sha) != 40:
            errors.append("baseline acquisition head_sha must be a 40-character Git commit SHA")

    return errors, {
        "series": len(baseline_series),
        "rows": int(baseline.get("row_count", 0) or 0),
        "geographies": int(baseline.get("canonical_geography_count", 0) or 0),
    }


def main() -> int:
    try:
        errors, counts = validate()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BPS panel baseline validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS panel baseline validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS panel baseline validation passed: "
        f"{counts['series']} series, {counts['rows']} rows, {counts['geographies']} canonical geographies."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
