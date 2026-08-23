#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from normalize_bps_dynamic import BPSDynamicNormalizationError, normalize_dynamic_payload
from materialize_milestone28_stage2a_numeric_pilot import (
    current_geographies,
    decimal_text,
    decimal_value,
    norm_text,
    value_ok,
    var169_map,
)
from materialize_milestone28_stage2b_full_history import (
    baseline_semantic_prechecks,
    baseline_title,
    claim_and_method,
)

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data/manifests/milestone28_stage2b_full_history.json"
AUTH = ROOT / "data/manifests/milestone28_stage2b_full_history_contract.json"
SERIES_CONTRACT = ROOT / "data/manifests/milestone28_stage2a_numeric_pilot_contract.json"
OUT_CERT = ROOT / "data/manifests/milestone28_stage2b_offline_reproducibility.json"
REGIME_YEARS = list(range(2018, 2026))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_bytes(fields: list[str], rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def main() -> int:
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    contract = json.loads(SERIES_CONTRACT.read_text(encoding="utf-8"))
    if live.get("schema") != "ranah-observatory/milestone28-stage2b-full-history/v1" or live.get("full_history_success") is not True:
        raise ValueError("M28 frozen full history is not qualified")
    if auth.get("schema") != "ranah-observatory/milestone28-stage2b-full-history-contract/v1":
        raise ValueError("M28 Stage 2B authorization drift")
    if live.get("authorized_request_count") != 49 or live.get("promoted_observation_count") != 931:
        raise ValueError("M28 frozen full-history footprint drift")

    baseline_semantic_prechecks()
    series = contract.get("series", [])
    if len(series) != 7:
        raise ValueError("M28 series contract footprint drift")
    geos = current_geographies()
    local_map = var169_map()

    raw_index: dict[tuple[int, int], dict[str, Any]] = {}
    for item in live.get("raw_snapshots", []):
        var_id = int(item["bps_var_id"])
        year = int(item["year"])
        path = ROOT / item["path"]
        if sha256_path(path) != item["sha256"]:
            raise ValueError(f"raw snapshot checksum drift: {path}")
        if (var_id, year) in raw_index:
            raise ValueError(f"duplicate raw snapshot manifest key: {(var_id, year)}")
        raw_index[(var_id, year)] = item
    if len(raw_index) != 49:
        raise ValueError(f"expected 49 unique frozen snapshots, got {len(raw_index)}")

    observations: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    replayed = 0

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

            item = raw_index.get((var_id, year))
            if item is None:
                raise ValueError(f"missing frozen snapshot for var={var_id}, year={year}")
            raw_path = ROOT / item["path"]
            envelope = json.loads(raw_path.read_text(encoding="utf-8"))
            request = envelope.get("request") or {}
            payload = envelope.get("result") or {}
            th_id = str(request.get("th", "")).strip()
            turvar_id = int(spec["selected_turvar_id"])
            turth_id = int(spec["selected_turth_id"])
            if int(request.get("var")) != var_id or int(request.get("turvar")) != turvar_id or int(request.get("turth")) != turth_id:
                raise ValueError(f"frozen request selector drift var={var_id}, year={year}")

            error = ""
            normalized: list[dict[str, Any]] = []
            diagnostics: dict[str, Any] = {}
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
            raw_rel = item["path"]
            raw_sha = item["sha256"]

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
                "raw_snapshot_path": raw_rel,
                "raw_snapshot_sha256": raw_sha,
            })

            if candidate_year_pass:
                for code in sorted(selected_by_geo):
                    selected = selected_by_geo[code]
                    geo = geos[code]
                    observations.append({
                        "candidate_id": spec["candidate_id"],
                        "indicator_id": spec["canonical_indicator"],
                        "geography_id": geo["geography_id"],
                        "bps_code": code,
                        "canonical_name": geo["canonical_name"],
                        "year": year,
                        "value": decimal_text(selected["value"]),
                        "unit": spec["canonical_unit"],
                        "claim_type": claim_type,
                        "methodology_regime": methodology_regime,
                        "source_var_id": var_id,
                        "source_vervar_id": selected["source"].get("bps_vervar_id", ""),
                        "source_reference_period": selected["source"].get("bps_th_label", ""),
                        "raw_snapshot_path": raw_rel,
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
                "raw_snapshot_path": raw_rel,
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
            replayed += 1

    if replayed != 49:
        raise ValueError(f"offline replay request footprint drift: {replayed}")
    observations.sort(key=lambda r: (r["indicator_id"], int(r["year"]), r["bps_code"]))
    provenance.sort(key=lambda r: (r["indicator_id"], int(r["year"])))
    audits.sort(key=lambda r: (r["candidate_id"], int(r["year"])))
    coverage.sort(key=lambda r: (r["indicator_id"], int(r["year"])))

    generated = {
        "observations_csv": csv_bytes(list(observations[0]), observations),
        "provenance_csv": csv_bytes(list(provenance[0]), provenance),
        "audit_csv": csv_bytes(list(audits[0]), audits),
        "coverage_csv": csv_bytes(list(coverage[0]), coverage),
    }
    comparisons: dict[str, dict[str, Any]] = {}
    all_identical = True
    for key, payload in generated.items():
        live_item = live[key]
        live_path = ROOT / live_item["path"]
        live_bytes = live_path.read_bytes()
        identical = payload == live_bytes
        generated_sha = sha256_bytes(payload)
        live_sha = sha256_bytes(live_bytes)
        if live_sha != live_item["sha256"]:
            raise ValueError(f"live canonical checksum drift for {key}")
        comparisons[key] = {
            "path": live_item["path"],
            "generated_sha256": generated_sha,
            "live_sha256": live_sha,
            "byte_identical": identical,
        }
        all_identical = all_identical and identical

    qualified = sum(r["classification"] == "qualified_numeric_candidate_year" for r in audits)
    structured_missing = sum(r["classification"] == "structured_missing_outside_qualified_source_regime" for r in coverage)
    rebuild_success = all_identical and qualified == 49 and structured_missing == 7 and len(observations) == 931
    cert = {
        "schema": "ranah-observatory/milestone28-stage2b-offline-reproducibility/v1",
        "milestone": 28,
        "stage": "stage2b_offline_byte_identical_rebuild",
        "offline_only": True,
        "network_requests_performed": False,
        "raw_snapshot_count_verified": len(raw_index),
        "replayed_candidate_year_count": replayed,
        "qualified_candidate_year_count": qualified,
        "structured_missing_candidate_year_count": structured_missing,
        "promoted_observation_count": len(observations),
        "outputs": comparisons,
        "all_outputs_byte_identical": all_identical,
        "rebuild_success": rebuild_success,
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "cross_year_aggregation_performed": False,
        "cross_indicator_aggregation_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
    }
    OUT_CERT.write_text(json.dumps(cert, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not rebuild_success:
        raise ValueError("M28 offline rebuild is not byte-identical")
    print(json.dumps({"rebuild_success": True, "candidate_years": qualified, "structured_missing": structured_missing, "observations": len(observations)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
