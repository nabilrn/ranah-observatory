from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient
from harvest_bps import write_snapshot
from normalize_bps_dynamic import BPSDynamicNormalizationError, normalize_dynamic_payload

SOURCE_ID = "bps_webapi"
SNAPSHOT_SCHEMA = "ranah-observatory/bps-webapi-snapshot/v1"
SERIES_SCHEMA = "ranah-observatory/bps-source-series/v1"


def _period_label(row: Mapping[str, Any]) -> str:
    return str(row.get("th", row.get("label", ""))).strip()


def _period_id(row: Mapping[str, Any]) -> str:
    return str(row.get("th_id", row.get("val", ""))).strip()


def resolve_periods(period_rows: list[Mapping[str, Any]], requested_labels: list[str]) -> list[tuple[str, str]]:
    by_label: dict[str, str] = {}
    duplicates: set[str] = set()
    for row in period_rows:
        label = _period_label(row)
        period_id = _period_id(row)
        if not label or not period_id:
            raise ValueError("BPS period metadata contains an empty label or id")
        if label in by_label and by_label[label] != period_id:
            duplicates.add(label)
        by_label[label] = period_id
    if duplicates:
        raise ValueError("ambiguous BPS period labels: " + ", ".join(sorted(duplicates)))
    missing = [label for label in requested_labels if label not in by_label]
    if missing:
        raise ValueError("requested BPS period labels are unavailable: " + ", ".join(missing))
    return [(label, by_label[label]) for label in requested_labels]


def year_labels(start_year: int, end_year: int) -> list[str]:
    if end_year < start_year:
        raise ValueError("end year must be greater than or equal to start year")
    return [str(year) for year in range(start_year, end_year + 1)]


def _write_long_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_id", "domain", "retrieved_at_utc", "bps_var_id", "bps_var_label",
        "bps_var_unit", "bps_var_decimal", "bps_var_definition", "bps_var_note", "bps_subject",
        "bps_vertical_dimension", "bps_vervar_id", "bps_vervar_label", "bps_turvar_id",
        "bps_turvar_label", "bps_th_id", "bps_th_label", "bps_turth_id", "bps_turth_label",
        "value", "source_key",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def harvest_series(*, api_key: str, domain: str, lang: str, var_id: int, requested_labels: list[str], output_dir: Path) -> dict[str, Any]:
    if not requested_labels:
        raise ValueError("at least one period label is required")
    client = BPSClient(api_key)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    periods = client.list_periods(domain=domain, lang=lang, var=var_id)
    resolved = resolve_periods(periods, requested_labels)
    output_dir.mkdir(parents=True, exist_ok=True)
    period_snapshot = {
        "snapshot_schema": SNAPSHOT_SCHEMA, "source_id": SOURCE_ID, "retrieved_at_utc": retrieved_at,
        "domain": domain, "language": lang, "command": "periods", "filters": {"var": var_id}, "result": periods,
    }
    write_snapshot(output_dir / f"var-{var_id}-periods.json", period_snapshot)
    long_rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    for label, period_id in resolved:
        payload = client.get_dynamic_data(domain=domain, lang=lang, var=var_id, th=period_id)
        snapshot = {
            "snapshot_schema": SNAPSHOT_SCHEMA, "source_id": SOURCE_ID, "retrieved_at_utc": retrieved_at,
            "domain": domain, "language": lang, "command": "dynamic",
            "filters": {"var": var_id, "th": period_id, "resolved_period_label": label}, "result": payload,
        }
        snapshot_path = output_dir / f"var-{var_id}-{label}.json"
        _, checksum_path = write_snapshot(snapshot_path, snapshot)
        normalized, diagnostics = normalize_dynamic_payload(payload)
        for row in normalized:
            row["source_id"] = SOURCE_ID
            row["domain"] = domain
            row["retrieved_at_utc"] = retrieved_at
        long_rows.extend(normalized)
        snapshots.append({
            "period_label": label, "period_id": period_id, "snapshot": snapshot_path.name,
            "checksum": checksum_path.name, "observed_values": diagnostics["observed_values"],
            "missing_combinations": diagnostics["missing_combinations"],
        })
    _write_long_csv(output_dir / f"var-{var_id}-long.csv", long_rows)
    manifest = {
        "schema": SERIES_SCHEMA, "source_id": SOURCE_ID, "domain": domain, "language": lang,
        "var_id": var_id, "retrieved_at_utc": retrieved_at, "requested_period_labels": requested_labels,
        "snapshots": snapshots, "normalized_rows": len(long_rows),
    }
    (output_dir / f"var-{var_id}-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve BPS period labels, fetch each period, and normalize source-native values.")
    parser.add_argument("--api-key", default=os.environ.get("BPS_API_KEY"))
    parser.add_argument("--domain", default="1300")
    parser.add_argument("--lang", default="ind", choices=("ind", "eng"))
    parser.add_argument("--var", required=True, type=int, dest="var_id")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--period", dest="periods", action="append", help="Exact BPS period label; repeat for multiple periods.")
    group.add_argument("--year-range", nargs=2, type=int, metavar=("START", "END"))
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.api_key:
        print("error: BPS API key is required; set BPS_API_KEY", file=sys.stderr)
        return 2
    requested = args.periods if args.periods is not None else year_labels(*args.year_range)
    try:
        manifest = harvest_series(api_key=args.api_key, domain=str(args.domain), lang=args.lang, var_id=args.var_id, requested_labels=requested, output_dir=args.output_dir)
    except (BPSApiError, BPSDynamicNormalizationError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
