from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

SCHEMA = "ranah-observatory/bps-candidate-discovery/v1"
SOURCE_ID = "bps_webapi"


def _label(row: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _period_id(row: Mapping[str, Any]) -> str:
    return _label(row, "th_id", "val")


def _period_label(row: Mapping[str, Any]) -> str:
    return _label(row, "th", "label")


def select_latest_numeric_period(rows: list[Mapping[str, Any]]) -> tuple[str, str]:
    candidates: list[tuple[int, str, str]] = []
    for row in rows:
        label = _period_label(row)
        period_id = _period_id(row)
        if not label or not period_id:
            continue
        try:
            year = int(label)
        except ValueError:
            continue
        candidates.append((year, label, period_id))
    if not candidates:
        raise ValueError("candidate has no numeric period labels")
    _, label, period_id = max(candidates)
    return label, period_id


def _safe_list(call, *, unavailable_ok: bool = True) -> list[Mapping[str, Any]]:
    try:
        rows = call()
    except BPSApiError:
        if unavailable_ok:
            return []
        raise
    return list(rows)


def discover_variable(client: BPSClient, *, domain: str, lang: str, var_id: int) -> dict[str, Any]:
    periods = client.list_periods(domain=domain, lang=lang, var=var_id)
    latest_label, latest_period_id = select_latest_numeric_period(periods)
    derived_variables = _safe_list(
        lambda: client.list_derived_variables(domain=domain, lang=lang, var=var_id)
    )
    derived_periods = _safe_list(
        lambda: client.list_derived_periods(domain=domain, lang=lang, var=var_id)
    )
    dynamic = client.get_dynamic_data(
        domain=domain,
        lang=lang,
        var=var_id,
        th=latest_period_id,
    )
    return {
        "var_id": var_id,
        "periods": periods,
        "derived_variables": derived_variables,
        "derived_periods": derived_periods,
        "latest_sample": {
            "period_label": latest_label,
            "period_id": latest_period_id,
            "payload": dynamic,
        },
    }


def discover(
    *, api_key: str, domain: str, lang: str, var_ids: list[int]
) -> dict[str, Any]:
    if not var_ids:
        raise ValueError("at least one BPS variable id is required")
    if len(var_ids) != len(set(var_ids)):
        raise ValueError("BPS variable ids must be unique")
    client = BPSClient(api_key)
    return {
        "schema": SCHEMA,
        "source_id": SOURCE_ID,
        "domain": domain,
        "language": lang,
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "variables": [
            discover_variable(client, domain=domain, lang=lang, var_id=var_id)
            for var_id in var_ids
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect period, derived-dimension, and latest-sample metadata for BPS candidate variables."
    )
    parser.add_argument("--api-key", default=os.environ.get("BPS_API_KEY"))
    parser.add_argument("--domain", default="1300")
    parser.add_argument("--lang", default="ind", choices=("ind", "eng"))
    parser.add_argument("--var", dest="var_ids", action="append", type=int, required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.api_key:
        print("error: BPS API key is required; set BPS_API_KEY", file=sys.stderr)
        return 2
    try:
        payload = discover(
            api_key=args.api_key,
            domain=str(args.domain),
            lang=args.lang,
            var_ids=args.var_ids,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (BPSApiError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"discovered {len(payload['variables'])} BPS candidate variables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
