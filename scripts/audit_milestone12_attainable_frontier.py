#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE12_ATTAINABLE_FRONTIER_SPEC.md"
GATE = ROOT / "data/manifests/milestone12_design_gate.json"
METHODS = ROOT / "data/registries/milestone12_frontier_method_qualification.csv"
MANIFEST = ROOT / "data/manifests/milestone12_attainable_frontier.json"
M11_MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M11_PRED = ROOT / "data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv"
M11_FRAME = ROOT / "data/analysis/engine/expected_performance_v2/m11-model-frame.csv"
M7_CV = ROOT / "data/analysis/expected_performance/m7-ridge-selected-loocv-predictions.csv"
M7_WS = ROOT / "data/analysis/expected_performance/m7-west-sumatra-expected-performance.json"
DISTRICT = ROOT / "data/analysis/engine/frontier_v1/m12-district-frontier.csv"
SUMMARY = ROOT / "data/analysis/engine/frontier_v1/m12-district-method-summary.csv"
NEIGHBOR_SENS = ROOT / "data/analysis/engine/frontier_v1/m12-neighbor-sensitivity.csv"
NATIONAL = ROOT / "data/analysis/engine/frontier_v1/m12-national-west-sumatra-frontier.json"

TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
DIRECTION = {
    "poverty_rate": "lower_is_favorable",
    "unemployment_rate": "lower_is_favorable",
    "real_grdp_growth": "higher_is_favorable",
}
PRIMARY_FEATURES = [
    "mean_years_schooling",
    "labor_force_participation",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
]
LOW_Q = 0.10
HIGH_Q = 0.90
CAL_MIN = 0.04
CAL_MAX = 0.20


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def f(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid numeric field {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric field {key}")
    return value


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("mean requires values")
    return sum(values) / len(values)


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires values")
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return abs(a - b) <= tolerance * max(1.0, abs(a), abs(b))


def favorable_quantile(target: str) -> float:
    return LOW_Q if DIRECTION[target] == "lower_is_favorable" else HIGH_Q


def distance(target: str, observed: float, reference: float) -> float:
    return observed - reference if DIRECTION[target] == "lower_is_favorable" else reference - observed


def exceeded(target: str, observed: float, reference: float) -> bool:
    return observed <= reference if DIRECTION[target] == "lower_is_favorable" else observed >= reference


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [SPEC, GATE, METHODS, MANIFEST, M11_MANIFEST, M11_PRED, M11_FRAME, M7_CV, M7_WS, DISTRICT, SUMMARY, NEIGHBOR_SENS, NATIONAL]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {"schema": "ranah-observatory/milestone12-audit/v1", "errors": [f"missing required file: {path}" for path in missing], "milestone12_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m11 = json.loads(M11_MANIFEST.read_text(encoding="utf-8"))
    method_rows = rows(METHODS)
    district = rows(DISTRICT)
    summary = rows(SUMMARY)
    neighbor_sensitivity = rows(NEIGHBOR_SENS)
    m11_predictions = rows(M11_PRED)
    m11_frame = rows(M11_FRAME)
    m7_cv = rows(M7_CV)
    m7_ws = json.loads(M7_WS.read_text(encoding="utf-8"))
    national = json.loads(NATIONAL.read_text(encoding="utf-8"))

    if m11.get("milestone11_complete") is not True or set(m11.get("benchmark_qualified_target_ids", [])) != set(TARGETS):
        errors.append("M12 requires completed benchmark-qualified M11 target set")

    expected_gate = {
        "schema": "ranah-observatory/milestone12-design-gate/v1",
        "district_primary_method": "conditional_favorable_residual_quantile",
        "district_alternative_method": "structural_neighbor_favorable_envelope",
        "district_target_ids": TARGETS,
        "lower_is_favorable_quantile": LOW_Q,
        "higher_is_favorable_quantile": HIGH_Q,
        "calibration_rate_min": CAL_MIN,
        "calibration_rate_max": CAL_MAX,
        "neighbor_k": 6,
        "neighbor_favorable_count": 2,
        "neighbor_k_sensitivity": [5, 7],
        "national_target_id": "real_grdp_per_capita",
        "national_reference_year": 2024,
        "national_favorable_residual_quantile": HIGH_Q,
        "frontier_computed": False,
        "frontier_results_inspected": False,
        "theoretical_maximum_claim_authorized": False,
        "causal_claim_authorized": False,
        "policy_counterfactual_claim_authorized": False,
        "monetary_wasted_potential_claim_authorized": False,
        "milestone12_complete": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            errors.append(f"M12 prefit design-gate drift: {key}")
    for flag in ["methods_selected_before_frontier_results", "quantiles_selected_before_frontier_results", "calibration_band_selected_before_frontier_results", "neighbor_parameters_selected_before_frontier_results"]:
        if gate.get(flag) is not True:
            errors.append(f"M12 prefit lock flag lost: {flag}")

    method_status = {row.get("method_id"): row.get("qualification_status") for row in method_rows}
    expected_status = {
        "conditional_favorable_residual_quantile": "qualified",
        "structural_neighbor_favorable_envelope": "qualified",
        "national_m7_favorable_residual_quantile": "qualified",
        "classic_dea": "rejected",
        "classic_halfnormal_sfa": "deferred",
        "linear_quantile_regression": "deferred",
    }
    if method_status != expected_status:
        errors.append("M12 method qualification registry drift")

    expected_manifest = {
        "schema": "ranah-observatory/milestone12-attainable-frontier/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 12,
        "district_row_count": 342,
        "district_method_summary_row_count": 3,
        "neighbor_sensitivity_row_count": 684,
        "district_primary_method": "conditional_favorable_residual_quantile",
        "district_alternative_method": "structural_neighbor_favorable_envelope",
        "lower_is_favorable_quantile": LOW_Q,
        "higher_is_favorable_quantile": HIGH_Q,
        "calibration_rate_band": [CAL_MIN, CAL_MAX],
        "neighbor_k": 6,
        "neighbor_favorable_count": 2,
        "neighbor_k_sensitivity": [5, 7],
        "focal_geography_excluded_from_primary_frontier_calibration": True,
        "same_year_nonfocal_peers_only_for_neighbor_method": True,
        "frontier_distance_truncated_at_zero": False,
        "posthoc_quantile_retuning_performed": False,
        "posthoc_neighbor_parameter_replacement_performed": False,
        "classic_dea_computed": False,
        "classic_halfnormal_sfa_computed": False,
        "linear_quantile_regression_computed": False,
        "theoretical_maximum_claim": False,
        "causal_claim": False,
        "policy_counterfactual_claim": False,
        "monetary_wasted_potential_claim": False,
        "national_population_aggregation_performed": False,
        "national_multi_year_loss_accumulation_performed": False,
        "milestone12_complete": True,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            errors.append(f"M12 manifest contract drift: {key}")
    if manifest.get("method_qualification_status") != expected_status:
        errors.append("M12 manifest method-status drift")

    for path_string, digest in manifest.get("source_inputs", {}).items():
        path = ROOT / path_string
        if not path.exists() or sha256(path) != digest:
            errors.append(f"M12 source checksum drift: {path_string}")
    output_map = {
        "district_frontier": DISTRICT,
        "district_method_summary": SUMMARY,
        "neighbor_sensitivity": NEIGHBOR_SENS,
        "national_west_sumatra_frontier": NATIONAL,
    }
    for key, path in output_map.items():
        record = manifest.get("outputs", {}).get(key, {})
        if record.get("path") != str(path.relative_to(ROOT)) or record.get("sha256") != sha256(path):
            errors.append(f"M12 output checksum/path drift: {key}")

    if len(district) != 342:
        errors.append(f"M12 district frontier must contain 342 rows, got {len(district)}")
    district_keys = {(row.get("target_id"), row.get("geography_id"), row.get("target_year")) for row in district}
    if len(district_keys) != 342:
        errors.append("M12 district frontier keys are not unique")
    m11_by_key = {(row["target_id"], row["geography_id"], row["target_year"]): row for row in m11_predictions}
    frame_by_key = {(row["geography_id"], row["target_year"]): row for row in m11_frame}
    if len(m11_by_key) != 342 or len(frame_by_key) != 114:
        errors.append("M12 M11 input key footprint drift")

    district_by_target: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in district:
        target = row.get("target_id", "")
        district_by_target[target].append(row)
        key = (target, row.get("geography_id", ""), row.get("target_year", ""))
        m11_row = m11_by_key.get(key)
        if m11_row is None:
            errors.append(f"M12 row lacks M11 source prediction: {key}")
            continue
        if row.get("claim_type") != "model_estimate" or row.get("frontier_scope") != "empirical_favorable_peer_reference":
            errors.append(f"M12 frontier claim-type/scope drift: {key}")
        for flag in ["theoretical_maximum_claim", "causal_claim", "policy_counterfactual_claim", "monetary_wasted_potential_claim"]:
            if row.get(flag) != "false":
                errors.append(f"M12 forbidden row-level claim flag: {key}/{flag}")
        if row.get("m11_benchmark_qualified") != m11_row.get("benchmark_qualified") or row.get("m11_support_warning") != m11_row.get("support_warning"):
            errors.append(f"M12 failed to inherit M11 gate/support flags: {key}")
        if not close(f(row, "observed"), f(m11_row, "observed")) or not close(f(row, "m11_expected"), f(m11_row, "expected")):
            errors.append(f"M12 failed to preserve M11 observed/expected values: {key}")

        target_rows = [candidate for candidate in m11_predictions if candidate["target_id"] == target]
        calibration = [f(candidate, "residual_observed_minus_expected") for candidate in target_rows if candidate["geography_id"] != row["geography_id"]]
        if len(calibration) != 108:
            errors.append(f"M12 primary calibration count drift: {key}")
            continue
        q = favorable_quantile(target)
        expected_q = quantile(calibration, q)
        expected_reference = f(m11_row, "expected") + expected_q
        expected_distance = distance(target, f(m11_row, "observed"), expected_reference)
        expected_exceeded = exceeded(target, f(m11_row, "observed"), expected_reference)
        if not close(f(row, "primary_favorable_quantile"), q):
            errors.append(f"M12 favorable quantile drift: {key}")
        if not close(f(row, "primary_favorable_residual_quantile_value"), expected_q, 1e-8):
            errors.append(f"M12 favorable residual quantile mismatch: {key}")
        if not close(f(row, "primary_favorable_reference"), expected_reference, 1e-8):
            errors.append(f"M12 primary reference mismatch: {key}")
        if not close(f(row, "primary_distance_to_favorable_reference"), expected_distance, 1e-8):
            errors.append(f"M12 primary distance mismatch: {key}")
        if (row.get("primary_observed_meets_or_exceeds_favorable_reference") == "true") != expected_exceeded:
            errors.append(f"M12 favorable exceedance flag mismatch: {key}")
        if row.get("primary_focal_excluded_calibration_residual_count") != "108":
            errors.append(f"M12 focal-excluded calibration footprint mismatch: {key}")

        neighbor_ids = row.get("alternative_favorable_neighbor_ids", "").split("|")
        if len(neighbor_ids) != 2 or row.get("geography_id") in neighbor_ids or len(set(neighbor_ids)) != 2:
            errors.append(f"M12 k6 favorable-neighbor IDs invalid: {key}")
        frame = frame_by_key.get((row["geography_id"], row["target_year"]))
        if frame is None:
            errors.append(f"M12 alternative method lacks frame row: {key}")
        peer_frame = [candidate for (geo, year), candidate in frame_by_key.items() if year == row["target_year"] and geo != row["geography_id"]]
        if len(peer_frame) != 18:
            errors.append(f"M12 alternative same-year peer footprint drift: {key}")
        valid_peer_ids = {candidate["geography_id"] for candidate in peer_frame}
        if any(peer not in valid_peer_ids for peer in neighbor_ids):
            errors.append(f"M12 alternative method uses non-same-year/non-peer geography: {key}")
        outcome_values = [float(value) for value in row.get("alternative_favorable_neighbor_outcomes", "").split("|") if value]
        if len(outcome_values) != 2 or not close(mean(outcome_values), f(row, "alternative_favorable_reference"), 1e-8):
            errors.append(f"M12 alternative favorable-neighbor mean mismatch: {key}")
        if not close(distance(target, f(row, "observed"), f(row, "alternative_favorable_reference")), f(row, "alternative_distance_to_favorable_reference"), 1e-8):
            errors.append(f"M12 alternative distance mismatch: {key}")

    summary_by_target = {row.get("target_id", ""): row for row in summary}
    if len(summary) != 3 or set(summary_by_target) != set(TARGETS):
        errors.append("M12 district method summary must contain exactly three targets")
    calibrated_targets: list[str] = []
    uncalibrated_targets: list[str] = []
    for target in TARGETS:
        target_rows = district_by_target.get(target, [])
        if len(target_rows) != 114:
            errors.append(f"M12 target row count must be 114: {target}")
            continue
        exceed_count = sum(row.get("primary_observed_meets_or_exceeds_favorable_reference") == "true" for row in target_rows)
        exceed_rate = exceed_count / len(target_rows)
        calibrated = CAL_MIN <= exceed_rate <= CAL_MAX
        summary_row = summary_by_target.get(target)
        if summary_row is None:
            continue
        if int(summary_row["primary_favorable_exceedance_count"]) != exceed_count or not close(f(summary_row, "primary_favorable_exceedance_rate"), exceed_rate, 1e-8):
            errors.append(f"M12 calibration summary mismatch: {target}")
        if (summary_row.get("primary_frontier_calibrated") == "true") != calibrated:
            errors.append(f"M12 calibration pass/fail mismatch: {target}")
        for row in target_rows:
            expected_authorized = row.get("m11_benchmark_qualified") == "true" and calibrated and row.get("m11_support_warning") == "false"
            if (row.get("primary_frontier_calibrated") == "true") != calibrated:
                errors.append(f"M12 row calibration flag mismatch: {target}")
            if (row.get("primary_frontier_interpretation_authorized") == "true") != expected_authorized:
                errors.append(f"M12 row interpretation authorization mismatch: {target}/{row.get('geography_id')}/{row.get('target_year')}")
        (calibrated_targets if calibrated else uncalibrated_targets).append(target)

    if set(manifest.get("primary_frontier_calibrated_target_ids", [])) != set(calibrated_targets):
        errors.append("M12 manifest calibrated-target set mismatch")
    if set(manifest.get("primary_frontier_uncalibrated_target_ids", [])) != set(uncalibrated_targets):
        errors.append("M12 manifest uncalibrated-target set mismatch")
    if manifest.get("primary_frontier_calibrated_target_count") != len(calibrated_targets):
        errors.append("M12 manifest calibrated-target count mismatch")

    if len(neighbor_sensitivity) != 684:
        errors.append(f"M12 neighbor sensitivity must contain 684 rows, got {len(neighbor_sensitivity)}")
    sensitivity_keys = {(row.get("target_id"), row.get("geography_id"), row.get("target_year"), row.get("k_neighbors")) for row in neighbor_sensitivity}
    if len(sensitivity_keys) != 684:
        errors.append("M12 neighbor-sensitivity keys are not unique")
    for row in neighbor_sensitivity:
        if row.get("k_neighbors") not in {"5", "7"} or row.get("favorable_neighbor_count") != "2":
            errors.append("M12 neighbor sensitivity parameters drift")
        if row.get("sensitivity_can_replace_locked_k6") != "false":
            errors.append("M12 sensitivity is not allowed to replace locked k6 method")
        ids = row.get("favorable_neighbor_ids", "").split("|")
        if len(ids) != 2 or row.get("geography_id") in ids:
            errors.append("M12 neighbor sensitivity contains invalid focal/neighbor IDs")

    if len(m7_cv) != 37:
        errors.append("M12 national anchor requires 37 M7 non-Sumbar crossfit residuals")
    else:
        residuals = [f(row, "residual_log_observed_minus_predicted") for row in m7_cv]
        q90 = quantile(residuals, HIGH_Q)
        predicted_log = float(m7_ws["predicted_log_target"])
        observed = float(m7_ws["observed_level"])
        expected_frontier_log = predicted_log + q90
        expected_frontier = math.exp(expected_frontier_log)
        if national.get("schema") != "ranah-observatory/milestone12-national-west-sumatra-frontier/v1":
            errors.append("M12 national frontier schema drift")
        numeric_expected = {
            "favorable_log_residual_quantile": q90,
            "m7_predicted_log_target": predicted_log,
            "observed_level": observed,
            "conditional_favorable_log_reference": expected_frontier_log,
            "conditional_favorable_level": expected_frontier,
            "distance_frontier_minus_observed_level": expected_frontier - observed,
            "observed_to_favorable_reference_ratio": observed / expected_frontier,
            "percent_distance_relative_to_favorable_reference": (1.0 - observed / expected_frontier) * 100.0,
        }
        for key, expected in numeric_expected.items():
            if not close(float(national[key]), expected, 1e-9):
                errors.append(f"M12 national frontier arithmetic mismatch: {key}")
        exceed_count = sum(value >= q90 for value in residuals)
        if national.get("non_sumbar_empirical_favorable_exceedance_count") != exceed_count or not close(float(national["non_sumbar_empirical_favorable_exceedance_rate"]), exceed_count / 37, 1e-9):
            errors.append("M12 national favorable-exceedance calibration mismatch")
        for flag in ["theoretical_maximum_claim", "causal_claim", "policy_counterfactual_claim", "monetary_wasted_potential_claim", "population_aggregation_performed", "multi_year_loss_accumulation_performed"]:
            if national.get(flag) is not False:
                errors.append(f"M12 forbidden national claim/aggregation flag: {flag}")
        if national.get("claim_type") != "model_estimate" or national.get("frontier_scope") != "empirical_favorable_peer_reference":
            errors.append("M12 national claim scope drift")

    required_phrases = [
        "does not estimate a physical maximum",
        "Distances are **not truncated at zero**",
        "M12 must not retune the quantile after seeing calibration",
        "Disagreement is itself an uncertainty signal",
        "must not be multiplied by population or accumulated over years",
        "this is the maximum West Sumatra can achieve",
        "West Sumatra lost Rp X",
    ]
    for phrase in required_phrases:
        if phrase not in spec:
            errors.append(f"M12 spec lost required guardrail phrase: {phrase}")

    return {
        "schema": "ranah-observatory/milestone12-audit/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 12,
        "district_row_count": len(district),
        "neighbor_sensitivity_row_count": len(neighbor_sensitivity),
        "calibrated_target_ids": calibrated_targets,
        "uncalibrated_target_ids": uncalibrated_targets,
        "calibrated_target_count": len(calibrated_targets),
        "national_anchor_present": national.get("geography_id") == "idn.13",
        "prefit_design_gate_preserved": gate.get("frontier_computed") is False and gate.get("frontier_results_inspected") is False,
        "m11_complete": m11.get("milestone11_complete") is True,
        "theoretical_maximum_claim": manifest.get("theoretical_maximum_claim") is True,
        "causal_claim": manifest.get("causal_claim") is True,
        "monetary_wasted_potential_claim": manifest.get("monetary_wasted_potential_claim") is True,
        "milestone12_complete": manifest.get("milestone12_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 12 Attainable Frontier Engine")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone12_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
