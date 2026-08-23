#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "data/registries/milestone28_stage1b_selector_decisions.csv"
CONTRACT = ROOT / "data/manifests/milestone28_stage1b_structure_contract.json"
GEOS = ROOT / "data/registries/geographies.csv"
STAGE1A_DIR = ROOT / "data/processed/bps/m28_stage1a_metadata"
OUT_DIR = ROOT / "data/processed/bps/m28_stage1b_structure"
OUT_CSV = ROOT / "data/analysis/engine/broader_panel_v1/m28-stage1b-structure-audit.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_stage1b_structure_probe.json"
DOMAIN = "1300"
PILOT_YEAR = 2024


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def as_mapping_list(payload: Mapping[str, Any], field: str) -> list[Mapping[str, Any]]:
    value = payload.get(field)
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, Mapping)]


def val(row: Mapping[str, Any]) -> str:
    for key in ("val", "id", "value"):
        if row.get(key) not in (None, ""):
            return str(row.get(key)).strip()
    return ""


def label(row: Mapping[str, Any]) -> str:
    for key in ("label", "name", "th", "turvar", "turth"):
        if row.get(key) not in (None, ""):
            return str(row.get(key)).strip()
    return ""


def expected_geographies() -> dict[str, str]:
    rows = read_csv(GEOS)
    result = {
        row["bps_code"]: row["canonical_name"]
        for row in rows
        if row.get("parent_geography_id") == "idn.13"
        and row.get("status") == "current"
        and row.get("geography_level") in {"regency", "city"}
    }
    if len(result) != 19:
        raise ValueError(f"expected 19 current Sumbar kabupaten/kota, got {len(result)}")
    return dict(sorted(result.items()))


def resolve_period_id(var_id: int, year: int) -> str:
    path = STAGE1A_DIR / f"var-{var_id}.json"
    frozen = json.loads(path.read_text(encoding="utf-8"))
    matches = [row for row in frozen.get("periods", []) if str(row.get("th", "")).strip() == str(year)]
    if len(matches) != 1:
        raise ValueError(f"var {var_id}: expected exactly one frozen period row for {year}, got {len(matches)}")
    return str(matches[0]["th_id"]).strip()


def expected_key_set(payload: Mapping[str, Any]) -> set[str]:
    fields = ["vervar", "var", "turvar", "tahun", "turtahun"]
    groups: list[list[str]] = []
    for field in fields:
        rows = as_mapping_list(payload, field)
        values = [val(row) for row in rows if val(row)]
        if not values:
            return set()
        groups.append(values)
    return {"".join(parts) for parts in itertools.product(*groups)}


def main() -> int:
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone28-stage1b-structure-contract/v1":
        raise ValueError("M28 Stage 1B contract schema drift")
    if contract.get("datacontent_values_may_be_inspected") is not False or contract.get("datacontent_values_may_be_persisted") is not False:
        raise ValueError("Stage 1B contract must prohibit datacontent values")

    decisions = read_csv(DECISIONS)
    retained = [row for row in decisions if row["decision"] == "retain_structure_pilot"]
    held = [row for row in decisions if row["decision"].startswith("held_")]
    if len(retained) != 7 or len(held) != 1:
        raise ValueError(f"expected 7 retained + 1 held decisions, got {len(retained)} + {len(held)}")
    if any(int(row["pilot_year"]) != PILOT_YEAR for row in retained):
        raise ValueError("all retained candidates must use locked 2024 pilot year")

    expected_geo = expected_geographies()
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_rows: list[dict[str, Any]] = []
    frozen_records: list[dict[str, Any]] = []

    for row in retained:
        var_id = int(row["bps_var_id"])
        th_id = resolve_period_id(var_id, PILOT_YEAR)
        turvar_id = row["selected_turvar_id"]
        turth_id = row["selected_turth_id"]
        request_turvar = int(turvar_id) if turvar_id else None
        request_turth = int(turth_id) if turth_id else None
        error = ""
        try:
            payload = client.get_dynamic_data(
                domain=DOMAIN,
                var=var_id,
                th=th_id,
                turvar=request_turvar,
                turth=request_turth,
            )
        except BPSApiError as exc:
            payload = {}
            error = str(exc)

        metadata_fields = ["status", "data-availability", "var", "vervar", "turvar", "tahun", "turtahun", "labelvervar", "last_update"]
        redacted = {key: payload.get(key) for key in metadata_fields if key in payload}
        data_content = payload.get("datacontent") if isinstance(payload, Mapping) else None
        actual_keys = sorted(str(key) for key in data_content.keys()) if isinstance(data_content, Mapping) else []
        expected_keys = expected_key_set(payload) if payload else set()
        unexpected_keys = sorted(set(actual_keys) - expected_keys) if expected_keys else list(actual_keys)

        vervar_rows = as_mapping_list(payload, "vervar") if payload else []
        source_geo = {val(item): label(item) for item in vervar_rows if val(item)}
        mapped_codes = sorted(code for code in expected_geo if code in source_geo)
        missing_codes = sorted(set(expected_geo) - set(mapped_codes))

        turvar_rows = as_mapping_list(payload, "turvar") if payload else []
        turvar_values = {val(item): label(item) for item in turvar_rows if val(item)}
        if turvar_id:
            selector_present = turvar_id in turvar_values and (not row["selected_turvar_label"] or turvar_values[turvar_id] == row["selected_turvar_label"])
        else:
            selector_present = len(turvar_values) == 1 and "0" in turvar_values

        turth_rows = as_mapping_list(payload, "turtahun") if payload else []
        turth_values = {val(item): label(item) for item in turth_rows if val(item)}
        turth_present = turth_id in turth_values if turth_id else True

        tahun_rows = as_mapping_list(payload, "tahun") if payload else []
        period_present = any(val(item) == th_id and label(item) == str(PILOT_YEAR) for item in tahun_rows)

        var_rows = as_mapping_list(payload, "var") if payload else []
        source_title = label(var_rows[0]) if len(var_rows) == 1 else ""
        source_unit = str(var_rows[0].get("unit", "")).strip() if len(var_rows) == 1 else ""
        source_definition = str(var_rows[0].get("def", "")).strip() if len(var_rows) == 1 else ""
        source_note = str(var_rows[0].get("note", "")).strip() if len(var_rows) == 1 else ""
        last_update = str(payload.get("last_update", "")).strip() if payload else ""
        vertical_label = str(payload.get("labelvervar", "")).strip() if payload else ""

        structure_pass = (
            not error
            and len(mapped_codes) == 19
            and not missing_codes
            and selector_present
            and turth_present
            and period_present
            and isinstance(data_content, Mapping)
            and len(actual_keys) > 0
            and not unexpected_keys
        )
        classification = "structure_pilot_pass" if structure_pass else "held_structure_pilot_failed"

        redacted.update({
            "schema": "ranah-observatory/milestone28-stage1b-redacted-structure/v1",
            "candidate_id": row["candidate_id"],
            "bps_var_id": var_id,
            "pilot_year": PILOT_YEAR,
            "resolved_th_id": th_id,
            "requested_turvar_id": turvar_id,
            "requested_turth_id": turth_id,
            "target_values_inspected": False,
            "datacontent_values_persisted": False,
            "datacontent_key_count": len(actual_keys),
            "datacontent_keys": actual_keys,
            "expected_datacontent_key_count_from_metadata": len(expected_keys),
            "unexpected_datacontent_keys": unexpected_keys,
            "mapped_geography_codes": mapped_codes,
            "missing_geography_codes": missing_codes,
            "source_title": source_title,
            "source_unit": source_unit,
            "source_definition": source_definition,
            "source_note": source_note,
            "source_last_update": last_update,
            "source_vertical_label": vertical_label,
            "selector_present": selector_present,
            "turth_present": turth_present,
            "period_present": period_present,
            "classification": classification,
            "error": error,
        })
        out_path = OUT_DIR / f"var-{var_id}-2024-structure.json"
        out_path.write_text(json.dumps(redacted, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        audit_rows.append({
            "candidate_id": row["candidate_id"],
            "bps_var_id": var_id,
            "pilot_year": PILOT_YEAR,
            "resolved_th_id": th_id,
            "selected_turvar_id": turvar_id,
            "selected_turvar_label": row["selected_turvar_label"],
            "selected_turth_id": turth_id,
            "provisional_claim_type": row["provisional_claim_type"],
            "mapped_geography_count": len(mapped_codes),
            "missing_geography_codes": "|".join(missing_codes),
            "selector_present": selector_present,
            "turth_present": turth_present,
            "period_present": period_present,
            "datacontent_key_count": len(actual_keys),
            "expected_key_count": len(expected_keys),
            "unexpected_key_count": len(unexpected_keys),
            "source_title": source_title,
            "source_unit": source_unit,
            "source_last_update": last_update,
            "classification": classification,
            "error": error,
            "redacted_structure_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
            "redacted_structure_sha256": sha256(out_path),
        })
        frozen_records.append({"bps_var_id": var_id, "path": str(out_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(out_path)})

    fields = list(audit_rows[0])
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(audit_rows)

    manifest = {
        "schema": "ranah-observatory/milestone28-stage1b-structure-probe/v1",
        "milestone": 28,
        "stage": "stage1b_structure_only_dynamic_pilot",
        "dynamic_payload_requested": True,
        "authorized_request_count": 7,
        "executed_candidate_count": len(audit_rows),
        "held_without_dynamic_request_count": len(held),
        "target_values_inspected": False,
        "datacontent_values_persisted": False,
        "datacontent_keys_inspected": True,
        "numeric_materialization_performed": False,
        "aggregation_performed": False,
        "derived_indicator_materialized": False,
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "structure_pass_count": sum(r["classification"] == "structure_pilot_pass" for r in audit_rows),
        "structure_hold_count": sum(r["classification"] != "structure_pilot_pass" for r in audit_rows),
        "held_selector_decisions": [{"candidate_id": r["candidate_id"], "bps_var_id": int(r["bps_var_id"]), "decision": r["decision"], "hold_reason": r["hold_reason"]} for r in held],
        "audit_csv": {"path": str(OUT_CSV.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_CSV)},
        "redacted_structure_files": frozen_records,
        "next_gate": "review source definition/note/unit and structural results; freeze candidate-specific numeric acquisition contracts only for retained candidates",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passes": manifest["structure_pass_count"], "holds": manifest["structure_hold_count"], "preheld": len(held)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
