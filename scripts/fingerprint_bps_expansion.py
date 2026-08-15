#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

VOLATILE_FIELDS = {"retrieved_at_utc", "source_snapshot", "source_snapshot_sha256"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def semantic_fingerprint(rows: list[dict[str, str]]) -> str:
    if not rows:
        raise ValueError("source panel is empty")
    fields = [field for field in rows[0] if field not in VOLATILE_FIELDS]
    stable_rows = [
        {field: row.get(field, "") for field in fields}
        for row in sorted(rows, key=lambda item: item["expansion_row_id"])
    ]
    payload = json.dumps(
        stable_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute retrieval-stable semantic fingerprint for a BPS expansion source panel.")
    parser.add_argument("source_panel", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        rows = read_rows(args.source_panel)
        digest = semantic_fingerprint(rows)
        payload = {
            "schema": "ranah-observatory/bps-expansion-semantic-fingerprint/v1",
            "row_count": len(rows),
            "semantic_fingerprint_sha256": digest,
            "excluded_fields": sorted(VOLATILE_FIELDS),
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
