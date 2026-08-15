#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "registries" / "bps_panel_series.csv"


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def build_held(source_panel: Path, registry: Path = DEFAULT_REGISTRY) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows = _read(source_panel)
    configs = {row["panel_series_id"]: row for row in _read(registry)}
    held_series = {
        series_id
        for series_id, config in configs.items()
        if config["canonical_promotion_status"] != "canonical_ready"
    }
    held = [row for row in rows if row["panel_series_id"] in held_series]
    if held_series != {"internet_person_5plus"}:
        raise ValueError(f"unexpected held-series set: {sorted(held_series)}")
    if len(held) != 160:
        raise ValueError(f"expected 160 held source-native rows, found {len(held)}")
    if {row["indicator_id"] for row in held} != {"internet_access"}:
        raise ValueError("held panel contains a non-internet canonical indicator mapping")
    if {row["bps_var_id"] for row in held} != {"320"} or {row["bps_turvar_id"] for row in held} != {"595"}:
        raise ValueError("held internet panel no longer represents BPS var 320 / turvar 595")
    if len({row["canonical_geography_id"] for row in held}) != 20:
        raise ValueError("held internet panel must cover 20 canonical geographies")
    if {row["bps_th_label"] for row in held} != {str(year) for year in range(2018, 2026)}:
        raise ValueError("held internet panel must cover 2018-2025")
    return held, {
        "schema": "ranah-observatory/bps-held-source-native/v1",
        "source_id": "bps_webapi",
        "held_series": sorted(held_series),
        "row_count": len(held),
        "indicator_ids": sorted({row["indicator_id"] for row in held}),
        "source_var_ids": sorted({row["bps_var_id"] for row in held}),
        "canonical_geography_count": len({row["canonical_geography_id"] for row in held}),
        "period_labels": sorted({row["bps_th_label"] for row in held}),
        "hold_reason": "person-level age-5-plus three-month internet-access universe is not silently promoted to the current household-oriented internet-access ontology",
    }


def write_outputs(rows: list[dict[str, str]], manifest: dict[str, Any], output_csv: Path, output_manifest: Path) -> dict[str, Any]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(manifest)
    manifest["csv_file"] = output_csv.name
    manifest["csv_sha256"] = hashlib.sha256(output_csv.read_bytes()).hexdigest()
    output_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze BPS source-native rows intentionally held from canonical promotion.")
    parser.add_argument("source_panel", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        rows, manifest = build_held(args.source_panel, args.registry)
        manifest = write_outputs(rows, manifest, args.output_csv, args.output_manifest)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
