from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from bps_publication import PublicationAcquisitionError, download_publication

SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.pdf$")


def acquire(requests_path: Path, output_dir: Path) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifests: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_outputs: set[str] = set()

    with requests_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row_number, row in enumerate(rows, start=2):
        request_id = row["request_id"].strip()
        page_url = row["official_page_url"].strip()
        output_filename = row["output_filename"].strip()
        if not request_id:
            raise ValueError(f"request row {row_number}: request_id is required")
        if request_id in seen_ids:
            raise ValueError(f"request row {row_number}: duplicate request_id={request_id!r}")
        if not SAFE_FILENAME.match(output_filename):
            raise ValueError(f"request row {row_number}: unsafe output filename={output_filename!r}")
        if output_filename in seen_outputs:
            raise ValueError(
                f"request row {row_number}: duplicate output filename={output_filename!r}"
            )
        seen_ids.add(request_id)
        seen_outputs.add(output_filename)

        manifest = download_publication(page_url, output_dir / output_filename)
        manifest["request_id"] = request_id
        manifest["purpose"] = row.get("purpose", "").strip()
        manifests.append(manifest)

    index = output_dir / "acquisition-index.json"
    index.write_text(
        json.dumps({"requests": manifests}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifests


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire approved public BPS publication requests.")
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifests = acquire(args.requests, args.output_dir)
    except (PublicationAcquisitionError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"acquired": len(manifests)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
