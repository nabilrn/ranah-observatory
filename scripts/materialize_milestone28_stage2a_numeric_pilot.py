#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from bps_client import BPSApiError, BPSClient
from normalize_bps_dynamic import BPSDynamicNormalizationError, normalize_dynamic_payload

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data/manifests/milestone28_stage2a_numeric_pilot_contract.json"
STAGE1A_DIR = ROOT / "data/processed/bps/m28_stage1a_metadata"
GEOS = ROOT / "data/registries/geographies.csv"
VAR169_MAP = ROOT / "data/registries/milestone28_var169_local_geography_map.csv"
OUT_RAW = ROOT / "data/processed/bps/m28_stage2a_numeric_pilot"
OUT_OBS = ROOT / "data/analysis/engine/broader_panel_v1/m28-stage2a-pilot-observations.csv"
OUT_PROV = ROOT / "data/analysis/engine/broader_panel_v1/m28-stage2a-pilot-provenance.csv"
OUT_AUDIT = ROOT / "data/analysis/engine/broader_panel_v1/m28-stage2a-pilot-audit.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_stage2a_numeric_pilot.json"
DOMAIN = "1300"
PILOT_YEAR = 2024


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm_text(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def decimal_value(raw: Any) -> Decimal:
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric source value {raw!r}") from exc
    if not value.is_finite():
        raise ValueError(f"non-finite source value {raw!r}")
    return value


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def source_period_id(var_id: int, year: int) -> str:
    frozen = json.loads((STAGE1A_DIR / f"var-{var_id}.json").read_text(encoding="utf-8"))
    rows = [r for r in frozen.get("periods", []) if str(r.get("th", "")).strip() == str(year)]
    if len(rows) != 1:
        raise ValueError(f"var {var_id}: expected one frozen period row for {year}, got {len(rows)}")
    return str(rows[0]["th_id"]).strip()


def current_geographies() -> dict[str, dict[str, str]]:
    rows = read_csv(GEOS)
    result = {
        r["bps_code"]: r
        for r in rows
        if r.get("parent_geography_id") == "idn.13"
        and r.get("status") == "current"
        and r.get("geography_level") in {"regency", "city"}
    }
    if len(result) != 19:
        raise ValueError(f"expected 19 current Sumbar kab/kota, got {len(result)}")
    return dict(sorted(result.items()))


def var169_map() -> dict[str, dict[str, str]]:
    rows = read_csv(VAR169_MAP)
    result = {r["source_vervar_id"]: r for r in rows}
    if len(result) != 19:
        raise ValueError("var169 map must contain 19 unique source IDs")
    return result


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def value_ok(value: Decimal, rule: str) -> bool:
    if rule == "finite_nonnegative":
        return value >= 0
    if rule == "percent_0_100":
        return Decimal("0") <= value <= Decimal("100")
    raise ValueError(f"unsupported value rule {rule}")


def main() -> int:
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone28-stage2a-numeric-pilot-contract/v1":
        raise ValueError("Stage 2A contract schema drift")
    if contract.get("design_locked_before_values") is not True or contract.get("full_history_materialization_authorized") is not False:
        raise ValueError("Stage 2A boundary drift")
    series = contract.get("series", [])
    if len(series) != 7:
        raise ValueError("Stage 2A requires seven locked series")

    geos = current_geographies()
    local_map = var169_map()
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    OUT_RAW.mkdir(parents=True, exist_ok=True)

    observations: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []

    for spec in series:
        var_id = int(spec["bps_var_id"])
        th_id = source_period_id(var_id, PILOT_YEAR)
        turvar_id = int(spec["selected_turvar_id"])
        turth_id = int(spec["selected_turth_id"])
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        error = ""
        try:
            payload = client.get_dynamic_data(
                domain=DOMAIN,
                var=var_id,
                th=th_id,
                turvar=turvar_id,
                turth=turth_id,
            )
        except BPSApiError as exc:
            payload = {}
            error = str(exc)

        envelope = {
            "snapshot_schema": "ranah-observatory/milestone28-bps-dynamic-snapshot/v1",
            "source_id": "bps_webapi",
            "domain": DOMAIN,
            "retrieved_at_utc": retrieved_at,
            "request": {"var": var_id, "th": th_id, "turvar": turvar_id, "turth": turth_id},
            "result": payload,
        }
        raw_path = OUT_RAW / f"var-{var_id}-2024.json"
        raw_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raw_sha = sha256(raw_path)
        raw_records.append({"bps_var_id": var_id, "path": str(raw_path.relative_to(ROOT)).replace("\\", "/"), "sha256": raw_sha})

        normalized: list[dict[str, Any]] = []
        diagnostics: dict[str, Any] = {}
        if payload:
            try:
                normalized, diagnostics = normalize_dynamic_payload(payload)
            except BPSDynamicNormalizationError as exc:
                error = str(exc)

        selected_by_geo: dict[str, dict[str, Any]] = {}
        duplicate_geographies: list[str] = []
        range_failures: list[str] = []
        selector_failures = 0
        unit_failures = 0
        geography_representation_failures: list[str] = []

        for source in normalized:
            if str(source.get("bps_th_label", "")).strip() != str(PILOT_YEAR):
                continue
            if str(source.get("bps_turvar_id", "")).strip() != str(turvar_id):
                selector_failures += 1
                continue
            if str(source.get("bps_turth_id", "")).strip() != str(turth_id):
                selector_failures += 1
                continue
            if norm_text(source.get("bps_turvar_label", "")) != norm_text(spec["selected_turvar_label"]):
                selector_failures += 1
                continue
            if str(source.get("bps_var_unit", "")).strip() != str(spec["expected_source_unit"]):
                unit_failures += 1
                continue

            source_geo_id = str(source.get("bps_vervar_id", "")).strip()
            source_geo_label = str(source.get("bps_vervar_label", "")).strip()
            canonical_code = ""
            if spec["geography_mode"] == "canonical_bps_code":
                if source_geo_id in geos:
                    canonical_code = source_geo_id
            elif spec["geography_mode"] == "var169_local_ordinal_map":
                mapping = local_map.get(source_geo_id)
                if mapping:
                    if source_geo_label != mapping["source_label"]:
                        geography_representation_failures.append(source_geo_id)
                        continue
                    canonical_code = mapping["bps_code"]
            else:
                raise ValueError(f"unsupported geography mode {spec['geography_mode']}")
            if not canonical_code:
                continue

            try:
                value = decimal_value(source.get("value"))
            except ValueError:
                range_failures.append(canonical_code)
                continue
            if not value_ok(value, spec["value_rule"]):
                range_failures.append(canonical_code)
                continue
            if canonical_code in selected_by_geo:
                duplicate_geographies.append(canonical_code)
                continue
            selected_by_geo[canonical_code] = {"source": source, "value": value}

        missing_codes = sorted(set(geos) - set(selected_by_geo))
        candidate_pass = (
            not error
            and len(selected_by_geo) == 19
            and not missing_codes
            and not duplicate_geographies
            and not range_failures
            and not geography_representation_failures
            and selector_failures == 0
            and unit_failures == 0
        )

        source_meta = normalized[0] if normalized else {}
        provenance.append({
            "candidate_id": spec["candidate_id"],
            "bps_var_id": var_id,
            "year": PILOT_YEAR,
            "resolved_th_id": th_id,
            "selected_turvar_id": turvar_id,
            "selected_turvar_label": spec["selected_turvar_label"],
            "selected_turth_id": turth_id,
            "source_title": source_meta.get("bps_var_label", ""),
            "source_unit": source_meta.get("bps_var_unit", ""),
            "source_definition": source_meta.get("bps_var_definition", ""),
            "source_note": source_meta.get("bps_var_note", ""),
            "source_last_update": source_meta.get("bps_last_update", ""),
            "claim_type": spec["claim_type_2024"],
            "methodology_regime": spec["methodology_regime_2024"],
            "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "raw_snapshot_sha256": raw_sha,
        })

        if candidate_pass:
            for code in sorted(selected_by_geo):
                item = selected_by_geo[code]
                geo = geos[code]
                observations.append({
                    "candidate_id": spec["candidate_id"],
                    "indicator_id": spec["canonical_indicator"],
                    "geography_id": geo["geography_id"],
                    "bps_code": code,
                    "canonical_name": geo["canonical_name"],
                    "year": PILOT_YEAR,
                    "value": decimal_text(item["value"]),
                    "unit": spec["canonical_unit"],
                    "claim_type": spec["claim_type_2024"],
                    "methodology_regime": spec["methodology_regime_2024"],
                    "source_var_id": var_id,
                    "source_vervar_id": item["source"].get("bps_vervar_id", ""),
                    "source_reference_period": item["source"].get("bps_th_label", ""),
                    "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                    "raw_snapshot_sha256": raw_sha,
                })

        audits.append({
            "candidate_id": spec["candidate_id"],
            "bps_var_id": var_id,
            "year": PILOT_YEAR,
            "normalized_source_row_count": len(normalized),
            "normalizer_observed_value_count": diagnostics.get("observed_values", 0),
            "selected_geography_count": len(selected_by_geo),
            "missing_geography_codes": "|".join(missing_codes),
            "duplicate_geography_codes": "|".join(sorted(set(duplicate_geographies))),
            "range_failure_codes": "|".join(sorted(set(range_failures))),
            "geography_representation_failure_ids": "|".join(sorted(set(geography_representation_failures))),
            "selector_failure_count": selector_failures,
            "unit_failure_count": unit_failures,
            "classification": "numeric_pilot_pass" if candidate_pass else "held_numeric_pilot_failed",
            "error": error,
            "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
            "raw_snapshot_sha256": raw_sha,
        })

    observations.sort(key=lambda r: (r["candidate_id"], r["bps_code"]))
    provenance.sort(key=lambda r: r["candidate_id"])
    audits.sort(key=lambda r: r["candidate_id"])
    write_csv(OUT_OBS, list(observations[0]) if observations else ["candidate_id"], observations)
    write_csv(OUT_PROV, list(provenance[0]), provenance)
    write_csv(OUT_AUDIT, list(audits[0]), audits)

    pass_count = sum(r["classification"] == "numeric_pilot_pass" for r in audits)
    full_pass = pass_count == 7 and len(observations) == 133
    manifest = {
        "schema": "ranah-observatory/milestone28-stage2a-numeric-pilot/v1",
        "milestone": 28,
        "pilot_year": PILOT_YEAR,
        "candidate_count": 7,
        "numeric_values_requested": True,
        "numeric_values_inspected": True,
        "raw_dynamic_payloads_frozen": True,
        "candidate_pass_count": pass_count,
        "candidate_hold_count": 7 - pass_count,
        "promoted_observation_count": len(observations),
        "pilot_success": full_pass,
        "full_history_materialization_authorized": False,
        "aggregation_across_geographies_performed": False,
        "aggregation_across_years_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "global_window_shortening_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "raw_snapshots": raw_records,
        "observations_csv": {"path": str(OUT_OBS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_OBS)},
        "provenance_csv": {"path": str(OUT_PROV.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_PROV)},
        "audit_csv": {"path": str(OUT_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_AUDIT)},
        "next_gate": "if and only if pilot_success=true, freeze a separate Stage 2B full-history authorization using the preregistered series-year regimes; otherwise diagnose held candidate(s) without changing value-based selection rules",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pilot_success": full_pass, "candidate_pass_count": pass_count, "observations": len(observations)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
