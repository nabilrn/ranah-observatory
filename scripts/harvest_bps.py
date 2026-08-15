from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

DEFAULT_DOMAIN = "1300"
SOURCE_ID = "bps_webapi"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Harvest BPS WebAPI metadata/data into immutable local JSON snapshots."
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("BPS_API_KEY"),
        help="BPS API key. Prefer the BPS_API_KEY environment variable.",
    )
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="Four-digit BPS website domain.")
    parser.add_argument("--lang", default="ind", choices=("ind", "eng"))
    parser.add_argument("--output", required=True, type=Path)

    subparsers = parser.add_subparsers(dest="command", required=True)

    subjects = subparsers.add_parser("subjects", help="List BPS dynamic-table subjects.")
    subjects.add_argument("--subcat", type=int)
    subjects.add_argument("--max-pages", type=int)

    publications = subparsers.add_parser("publications", help="List BPS publications.")
    publications.add_argument("--year", type=int)
    publications.add_argument("--month", type=int)
    publications.add_argument("--keyword")
    publications.add_argument("--max-pages", type=int)

    tables = subparsers.add_parser("static-tables", help="List BPS static tables.")
    tables.add_argument("--year", type=int)
    tables.add_argument("--month", type=int)
    tables.add_argument("--keyword")
    tables.add_argument("--max-pages", type=int)

    variables = subparsers.add_parser("variables", help="List dynamic-table variables.")
    variables.add_argument("--subject", type=int)
    variables.add_argument("--year", type=int)
    variables.add_argument("--area", type=int, choices=(0, 1))
    variables.add_argument("--vervar", type=int)
    variables.add_argument("--max-pages", type=int)

    periods = subparsers.add_parser(
        "periods", help="List source-native period IDs for dynamic-table variables."
    )
    periods.add_argument("--var", type=int)
    periods.add_argument("--max-pages", type=int)

    derived_variables = subparsers.add_parser(
        "derived-variables", help="List derived-variable selections for dynamic tables."
    )
    derived_variables.add_argument("--var", type=int)
    derived_variables.add_argument("--group", type=int)
    derived_variables.add_argument("--max-pages", type=int)

    derived_periods = subparsers.add_parser(
        "derived-periods", help="List derived-period selections for dynamic tables."
    )
    derived_periods.add_argument("--var", type=int)
    derived_periods.add_argument("--max-pages", type=int)

    dynamic = subparsers.add_parser("dynamic", help="Fetch one dynamic-table selection.")
    dynamic.add_argument("--var", required=True, type=int)
    dynamic.add_argument(
        "--th",
        required=True,
        help="BPS period-data ID selection, not necessarily a calendar year label.",
    )
    dynamic.add_argument("--turvar", type=int)
    dynamic.add_argument("--vervar", type=int)
    dynamic.add_argument("--turth")

    publication = subparsers.add_parser("publication", help="Fetch one publication detail record.")
    publication.add_argument("--id", required=True, dest="publication_id")

    return parser


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_snapshot(path: Path, envelope: Mapping[str, Any]) -> tuple[Path, Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    checksum = _sha256_bytes(serialized)

    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(serialized)
    temp_path.replace(path)

    checksum_path = path.with_suffix(path.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {path.name}\n", encoding="utf-8")
    return path, checksum_path


def _filters_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "subjects":
        return {"subcat": args.subcat, "max_pages": args.max_pages}
    if args.command in {"publications", "static-tables"}:
        return {
            "year": args.year,
            "month": args.month,
            "keyword": args.keyword,
            "max_pages": args.max_pages,
        }
    if args.command == "variables":
        return {
            "subject": args.subject,
            "year": args.year,
            "area": args.area,
            "vervar": args.vervar,
            "max_pages": args.max_pages,
        }
    if args.command == "periods":
        return {"var": args.var, "max_pages": args.max_pages}
    if args.command == "derived-variables":
        return {"var": args.var, "group": args.group, "max_pages": args.max_pages}
    if args.command == "derived-periods":
        return {"var": args.var, "max_pages": args.max_pages}
    if args.command == "dynamic":
        return {
            "var": args.var,
            "th": args.th,
            "turvar": args.turvar,
            "vervar": args.vervar,
            "turth": args.turth,
        }
    if args.command == "publication":
        return {"publication_id": args.publication_id}
    raise ValueError(f"unknown command: {args.command}")


def harvest(args: argparse.Namespace) -> Mapping[str, Any]:
    if not args.api_key:
        raise ValueError(
            "BPS API key is required. Set BPS_API_KEY or pass --api-key; never commit the key."
        )

    client = BPSClient(args.api_key)
    filters = _filters_from_args(args)

    if args.command == "subjects":
        result: Any = client.list_subjects(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "publications":
        result = client.list_publications(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "static-tables":
        result = client.list_static_tables(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "variables":
        result = client.list_variables(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "periods":
        result = client.list_periods(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "derived-variables":
        result = client.list_derived_variables(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "derived-periods":
        result = client.list_derived_periods(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "dynamic":
        result = client.get_dynamic_data(domain=args.domain, lang=args.lang, **filters)
    elif args.command == "publication":
        result = client.get_publication(domain=args.domain, lang=args.lang, **filters)
    else:
        raise ValueError(f"unknown command: {args.command}")

    return {
        "snapshot_schema": "ranah-observatory/bps-webapi-snapshot/v1",
        "source_id": SOURCE_ID,
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "domain": str(args.domain),
        "language": args.lang,
        "command": args.command,
        "filters": {key: value for key, value in filters.items() if value is not None},
        "result": result,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        envelope = harvest(args)
        output, checksum = write_snapshot(args.output, envelope)
    except (BPSApiError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"snapshot: {output}")
    print(f"checksum: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
