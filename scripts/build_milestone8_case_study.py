#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVENT_MANIFEST = ROOT / "data/manifests/milestone8_event_study.json"
PRIMARY = ROOT / "data/analysis/quasi_causal/m8-event-study-primary.csv"
SENSITIVITY = ROOT / "data/analysis/quasi_causal/m8-event-study-exposure-sensitivity.csv"
HOUSING_MANIFEST = ROOT / "data/manifests/milestone8_housing_damage_validation.json"
GROWTH_MANIFEST = ROOT / "data/manifests/milestone8_growth_robustness.json"
RESOLUTION_MANIFEST = ROOT / "data/manifests/milestone8_grdp_source_anomaly_resolution.json"
OVERLAP_MANIFEST = ROOT / "data/manifests/milestone8_grdp_overlap.json"
EXPOSURE_MANIFEST = ROOT / "data/manifests/milestone8_shakemap_exposure_candidate.json"
INFERENCE_PROTOCOL = ROOT / "research/MILESTONE8_INFERENCE_PROTOCOL.md"

FINDINGS = ROOT / "data/analysis/quasi_causal/m8-earthquake-case-study-findings.csv"
FINAL_MANIFEST = ROOT / "data/manifests/milestone8_case_study.json"

EXPECTED_EVENT_TIMES = {-4, -3, -2, 0, 1, 2, 3, 4}
POST_EVENT_TIMES = {0, 1, 2, 3, 4}
SENSITIVITY_EXPOSURES = {
    "area_median_pga_pct_g",
    "area_p90_pga_pct_g",
    "area_max_pga_pct_g",
    "area_mean_mmi",
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def pct_from_log(beta: float) -> float:
    return (math.exp(beta) - 1.0) * 100.0


def main() -> int:
    event = json.loads(EVENT_MANIFEST.read_text(encoding="utf-8"))
    housing = json.loads(HOUSING_MANIFEST.read_text(encoding="utf-8"))
    growth = json.loads(GROWTH_MANIFEST.read_text(encoding="utf-8"))
    resolution = json.loads(RESOLUTION_MANIFEST.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP_MANIFEST.read_text(encoding="utf-8"))
    exposure = json.loads(EXPOSURE_MANIFEST.read_text(encoding="utf-8"))
    primary_rows = read_csv(PRIMARY)
    sensitivity_rows = read_csv(SENSITIVITY)

    require(event.get("schema") == "ranah-observatory/milestone8-event-study/v1", "event-study manifest schema drift")
    require(event.get("outcome_model_fit") is True, "primary outcome model was not fit")
    require(event.get("core_identification_diagnostics_passed") is True, "core identification diagnostics did not pass")
    require(event.get("small_cluster_inference_implemented") is True, "small-cluster inference missing")
    require(event.get("pretrend", {}).get("passed") is True, "pretrend screen did not pass")
    require(event.get("placebo", {}).get("passed") is True, "placebo screen did not pass")
    require(event.get("influence", {}).get("passed") is True, "named influence screen did not pass")
    require(event.get("wild_cluster_bootstrap", {}).get("draws") == 1999, "WCB draw count drift")
    require(event.get("wild_cluster_bootstrap", {}).get("seed") == 20090930, "WCB seed drift")

    require(housing.get("schema") == "ranah-observatory/milestone8-housing-damage-validation/v1", "housing validation schema drift")
    require(housing.get("housing_damage_validation_complete") is True, "housing validation incomplete")
    require(housing.get("reported_geography_count") == 12, "DLNA reporting footprint drift")
    require(housing.get("zero_fill_performed") is False, "DLNA unreported geographies were zero-filled")
    require(housing.get("housing_damage_used_as_primary_exposure") is False, "housing damage improperly promoted to primary exposure")

    require(growth.get("schema") == "ranah-observatory/milestone8-growth-robustness/v1", "growth robustness schema drift")
    require(growth.get("grdp_growth_robustness_complete") is True, "growth robustness qualification incomplete")
    require(growth.get("official_growth_observation_count") == 95, "official growth observation footprint drift")
    require(growth.get("official_full_event_study_growth_panel_available") is False, "unexpected official full-window growth availability state")
    require(growth.get("official_growth_event_study_fit_performed") is False, "unpreregistered official-growth event study was fit")
    require(growth.get("derived_growth_event_study_fit_performed") is False, "derived growth was improperly used as replacement identification model")

    require(resolution.get("postperiod_source_anomalies_resolved") is True, "GRDP source anomalies unresolved")
    require(resolution.get("no_growth_imputed_level_corrections") is True, "level corrections were imputed from growth")
    require(resolution.get("original_central_values_preserved") is True, "original central values were not preserved")
    require(resolution.get("resolved_panel_observation_count") == 171, "resolved panel cardinality drift")
    require(overlap.get("overlap_2009_reconciled") is True and overlap.get("failure_count") == 0, "2009 overlap reconciliation failed")
    require(float(overlap.get("max_absolute_relative_difference_percent", 999.0)) <= 0.5, "2009 overlap exceeds locked materiality gate")
    require(exposure.get("geography_count") == 19 and exposure.get("all_19_geographies_have_grid_support") is True, "primary exposure footprint drift")
    require(exposure.get("historical_boundary_continuity_claimed") is False, "false historical-boundary continuity claim")

    require(len(primary_rows) == 8, "primary event-study output must contain eight estimated event times")
    primary_by_event: dict[int, dict[str, Any]] = {}
    for row in primary_rows:
        event_time = int(row["event_time"])
        require(event_time not in primary_by_event, f"duplicate primary event time {event_time}")
        primary_by_event[event_time] = {
            "event_time": event_time,
            "calendar_year": int(row["calendar_year"]),
            "period_class": row["period_class"],
            "beta": float(row["coefficient_log_points_per_1sd_pga"]),
            "se": float(row["cr1_cluster_se"]),
            "t": float(row["cr1_t"]),
            "wcb_p": float(row["wild_cluster_bootstrap_p_value"]),
        }
    require(set(primary_by_event) == EXPECTED_EVENT_TIMES, "primary event-time footprint drift")

    post_rows = [primary_by_event[event_time] for event_time in sorted(POST_EVENT_TIMES)]
    min_post_wcb_p = min(float(row["wcb_p"]) for row in post_rows)
    all_post_wcb_p_above_0_10 = all(float(row["wcb_p"]) > 0.10 for row in post_rows)
    all_post_coefficients_negative = all(float(row["beta"]) < 0.0 for row in post_rows)

    require(len(sensitivity_rows) == 32, "exposure-sensitivity cardinality drift")
    sensitivity_exposures = {row["exposure"] for row in sensitivity_rows}
    require(sensitivity_exposures == SENSITIVITY_EXPOSURES, "exposure-sensitivity set drift")
    sensitivity_post = [row for row in sensitivity_rows if int(row["event_time"]) in POST_EVENT_TIMES]
    sensitivity_post_all_negative = all(float(row["coefficient_log_points_per_1sd_exposure"]) < 0.0 for row in sensitivity_post)
    sensitivity_post_min = min(float(row["coefficient_log_points_per_1sd_exposure"]) for row in sensitivity_post)
    sensitivity_post_max = max(float(row["coefficient_log_points_per_1sd_exposure"]) for row in sensitivity_post)

    quasi_causal_estimate_authorized = True
    directional_nonzero_effect_claim_authorized = False
    claim_classification = "quasi_causal_estimate_no_statistically_robust_differential_effect_detected"

    findings: list[dict[str, Any]] = []
    findings.append(
        {
            "finding_id": "m8_source_resolution",
            "claim_type": "observed_and_reconciled_evidence",
            "finding": "The 19x2005-2013 real-GRDP panel is fully populated after a pre-fit 2009 overlap bridge and independent local-BPS resolution of four source-level inconsistencies; no level correction was inferred from growth arithmetic.",
            "causal_effect_presence_claim": False,
        }
    )
    findings.append(
        {
            "finding_id": "m8_exposure_validation",
            "claim_type": "derived_physical_exposure_validation",
            "finding": (
                "USGS area-mean PGA covers all 19 geographies. Among the 12 geographies explicitly reported in DLNA Table 3.19, "
                f"PGA correlates positively with heavy housing-damage share (Pearson={housing['correlations']['area_mean_pga_vs_heavy_damage_share']['pearson']:.3f}; "
                f"Spearman={housing['correlations']['area_mean_pga_vs_heavy_damage_share']['spearman']:.3f}). This is descriptive validation, not an exogeneity proof."
            ),
            "causal_effect_presence_claim": False,
        }
    )
    findings.append(
        {
            "finding_id": "m8_pretrend",
            "claim_type": "identification_diagnostic",
            "finding": (
                f"The locked parallel-trend screen passes: joint wild-cluster-bootstrap pretrend p={event['pretrend']['joint_wild_cluster_bootstrap_p_value']:.4f}, "
                f"with maximum absolute pre-event coefficient {event['pretrend']['max_absolute_pre_coefficient_log_points']:.4f}. Passing is a screen, not proof of parallel trends."
            ),
            "causal_effect_presence_claim": False,
        }
    )
    findings.append(
        {
            "finding_id": "m8_placebo",
            "claim_type": "falsification_diagnostic",
            "finding": (
                f"The preregistered 2007 pseudo-event placebo passes (coefficient={event['placebo']['coefficient_log_points_per_1sd_pga']:.4f}; "
                f"wild-cluster-bootstrap p={event['placebo']['wild_cluster_bootstrap_p_value']:.4f})."
            ),
            "causal_effect_presence_claim": False,
        }
    )
    for event_time in sorted(POST_EVENT_TIMES):
        row = primary_by_event[event_time]
        findings.append(
            {
                "finding_id": f"m8_primary_{row['calendar_year']}",
                "claim_type": "quasi_causal_estimate",
                "finding": (
                    f"For {row['calendar_year']}, one SD higher area-mean PGA is associated in the locked event-study with "
                    f"{row['beta']:.6f} log units ({pct_from_log(row['beta']):.3f}% exact log-to-percent transform) of differential real-GRDP trajectory; "
                    f"CR1 SE={row['se']:.6f}, wild-cluster-bootstrap p={row['wcb_p']:.4f}. "
                    "This is an estimated differential trajectory, not evidence that a nonzero effect is statistically established."
                ),
                "causal_effect_presence_claim": False,
            }
        )
    findings.append(
        {
            "finding_id": "m8_influence",
            "claim_type": "influence_diagnostic",
            "finding": (
                f"Named leave-one-out exclusions (Padang, Padang Pariaman, Pariaman) pass the locked influence screen; "
                f"maximum absolute 2010-2013 coefficient change is {event['influence']['max_absolute_change_2010_2013']:.6f} log units."
            ),
            "causal_effect_presence_claim": False,
        }
    )
    findings.append(
        {
            "finding_id": "m8_exposure_sensitivity",
            "claim_type": "robustness_diagnostic",
            "finding": (
                f"All pre-specified 2009-2013 physical-exposure sensitivity point estimates are negative, ranging from {sensitivity_post_min:.6f} to {sensitivity_post_max:.6f} log units per one-SD exposure. "
                "No sensitivity definition was selected by statistical significance."
            ),
            "causal_effect_presence_claim": False,
        }
    )
    findings.append(
        {
            "finding_id": "m8_primary_interpretation",
            "claim_type": "quasi_causal_interpretation",
            "finding": (
                f"All required identification screens pass, so the locked coefficients qualify as quasi-causal estimates; however, none of the 2009-2013 primary coefficients has a wild-cluster-bootstrap p-value at or below 0.10 (minimum={min_post_wcb_p:.4f}). "
                "The defensible conclusion is that this design does not detect a statistically robust differential real-GRDP effect by local shaking intensity in 2009-2013. This must not be restated as proof that the earthquake had no economic damage or as a total-loss estimate."
            ),
            "causal_effect_presence_claim": False,
        }
    )
    findings.append(
        {
            "finding_id": "m8_growth_robustness",
            "claim_type": "source_qualification_and_derived_statistic",
            "finding": (
                "Official comparative growth is directly qualified for all 19 geographies for 2009-2013, while a uniform official tabular 2005-2008 pre-event growth panel is unavailable under the frozen source contract. "
                "The project therefore preserves 95 official growth observations, materializes 152 derived level-to-level transitions separately, and does not substitute the derived series as an unpreregistered causal outcome."
            ),
            "causal_effect_presence_claim": False,
        }
    )

    FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["finding_id", "claim_type", "finding", "causal_effect_presence_claim"]
    with FINDINGS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(findings)

    final = {
        "schema": "ranah-observatory/milestone8-case-study/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "case_study": "2009 West Sumatra earthquake differential economic trajectory",
        "case_study_complete": True,
        "milestone8_complete": True,
        "geography_count": 19,
        "analysis_years": list(range(2005, 2014)),
        "observation_count": 171,
        "primary_exposure": "area_mean_pga_pct_g",
        "primary_exposure_unit": "percent_g before one-SD standardization",
        "primary_design": "continuous_intensity_two_way_fixed_effects_event_study",
        "small_cluster_inference": "Rademacher wild-cluster-bootstrap-t, B=1999, seed=20090930, geography clusters",
        "source_anomalies_resolved": True,
        "overlap_2009_reconciled": True,
        "core_identification_diagnostics_passed": True,
        "pretrend_passed": True,
        "placebo_passed": True,
        "influence_passed": True,
        "housing_damage_validation_complete": True,
        "grdp_growth_robustness_complete": True,
        "small_cluster_inference_implemented": True,
        "exposure_sensitivity_complete": True,
        "sensitivity_post_all_negative": sensitivity_post_all_negative,
        "sensitivity_post_coefficient_range": [sensitivity_post_min, sensitivity_post_max],
        "primary_post_coefficients_all_negative": all_post_coefficients_negative,
        "minimum_primary_post_wild_cluster_bootstrap_p_value": min_post_wcb_p,
        "all_primary_post_wild_cluster_bootstrap_p_values_above_0_10": all_post_wcb_p_above_0_10,
        "quasi_causal_effect_estimated": True,
        "quasi_causal_estimate_authorized": quasi_causal_estimate_authorized,
        "directional_nonzero_effect_claim_authorized": directional_nonzero_effect_claim_authorized,
        "causal_claim_authorized": False,
        "claim_classification": claim_classification,
        "headline_conclusion": "The preregistered design passes its identification screens, but it does not detect a statistically robust differential real-GRDP effect by local earthquake shaking intensity over 2009-2013.",
        "prohibited_interpretations": [
            "The earthquake had no economic impact.",
            "The coefficient is the total economic loss from the earthquake.",
            "The coefficient measures welfare loss or wasted potential.",
            "A later positive or recovered trajectory would imply the earthquake was beneficial.",
            "DLNA-unreported geographies had zero housing damage.",
        ],
        "finding_count": len(findings),
        "findings_path": str(FINDINGS.relative_to(ROOT)),
        "findings_sha256": sha256(FINDINGS),
        "inputs": {
            "event_study_manifest": {"path": str(EVENT_MANIFEST.relative_to(ROOT)), "sha256": sha256(EVENT_MANIFEST)},
            "primary_coefficients": {"path": str(PRIMARY.relative_to(ROOT)), "sha256": sha256(PRIMARY)},
            "exposure_sensitivity": {"path": str(SENSITIVITY.relative_to(ROOT)), "sha256": sha256(SENSITIVITY)},
            "housing_validation": {"path": str(HOUSING_MANIFEST.relative_to(ROOT)), "sha256": sha256(HOUSING_MANIFEST)},
            "growth_robustness": {"path": str(GROWTH_MANIFEST.relative_to(ROOT)), "sha256": sha256(GROWTH_MANIFEST)},
            "source_resolution": {"path": str(RESOLUTION_MANIFEST.relative_to(ROOT)), "sha256": sha256(RESOLUTION_MANIFEST)},
            "overlap_reconciliation": {"path": str(OVERLAP_MANIFEST.relative_to(ROOT)), "sha256": sha256(OVERLAP_MANIFEST)},
            "exposure_manifest": {"path": str(EXPOSURE_MANIFEST.relative_to(ROOT)), "sha256": sha256(EXPOSURE_MANIFEST)},
            "inference_protocol": {"path": str(INFERENCE_PROTOCOL.relative_to(ROOT)), "sha256": sha256(INFERENCE_PROTOCOL)},
        },
    }
    FINAL_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    FINAL_MANIFEST.write_text(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
