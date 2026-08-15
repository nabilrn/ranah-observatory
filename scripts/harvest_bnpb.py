from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bnpb_client import BNPBApiError, BNPBClient

SOURCE_ID = "bnpb_satu_data"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest official BNPB CKAN metadata/data snapshots.")
    parser.add_argument("--output", required=True, type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    package = subparsers.add_parser("package", help="Fetch one CKAN package metadata record.")
    package.add_argument("--id", required=True, dest="dataset_id")

    datastore = subparsers.add_parser("datastore", help="Fetch all records from one DataStore resource.")
    datastore.add_argument("--resource-id", required=True)
    datastore.add_argument("--page-size", type=int, default=100)
    datastore.add_argument("--max-records", type=int)
    return parser


def _snapshot(command: str, filters: Mapping[str, Any], result: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "snapshot_schema": "ranah-observatory/bnpb-ckan-snapshot/v1",
        "source_id": SOURCE_ID,
        "retrieved_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "command": command,
        "filters": {key: value for key, value in filters.items() if value is not None},
        "result": result,
    }


def write_snapshot(path: Path, payload: Mapping[str, Any]) -> tuple[Path, Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(serialized)
    temp.replace(path)
    checksum = path.with_suffix(path.suffix + ".sha256")
    checksum.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return path, checksum


def main() -> int:
    args = build_parser().parse_args()
    client = BNPBClient()
    try:
        if args.command == "package":
            filters = {"dataset_id": args.dataset_id}
            result = client.package_show(args.dataset_id)
        elif args.command == "datastore":
            filters = {
                "resource_id": args.resource_id,
                "page_size": args.page_size,
                "max_records": args.max_records,
            }
            result = client.datastore_search_all(
                args.resource_id,
                page_size=args.page_size,
                max_records=args.max_records,
            )
        else:
            raise ValueError(f"unknown command {args.command!r}")
        output, checksum = write_snapshot(args.output, _snapshot(args.command, filters, result))
    except (BNPBApiError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"snapshot: {output}")
    print(f"checksum: {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
