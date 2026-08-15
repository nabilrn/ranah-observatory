from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import product
from pathlib import Path
from typing import Any, Mapping


class BPSDynamicNormalizationError(RuntimeError):
    pass


def _as_list(payload: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise BPSDynamicNormalizationError(f"dynamic payload field {field!r} must be a non-empty list")
    rows: list[Mapping[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise BPSDynamicNormalizationError(f"dynamic payload field {field!r} contains a non-object item")
        if "val" not in item:
            raise BPSDynamicNormalizationError(f"dynamic payload field {field!r} item is missing val")
        rows.append(item)
    return rows


def _id(value: Any) -> str:
    return str(value).strip()


def normalize_dynamic_payload(payload: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if str(payload.get("status", "")) != "OK":
        raise BPSDynamicNormalizationError("dynamic payload status is not OK")
    if str(payload.get("data-availability", "")) != "available":
        raise BPSDynamicNormalizationError("dynamic payload data is not available")

    variables = _as_list(payload, "var")
    verticals = _as_list(payload, "vervar")
    derived_variables = _as_list(payload, "turvar")
    periods = _as_list(payload, "tahun")
    derived_periods = _as_list(payload, "turtahun")
    data_content = payload.get("datacontent")
    if not isinstance(data_content, Mapping):
        raise BPSDynamicNormalizationError("dynamic payload datacontent must be an object")

    vertical_label = str(payload.get("labelvervar", "")).strip()
    expected_keys: set[str] = set()
    records: list[dict[str, Any]] = []

    for variable, vertical, derived_variable, period, derived_period in product(
        variables, verticals, derived_variables, periods, derived_periods
    ):
        source_key = "".join(
            _id(item["val"])
            for item in (vertical, variable, derived_variable, period, derived_period)
        )
        if source_key in expected_keys:
            raise BPSDynamicNormalizationError(
                f"BPS metadata generates an ambiguous datacontent key: {source_key}"
            )
        expected_keys.add(source_key)
        if source_key not in data_content:
            continue

        records.append(
            {
                "bps_var_id": _id(variable["val"]),
                "bps_var_label": str(variable.get("label", "")).strip(),
                "bps_var_unit": str(variable.get("unit", "")).strip(),
                "bps_var_decimal": variable.get("decimal"),
                "bps_var_definition": str(variable.get("def", "")).strip(),
                "bps_var_note": str(variable.get("note", "")).strip(),
                "bps_subject": str(variable.get("subj", "")).strip(),
                "bps_vertical_dimension": vertical_label,
                "bps_vervar_id": _id(vertical["val"]),
                "bps_vervar_label": str(vertical.get("label", "")).strip(),
                "bps_turvar_id": _id(derived_variable["val"]),
                "bps_turvar_label": str(derived_variable.get("label", "")).strip(),
                "bps_th_id": _id(period["val"]),
                "bps_th_label": str(period.get("label", "")).strip(),
                "bps_turth_id": _id(derived_period["val"]),
                "bps_turth_label": str(derived_period.get("label", "")).strip(),
                "value": data_content[source_key],
                "source_key": source_key,
            }
        )

    actual_keys = {str(key) for key in data_content.keys()}
    diagnostics = {
        "expected_combinations": len(expected_keys),
        "observed_values": len(records),
        "missing_combinations": len(expected_keys - actual_keys),
        "unexpected_datacontent_keys": sorted(actual_keys - expected_keys),
    }
    if diagnostics["unexpected_datacontent_keys"]:
        raise BPSDynamicNormalizationError(
            "datacontent contains keys that cannot be reconstructed from response metadata: "
            + ", ".join(diagnostics["unexpected_datacontent_keys"][:5])
        )
    return records, diagnostics


def normalize_snapshot(snapshot: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    result = snapshot.get("result")
    if not isinstance(result, Mapping):
        raise BPSDynamicNormalizationError("snapshot result must contain a dynamic payload object")
    records, diagnostics = normalize_dynamic_payload(result)
    for row in records:
        row["source_id"] = str(snapshot.get("source_id", "bps_webapi"))
        row["domain"] = str(snapshot.get("domain", ""))
        row["retrieved_at_utc"] = str(snapshot.get("retrieved_at_utc", ""))
    return records, diagnostics


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
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
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize one BPS dynamic snapshot to source-native long form.")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
        records, diagnostics = normalize_snapshot(snapshot)
        write_csv(args.output, records)
    except (OSError, json.JSONDecodeError, BPSDynamicNormalizationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
