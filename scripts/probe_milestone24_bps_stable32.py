#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from bps_client import BPSApiError, BPSClient
from normalize_bps_dynamic import BPSDynamicNormalizationError, normalize_dynamic_payload

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERIES = ROOT / "data/registries/bps_comparative_panel_series.csv"
DEFAULT_GEOS = ROOT / "data/registries/geographies.csv"
DEFAULT_GATE = ROOT / "data/manifests/milestone24_design_gate.json"
DEFAULT_OUTPUT = ROOT / "data/manifests/milestone24_bps_stable32_probe.json"
DEFAULT_COVERAGE = ROOT / "data/analysis/engine/bps_stable32_v1/m24-probe-coverage.csv"

DOMAIN = "0000"
YEARS = list(range(2018, 2026))
EXCLUDED_CODES = {"91", "92", "94", "95", "96", "97"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_digest(payload: Mapping[str, Any]) -> str:
    selected = {
        "var": payload.get("var"),
        "turvar": payload.get("turvar"),
        "labelvervar": payload.get("labelvervar"),
        "vervar": payload.get("vervar"),
        "tahun": payload.get("tahun"),
        "turtahun": payload.get("turtahun"),
        "metadata": payload.get("metadata"),
        "datacontent": payload.get("datacontent"),
        "last_update": payload.get("last_update"),
    }
    encoded = json.dumps(selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def period_map(rows: list[Mapping[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        label = str(row.get("th", row.get("label", "")) or "").strip()
        period_id = str(row.get("th_id", row.get("val", "")) or "").strip()
        if label and period_id:
            if label in result and result[label] != period_id:
                raise ValueError(f"ambiguous period label {label}")
            result[label] = period_id
    return result


def current_provinces(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(path)
    stable: dict[str, dict[str, str]] = {}
    excluded: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("geography_level") != "province" or row.get("status") != "current" or row.get("parent_geography_id") != "idn":
            continue
        code = row.get("bps_code", "")
        if len(code) != 2 or not code.isdigit():
            raise ValueError(f"invalid current province BPS code: {code!r}")
        source_code = code + "00"
        target = excluded if code in EXCLUDED_CODES else stable
        target[source_code] = row
    if len(stable) != 32 or len(excluded) != 6:
        raise ValueError(f"stable/excluded province footprint drift: stable={len(stable)} excluded={len(excluded)}")
    if "1300" not in stable or stable["1300"].get("geography_id") != "idn.13":
        raise ValueError("West Sumatra missing from stable32 geography set")
    return dict(sorted(stable.items())), dict(sorted(excluded.items()))


def load_contracts(path: Path, gate: Mapping[str, Any]) -> list[dict[str, str]]:
    rows = read_csv(path)
    by_id = {row["series_id"]: row for row in rows}
    expected_ids = list(gate["candidate_series_ids"])
    if any(series_id not in by_id for series_id in expected_ids):
        raise ValueError("M24 candidate series missing from M5 comparative registry")
    selected = [by_id[series_id] for series_id in expected_ids]
    if len(selected) != 6:
        raise ValueError("M24 requires exact six candidate contracts")
    for row in selected:
        if row.get("qualification_status") != "qualified_current38":
            raise ValueError(f"M24 candidate lacks prior current38 qualification: {row['series_id']}")
    return selected


def validate_gate(path: Path) -> dict[str, Any]:
    gate = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": "ranah-observatory/milestone24-design-gate/v1",
        "design_locked_before_probe": True,
        "domain": DOMAIN,
        "target_start_year": 2018,
        "target_end_year": 2025,
        "target_year_count": 8,
        "geography_level": "province",
        "stable_geography_count": 32,
        "excluded_current_papua_bps_codes": ["91", "92", "94", "95", "96", "97"],
        "candidate_count": 6,
        "probe_candidate_year_count": 48,
        "exact_selector_reuse_required": True,
        "selector_search_after_probe_authorized": False,
        "imputation_authorized": False,
        "geographic_backcasting_authorized": False,
        "province_district_model_pooling_authorized": False,
        "credential_persistence_authorized": False,
    }
    for key, value in expected.items():
        if gate.get(key) != value:
            raise ValueError(f"M24 design gate drift: {key}={gate.get(key)!r} expected={value!r}")
    return gate


def exact_selector(row: Mapping[str, Any], contract: Mapping[str, str]) -> bool:
    return (
        str(row.get("bps_turvar_id", "")) == contract["selected_turvar_id"]
        and str(row.get("bps_turvar_label", "")) == contract["selected_turvar_label"]
        and str(row.get("bps_turth_id", "")) == contract["selected_turth_id"]
        and str(row.get("bps_turth_label", "")) == contract["selected_turth_label"]
    )


def transform_value(raw: Any, transform: str) -> float:
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("non-finite source value")
    if transform == "identity":
        return value
    if transform == "divide_1000":
        return value / 1000.0
    raise ValueError(f"unsupported transform {transform}")


def probe_contract(
    client: BPSClient,
    contract: dict[str, str],
    stable: dict[str, dict[str, str]],
    excluded: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    var_id = int(contract["bps_var_id"])
    period_rows = client.list_periods(domain=DOMAIN, var=var_id)
    periods = period_map(period_rows)
    coverage_rows: list[dict[str, Any]] = []
    semantic_digests: dict[str, str] = {}

    for year in YEARS:
        period_id = periods.get(str(year), "")
        row: dict[str, Any] = {
            "series_id": contract["series_id"],
            "indicator_id": contract["indicator_id"],
            "bps_var_id": var_id,
            "year": year,
            "period_available": bool(period_id),
            "period_id": period_id,
            "selected_turvar_id": contract["selected_turvar_id"],
            "selected_turvar_label": contract["selected_turvar_label"],
            "selected_turth_id": contract["selected_turth_id"],
            "selected_turth_label": contract["selected_turth_label"],
            "stable32_required_count": 32,
        }
        if not period_id:
            row.update({
                "vertical_dimension": "",
                "source_title": "",
                "source_unit": "",
                "source_last_update": "",
                "selected_row_count_all_geographies": 0,
                "stable32_selected_count": 0,
                "missing_stable32_codes": "|".join(stable),
                "selected_excluded_current_codes": "",
                "nonfinite_stable32_value_count": 0,
                "expected_source_unit_match": False,
                "exact_selector_labels_match": False,
                "probe_pass": False,
                "hold_reasons": "period_unavailable",
                "semantic_sha256": "",
            })
            coverage_rows.append(row)
            continue

        payload = client.get_dynamic_data(domain=DOMAIN, var=var_id, th=period_id)
        normalized, diagnostics = normalize_dynamic_payload(payload)
        selected = [source for source in normalized if exact_selector(source, contract)]
        by_code: dict[str, list[dict[str, Any]]] = {}
        for source in selected:
            by_code.setdefault(str(source["bps_vervar_id"]), []).append(source)
        stable_selected = {code: items for code, items in by_code.items() if code in stable}
        missing = sorted(set(stable) - set(stable_selected))
        duplicates = sorted(code for code, items in stable_selected.items() if len(items) != 1)
        excluded_present = sorted(code for code in by_code if code in excluded)
        vertical_dimensions = {str(source["bps_vertical_dimension"]) for source in selected}
        source_titles = {str(source["bps_var_label"]) for source in selected}
        source_units = {str(source["bps_var_unit"]) for source in selected}
        source_updates = {str(source["bps_last_update"]) for source in selected}
        selector_labels_match = all(exact_selector(source, contract) for source in selected)
        finite_failures = 0
        for code, items in stable_selected.items():
            if len(items) != 1:
                continue
            try:
                transform_value(items[0]["value"], contract["transform"])
            except (TypeError, ValueError):
                finite_failures += 1
        expected_unit = contract.get("source_unit", "")
        source_unit = next(iter(source_units)) if len(source_units) == 1 else "|".join(sorted(source_units))
        unit_match = (not expected_unit) or (len(source_units) == 1 and source_unit.casefold() == expected_unit.casefold())
        vertical = next(iter(vertical_dimensions)) if len(vertical_dimensions) == 1 else "|".join(sorted(vertical_dimensions))
        is_province = len(vertical_dimensions) == 1 and "provinsi" in vertical.casefold()
        reasons: list[str] = []
        if not is_province:
            reasons.append("vertical_not_province")
        if missing:
            reasons.append("stable32_missing")
        if duplicates:
            reasons.append("stable32_duplicate")
        if finite_failures:
            reasons.append("nonfinite_value")
        if not unit_match:
            reasons.append("source_unit_drift")
        if not selected:
            reasons.append("selector_no_rows")
        if not selector_labels_match:
            reasons.append("selector_label_drift")
        passed = not reasons and len(stable_selected) == 32
        digest = semantic_digest(payload)
        semantic_digests[str(year)] = digest
        row.update({
            "vertical_dimension": vertical,
            "source_title": next(iter(source_titles)) if len(source_titles) == 1 else "|".join(sorted(source_titles)),
            "source_unit": source_unit,
            "source_last_update": next(iter(source_updates)) if len(source_updates) == 1 else "|".join(sorted(source_updates)),
            "selected_row_count_all_geographies": len(selected),
            "stable32_selected_count": len(stable_selected),
            "missing_stable32_codes": "|".join(missing),
            "duplicate_stable32_codes": "|".join(duplicates),
            "selected_excluded_current_codes": "|".join(excluded_present),
            "nonfinite_stable32_value_count": finite_failures,
            "expected_source_unit_match": unit_match,
            "exact_selector_labels_match": bool(selected) and selector_labels_match,
            "probe_pass": passed,
            "hold_reasons": "|".join(reasons),
            "normalizer_observed_values": diagnostics["observed_values"],
            "semantic_sha256": digest,
        })
        coverage_rows.append(row)

    passed_years = [int(row["year"]) for row in coverage_rows if row["probe_pass"]]
    candidate = {
        "series_id": contract["series_id"],
        "indicator_id": contract["indicator_id"],
        "bps_var_id": var_id,
        "requested_years": YEARS,
        "passed_years": passed_years,
        "passed_year_count": len(passed_years),
        "qualification_status": "stable32_2018_2025_probe_qualified" if passed_years == YEARS else "held_probe_incomplete",
        "semantic_sha256_by_year": semantic_digests,
    }
    return coverage_rows, candidate


def run_probe(series_path: Path, geos_path: Path, gate_path: Path, output_path: Path, coverage_path: Path) -> dict[str, Any]:
    api_key = os.environ.get("BPS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("BPS_API_KEY is required")
    gate = validate_gate(gate_path)
    stable, excluded = current_provinces(geos_path)
    contracts = load_contracts(series_path, gate)
    client = BPSClient(api_key, retries=3, retry_backoff_seconds=1.0)

    coverage_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for contract in contracts:
        rows, candidate = probe_contract(client, contract, stable, excluded)
        coverage_rows.extend(rows)
        candidates.append(candidate)

    if len(coverage_rows) != 48:
        raise ValueError(f"M24 probe footprint must be 48 candidate-years; got {len(coverage_rows)}")
    qualified = [item["series_id"] for item in candidates if item["qualification_status"] == "stable32_2018_2025_probe_qualified"]
    report = {
        "schema": "ranah-observatory/milestone24-bps-stable32-probe/v1",
        "milestone": 24,
        "phase": "post_phase2_national_comparator_expansion",
        "source_id": "bps_webapi",
        "domain": DOMAIN,
        "target_years": YEARS,
        "stable_geography_count": len(stable),
        "stable_source_codes": list(stable),
        "excluded_current_papua_source_codes": list(excluded),
        "candidate_count": len(candidates),
        "candidate_year_probe_count": len(coverage_rows),
        "qualified_candidate_count": len(qualified),
        "qualified_series_ids": qualified,
        "candidates": candidates,
        "exact_selector_reuse_required": True,
        "selector_search_after_probe_performed": False,
        "imputation_performed": False,
        "geographic_backcasting_performed": False,
        "province_district_model_pooling_performed": False,
        "credential_persisted": False,
        "inputs": {
            "series_registry": {"path": str(series_path.relative_to(ROOT)), "sha256": sha256(series_path)},
            "geography_registry": {"path": str(geos_path.relative_to(ROOT)), "sha256": sha256(geos_path)},
            "design_gate": {"path": str(gate_path.relative_to(ROOT)), "sha256": sha256(gate_path)},
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fields = list(coverage_rows[0].keys())
    write_csv(coverage_path, fields, coverage_rows)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe BPS national-domain M24 stable-32 comparator candidates.")
    parser.add_argument("--series", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOS)
    parser.add_argument("--design-gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    args = parser.parse_args()
    try:
        report = run_probe(args.series, args.geographies, args.design_gate, args.output, args.coverage)
    except (BPSApiError, BPSDynamicNormalizationError, OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "qualified_candidate_count": report["qualified_candidate_count"],
        "qualified_series_ids": report["qualified_series_ids"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
