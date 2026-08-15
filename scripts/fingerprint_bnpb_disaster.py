from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_FIELDS = (
    "source_record_id",
    "metric_family",
    "canonical_geography_id",
    "source_geography_code",
    "source_geography_name",
    "year",
    "disaster_type",
    "value_numeric",
    "unit",
    "promotion_status",
    "notes",
)
CANONICAL_FIELDS = (
    "indicator_id",
    "geography_id",
    "time_start",
    "time_end",
    "frequency",
    "value_numeric",
    "unit",
    "claim_type",
    "suppressed",
    "comparable",
    "methodology_version",
    "price_basis",
    "notes",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _project(rows: list[dict[str, str]], fields: tuple[str, ...]) -> list[dict[str, str]]:
    projected = [{field: row[field] for field in fields} for row in rows]
    return sorted(projected, key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))


def semantic_payload(root: Path) -> dict[str, Any]:
    source_path = root / "bnpb-disaster-source-native.csv"
    canonical_path = root / "bnpb-disaster-canonical-observations.csv"
    manifest_path = root / "bnpb-disaster-panel.manifest.json"
    source_rows = _read_csv(source_path)
    canonical_rows = _read_csv(canonical_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "schema": "ranah-observatory/bnpb-disaster-semantic-fingerprint/v1",
        "source_id": manifest.get("source_id"),
        "official_crosscheck": manifest.get("official_crosscheck"),
        "geography_mapping": manifest.get("geography_mapping"),
        "source_native_count": len(source_rows),
        "canonical_observation_count": len(canonical_rows),
        "mapped_geography_count": manifest.get("mapped_geography_count"),
        "canonical_indicators": sorted(manifest.get("canonical_indicators", [])),
        "source_native": _project(source_rows, SOURCE_FIELDS),
        "canonical": _project(canonical_rows, CANONICAL_FIELDS),
    }


def fingerprint(root: Path) -> tuple[str, dict[str, Any]]:
    payload = semantic_payload(root)
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest(), payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute retrieval-stable semantic fingerprint for BNPB disaster panel.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    digest, payload = fingerprint(args.root)
    result = {
        "schema": "ranah-observatory/bnpb-disaster-semantic-fingerprint-result/v1",
        "semantic_fingerprint_sha256": digest,
        "source_native_count": payload["source_native_count"],
        "canonical_observation_count": payload["canonical_observation_count"],
        "mapped_geography_count": payload["mapped_geography_count"],
        "canonical_indicators": payload["canonical_indicators"],
        "official_crosscheck": payload["official_crosscheck"],
        "geography_mapping": payload["geography_mapping"],
        "excluded_retrieval_fields": [
            "source_row_id",
            "source_snapshot_sha256",
            "observation_id",
            "provenance_id",
            "provenance retrieval/checksum fields",
        ],
    }
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
