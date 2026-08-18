#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from scripts.audit_milestone8_design import audit as audit_prefit_design

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/manifests/milestone8_case_study.json"
FINDINGS = ROOT / "data/analysis/quasi_causal/m8-earthquake-case-study-findings.csv"
EVENT = ROOT / "data/manifests/milestone8_event_study.json"
PRIMARY = ROOT / "data/analysis/quasi_causal/m8-event-study-primary.csv"
SENSITIVITY = ROOT / "data/analysis/quasi_causal/m8-event-study-exposure-sensitivity.csv"
HOUSING = ROOT / "data/manifests/milestone8_housing_damage_validation.json"
GROWTH = ROOT / "data/manifests/milestone8_growth_robustness.json"
RESOLUTION = ROOT / "data/manifests/milestone8_grdp_source_anomaly_resolution.json"
OVERLAP = ROOT / "data/manifests/milestone8_grdp_overlap.json"
EXPOSURE = ROOT / "data/manifests/milestone8_shakemap_exposure_candidate.json"
PREFIT_GATE = ROOT / "data/manifests/milestone8_design_gate.json"
INFERENCE = ROOT / "research/MILESTONE8_INFERENCE_PROTOCOL.md"
OUTPUT = ROOT / "data/manifests/milestone8_complete_audit.json"

EXPECTED_POST_EVENT_TIMES = {0, 1, 2, 3, 4}
EXPECTED_SENSITIVITY_EXPOSURES = {
    "area_median_pga_pct_g",
    "area_p90_pga_pct_g",
    "area_max_pga_pct_g",
    "area_mean_mmi",
}
EXPECTED_PROHIBITED_INTERPRETATIONS = {
    "The earthquake had no economic impact.",
    "The coefficient is the total economic loss from the earthquake.",
    "The coefficient measures welfare loss or wasted potential.",
    "A later positive or recovered trajectory would imply the earthquake was beneficial.",
    "DLNA-unreported geographies had zero housing damage.",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [
        FINAL,
        FINDINGS,
        EVENT,
        PRIMARY,
        SENSITIVITY,
        HOUSING,
        GROWTH,
        RESOLUTION,
        OVERLAP,
        EXPOSURE,
        PREFIT_GATE,
        INFERENCE,
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required Milestone 8 completion input: {path.relative_to(ROOT)}")
    if errors:
        return {
            "schema": "ranah-observatory/milestone8-complete-audit/v1",
            "criterion": "one focused causal or quasi-causal case study",
            "milestone8_complete": False,
            "errors": errors,
        }

    prefit = audit_prefit_design()
    if prefit.get("errors"):
        errors.extend(f"pre-fit design audit: {error}" for error in prefit["errors"])
    if prefit.get("design_preregistered") is not True:
        errors.append("pre-fit design is not preregistered")
    if prefit.get("model_fit_authorized") is not True:
        errors.append("pre-fit model authorization gate is not closed")
    if prefit.get("outcome_model_fit") is not False:
        errors.append("pre-fit gate was mutated after model fitting")
    if prefit.get("quasi_causal_effect_estimated") is not False:
        errors.append("pre-fit gate improperly contains a post-fit quasi-causal estimate")
    if prefit.get("milestone8_complete") is not False:
        errors.append("pre-fit gate was improperly rewritten as complete")

    final = json.loads(FINAL.read_text(encoding="utf-8"))
    event = json.loads(EVENT.read_text(encoding="utf-8"))
    housing = json.loads(HOUSING.read_text(encoding="utf-8"))
    growth = json.loads(GROWTH.read_text(encoding="utf-8"))
    resolution = json.loads(RESOLUTION.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    exposure = json.loads(EXPOSURE.read_text(encoding="utf-8"))
    prefit_gate = json.loads(PREFIT_GATE.read_text(encoding="utf-8"))
    findings = read_csv(FINDINGS)
    primary_rows = read_csv(PRIMARY)
    sensitivity_rows = read_csv(SENSITIVITY)

    if final.get("schema") != "ranah-observatory/milestone8-case-study/v1":
        errors.append("Milestone 8 final case-study schema drift")
    if final.get("criterion") != "one focused causal or quasi-causal case study":
        errors.append("Milestone 8 criterion drift")
    if final.get("case_study") != "2009 West Sumatra earthquake differential economic trajectory":
        errors.append("Milestone 8 case-study identity drift")
    if final.get("case_study_complete") is not True or final.get("milestone8_complete") is not True:
        errors.append("Milestone 8 final synthesis is not complete")
    if final.get("geography_count") != 19 or final.get("observation_count") != 171:
        errors.append("Milestone 8 final panel cardinality drift")
    if final.get("analysis_years") != list(range(2005, 2014)):
        errors.append("Milestone 8 final year footprint drift")
    if final.get("primary_exposure") != "area_mean_pga_pct_g":
        errors.append("Milestone 8 final primary exposure drift")
    if final.get("primary_design") != "continuous_intensity_two_way_fixed_effects_event_study":
        errors.append("Milestone 8 final design drift")

    required_true = [
        "source_anomalies_resolved",
        "overlap_2009_reconciled",
        "core_identification_diagnostics_passed",
        "pretrend_passed",
        "placebo_passed",
        "influence_passed",
        "housing_damage_validation_complete",
        "grdp_growth_robustness_complete",
        "small_cluster_inference_implemented",
        "exposure_sensitivity_complete",
        "quasi_causal_effect_estimated",
        "quasi_causal_estimate_authorized",
    ]
    for key in required_true:
        if final.get(key) is not True:
            errors.append(f"Milestone 8 final completion gate is not true: {key}")
    if final.get("directional_nonzero_effect_claim_authorized") is not False:
        errors.append("Milestone 8 must not authorize a directional nonzero effect claim")
    if final.get("causal_claim_authorized") is not False:
        errors.append("Milestone 8 must not authorize an unconditional causal claim")
    if final.get("claim_classification") != "quasi_causal_estimate_no_statistically_robust_differential_effect_detected":
        errors.append("Milestone 8 final claim classification drift")
    if final.get("all_primary_post_wild_cluster_bootstrap_p_values_above_0_10") is not True:
        errors.append("Milestone 8 final synthesis lost the no-post-p<=0.10 condition")
    if final.get("primary_post_coefficients_all_negative") is not True:
        errors.append("Milestone 8 final primary post coefficient sign summary drift")
    if final.get("sensitivity_post_all_negative") is not True:
        errors.append("Milestone 8 final sensitivity sign summary drift")
    if set(final.get("prohibited_interpretations", [])) != EXPECTED_PROHIBITED_INTERPRETATIONS:
        errors.append("Milestone 8 prohibited-interpretation contract drift")

    if event.get("schema") != "ranah-observatory/milestone8-event-study/v1":
        errors.append("Milestone 8 event-study schema drift")
    if event.get("core_identification_diagnostics_passed") is not True:
        errors.append("Milestone 8 event-study core diagnostics no longer pass")
    if event.get("pretrend", {}).get("passed") is not True:
        errors.append("Milestone 8 pretrend gate no longer passes")
    if event.get("placebo", {}).get("passed") is not True:
        errors.append("Milestone 8 placebo gate no longer passes")
    if event.get("influence", {}).get("passed") is not True:
        errors.append("Milestone 8 influence gate no longer passes")
    if event.get("small_cluster_inference_implemented") is not True:
        errors.append("Milestone 8 wild-cluster inference is missing")
    if event.get("wild_cluster_bootstrap", {}).get("draws") != 1999:
        errors.append("Milestone 8 WCB draw count drift")
    if event.get("wild_cluster_bootstrap", {}).get("seed") != 20090930:
        errors.append("Milestone 8 WCB seed drift")

    post_rows = [row for row in primary_rows if int(row["event_time"]) in EXPECTED_POST_EVENT_TIMES]
    if len(post_rows) != 5 or {int(row["event_time"]) for row in post_rows} != EXPECTED_POST_EVENT_TIMES:
        errors.append("Milestone 8 primary post-event coefficient footprint drift")
    else:
        pvalues = [float(row["wild_cluster_bootstrap_p_value"]) for row in post_rows]
        betas = [float(row["coefficient_log_points_per_1sd_pga"]) for row in post_rows]
        if not all(value > 0.10 for value in pvalues):
            errors.append("Milestone 8 final interpretation inconsistent: a primary post WCB p-value is <=0.10")
        if not all(value < 0.0 for value in betas):
            errors.append("Milestone 8 final interpretation inconsistent: a primary post coefficient is nonnegative")
        if not close(min(pvalues), float(final.get("minimum_primary_post_wild_cluster_bootstrap_p_value", -1.0))):
            errors.append("Milestone 8 minimum primary post WCB p-value summary drift")

    if len(sensitivity_rows) != 32:
        errors.append("Milestone 8 exposure-sensitivity cardinality drift")
    if {row.get("exposure", "") for row in sensitivity_rows} != EXPECTED_SENSITIVITY_EXPOSURES:
        errors.append("Milestone 8 exposure-sensitivity set drift")
    sensitivity_post = [row for row in sensitivity_rows if int(row["event_time"]) in EXPECTED_POST_EVENT_TIMES]
    if sensitivity_post and not all(float(row["coefficient_log_points_per_1sd_exposure"]) < 0.0 for row in sensitivity_post):
        errors.append("Milestone 8 final sensitivity sign summary does not match sensitivity output")

    if housing.get("housing_damage_validation_complete") is not True:
        errors.append("Milestone 8 housing-damage validation incomplete")
    if housing.get("reported_geography_count") != 12 or housing.get("zero_fill_performed") is not False:
        errors.append("Milestone 8 housing-damage reporting/zero-fill contract drift")
    if housing.get("housing_damage_used_as_primary_exposure") is not False:
        errors.append("Milestone 8 housing damage was improperly promoted to primary exposure")
    pga_heavy = float(housing.get("correlations", {}).get("area_mean_pga_vs_heavy_damage_share", {}).get("pearson", float("nan")))
    if not math.isfinite(pga_heavy) or pga_heavy <= 0.0:
        errors.append("Milestone 8 descriptive PGA-heavy-damage validation is missing or nonpositive")

    if growth.get("grdp_growth_robustness_complete") is not True:
        errors.append("Milestone 8 growth robustness incomplete")
    if growth.get("official_growth_observation_count") != 95:
        errors.append("Milestone 8 official growth crosscheck cardinality drift")
    if growth.get("official_full_event_study_growth_panel_available") is not False:
        errors.append("Milestone 8 official growth availability limitation was lost")
    if growth.get("official_growth_event_study_fit_performed") is not False:
        errors.append("Milestone 8 fitted an unqualified official-growth event study")
    if growth.get("derived_growth_event_study_fit_performed") is not False:
        errors.append("Milestone 8 improperly substituted derived growth as an identification model")

    if resolution.get("postperiod_source_anomalies_resolved") is not True:
        errors.append("Milestone 8 source anomaly resolution incomplete")
    if resolution.get("decision_count") != 5 or resolution.get("override_count") != 4 or resolution.get("confirmation_count") != 1:
        errors.append("Milestone 8 source anomaly resolution cardinality drift")
    if resolution.get("no_growth_imputed_level_corrections") is not True:
        errors.append("Milestone 8 source resolution used growth-imputed level corrections")
    if resolution.get("original_central_values_preserved") is not True:
        errors.append("Milestone 8 source resolution lost original central values")

    if overlap.get("overlap_2009_reconciled") is not True or overlap.get("failure_count") != 0:
        errors.append("Milestone 8 2009 overlap reconciliation no longer passes")
    if float(overlap.get("max_absolute_relative_difference_percent", 999.0)) > 0.5:
        errors.append("Milestone 8 2009 overlap exceeds locked materiality gate")
    if exposure.get("geography_count") != 19 or exposure.get("all_19_geographies_have_grid_support") is not True:
        errors.append("Milestone 8 physical exposure footprint drift")
    if exposure.get("historical_boundary_continuity_claimed") is not False:
        errors.append("Milestone 8 false historical-boundary continuity claim")

    if prefit_gate.get("schema") != "ranah-observatory/milestone8-design-gate/v4":
        errors.append("Milestone 8 pre-fit design gate schema/history drift")
    if prefit_gate.get("outcome_model_fit") is not False:
        errors.append("Milestone 8 pre-fit design gate was rewritten after fit")
    if prefit_gate.get("inference_protocol_locked_before_outcome_model_fit") is not True:
        errors.append("Milestone 8 inference protocol was not locked before model fit")

    if final.get("finding_count") != len(findings):
        errors.append("Milestone 8 finding count drift")
    if final.get("findings_sha256") != sha256(FINDINGS):
        errors.append("Milestone 8 findings SHA-256 drift")
    if any(row.get("causal_effect_presence_claim", "").lower() != "false" for row in findings):
        errors.append("Milestone 8 finding improperly claims an established nonzero causal effect")
    if not any(row.get("finding_id") == "m8_primary_interpretation" for row in findings):
        errors.append("Milestone 8 final interpretation finding missing")

    input_path_map = {
        "event_study_manifest": EVENT,
        "primary_coefficients": PRIMARY,
        "exposure_sensitivity": SENSITIVITY,
        "housing_validation": HOUSING,
        "growth_robustness": GROWTH,
        "source_resolution": RESOLUTION,
        "overlap_reconciliation": OVERLAP,
        "exposure_manifest": EXPOSURE,
        "inference_protocol": INFERENCE,
    }
    final_inputs = final.get("inputs", {})
    for key, path in input_path_map.items():
        entry = final_inputs.get(key, {})
        if entry.get("path") != str(path.relative_to(ROOT)):
            errors.append(f"Milestone 8 final input path drift: {key}")
        if entry.get("sha256") != sha256(path):
            errors.append(f"Milestone 8 final input SHA-256 drift: {key}")

    report = {
        "schema": "ranah-observatory/milestone8-complete-audit/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "case_study": final.get("case_study"),
        "geography_count": final.get("geography_count"),
        "observation_count": final.get("observation_count"),
        "finding_count": final.get("finding_count"),
        "source_anomalies_resolved": final.get("source_anomalies_resolved") is True,
        "overlap_2009_reconciled": final.get("overlap_2009_reconciled") is True,
        "core_identification_diagnostics_passed": final.get("core_identification_diagnostics_passed") is True,
        "housing_damage_validation_complete": final.get("housing_damage_validation_complete") is True,
        "grdp_growth_robustness_complete": final.get("grdp_growth_robustness_complete") is True,
        "small_cluster_inference_implemented": final.get("small_cluster_inference_implemented") is True,
        "quasi_causal_effect_estimated": final.get("quasi_causal_effect_estimated") is True,
        "quasi_causal_estimate_authorized": final.get("quasi_causal_estimate_authorized") is True,
        "directional_nonzero_effect_claim_authorized": final.get("directional_nonzero_effect_claim_authorized") is True,
        "causal_claim_authorized": final.get("causal_claim_authorized") is True,
        "claim_classification": final.get("claim_classification"),
        "milestone8_complete": final.get("milestone8_complete") is True and not errors,
        "errors": errors,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit completed Milestone 8 earthquake quasi-causal case study")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    report = audit()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")

    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone8_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
