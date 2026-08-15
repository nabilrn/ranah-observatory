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

OUTPUT_FIELDS = [
    "panel_row_id",
    "panel_series_id",
    "indicator_id",
    "canonical_promotion_status",
    "source_id",
    "domain",
    "retrieved_at_utc",
    "bps_var_id",
    "bps_var_label",
    "bps_var_unit",
    "bps_var_decimal",
    "bps_var_definition",
    "bps_var_note",
    "bps_subject",
    "bps_vertical_dimension",
    "bps_vervar_id",
    "bps_vervar_label",
    "bps_turvar_id",
    "bps_turvar_label",
    "bps_th_id",
    "bps_th_label",
    "bps_turth_id",
    "bps_turth_label",
    "value",
    "source_key",
    "source_snapshot",
    "source_snapshot_sha256",
    "canonical_geography_id",
    "geography_mapping_status",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _find_one(root: Path, pattern: str) -> Path:
    matches = list(root.rglob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {pattern!r} under {root}, found {len(matches)}")
    return matches[0]


def _checksum_from_sidecar(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    parts = text.split("  ", 1)
    if len(parts) != 2 or len(parts[0]) != 64:
        raise ValueError(f"invalid checksum sidecar: {path}")
    int(parts[0], 16)
    return parts[0].lower()


def _panel_row_id(series_id: str, row: dict[str, str]) -> str:
    return ":".join(
        [
            series_id,
            row["bps_vervar_id"],
            row["bps_var_id"],
            row["bps_turvar_id"],
            row["bps_th_id"],
            row["bps_turth_id"],
        ]
    )


def build_panel(input_root: Path, registry_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    registry = read_csv(registry_path)
    panel_rows: list[dict[str, str]] = []
    series_summary: list[dict[str, Any]] = []
    seen_row_ids: set[str] = set()

    for config in registry:
        var_id = config["bps_var_id"]
        series_id = config["panel_series_id"]
        long_path = _find_one(input_root, f"var-{var_id}-long.csv")
        manifest_path = _find_one(input_root, f"var-{var_id}-manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        long_rows = read_csv(long_path)

        if str(manifest.get("var_id")) != var_id:
            raise ValueError(f"{series_id}: manifest var_id does not match registry")

        snapshots: dict[str, tuple[str, str]] = {}
        for item in manifest.get("snapshots", []):
            label = str(item.get("period_label", ""))
            snapshot_name = str(item.get("snapshot", ""))
            checksum_name = str(item.get("checksum", ""))
            if not label or not snapshot_name or not checksum_name:
                raise ValueError(f"{series_id}: incomplete snapshot manifest entry")
            snapshot_path = manifest_path.parent / snapshot_name
            checksum_path = manifest_path.parent / checksum_name
            if not snapshot_path.is_file() or not checksum_path.is_file():
                raise ValueError(f"{series_id}: snapshot or checksum file is missing for period {label}")
            digest = _checksum_from_sidecar(checksum_path)
            actual = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
            if actual != digest:
                raise ValueError(f"{series_id}: checksum mismatch for period {label}")
            snapshots[label] = (snapshot_name, digest)

        selected_turvar = config["selected_turvar_id"]
        selected = [row for row in long_rows if row["bps_turvar_id"] == selected_turvar]
        if not selected:
            raise ValueError(f"{series_id}: selector turvar={selected_turvar} produced no rows")

        actual_labels = {row["bps_th_label"] for row in selected}
        expected_labels = {
            str(year)
            for year in range(int(config["target_start_year"]), int(config["target_end_year"]) + 1)
        }
        missing = sorted(expected_labels - actual_labels)
        extra = sorted(actual_labels - expected_labels)
        if missing:
            raise ValueError(f"{series_id}: missing target period labels: {', '.join(missing)}")
        if extra:
            raise ValueError(f"{series_id}: unexpected period labels: {', '.join(extra)}")

        source_titles = {row["bps_var_label"] for row in selected}
        if source_titles != {config["source_title"]}:
            raise ValueError(f"{series_id}: source title drift detected: {sorted(source_titles)}")

        selector_labels = {row["bps_turvar_label"].strip() for row in selected}
        if config["selected_turvar_label"].strip() not in selector_labels:
            raise ValueError(f"{series_id}: selected turvar label drift detected: {sorted(selector_labels)}")

        counts_by_period: dict[str, int] = {}
        for source_row in selected:
            period_label = source_row["bps_th_label"]
            snapshot = snapshots.get(period_label)
            if snapshot is None:
                raise ValueError(f"{series_id}: no frozen snapshot metadata for period {period_label}")
            row_id = _panel_row_id(series_id, source_row)
            if row_id in seen_row_ids:
                raise ValueError(f"duplicate panel row id {row_id}")
            seen_row_ids.add(row_id)

            row = {field: source_row.get(field, "") for field in OUTPUT_FIELDS}
            row.update(
                {
                    "panel_row_id": row_id,
                    "panel_series_id": series_id,
                    "indicator_id": config["indicator_id"],
                    "canonical_promotion_status": config["canonical_promotion_status"],
                    "source_snapshot": snapshot[0],
                    "source_snapshot_sha256": snapshot[1],
                    "canonical_geography_id": "",
                    "geography_mapping_status": "source_native_unmapped",
                }
            )
            panel_rows.append(row)
            counts_by_period[period_label] = counts_by_period.get(period_label, 0) + 1

        series_summary.append(
            {
                "panel_series_id": series_id,
                "indicator_id": config["indicator_id"],
                "bps_var_id": int(var_id),
                "selected_turvar_id": int(selected_turvar),
                "periods": sorted(counts_by_period),
                "rows": len(selected),
                "rows_by_period": dict(sorted(counts_by_period.items())),
                "canonical_promotion_status": config["canonical_promotion_status"],
            }
        )

    return panel_rows, {
        "schema": "ranah-observatory/bps-source-native-panel/v1",
        "source_id": "bps_webapi",
        "series_count": len(series_summary),
        "row_count": len(panel_rows),
        "series": series_summary,
    }


def write_panel(rows: list[dict[str, str]], manifest: dict[str, Any], output_csv: Path, output_manifest: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(output_csv.read_bytes()).hexdigest()
    manifest = dict(manifest)
    manifest["panel_csv"] = output_csv.name
    manifest["panel_csv_sha256"] = digest
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a selected, provenance-linked BPS source-native panel.")
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        rows, manifest = build_panel(args.input_root, args.registry)
        write_panel(rows, manifest, args.output_csv, args.output_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
