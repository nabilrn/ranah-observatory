#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from fingerprint_bps_expansion import read_rows, semantic_fingerprint

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "data" / "manifests" / "bps_expansion_baseline.json"


def compare(source_panel: Path, canonical_manifest_path: Path, baseline_path: Path = DEFAULT_BASELINE) -> list[str]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    canonical = json.loads(canonical_manifest_path.read_text(encoding="utf-8"))
    rows = read_rows(source_panel)
    errors: list[str] = []

    fingerprint = semantic_fingerprint(rows)
    if fingerprint != baseline.get("semantic_fingerprint_sha256"):
        errors.append(
            "semantic fingerprint changed: "
            f"baseline={baseline.get('semantic_fingerprint_sha256')} fresh={fingerprint}"
        )
    if len(rows) != baseline.get("source_row_count"):
        errors.append(f"source row count changed: baseline={baseline.get('source_row_count')} fresh={len(rows)}")
    expected_canonical = baseline.get("canonical_observation_count")
    if canonical.get("observation_count") != expected_canonical:
        errors.append(
            f"canonical observation count changed: baseline={expected_canonical} fresh={canonical.get('observation_count')}"
        )
    expected_held = baseline.get("held_source_native_count")
    if canonical.get("held_source_native_count") != expected_held:
        errors.append(
            f"held row count changed: baseline={expected_held} fresh={canonical.get('held_source_native_count')}"
        )
    expected_prov = baseline.get("canonical_provenance_count")
    if canonical.get("provenance_count") != expected_prov:
        errors.append(
            f"provenance count changed: baseline={expected_prov} fresh={canonical.get('provenance_count')}"
        )

    baseline_series = {
        item["expansion_series_id"]: item
        for item in baseline.get("series", [])
        if isinstance(item, dict) and item.get("expansion_series_id")
    }
    rows_by_series: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for row in rows:
        rows_by_series[row["expansion_series_id"]].append(row)
    if set(rows_by_series) != set(baseline_series):
        errors.append(
            f"source series membership changed: baseline={sorted(baseline_series)} fresh={sorted(rows_by_series)}"
        )
        return errors

    canonical_counts = canonical.get("series_rows", {})
    held_series = set(canonical.get("held_series", []))
    for series_id, expected in sorted(baseline_series.items()):
        fresh = rows_by_series[series_id]
        if len(fresh) != expected.get("source_rows"):
            errors.append(
                f"{series_id}: source rows changed from {expected.get('source_rows')} to {len(fresh)}"
            )
        years = sorted({int(row["bps_th_label"]) for row in fresh})
        if not years or years[0] != expected.get("period_start") or years[-1] != expected.get("period_end"):
            errors.append(
                f"{series_id}: period window changed from {expected.get('period_start')}-{expected.get('period_end')} "
                f"to {years[0] if years else 'missing'}-{years[-1] if years else 'missing'}"
            )
        updates = sorted({row["bps_last_update"] for row in fresh})
        if updates != [expected.get("source_last_update")]:
            errors.append(
                f"{series_id}: BPS last_update changed from {expected.get('source_last_update')!r} to {updates!r}"
            )
        if canonical_counts.get(series_id) != expected.get("canonical_rows"):
            errors.append(
                f"{series_id}: canonical rows changed from {expected.get('canonical_rows')} "
                f"to {canonical_counts.get(series_id)}"
            )
        expected_held_rows = int(expected.get("held_rows", 0))
        if expected_held_rows and series_id not in held_series:
            errors.append(f"{series_id}: expected held source-native rows disappeared")
        if not expected_held_rows and series_id in held_series:
            errors.append(f"{series_id}: unexpectedly entered held-source set")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare a fresh BPS structural expansion harvest to the reviewed semantic baseline.")
    parser.add_argument("source_panel", type=Path)
    parser.add_argument("canonical_manifest", type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        errors = compare(args.source_panel, args.canonical_manifest, args.baseline)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BPS expansion baseline comparison FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS structural expansion semantic drift detected", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print("Review source revisions before updating the committed expansion baseline.", file=sys.stderr)
        return 1
    print("BPS structural expansion matches the reviewed semantic baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
