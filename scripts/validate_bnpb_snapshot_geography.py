from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "data" / "registries" / "bnpb_geography_map.csv"
CODE_FIELDS = ("Kode Wilayah Kabupaten / Kota", "Kode Wilayah Kabupaten/Kota")
NAME_FIELDS = ("Nama Kabupaten/Kota", "NAMA KABUPATEN/KOTA", "Nama Kabupaten / Kota")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _value(record: Mapping[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        if field in record:
            return record[field]
    raise ValueError(f"snapshot record missing required field; tried {fields!r}")


def _normalize_code(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return re.sub(r"\D", "", text)
    if number.is_integer():
        return str(int(number))
    return re.sub(r"\D", "", text)


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[._,/\\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def expected_pairs(map_path: Path = DEFAULT_MAP) -> dict[str, str]:
    rows = _read_csv(map_path)
    pairs: dict[str, str] = {}
    for row in rows:
        code = row["source_code_normalized"]
        name = _normalize_name(row["source_name_expected"])
        if not code or not name:
            raise ValueError(f"{map_path}: source code/name expectation is incomplete")
        if code in pairs:
            raise ValueError(f"{map_path}: duplicate source code {code}")
        pairs[code] = name
    if len(pairs) != 19:
        raise ValueError(f"{map_path}: expected 19 source code/name pairs, found {len(pairs)}")
    return pairs


def validate_snapshot(path: Path, pairs: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("snapshot_schema") != "ranah-observatory/bnpb-ckan-snapshot/v1":
        return [f"{path}: unexpected BNPB snapshot schema"]
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("records"), list):
        return [f"{path}: missing DataStore records"]

    observed: dict[str, str] = {}
    for raw in result["records"]:
        if not isinstance(raw, Mapping):
            errors.append(f"{path}: non-object DataStore record")
            continue
        code = _normalize_code(_value(raw, CODE_FIELDS))
        if code not in pairs:
            continue
        name = _normalize_name(_value(raw, NAME_FIELDS))
        if code in observed:
            errors.append(f"{path}: duplicate reviewed Sumatera Barat source code {code}")
            continue
        observed[code] = name
        if name != pairs[code]:
            errors.append(
                f"{path}: source code/name drift for {code}: observed={name!r} expected={pairs[code]!r}"
            )

    missing = sorted(set(pairs) - set(observed))
    if missing:
        errors.append(f"{path}: missing reviewed Sumatera Barat source codes {missing}")
    if len(observed) != 19:
        errors.append(f"{path}: observed {len(observed)} reviewed Sumatera Barat rows, expected 19")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate live BNPB source code/name pairs before applying the explicit geography crosswalk."
    )
    parser.add_argument("snapshots", nargs="+", type=Path)
    parser.add_argument("--geography-map", type=Path, default=DEFAULT_MAP)
    args = parser.parse_args()
    try:
        pairs = expected_pairs(args.geography_map)
        errors: list[str] = []
        for snapshot in args.snapshots:
            errors.extend(validate_snapshot(snapshot, pairs))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BNPB live geography validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BNPB live geography validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"BNPB live geography validation passed for {len(args.snapshots)} snapshots and 19 code/name pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
