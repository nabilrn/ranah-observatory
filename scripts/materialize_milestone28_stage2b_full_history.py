#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bps_client import BPSApiError, BPSClient
from normalize_bps_dynamic import BPSDynamicNormalizationError, normalize_dynamic_payload
from materialize_milestone28_stage2a_numeric_pilot import (
    current_geographies,
    decimal_text,
    decimal_value,
    norm_text,
    read_csv,
    sha256,
    source_period_id,
    value_ok,
    var169_map,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "data/manifests/milestone28_stage2b_full_history_contract.json"
SERIES_CONTRACT = ROOT / "data/manifests/milestone28_stage2a_numeric_pilot_contract.json"
PILOT = ROOT / "data/manifests/milestone28_stage2a_numeric_pilot.json"
STAGE1B_DIR = ROOT / "data/processed/bps/m28_stage1b_structure"
OUT_RAW = ROOT / "data/processed/bps/m28_stage2b_full_history"
OUT_OBS = ROOT / "data/analysis/engine/broader_panel_v1/m28-broader-panel-observations.csv"
OUT_PROV = ROOT / "data/analysis/engine/broader_panel_v1/m28-broader-panel-provenance.csv"
OUT_AUDIT = ROOT / "data/analysis/engine/broader_panel_v1/m28-full-history-audit.csv"
OUT_COVERAGE = ROOT / "data/analysis/engine/broader_panel_v1/m28-indicator-year-coverage.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_stage2b_full_history.json"
DOMAIN = "1300"
REGIME_YEARS = list(range(2018, 2026))


def claim_and_method(spec: dict[str, Any], year: int) -> tuple[str, str]:
    claim = spec.get("future_year_claim_overrides", {}).get(str(year), spec["claim_type_2024"])
    method = spec.get("future_year_methodology_overrides", {}).get(str(year), spec["methodology_regime_2024"])
    return str(claim), str(method)


def baseline_title(var_id: int) -> str:
    obj = json.loads((STAGE1B_DIR / f"var-{var_id}-2024-structure.json").read_text(encoding="utf-8"))
    return str(obj.get("source_title", "")).strip()


def baseline_semantic_prechecks() -> None:
    water = json.loads((STAGE1B_DIR / "var-352-2024-structure.json").read_text(encoding="utf-8"))
    water_def = norm_text(water.get("source_definition", ""))
    if "sejak tahun 2019" not in water_def or "backcasting" not in water_def:
        raise ValueError("var352 baseline no longer supports 2019+ SDGs/backcasting contract")
    dependency = json.loads((STAGE1B_DIR / "var-756-2024-structure.json").read_text(encoding="utf-8"))
    dep_note = norm_text(dependency.get("source_note", ""))
    if "tahun 2020" not in dep_note or "long form" not in dep_note or "2021-2024" not in dep_note or "proyeksi" not in dep_note:
        raise ValueError("var756 baseline no longer supports anchor/projection split")
    jkn = json.loads((STAGE1B_DIR / "var-763-2024-structure.json").read_text(encoding="utf-8"))
    jkn_def = norm_text(jkn.get("source_definition", ""))
    if "bpjs mandiri" not in jkn_def or "bpjs pbi" not in jkn_def:
        raise ValueError("var763 baseline JKN definition drift")


def main() -> int:
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        print("error: BPS_API_KEY is required", file=sys.stderr)
        return 2

    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    contract = json.loads(SERIES_CONTRACT.read_text(encoding="utf-8"))
    if auth.get("schema") != "ranah-observatory/milestone28-stage2b-full-history-contract/v1":
        raise ValueError("Stage 2B authorization schema drift")
    if pilot.get("pilot_success") is not True or pilot.get("promoted_observation_count") != 133:
        raise ValueError("Stage 2B requires successful frozen 133-observation pilot")
    if auth.get("numeric_materialization_authorized") is not True:
        raise ValueError("Stage 2B numeric authorization missing")
    if auth.get("authorized_request_count") != 49 or auth.get("maximum_promoted_observation_count") != 931:
        raise ValueError("Stage 2B request/observation footprint drift")
    series = contract.get("series", [])
    if len(series) != 7:
        raise ValueError("series footprint drift")
    baseline_semantic_prechecks()

    geos = current_geographies()
    local_map = var169_map()
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)
    OUT_RAW.mkdir(parents=True, exist_ok=True)

    observations: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    raw_records: list[dict[str, Any]] = []

    total_requests = 0
    for spec in series:
        var_id = int(spec["bps_var_id"])
        requested_years = [int(y) for y in spec["future_full_history_years_if_pilot_passes"]]
        requested_set = set(requested_years)
        title_expected = baseline_title(var_id)

        for year in REGIME_YEARS:
            if year not in requested_set:
                explicit_reason = str(spec.get("explicitly_excluded_years", {}).get(str(year), "")).strip()
                coverage.append({
                    "candidate_id": spec["candidate_id"],
                    "indicator_id": spec["canonical_indicator"],
                    "year": year,
                    "request_authorized": False,
                    "classification": "structured_missing_outside_qualified_source_regime",
                    "observation_count": 0,
                    "reason": explicit_reason or "source period unavailable or outside the preregistered qualified methodology regime",
                })
                continue

            total_requests += 1
            th_id = source_period_id(var_id, year)
            turvar_id = int(spec["selected_turvar_id"])
            turth_id = int(spec["selected_turth_id"])
            retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            error = ""
            try:
                payload = client.get_dynamic_data(domain=DOMAIN, var=var_id, th=th_id, turvar=turvar_id, turth=turth_id)
            except BPSApiError as exc:
                payload = {}
                error = str(exc)

            var_dir = OUT_RAW / f"var-{var_id}"
            var_dir.mkdir(parents=True, exist_ok=True)
            raw_path = var_dir / f"{year}.json"
            envelope = {
                "snapshot_schema": "ranah-observatory/milestone28-bps-dynamic-snapshot/v1",
                "source_id": "bps_webapi",
                "domain": DOMAIN,
                "retrieved_at_utc": retrieved_at,
                "request": {"var": var_id, "th": th_id, "turvar": turvar_id, "turth": turth_id},
                "result": payload,
            }
            raw_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raw_sha = sha256(raw_path)
            raw_records.append({"bps_var_id": var_id, "year": year, "path": str(raw_path.relative_to(ROOT)).replace("\\", "/"), "sha256": raw_sha})

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
            geography_representation_failures: list[str] = []
            selector_failure_count = 0
            unit_failure_count = 0
            title_failure_count = 0

            for source in normalized:
                if str(source.get("bps_th_label", "")).strip() != str(year):
                    continue
                if str(source.get("bps_turvar_id", "")).strip() != str(turvar_id):
                    selector_failure_count += 1
                    continue
                if str(source.get("bps_turth_id", "")).strip() != str(turth_id):
                    selector_failure_count += 1
                    continue
                if norm_text(source.get("bps_turvar_label", "")) != norm_text(spec["selected_turvar_label"]):
                    selector_failure_count += 1
                    continue
                if str(source.get("bps_var_unit", "")).strip() != str(spec["expected_source_unit"]):
                    unit_failure_count += 1
                    continue
                if norm_text(source.get("bps_var_label", "")) != norm_text(title_expected):
                    title_failure_count += 1
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
            candidate_year_pass = (
                not error
                and len(selected_by_geo) == 19
                and not missing_codes
                and not duplicate_geographies
                and not range_failures
                and not geography_representation_failures
                and selector_failure_count == 0
                and unit_failure_count == 0
                and title_failure_count == 0
            )
            classification = "qualified_numeric_candidate_year" if candidate_year_pass else "held_failed_validation"
            claim_type, methodology_regime = claim_and_method(spec, year)
            source_meta = normalized[0] if normalized else {}
            provenance.append({
                "candidate_id": spec["candidate_id"],
                "indicator_id": spec["canonical_indicator"],
                "bps_var_id": var_id,
                "year": year,
                "resolved_th_id": th_id,
                "selected_turvar_id": turvar_id,
                "selected_turvar_label": spec["selected_turvar_label"],
                "selected_turth_id": turth_id,
                "source_title": source_meta.get("bps_var_label", ""),
                "source_unit": source_meta.get("bps_var_unit", ""),
                "source_definition": source_meta.get("bps_var_definition", ""),
                "source_note": source_meta.get("bps_var_note", ""),
                "source_last_update": source_meta.get("bps_last_update", ""),
                "claim_type": claim_type,
                "methodology_regime": methodology_regime,
                "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "raw_snapshot_sha256": raw_sha,
            })

            if candidate_year_pass:
                for code in sorted(selected_by_geo):
                    item = selected_by_geo[code]
                    geo = geos[code]
                    observations.append({
                        "candidate_id": spec["candidate_id"],
                        "indicator_id": spec["canonical_indicator"],
                        "geography_id": geo["geography_id"],
                        "bps_code": code,
                        "canonical_name": geo["canonical_name"],
                        "year": year,
                        "value": decimal_text(item["value"]),
                        "unit": spec["canonical_unit"],
                        "claim_type": claim_type,
                        "methodology_regime": methodology_regime,
                        "source_var_id": var_id,
                        "source_vervar_id": item["source"].get("bps_vervar_id", ""),
                        "source_reference_period": item["source"].get("bps_th_label", ""),
                        "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                        "raw_snapshot_sha256": raw_sha,
                    })

            audits.append({
                "candidate_id": spec["candidate_id"],
                "bps_var_id": var_id,
                "year": year,
                "normalized_source_row_count": len(normalized),
                "normalizer_observed_value_count": diagnostics.get("observed_values", 0),
                "selected_geography_count": len(selected_by_geo),
                "missing_geography_codes": "|".join(missing_codes),
                "duplicate_geography_codes": "|".join(sorted(set(duplicate_geographies))),
                "range_failure_codes": "|".join(sorted(set(range_failures))),
                "geography_representation_failure_ids": "|".join(sorted(set(geography_representation_failures))),
                "selector_failure_count": selector_failure_count,
                "unit_failure_count": unit_failure_count,
                "title_failure_count": title_failure_count,
                "classification": classification,
                "claim_type": claim_type,
                "methodology_regime": methodology_regime,
                "error": error,
                "raw_snapshot_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
                "raw_snapshot_sha256": raw_sha,
            })
            coverage.append({
                "candidate_id": spec["candidate_id"],
                "indicator_id": spec["canonical_indicator"],
                "year": year,
                "request_authorized": True,
                "classification": classification,
                "observation_count": 19 if candidate_year_pass else 0,
                "reason": "" if candidate_year_pass else error or "candidate-year validation failed",
            })

    if total_requests != 49:
        raise ValueError(f"executed request footprint drift before network accounting: {total_requests}")

    observations.sort(key=lambda r: (r["indicator_id"], int(r["year"]), r["bps_code"]))
    provenance.sort(key=lambda r: (r["indicator_id"], int(r["year"])))
    audits.sort(key=lambda r: (r["candidate_id"], int(r["year"])))
    coverage.sort(key=lambda r: (r["indicator_id"], int(r["year"])))
    write_csv(OUT_OBS, list(observations[0]) if observations else ["candidate_id"], observations)
    write_csv(OUT_PROV, list(provenance[0]) if provenance else ["candidate_id"], provenance)
    write_csv(OUT_AUDIT, list(audits[0]) if audits else ["candidate_id"], audits)
    write_csv(OUT_COVERAGE, list(coverage[0]), coverage)

    qualified_cells = sum(r["classification"] == "qualified_numeric_candidate_year" for r in audits)
    held_cells = len(audits) - qualified_cells
    structured_missing = sum(r["classification"] == "structured_missing_outside_qualified_source_regime" for r in coverage)
    full_success = qualified_cells == 49 and held_cells == 0 and structured_missing == 7 and len(observations) == 931
    manifest = {
        "schema": "ranah-observatory/milestone28-stage2b-full-history/v1",
        "milestone": 28,
        "candidate_count": 7,
        "regime_year_count": 8,
        "candidate_year_cell_count": 56,
        "authorized_request_count": 49,
        "executed_request_count": total_requests,
        "qualified_candidate_year_count": qualified_cells,
        "held_candidate_year_count": held_cells,
        "structured_missing_candidate_year_count": structured_missing,
        "promoted_observation_count": len(observations),
        "full_history_success": full_success,
        "raw_dynamic_payloads_frozen": True,
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "cross_year_aggregation_performed": False,
        "cross_indicator_aggregation_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "raw_snapshots": raw_records,
        "observations_csv": {"path": str(OUT_OBS.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_OBS)},
        "provenance_csv": {"path": str(OUT_PROV.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_PROV)},
        "audit_csv": {"path": str(OUT_AUDIT.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_AUDIT)},
        "coverage_csv": {"path": str(OUT_COVERAGE.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_COVERAGE)},
        "next_gate": "install an offline byte-identical rebuild from frozen Stage 2B snapshots and then join the promoted evidence to the existing 19-geography 2018-2025 analytical regime without filling structured missingness",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"success": full_success, "qualified_cells": qualified_cells, "held_cells": held_cells, "structured_missing": structured_missing, "observations": len(observations)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
