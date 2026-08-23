#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient

ROOT = Path(__file__).resolve().parents[1]
SHORTLIST = ROOT / "data/registries/milestone28_stage1a_shortlist.csv"
CONTRACT = ROOT / "data/manifests/milestone28_stage1a_metadata_contract.json"
OUT_DIR = ROOT / "data/processed/bps/m28_stage1a_metadata"
OUT_CSV = ROOT / "data/analysis/engine/broader_panel_v1/m28-stage1a-metadata-audit.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_stage1a_metadata_probe.json"
DOMAIN = "1300"
TARGET_YEARS = list(range(2018, 2026))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def extract_year(value: Any) -> int | None:
    text = str(value or "")
    match = re.search(r"\b(?:19|20)\d{2}\b", text)
    return int(match.group(0)) if match else None


def option(row: Mapping[str, Any], id_keys: tuple[str, ...], label_keys: tuple[str, ...]) -> dict[str, str]:
    value = ""
    label = ""
    for key in id_keys:
        if row.get(key) not in (None, ""):
            value = str(row.get(key)).strip()
            break
    for key in label_keys:
        if row.get(key) not in (None, ""):
            label = str(row.get(key)).strip()
            break
    return {"value": value, "label": label}


def main() -> int:
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone28-stage1a-metadata-contract/v1":
        raise ValueError("M28 Stage 1A contract schema drift")
    if contract.get("dynamic_data_request_authorized") is not False:
        raise ValueError("Stage 1A must prohibit dynamic data requests")

    shortlist = read_csv(SHORTLIST)
    if len(shortlist) != 8:
        raise ValueError(f"expected 8 Stage 1A candidates, got {len(shortlist)}")
    if len({row["bps_var_id"] for row in shortlist}) != len(shortlist):
        raise ValueError("duplicate BPS var ID in Stage 1A shortlist")

    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_rows: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []

    for candidate in shortlist:
        var_id = int(candidate["bps_var_id"])
        try:
            periods = client.list_periods(domain=DOMAIN, var=var_id)
            turvars = client.list_derived_variables(domain=DOMAIN, var=var_id)
            turths = client.list_derived_periods(domain=DOMAIN, var=var_id)
            error = ""
        except BPSApiError as exc:
            periods, turvars, turths = [], [], []
            error = str(exc)

        raw = {
            "schema": "ranah-observatory/milestone28-stage1a-candidate-metadata/v1",
            "source_id": "bps_webapi",
            "domain": DOMAIN,
            "candidate_id": candidate["candidate_id"],
            "bps_var_id": var_id,
            "metadata_only": True,
            "dynamic_data_requested": False,
            "target_values_inspected": False,
            "periods": periods,
            "turvar": turvars,
            "turth": turths,
            "error": error,
        }
        raw_path = OUT_DIR / f"var-{var_id}.json"
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        period_options = [option(row, ("th_id", "val", "id"), ("th", "label", "name")) for row in periods]
        turvar_options = [option(row, ("turvar_id", "val", "id"), ("turvar", "label", "name")) for row in turvars]
        turth_options = [option(row, ("turth_id", "val", "id"), ("turth", "label", "name")) for row in turths]
        years = sorted({year for row in periods for year in [extract_year(row.get("th", row.get("label", row.get("name", ""))))] if year is not None})
        target_available = sorted(set(years) & set(TARGET_YEARS))
        missing = sorted(set(TARGET_YEARS) - set(target_available))
        if not periods and error:
            classification = "held_metadata_request_error"
        elif not target_available:
            classification = "held_no_target_period_overlap"
        elif not missing:
            classification = "metadata_full_target_period_coverage"
        else:
            classification = "metadata_partial_target_period_coverage"

        audit_rows.append({
            "candidate_id": candidate["candidate_id"],
            "bps_var_id": var_id,
            "family": candidate["family"],
            "intended_indicator": candidate["intended_indicator"],
            "source_unit": candidate["source_unit"],
            "stage1a_status": candidate["stage1a_status"],
            "classification": classification,
            "available_years": "|".join(map(str, years)),
            "target_available_years": "|".join(map(str, target_available)),
            "missing_target_years": "|".join(map(str, missing)),
            "period_option_count": len(period_options),
            "turvar_option_count": len(turvar_options),
            "turth_option_count": len(turth_options),
            "turvar_options_json": json.dumps(turvar_options, ensure_ascii=False, sort_keys=True),
            "turth_options_json": json.dumps(turth_options, ensure_ascii=False, sort_keys=True),
            "selector_rule": candidate["selector_rule"],
            "methodology_boundary": candidate["methodology_boundary"],
            "error": error,
            "raw_metadata_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "raw_metadata_sha256": sha256(raw_path),
        })
        raw_records.append({
            "bps_var_id": var_id,
            "path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(raw_path),
        })

    fields = list(audit_rows[0])
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(audit_rows)

    manifest = {
        "schema": "ranah-observatory/milestone28-stage1a-metadata-probe/v1",
        "milestone": 28,
        "stage": "stage1a_selector_period_metadata",
        "domain": DOMAIN,
        "candidate_count": len(audit_rows),
        "metadata_only": True,
        "allowed_api_models_used": ["th", "turvar", "turth"],
        "dynamic_observation_requested": False,
        "target_values_inspected": False,
        "target_values_persisted": False,
        "credential_persisted": False,
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "derived_indicator_materialized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "classification_counts": {name: sum(row["classification"] == name for row in audit_rows) for name in sorted({row["classification"] for row in audit_rows})},
        "audit_csv": {"path": str(OUT_CSV.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_CSV)},
        "candidate_metadata": raw_records,
        "next_gate": "lock exact source-native selectors and methodology treatment from this frozen metadata; only then authorize one structure-only dynamic pilot per retained candidate",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"candidate_count": len(audit_rows), "classifications": manifest["classification_counts"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
