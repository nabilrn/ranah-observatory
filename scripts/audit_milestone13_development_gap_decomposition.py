#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE13_DEVELOPMENT_GAP_DECOMPOSITION_SPEC.md"
GATE = ROOT / "data/manifests/milestone13_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone13_development_gap_decomposition.json"
M11_MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M12_MANIFEST = ROOT / "data/manifests/milestone12_attainable_frontier.json"
M11_PRED = ROOT / "data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv"
M11_SUMMARY = ROOT / "data/analysis/engine/expected_performance_v2/m11-target-summary.csv"
M12_DISTRICT = ROOT / "data/analysis/engine/frontier_v1/m12-district-frontier.csv"
M12_NATIONAL = ROOT / "data/analysis/engine/frontier_v1/m12-national-west-sumatra-frontier.json"
GAP = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv"
PERSISTENCE = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-persistence-by-geography-target.csv"
PROFILES = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-geography-profiles.csv"
NATIONAL = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-national-income-anchor.json"

TARGETS = ["poverty_rate", "unemployment_rate", "real_grdp_growth"]
DIMENSIONS = {
    "poverty_rate": "living_standards_inclusion",
    "unemployment_rate": "labor_market",
    "real_grdp_growth": "economic_dynamism",
}
DIRECTION = {
    "poverty_rate": "lower_is_favorable",
    "unemployment_rate": "lower_is_favorable",
    "real_grdp_growth": "higher_is_favorable",
}
MIN_AUTH = 4
PERSIST_THRESHOLD = 2.0 / 3.0
MEETS_THRESHOLD = 1.0 / 3.0
TARGET_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def num(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"invalid numeric field {key}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric field {key}")
    return value


def close(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("median needs values")
    return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def sign(value: float, eps: float = 1e-12) -> int:
    return 1 if value > eps else -1 if value < -eps else 0


def interval_class(target: str, observed: float, lower: float, upper: float) -> str:
    if DIRECTION[target] == "lower_is_favorable":
        if observed > upper:
            return "materially_less_favorable_than_expected"
        if observed < lower:
            return "materially_more_favorable_than_expected"
    else:
        if observed < lower:
            return "materially_less_favorable_than_expected"
        if observed > upper:
            return "materially_more_favorable_than_expected"
    return "within_expected_interval"


def persistence_label(authorized: int, rate: float | None) -> str:
    if authorized < MIN_AUTH:
        return "insufficient_supported_years"
    assert rate is not None
    if rate >= PERSIST_THRESHOLD:
        return "persistent_less_favorable_than_favorable_reference"
    if rate <= MEETS_THRESHOLD:
        return "mostly_meets_or_exceeds_favorable_reference"
    return "mixed_relative_to_favorable_reference"


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [SPEC, GATE, MANIFEST, M11_MANIFEST, M12_MANIFEST, M11_PRED, M11_SUMMARY, M12_DISTRICT, M12_NATIONAL, GAP, PERSISTENCE, PROFILES, NATIONAL]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        return {"schema": "ranah-observatory/milestone13-audit/v1", "errors": [f"missing: {p}" for p in missing], "milestone13_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    m11_manifest = json.loads(M11_MANIFEST.read_text(encoding="utf-8"))
    m12_manifest = json.loads(M12_MANIFEST.read_text(encoding="utf-8"))
    m11 = rows(M11_PRED)
    m11_summary = rows(M11_SUMMARY)
    m12 = rows(M12_DISTRICT)
    m12_national = json.loads(M12_NATIONAL.read_text(encoding="utf-8"))
    gap = rows(GAP)
    persistence = rows(PERSISTENCE)
    profiles = rows(PROFILES)
    national = json.loads(NATIONAL.read_text(encoding="utf-8"))

    if m11_manifest.get("milestone11_complete") is not True or m12_manifest.get("milestone12_complete") is not True:
        errors.append("M13 requires complete M11/M12")

    expected_gate = {
        "schema": "ranah-observatory/milestone13-design-gate/v1",
        "target_ids": TARGETS,
        "dimension_map": DIMENSIONS,
        "standardization_scale": "m11_target_crossfit_rmse",
        "minimum_authorized_years_for_persistence_label": MIN_AUTH,
        "persistent_positive_gap_rate_threshold": PERSIST_THRESHOLD,
        "mostly_meets_or_exceeds_rate_threshold": MEETS_THRESHOLD,
        "weighted_composite_score_authorized": False,
        "cross_target_ranking_authorized": False,
        "clipping_authorized": False,
        "winsorization_authorized": False,
        "gap_values_computed": False,
        "persistence_results_inspected": False,
        "national_anchor_combined_with_district_gaps": False,
        "milestone13_complete": False,
    }
    for key, expected in expected_gate.items():
        if gate.get(key) != expected:
            errors.append(f"M13 design-gate drift: {key}")

    expected_manifest = {
        "schema": "ranah-observatory/milestone13-development-gap-decomposition/v1",
        "milestone": 13,
        "geography_count": 19,
        "target_year_count": 6,
        "target_ids": TARGETS,
        "dimension_map": DIMENSIONS,
        "gap_panel_row_count": 342,
        "persistence_row_count": 57,
        "geography_profile_row_count": 19,
        "minimum_authorized_years_for_persistence_label": MIN_AUTH,
        "persistent_positive_gap_rate_threshold": PERSIST_THRESHOLD,
        "mostly_meets_or_exceeds_rate_threshold": MEETS_THRESHOLD,
        "weighted_composite_score_computed": False,
        "cross_target_ranking_computed": False,
        "clipping_performed": False,
        "winsorization_performed": False,
        "national_anchor_combined_with_district_gaps": False,
        "population_aggregation_performed": False,
        "multi_year_monetary_accumulation_performed": False,
        "causal_analysis_performed": False,
        "theoretical_maximum_claim": False,
        "policy_counterfactual_claim": False,
        "monetary_wasted_potential_claim": False,
        "prefit_thresholds_preserved": True,
        "milestone13_complete": True,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            errors.append(f"M13 manifest drift: {key}")

    for path_string, digest in manifest.get("source_inputs", {}).items():
        p = ROOT / path_string
        if not p.exists() or sha256(p) != digest:
            errors.append(f"M13 source checksum drift: {path_string}")
    out_map = {"gap_panel": GAP, "persistence": PERSISTENCE, "geography_profiles": PROFILES, "national_income_anchor": NATIONAL}
    for key, p in out_map.items():
        rec = manifest.get("outputs", {}).get(key, {})
        if rec.get("path") != str(p.relative_to(ROOT)) or rec.get("sha256") != sha256(p):
            errors.append(f"M13 output checksum drift: {key}")

    m11_by = {(r["target_id"], r["geography_id"], r["target_year"]): r for r in m11}
    m12_by = {(r["target_id"], r["geography_id"], r["target_year"]): r for r in m12}
    gap_by = {(r["target_id"], r["geography_id"], r["target_year"]): r for r in gap}
    if len(m11_by) != 342 or len(m12_by) != 342 or len(gap_by) != 342 or set(m11_by) != set(m12_by) or set(m11_by) != set(gap_by):
        errors.append("M13 one-to-one 342-row reconciliation failed")

    rmse_by_target = {r["target_id"]: num(r, "model_rmse") for r in m11_summary}
    interval_counts: Counter[str] = Counter()
    sign_agree = 0
    authorized = 0
    for key, row in gap_by.items():
        target = key[0]
        upstream11 = m11_by[key]
        upstream12 = m12_by[key]
        observed = num(upstream11, "observed")
        expected = num(upstream11, "expected")
        lower = num(upstream11, "exploratory_prediction_interval_lower")
        upper = num(upstream11, "exploratory_prediction_interval_upper")
        exp_gap = observed - expected if DIRECTION[target] == "lower_is_favorable" else expected - observed
        primary = num(upstream12, "primary_distance_to_favorable_reference")
        alternative = num(upstream12, "alternative_distance_to_favorable_reference")
        scale = rmse_by_target[target]
        classification = interval_class(target, observed, lower, upper)
        interval_counts[classification] += 1
        agreement = sign(primary) == sign(alternative)
        sign_agree += agreement
        expected_authorized = upstream12["primary_frontier_interpretation_authorized"] == "true"
        authorized += expected_authorized

        checks = {
            "observed": observed,
            "m11_expected": expected,
            "expected_adverse_gap": exp_gap,
            "m11_target_crossfit_rmse": scale,
            "expected_gap_rmse_units": exp_gap / scale,
            "m12_primary_favorable_reference": num(upstream12, "primary_favorable_reference"),
            "favorable_peer_gap": primary,
            "favorable_peer_gap_rmse_units": primary / scale,
            "m12_alternative_favorable_reference": num(upstream12, "alternative_favorable_reference"),
            "alternative_favorable_peer_gap": alternative,
            "alternative_gap_rmse_units": alternative / scale,
        }
        for field, expected_value in checks.items():
            if not close(num(row, field), expected_value):
                errors.append(f"M13 arithmetic mismatch: {key}/{field}")
        if row.get("dimension_id") != DIMENSIONS[target] or row.get("target_direction") != DIRECTION[target]:
            errors.append(f"M13 dimension/direction drift: {key}")
        if row.get("expected_interval_classification") != classification:
            errors.append(f"M13 interval classification mismatch: {key}")
        if (row.get("frontier_gap_sign_agreement") == "true") != agreement:
            errors.append(f"M13 method-sign agreement mismatch: {key}")
        if (row.get("gap_interpretation_authorized") == "true") != expected_authorized:
            errors.append(f"M13 support authorization mismatch: {key}")
        if row.get("m11_support_warning") != upstream12["m11_support_warning"]:
            errors.append(f"M13 support warning lineage mismatch: {key}")
        for claim in ["causal_claim", "theoretical_maximum_claim", "policy_counterfactual_claim", "monetary_wasted_potential_claim"]:
            if row.get(claim) != "false":
                errors.append(f"M13 forbidden row claim: {key}/{claim}")

    if manifest.get("gap_interpretation_authorized_row_count") != authorized or manifest.get("gap_interpretation_blocked_row_count") != 342 - authorized:
        errors.append("M13 authorization counts drift")
    if manifest.get("frontier_gap_sign_agreement_count") != sign_agree or manifest.get("frontier_gap_sign_disagreement_count") != 342 - sign_agree:
        errors.append("M13 sign-agreement counts drift")
    if manifest.get("expected_interval_classification_counts") != dict(sorted(interval_counts.items())):
        errors.append("M13 interval-classification manifest counts drift")

    grouped_gap: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in gap:
        grouped_gap[(row["geography_id"], row["target_id"])].append(row)
    persistence_by = {(r["geography_id"], r["target_id"]): r for r in persistence}
    if len(persistence_by) != 57:
        errors.append("M13 persistence must contain 57 unique geography-target rows")
    label_counts: Counter[str] = Counter()
    for key, source_rows in grouped_gap.items():
        source_rows = sorted(source_rows, key=lambda r: int(r["target_year"]))
        p = persistence_by.get(key)
        if p is None or len(source_rows) != 6:
            errors.append(f"M13 persistence source footprint mismatch: {key}")
            continue
        auth_rows = [r for r in source_rows if r["gap_interpretation_authorized"] == "true"]
        positive = [r for r in auth_rows if num(r, "favorable_peer_gap") > 0]
        rate = len(positive) / len(auth_rows) if auth_rows else None
        expected_label = persistence_label(len(auth_rows), rate)
        label_counts[expected_label] += 1
        if int(p["interpretation_authorized_row_count"]) != len(auth_rows):
            errors.append(f"M13 persistence authorized count mismatch: {key}")
        support_count = sum(r["m11_support_warning"] == "true" for r in source_rows)
        if int(p["support_warning_row_count"]) != support_count:
            errors.append(f"M13 persistence support count mismatch: {key}")
        if int(p["positive_favorable_peer_gap_authorized_year_count"]) != len(positive):
            errors.append(f"M13 persistence positive count mismatch: {key}")
        if p["persistence_label"] != expected_label:
            errors.append(f"M13 persistence label mismatch: {key}")
        if rate is None:
            if p["positive_gap_persistence_rate_authorized_rows"] != "":
                errors.append(f"M13 persistence empty-rate mismatch: {key}")
        elif not close(num(p, "positive_gap_persistence_rate_authorized_rows"), rate):
            errors.append(f"M13 persistence rate mismatch: {key}")
        if not close(num(p, "median_expected_adverse_gap"), median([num(r, "expected_adverse_gap") for r in source_rows])):
            errors.append(f"M13 persistence expected median mismatch: {key}")
        if not close(num(p, "median_favorable_peer_gap"), median([num(r, "favorable_peer_gap") for r in source_rows])):
            errors.append(f"M13 persistence frontier median mismatch: {key}")

    if manifest.get("persistence_label_counts") != dict(sorted(label_counts.items())):
        errors.append("M13 persistence-label manifest counts drift")

    if len(profiles) != 19 or len({r["geography_id"] for r in profiles}) != 19:
        errors.append("M13 geography profiles must contain exact 19 unique rows")
    for profile in profiles:
        if profile.get("weighted_composite_score") != "" or profile.get("cross_target_rank") != "":
            errors.append(f"M13 profile illegally contains composite/rank: {profile.get('geography_id')}")
        target_rows = [persistence_by[(profile["geography_id"], target)] for target in TARGETS]
        counts = Counter(r["persistence_label"] for r in target_rows)
        expected_counts = {
            "persistent_less_favorable_target_count": counts["persistent_less_favorable_than_favorable_reference"],
            "mostly_meets_or_exceeds_target_count": counts["mostly_meets_or_exceeds_favorable_reference"],
            "mixed_target_count": counts["mixed_relative_to_favorable_reference"],
            "insufficient_supported_target_count": counts["insufficient_supported_years"],
        }
        for field, value in expected_counts.items():
            if int(profile[field]) != value:
                errors.append(f"M13 profile count mismatch: {profile['geography_id']}/{field}")

    if national.get("schema") != "ranah-observatory/milestone13-national-income-anchor/v1":
        errors.append("M13 national anchor schema drift")
    obs = float(m12_national["observed_level"])
    expected = float(m12_national["m7_smearing_corrected_expected_level_context"])
    favorable = float(m12_national["conditional_favorable_level"])
    national_checks = {
        "observed_level": obs,
        "m7_conditional_expected_level": expected,
        "m12_conditional_favorable_peer_level": favorable,
        "observed_minus_expected_level": obs - expected,
        "expected_minus_observed_level": expected - obs,
        "favorable_peer_minus_observed_level": favorable - obs,
        "observed_to_expected_ratio": obs / expected,
        "observed_to_favorable_peer_ratio": obs / favorable,
    }
    for field, value in national_checks.items():
        if not close(float(national[field]), value):
            errors.append(f"M13 national anchor arithmetic mismatch: {field}")
    for flag in ["anchor_combined_with_district_gap_score", "population_aggregation_performed", "multi_year_accumulation_performed", "causal_claim", "theoretical_maximum_claim", "policy_counterfactual_claim", "monetary_wasted_potential_claim"]:
        if national.get(flag) is not False:
            errors.append(f"M13 forbidden national flag: {flag}")

    required_phrases = [
        "does **not** collapse all domains into one score",
        "positive = observed outcome is less favorable than the reference",
        "No winsorization, clipping, or sign truncation is allowed",
        "No rank or league table is authorized",
        "neither difference may be multiplied by population",
        "Sumatera Barat lost the national income-anchor difference",
    ]
    for phrase in required_phrases:
        if phrase not in spec:
            errors.append(f"M13 spec lost guardrail phrase: {phrase}")

    return {
        "schema": "ranah-observatory/milestone13-audit/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 13,
        "gap_panel_row_count": len(gap),
        "persistence_row_count": len(persistence),
        "geography_profile_row_count": len(profiles),
        "authorized_gap_row_count": authorized,
        "interval_classification_counts": dict(sorted(interval_counts.items())),
        "persistence_label_counts": dict(sorted(label_counts.items())),
        "prefit_design_gate_preserved": gate.get("gap_values_computed") is False and gate.get("persistence_results_inspected") is False,
        "m11_complete": m11_manifest.get("milestone11_complete") is True,
        "m12_complete": m12_manifest.get("milestone12_complete") is True,
        "weighted_composite_score_computed": manifest.get("weighted_composite_score_computed") is True,
        "cross_target_ranking_computed": manifest.get("cross_target_ranking_computed") is True,
        "monetary_wasted_potential_claim": manifest.get("monetary_wasted_potential_claim") is True,
        "milestone13_complete": manifest.get("milestone13_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 13 Development Gap Decomposition")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone13_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
