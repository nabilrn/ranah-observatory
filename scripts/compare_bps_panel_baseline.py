#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "data" / "manifests" / "bps_panel_baseline.json"


def _series_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("series")
    if not isinstance(rows, list):
        raise ValueError("manifest series must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("manifest series contains a non-object entry")
        series_id = str(item.get("panel_series_id", "")).strip()
        if not series_id or series_id in result:
            raise ValueError("manifest series contains a missing or duplicate panel_series_id")
        result[series_id] = item
    return result


def compare(baseline: dict[str, Any], generated: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    baseline_fingerprint = str(baseline.get("semantic_fingerprint_sha256", ""))
    generated_fingerprint = str(generated.get("semantic_fingerprint_sha256", ""))
    if baseline_fingerprint != generated_fingerprint:
        errors.append(
            "semantic fingerprint changed: "
            f"baseline={baseline_fingerprint or 'missing'} generated={generated_fingerprint or 'missing'}"
        )

    for field in ("source_id", "series_count", "row_count"):
        if baseline.get(field) != generated.get(field):
            errors.append(
                f"{field} changed: baseline={baseline.get(field)!r} generated={generated.get(field)!r}"
            )

    baseline_series = _series_by_id(baseline)
    generated_series = _series_by_id(generated)
    if set(baseline_series) != set(generated_series):
        errors.append(
            "series membership changed: "
            f"baseline={sorted(baseline_series)} generated={sorted(generated_series)}"
        )
        return errors

    for series_id in sorted(baseline_series):
        expected = baseline_series[series_id]
        actual = generated_series[series_id]
        comparisons = {
            "indicator_id": actual.get("indicator_id"),
            "bps_var_id": actual.get("bps_var_id"),
            "selected_turvar_id": actual.get("selected_turvar_id"),
            "rows": actual.get("rows"),
            "canonical_promotion_status": actual.get("canonical_promotion_status"),
        }
        for field, actual_value in comparisons.items():
            if expected.get(field) != actual_value:
                errors.append(
                    f"{series_id}: {field} changed from {expected.get(field)!r} to {actual_value!r}"
                )

        expected_period_start = expected.get("period_start")
        expected_period_end = expected.get("period_end")
        periods = actual.get("periods")
        if not isinstance(periods, list) or not periods:
            errors.append(f"{series_id}: generated period list is missing")
        else:
            try:
                actual_start = int(str(periods[0]))
                actual_end = int(str(periods[-1]))
            except ValueError:
                errors.append(f"{series_id}: generated period labels are not integer years")
            else:
                if expected_period_start != actual_start or expected_period_end != actual_end:
                    errors.append(
                        f"{series_id}: period window changed from {expected_period_start}-{expected_period_end} "
                        f"to {actual_start}-{actual_end}"
                    )

        expected_update = expected.get("source_last_update")
        actual_updates = actual.get("source_last_updates")
        if actual_updates != [expected_update]:
            errors.append(
                f"{series_id}: BPS source last_update changed from {expected_update!r} to {actual_updates!r}"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a fresh BPS source-native panel differs semantically from its reviewed baseline."
    )
    parser.add_argument("generated_manifest", type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        generated = json.loads(args.generated_manifest.read_text(encoding="utf-8"))
        errors = compare(baseline, generated)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BPS panel baseline comparison FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS panel semantic drift detected", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(
            "Inspect BPS source revisions and qualification implications before updating the committed baseline.",
            file=sys.stderr,
        )
        return 1
    print("BPS panel semantic fingerprint matches the reviewed baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
