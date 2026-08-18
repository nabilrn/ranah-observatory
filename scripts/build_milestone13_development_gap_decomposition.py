#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
M11_PREDICTIONS = ROOT / "data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv"
M11_SUMMARY = ROOT / "data/analysis/engine/expected_performance_v2/m11-target-summary.csv"
M11_MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M12_DISTRICT = ROOT / "data/analysis/engine/frontier_v1/m12-district-frontier.csv"
M12_NATIONAL = ROOT / "data/analysis/engine/frontier_v1/m12-national-west-sumatra-frontier.json"
M12_MANIFEST = ROOT / "data/manifests/milestone12_attainable_frontier.json"
GATE = ROOT / "data/manifests/milestone13_design_gate.json"
SPEC = ROOT / "research/MILESTONE13_DEVELOPMENT_GAP_DECOMPOSITION_SPEC.md"
OUT_DIR = ROOT / "data/analysis/engine/gap_decomposition_v1"
GAP_PANEL_OUT = OUT_DIR / "m13-gap-panel.csv"
PERSISTENCE_OUT = OUT_DIR / "m13-persistence-by-geography-target.csv"
PROFILE_OUT = OUT_DIR / "m13-geography-profiles.csv"
NATIONAL_OUT = OUT_DIR / "m13-national-income-anchor.json"
MANIFEST_OUT = ROOT / "data/manifests/milestone13_development_gap_decomposition.json"

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
MIN_AUTHORIZED_YEARS = 4
PERSISTENT_THRESHOLD = 2.0 / 3.0
MOSTLY_MEETS_THRESHOLD = 1.0 / 3.0
TARGET_YEARS = list(range(2019, 2025))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


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


def median(values: list[float]) -> float:
    if not values:
        raise ValueError("median requires values")
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def sign(value: float, eps: float = 1e-12) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def fmt(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.12g}"
    return value


def expected_adverse_gap(target: str, observed: float, expected: float) -> float:
    if DIRECTION[target] == "lower_is_favorable":
        return observed - expected
    return expected - observed


def interval_classification(target: str, observed: float, lower: float, upper: float) -> str:
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


def persistence_label(authorized_count: int, positive_rate: float | None) -> str:
    if authorized_count < MIN_AUTHORIZED_YEARS:
        return "insufficient_supported_years"
    if positive_rate is None:
        raise ValueError("positive rate required when sufficient years exist")
    if positive_rate >= PERSISTENT_THRESHOLD:
        return "persistent_less_favorable_than_favorable_reference"
    if positive_rate <= MOSTLY_MEETS_THRESHOLD:
        return "mostly_meets_or_exceeds_favorable_reference"
    return "mixed_relative_to_favorable_reference"


def validate_gate() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    m11 = json.loads(M11_MANIFEST.read_text(encoding="utf-8"))
    m12 = json.loads(M12_MANIFEST.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    if m11.get("milestone11_complete") is not True or m12.get("milestone12_complete") is not True:
        raise ValueError("M13 requires completed M11 and M12")
    if set(m11.get("benchmark_qualified_target_ids", [])) != set(TARGETS):
        raise ValueError("M13 requires benchmark-qualified M11 target set")
    if set(m12.get("primary_frontier_calibrated_target_ids", [])) != set(TARGETS):
        raise ValueError("M13 requires calibrated M12 target set")
    expected = {
        "schema": "ranah-observatory/milestone13-design-gate/v1",
        "district_scope": "current_sumbar_19_kabkota_2019_2024",
        "target_ids": TARGETS,
        "dimension_map": DIMENSIONS,
        "expected_gap_orientation": "positive_means_less_favorable_than_expected",
        "favorable_peer_gap_orientation": "positive_means_less_favorable_than_empirical_favorable_reference",
        "standardization_scale": "m11_target_crossfit_rmse",
        "minimum_authorized_years_for_persistence_label": MIN_AUTHORIZED_YEARS,
        "persistent_positive_gap_rate_threshold": PERSISTENT_THRESHOLD,
        "mostly_meets_or_exceeds_rate_threshold": MOSTLY_MEETS_THRESHOLD,
        "weighted_composite_score_authorized": False,
        "cross_target_ranking_authorized": False,
        "clipping_authorized": False,
        "winsorization_authorized": False,
        "gap_values_computed": False,
        "persistence_results_inspected": False,
        "national_anchor_combined_with_district_gaps": False,
        "milestone13_complete": False,
    }
    for key, value in expected.items():
        if gate.get(key) != value:
            raise ValueError(f"M13 design-gate drift: {key}")
    return m11, m12, gate


def build_gap_panel() -> tuple[list[dict[str, Any]], dict[str, float], list[str]]:
    m11_rows = read_csv(M11_PREDICTIONS)
    m12_rows = read_csv(M12_DISTRICT)
    summary_rows = read_csv(M11_SUMMARY)
    if len(m11_rows) != 342 or len(m12_rows) != 342:
        raise ValueError("M13 expects exact 342-row M11/M12 inputs")
    m11_by_key = {(row["target_id"], row["geography_id"], row["target_year"]): row for row in m11_rows}
    m12_by_key = {(row["target_id"], row["geography_id"], row["target_year"]): row for row in m12_rows}
    if len(m11_by_key) != 342 or len(m12_by_key) != 342 or set(m11_by_key) != set(m12_by_key):
        raise ValueError("M13 M11/M12 one-to-one key reconciliation failed")
    rmse_by_target = {row["target_id"]: f(row, "model_rmse") for row in summary_rows}
    if set(rmse_by_target) != set(TARGETS) or any(value <= 0 for value in rmse_by_target.values()):
        raise ValueError("M13 invalid M11 target RMSE scale")

    geographies = sorted({key[1] for key in m11_by_key})
    if len(geographies) != 19:
        raise ValueError("M13 requires exact 19 geographies")

    output: list[dict[str, Any]] = []
    for key in sorted(m11_by_key, key=lambda item: (TARGETS.index(item[0]), item[1], int(item[2]))):
        target, geography_id, target_year_string = key
        m11 = m11_by_key[key]
        m12 = m12_by_key[key]
        target_year = int(target_year_string)
        observed = f(m11, "observed")
        expected = f(m11, "expected")
        lower = f(m11, "exploratory_prediction_interval_lower")
        upper = f(m11, "exploratory_prediction_interval_upper")
        expected_gap = expected_adverse_gap(target, observed, expected)
        primary_gap = f(m12, "primary_distance_to_favorable_reference")
        alternative_gap = f(m12, "alternative_distance_to_favorable_reference")
        scale = rmse_by_target[target]
        primary_sign = sign(primary_gap)
        alternative_sign = sign(alternative_gap)
        classification = interval_classification(target, observed, lower, upper)
        authorized = m12.get("primary_frontier_interpretation_authorized") == "true"
        output.append({
            "target_id": target,
            "dimension_id": DIMENSIONS[target],
            "target_direction": DIRECTION[target],
            "geography_id": geography_id,
            "geography_name": m11["geography_name"],
            "target_year": target_year,
            "observed": observed,
            "m11_expected": expected,
            "m11_prediction_interval_lower": lower,
            "m11_prediction_interval_upper": upper,
            "expected_interval_classification": classification,
            "expected_adverse_gap": expected_gap,
            "m11_target_crossfit_rmse": scale,
            "expected_gap_rmse_units": expected_gap / scale,
            "m12_primary_favorable_reference": f(m12, "primary_favorable_reference"),
            "favorable_peer_gap": primary_gap,
            "favorable_peer_gap_rmse_units": primary_gap / scale,
            "m12_alternative_favorable_reference": f(m12, "alternative_favorable_reference"),
            "alternative_favorable_peer_gap": alternative_gap,
            "alternative_gap_rmse_units": alternative_gap / scale,
            "frontier_gap_primary_sign": primary_sign,
            "frontier_gap_alternative_sign": alternative_sign,
            "frontier_gap_sign_agreement": primary_sign == alternative_sign,
            "m11_benchmark_qualified": m12["m11_benchmark_qualified"] == "true",
            "m11_support_warning": m12["m11_support_warning"] == "true",
            "m12_primary_frontier_calibrated": m12["primary_frontier_calibrated"] == "true",
            "gap_interpretation_authorized": authorized,
            "expected_gap_claim_type": "model_estimate_difference",
            "favorable_peer_gap_claim_type": "model_estimate_empirical_peer_reference_difference",
            "causal_claim": False,
            "theoretical_maximum_claim": False,
            "policy_counterfactual_claim": False,
            "monetary_wasted_potential_claim": False,
        })
    return output, rmse_by_target, geographies


def build_persistence(gap_rows: list[dict[str, Any]], geographies: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in gap_rows:
        grouped[(row["geography_id"], row["target_id"])].append(row)
    output: list[dict[str, Any]] = []
    for geography_id in geographies:
        for target in TARGETS:
            rows = sorted(grouped[(geography_id, target)], key=lambda row: int(row["target_year"]))
            if len(rows) != 6 or [int(row["target_year"]) for row in rows] != TARGET_YEARS:
                raise ValueError(f"M13 persistence footprint drift for {geography_id}/{target}")
            authorized = [row for row in rows if bool(row["gap_interpretation_authorized"])]
            positive = [row for row in authorized if float(row["favorable_peer_gap"]) > 0.0]
            nonpositive = [row for row in authorized if float(row["favorable_peer_gap"]) <= 0.0]
            rate = len(positive) / len(authorized) if authorized else None
            label = persistence_label(len(authorized), rate)
            latest = rows[-1]
            output.append({
                "geography_id": geography_id,
                "geography_name": rows[0]["geography_name"],
                "target_id": target,
                "dimension_id": DIMENSIONS[target],
                "target_direction": DIRECTION[target],
                "row_count": len(rows),
                "interpretation_authorized_row_count": len(authorized),
                "support_warning_row_count": sum(bool(row["m11_support_warning"]) for row in rows),
                "positive_favorable_peer_gap_authorized_year_count": len(positive),
                "nonpositive_favorable_peer_gap_authorized_year_count": len(nonpositive),
                "positive_gap_persistence_rate_authorized_rows": "" if rate is None else rate,
                "persistence_label": label,
                "median_expected_adverse_gap": median([float(row["expected_adverse_gap"]) for row in rows]),
                "median_favorable_peer_gap": median([float(row["favorable_peer_gap"]) for row in rows]),
                "median_expected_gap_rmse_units": median([float(row["expected_gap_rmse_units"]) for row in rows]),
                "median_favorable_peer_gap_rmse_units": median([float(row["favorable_peer_gap_rmse_units"]) for row in rows]),
                "latest_year": 2024,
                "latest_observed": latest["observed"],
                "latest_expected_adverse_gap": latest["expected_adverse_gap"],
                "latest_favorable_peer_gap": latest["favorable_peer_gap"],
                "latest_expected_gap_rmse_units": latest["expected_gap_rmse_units"],
                "latest_favorable_peer_gap_rmse_units": latest["favorable_peer_gap_rmse_units"],
                "latest_expected_interval_classification": latest["expected_interval_classification"],
                "latest_support_warning": latest["m11_support_warning"],
                "latest_gap_interpretation_authorized": latest["gap_interpretation_authorized"],
                "primary_alternative_gap_sign_agreement_rate": sum(bool(row["frontier_gap_sign_agreement"]) for row in rows) / len(rows),
                "minimum_authorized_years_for_label": MIN_AUTHORIZED_YEARS,
                "persistent_positive_gap_rate_threshold": PERSISTENT_THRESHOLD,
                "mostly_meets_or_exceeds_rate_threshold": MOSTLY_MEETS_THRESHOLD,
                "claim_type": "derived_descriptive_classification",
                "causal_claim": False,
                "monetary_wasted_potential_claim": False,
            })
    if len(output) != 57:
        raise ValueError(f"M13 persistence output must contain 57 rows, got {len(output)}")
    return output


def build_profiles(persistence_rows: list[dict[str, Any]], geographies: list[str]) -> list[dict[str, Any]]:
    by_key = {(row["geography_id"], row["target_id"]): row for row in persistence_rows}
    output: list[dict[str, Any]] = []
    for geography_id in geographies:
        target_rows = [by_key[(geography_id, target)] for target in TARGETS]
        row: dict[str, Any] = {
            "geography_id": geography_id,
            "geography_name": target_rows[0]["geography_name"],
        }
        label_counts = Counter(target_row["persistence_label"] for target_row in target_rows)
        for target in TARGETS:
            target_row = by_key[(geography_id, target)]
            prefix = target
            row[f"{prefix}_persistence_label"] = target_row["persistence_label"]
            row[f"{prefix}_authorized_year_count"] = target_row["interpretation_authorized_row_count"]
            row[f"{prefix}_positive_gap_persistence_rate"] = target_row["positive_gap_persistence_rate_authorized_rows"]
            row[f"{prefix}_median_favorable_peer_gap_rmse_units"] = target_row["median_favorable_peer_gap_rmse_units"]
            row[f"{prefix}_2024_favorable_peer_gap_rmse_units"] = target_row["latest_favorable_peer_gap_rmse_units"]
            row[f"{prefix}_2024_expected_interval_classification"] = target_row["latest_expected_interval_classification"]
            row[f"{prefix}_2024_support_warning"] = target_row["latest_support_warning"]
            row[f"{prefix}_2024_gap_interpretation_authorized"] = target_row["latest_gap_interpretation_authorized"]
        row["persistent_less_favorable_target_count"] = label_counts["persistent_less_favorable_than_favorable_reference"]
        row["mostly_meets_or_exceeds_target_count"] = label_counts["mostly_meets_or_exceeds_favorable_reference"]
        row["mixed_target_count"] = label_counts["mixed_relative_to_favorable_reference"]
        row["insufficient_supported_target_count"] = label_counts["insufficient_supported_years"]
        row["weighted_composite_score"] = ""
        row["cross_target_rank"] = ""
        row["profile_claim_type"] = "derived_multidimensional_profile_no_composite_score"
        row["causal_claim"] = False
        row["monetary_wasted_potential_claim"] = False
        output.append(row)
    if len(output) != 19:
        raise ValueError(f"M13 geography profile output must contain 19 rows, got {len(output)}")
    return output


def build_national_anchor() -> dict[str, Any]:
    m12 = json.loads(M12_NATIONAL.read_text(encoding="utf-8"))
    observed = float(m12["observed_level"])
    expected = float(m12["m7_smearing_corrected_expected_level_context"])
    favorable = float(m12["conditional_favorable_level"])
    return {
        "schema": "ranah-observatory/milestone13-national-income-anchor/v1",
        "dimension_id": "income_productivity_national_anchor",
        "geography_id": "idn.13",
        "geography_name": "Sumatera Barat",
        "reference_year": 2024,
        "target_id": "real_grdp_per_capita",
        "target_unit": m12["target_unit"],
        "observed_level": observed,
        "m7_conditional_expected_level": expected,
        "m12_conditional_favorable_peer_level": favorable,
        "observed_minus_expected_level": observed - expected,
        "expected_minus_observed_level": expected - observed,
        "favorable_peer_minus_observed_level": favorable - observed,
        "observed_to_expected_ratio": observed / expected,
        "observed_to_favorable_peer_ratio": observed / favorable,
        "m7_all_features_inside_training_univariate_minmax": m12["m7_all_features_inside_training_univariate_minmax"],
        "m7_maximum_absolute_training_standardized_z": m12["m7_maximum_absolute_training_standardized_z"],
        "anchor_combined_with_district_gap_score": False,
        "population_aggregation_performed": False,
        "multi_year_accumulation_performed": False,
        "claim_type": "model_estimate_context",
        "causal_claim": False,
        "theoretical_maximum_claim": False,
        "policy_counterfactual_claim": False,
        "monetary_wasted_potential_claim": False,
    }


def build() -> dict[str, Any]:
    m11, m12, gate = validate_gate()
    gap_rows, rmse_by_target, geographies = build_gap_panel()
    persistence_rows = build_persistence(gap_rows, geographies)
    profile_rows = build_profiles(persistence_rows, geographies)
    national = build_national_anchor()

    gap_fields = [
        "target_id", "dimension_id", "target_direction", "geography_id", "geography_name", "target_year",
        "observed", "m11_expected", "m11_prediction_interval_lower", "m11_prediction_interval_upper",
        "expected_interval_classification", "expected_adverse_gap", "m11_target_crossfit_rmse", "expected_gap_rmse_units",
        "m12_primary_favorable_reference", "favorable_peer_gap", "favorable_peer_gap_rmse_units",
        "m12_alternative_favorable_reference", "alternative_favorable_peer_gap", "alternative_gap_rmse_units",
        "frontier_gap_primary_sign", "frontier_gap_alternative_sign", "frontier_gap_sign_agreement",
        "m11_benchmark_qualified", "m11_support_warning", "m12_primary_frontier_calibrated", "gap_interpretation_authorized",
        "expected_gap_claim_type", "favorable_peer_gap_claim_type", "causal_claim", "theoretical_maximum_claim",
        "policy_counterfactual_claim", "monetary_wasted_potential_claim",
    ]
    write_csv(GAP_PANEL_OUT, gap_fields, [{k: fmt(v) for k, v in row.items()} for row in gap_rows])

    persistence_fields = [
        "geography_id", "geography_name", "target_id", "dimension_id", "target_direction", "row_count",
        "interpretation_authorized_row_count", "support_warning_row_count", "positive_favorable_peer_gap_authorized_year_count",
        "nonpositive_favorable_peer_gap_authorized_year_count", "positive_gap_persistence_rate_authorized_rows", "persistence_label",
        "median_expected_adverse_gap", "median_favorable_peer_gap", "median_expected_gap_rmse_units",
        "median_favorable_peer_gap_rmse_units", "latest_year", "latest_observed", "latest_expected_adverse_gap",
        "latest_favorable_peer_gap", "latest_expected_gap_rmse_units", "latest_favorable_peer_gap_rmse_units",
        "latest_expected_interval_classification", "latest_support_warning", "latest_gap_interpretation_authorized",
        "primary_alternative_gap_sign_agreement_rate", "minimum_authorized_years_for_label",
        "persistent_positive_gap_rate_threshold", "mostly_meets_or_exceeds_rate_threshold", "claim_type", "causal_claim",
        "monetary_wasted_potential_claim",
    ]
    write_csv(PERSISTENCE_OUT, persistence_fields, [{k: fmt(v) for k, v in row.items()} for row in persistence_rows])

    profile_fields = ["geography_id", "geography_name"]
    for target in TARGETS:
        profile_fields.extend([
            f"{target}_persistence_label",
            f"{target}_authorized_year_count",
            f"{target}_positive_gap_persistence_rate",
            f"{target}_median_favorable_peer_gap_rmse_units",
            f"{target}_2024_favorable_peer_gap_rmse_units",
            f"{target}_2024_expected_interval_classification",
            f"{target}_2024_support_warning",
            f"{target}_2024_gap_interpretation_authorized",
        ])
    profile_fields.extend([
        "persistent_less_favorable_target_count", "mostly_meets_or_exceeds_target_count", "mixed_target_count",
        "insufficient_supported_target_count", "weighted_composite_score", "cross_target_rank", "profile_claim_type",
        "causal_claim", "monetary_wasted_potential_claim",
    ])
    write_csv(PROFILE_OUT, profile_fields, [{k: fmt(v) for k, v in row.items()} for row in profile_rows])

    NATIONAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    NATIONAL_OUT.write_text(json.dumps(national, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    label_counts = Counter(row["persistence_label"] for row in persistence_rows)
    interval_counts = Counter(row["expected_interval_classification"] for row in gap_rows)
    authorized_count = sum(bool(row["gap_interpretation_authorized"]) for row in gap_rows)
    sign_agreement_count = sum(bool(row["frontier_gap_sign_agreement"]) for row in gap_rows)
    manifest = {
        "schema": "ranah-observatory/milestone13-development-gap-decomposition/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 13,
        "district_scope": "current_sumbar_19_kabkota_2019_2024",
        "geography_count": 19,
        "target_years": TARGET_YEARS,
        "target_year_count": 6,
        "target_ids": TARGETS,
        "dimension_map": DIMENSIONS,
        "gap_panel_row_count": len(gap_rows),
        "persistence_row_count": len(persistence_rows),
        "geography_profile_row_count": len(profile_rows),
        "m11_target_crossfit_rmse": rmse_by_target,
        "gap_interpretation_authorized_row_count": authorized_count,
        "gap_interpretation_blocked_row_count": len(gap_rows) - authorized_count,
        "frontier_gap_sign_agreement_count": sign_agreement_count,
        "frontier_gap_sign_disagreement_count": len(gap_rows) - sign_agreement_count,
        "expected_interval_classification_counts": dict(sorted(interval_counts.items())),
        "persistence_label_counts": dict(sorted(label_counts.items())),
        "minimum_authorized_years_for_persistence_label": MIN_AUTHORIZED_YEARS,
        "persistent_positive_gap_rate_threshold": PERSISTENT_THRESHOLD,
        "mostly_meets_or_exceeds_rate_threshold": MOSTLY_MEETS_THRESHOLD,
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
        "gap_orientation": "positive_means_less_favorable_than_reference",
        "standardization_scale": "m11_target_crossfit_rmse",
        "prefit_thresholds_preserved": (
            gate.get("minimum_authorized_years_for_persistence_label") == MIN_AUTHORIZED_YEARS
            and gate.get("persistent_positive_gap_rate_threshold") == PERSISTENT_THRESHOLD
            and gate.get("mostly_meets_or_exceeds_rate_threshold") == MOSTLY_MEETS_THRESHOLD
        ),
        "source_inputs": {
            str(M11_PREDICTIONS.relative_to(ROOT)): sha256(M11_PREDICTIONS),
            str(M11_SUMMARY.relative_to(ROOT)): sha256(M11_SUMMARY),
            str(M11_MANIFEST.relative_to(ROOT)): sha256(M11_MANIFEST),
            str(M12_DISTRICT.relative_to(ROOT)): sha256(M12_DISTRICT),
            str(M12_NATIONAL.relative_to(ROOT)): sha256(M12_NATIONAL),
            str(M12_MANIFEST.relative_to(ROOT)): sha256(M12_MANIFEST),
            str(GATE.relative_to(ROOT)): sha256(GATE),
            str(SPEC.relative_to(ROOT)): sha256(SPEC),
        },
        "outputs": {
            "gap_panel": {"path": str(GAP_PANEL_OUT.relative_to(ROOT)), "sha256": sha256(GAP_PANEL_OUT)},
            "persistence": {"path": str(PERSISTENCE_OUT.relative_to(ROOT)), "sha256": sha256(PERSISTENCE_OUT)},
            "geography_profiles": {"path": str(PROFILE_OUT.relative_to(ROOT)), "sha256": sha256(PROFILE_OUT)},
            "national_income_anchor": {"path": str(NATIONAL_OUT.relative_to(ROOT)), "sha256": sha256(NATIONAL_OUT)},
        },
        "milestone13_complete": True,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return manifest


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
