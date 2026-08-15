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
DEFAULT_SERIES = ROOT / "data" / "registries" / "bps_expansion_series.csv"
DEFAULT_GEOGRAPHY_MAP = ROOT / "data" / "registries" / "bps_expansion_geography_map.csv"

FIELDS = [
    "expansion_row_id", "expansion_series_id", "indicator_id", "canonical_promotion_status",
    "claim_type", "source_id", "domain", "retrieved_at_utc", "bps_last_update",
    "bps_var_id", "bps_var_label", "bps_var_unit", "bps_var_decimal", "bps_var_definition",
    "bps_var_note", "bps_subject", "bps_th_id", "bps_th_label", "bps_turth_id",
    "bps_turth_label", "source_geography_dimension", "source_geography_id",
    "source_geography_label", "canonical_geography_id", "geography_mapping_status",
    "selected_vervar_id", "selected_vervar_label", "selected_turvar_id", "selected_turvar_label",
    "raw_value", "denominator_raw_value", "transform", "source_key", "denominator_source_key",
    "source_snapshot", "source_snapshot_sha256",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _find_one(root: Path, pattern: str) -> Path:
    matches = list(root.rglob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {pattern!r} under {root}, found {len(matches)}")
    return matches[0]


def _checksum(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    parts = text.split("  ", 1)
    if len(parts) != 2 or len(parts[0]) != 64:
        raise ValueError(f"invalid checksum sidecar: {path}")
    int(parts[0], 16)
    return parts[0].lower()


def _snapshots(manifest_path: Path) -> dict[str, tuple[str, str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshots: dict[str, tuple[str, str]] = {}
    for item in manifest.get("snapshots", []):
        label = str(item.get("period_label", "")).strip()
        snapshot_name = str(item.get("snapshot", "")).strip()
        checksum_name = str(item.get("checksum", "")).strip()
        if not label or not snapshot_name or not checksum_name:
            raise ValueError(f"{manifest_path}: incomplete snapshot manifest entry")
        snapshot_path = manifest_path.parent / snapshot_name
        checksum_path = manifest_path.parent / checksum_name
        digest = _checksum(checksum_path)
        if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"{snapshot_path}: snapshot checksum mismatch")
        snapshots[label] = (snapshot_name, digest)
    return snapshots


def _geography_map(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv(path):
        key = (row["source_dimension"], row["bps_dimension_id"])
        if key in result:
            raise ValueError(f"duplicate expansion geography mapping {key}")
        result[key] = row
    return result


def _resolve_geography(
    row: dict[str, str],
    dimension: str,
    year: int,
    mapping: dict[tuple[str, str], dict[str, str]],
) -> tuple[str, str, str, str]:
    if dimension == "constant_province":
        return "constant_province", "idn.13", "Sumatera Barat", "qualified_constant_source_scope"
    if dimension == "vervar":
        source_id = row["bps_vervar_id"]
        source_label = row["bps_vervar_label"]
    elif dimension == "turvar":
        source_id = row["bps_turvar_id"]
        source_label = row["bps_turvar_label"]
    else:
        raise ValueError(f"unsupported geography_dimension {dimension!r}")
    qualified = mapping.get((dimension, source_id))
    if qualified is None:
        raise ValueError(f"unmapped expansion geography {dimension}:{source_id}")
    start = int(qualified["applicable_start_year"])
    end = int(qualified["applicable_end_year"])
    if not start <= year <= end:
        raise ValueError(f"geography mapping {dimension}:{source_id} does not cover {year}")
    status = {
        "direct_current_code": "qualified_current_code",
        "source_aggregate_alias": "qualified_source_aggregate_alias",
        "source_dimension_alias": "qualified_source_dimension_alias",
    }.get(qualified["mapping_type"])
    if status is None:
        raise ValueError(f"unsupported expansion mapping_type {qualified['mapping_type']!r}")
    return source_id, qualified["canonical_geography_id"], source_label, status


def _select(rows: list[dict[str, str]], config: dict[str, str]) -> list[dict[str, str]]:
    selected = rows
    if config["selected_vervar_id"]:
        selected = [row for row in selected if row["bps_vervar_id"] == config["selected_vervar_id"]]
    if config["selected_turvar_id"]:
        selected = [row for row in selected if row["bps_turvar_id"] == config["selected_turvar_id"]]
    return selected


def _denominator_index(rows: list[dict[str, str]], denominator_vervar_id: str) -> dict[tuple[str, str, str], dict[str, str]]:
    if not denominator_vervar_id:
        return {}
    index: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        if row["bps_vervar_id"] != denominator_vervar_id:
            continue
        key = (row["bps_turvar_id"], row["bps_th_id"], row["bps_turth_id"])
        if key in index:
            raise ValueError(f"ambiguous denominator source row for {key}")
        index[key] = row
    return index


def _row_id(series_id: str, geography_id: str, source_row: dict[str, str]) -> str:
    token = "|".join(
        [series_id, geography_id, source_row["bps_th_id"], source_row["bps_turth_id"]]
    )
    return "bpsexp_" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def build_panel(
    input_root: Path,
    series_registry: Path = DEFAULT_SERIES,
    geography_map_path: Path = DEFAULT_GEOGRAPHY_MAP,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    configs = read_csv(series_registry)
    mapping = _geography_map(geography_map_path)
    source_cache: dict[str, tuple[list[dict[str, str]], dict[str, tuple[str, str]]]] = {}
    output: list[dict[str, str]] = []
    series_summary: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for config in configs:
        var_id = config["bps_var_id"]
        if var_id not in source_cache:
            long_path = _find_one(input_root, f"var-{var_id}-long.csv")
            manifest_path = _find_one(input_root, f"var-{var_id}-manifest.json")
            source_cache[var_id] = (read_csv(long_path), _snapshots(manifest_path))
        source_rows, snapshots = source_cache[var_id]
        selected = _select(source_rows, config)
        if not selected:
            raise ValueError(f"{config['expansion_series_id']}: selector produced no rows")
        denominator = _denominator_index(source_rows, config["denominator_vervar_id"])

        expected_years = {
            str(year) for year in range(int(config["target_start_year"]), int(config["target_end_year"]) + 1)
        }
        actual_years = {row["bps_th_label"] for row in selected}
        if actual_years != expected_years:
            raise ValueError(
                f"{config['expansion_series_id']}: period labels differ; "
                f"expected={sorted(expected_years)} actual={sorted(actual_years)}"
            )

        counts: dict[str, int] = {}
        for row in selected:
            year = int(row["bps_th_label"])
            source_geo_id, canonical_geo_id, source_geo_label, mapping_status = _resolve_geography(
                row, config["geography_dimension"], year, mapping
            )
            snapshot = snapshots.get(row["bps_th_label"])
            if snapshot is None:
                raise ValueError(
                    f"{config['expansion_series_id']}: missing source snapshot for {row['bps_th_label']}"
                )
            denom_value = ""
            denom_key = ""
            if config["denominator_vervar_id"]:
                key = (row["bps_turvar_id"], row["bps_th_id"], row["bps_turth_id"])
                denom_row = denominator.get(key)
                if denom_row is None:
                    raise ValueError(f"{config['expansion_series_id']}: missing denominator for {key}")
                denom_value = denom_row["value"]
                denom_key = denom_row["source_key"]

            rid = _row_id(config["expansion_series_id"], canonical_geo_id, row)
            if rid in seen_ids:
                raise ValueError(f"duplicate expansion row id {rid}")
            seen_ids.add(rid)
            output.append(
                {
                    "expansion_row_id": rid,
                    "expansion_series_id": config["expansion_series_id"],
                    "indicator_id": config["indicator_id"],
                    "canonical_promotion_status": config["canonical_promotion_status"],
                    "claim_type": config["claim_type"],
                    "source_id": row["source_id"],
                    "domain": row["domain"],
                    "retrieved_at_utc": row["retrieved_at_utc"],
                    "bps_last_update": row.get("bps_last_update", ""),
                    "bps_var_id": row["bps_var_id"],
                    "bps_var_label": row["bps_var_label"],
                    "bps_var_unit": row["bps_var_unit"],
                    "bps_var_decimal": row["bps_var_decimal"],
                    "bps_var_definition": row["bps_var_definition"],
                    "bps_var_note": row["bps_var_note"],
                    "bps_subject": row["bps_subject"],
                    "bps_th_id": row["bps_th_id"],
                    "bps_th_label": row["bps_th_label"],
                    "bps_turth_id": row["bps_turth_id"],
                    "bps_turth_label": row["bps_turth_label"],
                    "source_geography_dimension": config["geography_dimension"],
                    "source_geography_id": source_geo_id,
                    "source_geography_label": source_geo_label,
                    "canonical_geography_id": canonical_geo_id,
                    "geography_mapping_status": mapping_status,
                    "selected_vervar_id": row["bps_vervar_id"],
                    "selected_vervar_label": row["bps_vervar_label"],
                    "selected_turvar_id": row["bps_turvar_id"],
                    "selected_turvar_label": row["bps_turvar_label"],
                    "raw_value": row["value"],
                    "denominator_raw_value": denom_value,
                    "transform": config["transform"],
                    "source_key": row["source_key"],
                    "denominator_source_key": denom_key,
                    "source_snapshot": snapshot[0],
                    "source_snapshot_sha256": snapshot[1],
                }
            )
            counts[row["bps_th_label"]] = counts.get(row["bps_th_label"], 0) + 1

        series_summary.append(
            {
                "expansion_series_id": config["expansion_series_id"],
                "indicator_id": config["indicator_id"],
                "bps_var_id": int(var_id),
                "rows": sum(counts.values()),
                "rows_by_period": dict(sorted(counts.items())),
                "canonical_promotion_status": config["canonical_promotion_status"],
            }
        )

    output.sort(key=lambda row: row["expansion_row_id"])
    return output, {
        "schema": "ranah-observatory/bps-expansion-source-panel/v1",
        "source_id": "bps_webapi",
        "series_count": len(series_summary),
        "row_count": len(output),
        "series": series_summary,
    }


def write_outputs(rows: list[dict[str, str]], manifest: dict[str, Any], output_csv: Path, output_manifest: Path) -> dict[str, Any]:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(manifest)
    manifest["panel_csv"] = output_csv.name
    manifest["panel_csv_sha256"] = hashlib.sha256(output_csv.read_bytes()).hexdigest()
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the reviewed structural-economic BPS expansion source panel.")
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--series-registry", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--geography-map", type=Path, default=DEFAULT_GEOGRAPHY_MAP)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        rows, manifest = build_panel(args.input_root, args.series_registry, args.geography_map)
        manifest = write_outputs(rows, manifest, args.output_csv, args.output_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
