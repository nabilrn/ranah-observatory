#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE8_QUASI_CAUSAL_SPEC.md"
SOURCE_PLAN = ROOT / "data/registries/milestone8_earthquake_source_plan.csv"
GEOGRAPHY_CONTRACT = ROOT / "data/registries/milestone8_geography_contract.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone8_design_gate.json"
EXPOSURE_MANIFEST = ROOT / "data/manifests/milestone8_shakemap_exposure_candidate.json"
EXPOSURE_CSV = ROOT / "data/analysis/quasi_causal/m8-shakemap-exposure-candidate.csv"
OVERLAP_MANIFEST = ROOT / "data/manifests/milestone8_grdp_overlap.json"
OVERLAP_CSV = ROOT / "data/analysis/quasi_causal/m8-grdp-2009-overlap.csv"
PANEL_MANIFEST = ROOT / "data/manifests/milestone8_grdp_panel.json"
PANEL_CSV = ROOT / "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013.csv"

EXPECTED_GEOGRAPHIES = {
    "idn.13.1301", "idn.13.1302", "idn.13.1303", "idn.13.1304", "idn.13.1305",
    "idn.13.1306", "idn.13.1307", "idn.13.1308", "idn.13.1309", "idn.13.1310",
    "idn.13.1311", "idn.13.1312", "idn.13.1371", "idn.13.1372", "idn.13.1373",
    "idn.13.1374", "idn.13.1375", "idn.13.1376", "idn.13.1377",
}
EXPECTED_ANOMALY_GEOGRAPHIES = {"idn.13.1310", "idn.13.1375"}
EXPECTED_SOURCE_IDS = {
    "m8_event_bnpb",
    "m8_damage_dlna",
    "m8_damage_dlna_mirror",
    "m8_usgs_shakemap",
    "m8_big_fixed_boundary",
    "m8_grdp_pre",
    "m8_grdp_pre_national",
    "m8_grdp_post",
    "m8_padang_validation",
    "m8_padang_pariaman_validation",
    "m8_geography_registry",
}
LEGAL_ANCHORS_REQUIRED = {
    "idn.13.1310": "UU 38/2003",
    "idn.13.1311": "UU 38/2003",
    "idn.13.1312": "UU 38/2003",
    "idn.13.1377": "UU 12/2002",
}
LOCKED_DESIGN = {
    "criterion": "one focused causal or quasi-causal case study",
    "case_study": "2009 West Sumatra earthquake differential economic trajectory",
    "event_date": "2009-09-30",
    "intended_geography_count": 19,
    "target_start_year": 2005,
    "target_end_year": 2013,
    "primary_outcome": "log_real_grdp_constant_2000",
    "original_primary_exposure": "heavy_housing_damage_share",
    "primary_exposure": "area_mean_pga_pct_g",
    "primary_exposure_standardized_form": "z(area_mean_pga_pct_g)",
    "primary_design": "continuous_intensity_two_way_fixed_effects_event_study",
    "baseline_year": 2008,
    "partial_treatment_year": 2009,
}
REQUIRED_SPEC_PHRASES = [
    "Amendment 1 — physical shaking exposure, before outcome-model fitting",
    "30 September 2009",
    "area_mean_pga_pct_g",
    "fixed-current-boundary",
    "continuous-intensity two-way fixed-effects event study",
    "2008 (`k=-1`) is the omitted baseline",
    "partial-treatment year",
    "wild cluster bootstrap",
    "quasi-causal estimate",
    "association",
    "No outcome model has been fit",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [
        SPEC, SOURCE_PLAN, GEOGRAPHY_CONTRACT, DESIGN_GATE,
        EXPOSURE_MANIFEST, EXPOSURE_CSV,
        OVERLAP_MANIFEST, OVERLAP_CSV,
        PANEL_MANIFEST, PANEL_CSV,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {
            "schema": "ranah-observatory/milestone8-design-audit/v3",
            "criterion": LOCKED_DESIGN["criterion"],
            "errors": [f"missing required file: {path}" for path in missing],
            "design_preregistered": False,
            "milestone8_complete": False,
        }

    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    exposure_manifest = json.loads(EXPOSURE_MANIFEST.read_text(encoding="utf-8"))
    overlap_manifest = json.loads(OVERLAP_MANIFEST.read_text(encoding="utf-8"))
    panel_manifest = json.loads(PANEL_MANIFEST.read_text(encoding="utf-8"))
    spec_text = SPEC.read_text(encoding="utf-8")
    source_rows = read_csv(SOURCE_PLAN)
    geography_rows = read_csv(GEOGRAPHY_CONTRACT)
    exposure_rows = read_csv(EXPOSURE_CSV)
    panel_rows = read_csv(PANEL_CSV)

    if gate.get("schema") != "ranah-observatory/milestone8-design-gate/v3":
        errors.append("Milestone 8 design-gate schema drift")
    for key, expected in LOCKED_DESIGN.items():
        if gate.get(key) != expected:
            errors.append(f"Milestone 8 locked design drift: {key}")

    if gate.get("design_preregistered") is not True:
        errors.append("Milestone 8 design must remain preregistered")
    if gate.get("design_amendment_count") != 1:
        errors.append("Milestone 8 must retain exactly one pre-fit design amendment")
    if gate.get("amendment_1_applied_before_outcome_model_fit") is not True:
        errors.append("Milestone 8 Amendment 1 must remain explicitly pre-fit")
    if gate.get("outcome_model_fit") is not False:
        errors.append("Milestone 8 design audit must remain pre outcome-model fit")
    if gate.get("geography_2005_2013_qualified") is not True:
        errors.append("Milestone 8 geography gate is not qualified")
    if gate.get("geography_qualification_scope") != "M8 analytical footprint only; no general historical backcast":
        errors.append("Milestone 8 geography qualification scope drift")
    if gate.get("primary_exposure_spatial_frame") != "BIG June 2026 fixed-current-boundary polygons":
        errors.append("Milestone 8 primary-exposure spatial frame drift")
    if gate.get("historical_boundary_continuity_claimed_for_exposure") is not False:
        errors.append("Milestone 8 must not claim historical boundary continuity for exposure polygons")
    if gate.get("full_exposure_19_geographies_frozen") is not True:
        errors.append("Milestone 8 physical exposure must cover exact 19 geographies before fit")
    if gate.get("housing_damage_reporting_geography_count") != 12:
        errors.append("Milestone 8 must retain observed 12-geography DLNA reporting limitation")
    if gate.get("housing_damage_zero_fill_forbidden") is not True:
        errors.append("Milestone 8 must forbid zero-filling unreported DLNA geographies")

    if gate.get("preperiod_table_value_extraction_complete") is not True:
        errors.append("Milestone 8 pre-period table-value extraction gate is not closed")
    if gate.get("postperiod_table_value_extraction_complete") is not True:
        errors.append("Milestone 8 post-period table-value extraction gate is not closed")
    if gate.get("overlap_2009_reconciled") is not True:
        errors.append("Milestone 8 2009 overlap must remain reconciled")
    if float(gate.get("overlap_materiality_threshold_percent", -1)) != 0.5:
        errors.append("Milestone 8 overlap materiality threshold drift")
    if float(gate.get("overlap_max_absolute_relative_difference_percent", 999)) > 0.5:
        errors.append("Milestone 8 overlap maximum difference exceeds locked materiality gate")
    if gate.get("overlap_bridge_source_for_2009") != "later_postperiod_source_table_13_1_2":
        errors.append("Milestone 8 2009 bridge source drift")
    if gate.get("outcome_panel_combined") is not True or gate.get("outcome_panel_observation_count") != 171:
        errors.append("Milestone 8 exact 19x9 outcome panel gate is not closed")

    # Current pre-fit checkpoint intentionally retains these source anomalies.
    if gate.get("postperiod_source_anomalies_resolved") is not False:
        errors.append("Milestone 8 design checkpoint must not silently mark source anomalies resolved")
    if gate.get("postperiod_source_anomaly_row_count") != 4:
        errors.append("Milestone 8 post-period anomaly row count drift")
    if set(gate.get("postperiod_source_anomaly_geography_ids", [])) != EXPECTED_ANOMALY_GEOGRAPHIES:
        errors.append("Milestone 8 post-period anomaly geography set drift")
    if "do not silently correct" not in str(gate.get("postperiod_source_anomaly_rule", "")):
        errors.append("Milestone 8 source-anomaly no-silent-correction rule lost")

    if gate.get("quasi_causal_effect_estimated") is not False:
        errors.append("Milestone 8 foundation must not yet claim an estimated quasi-causal effect")
    if gate.get("causal_claim_authorized") is not False:
        errors.append("Milestone 8 foundation must not yet authorize causal language")
    if gate.get("milestone8_complete") is not False:
        errors.append("Milestone 8 cannot be complete at the current data-qualification stage")
    blocking_reasons = gate.get("blocking_reasons")
    if not isinstance(blocking_reasons, list) or not blocking_reasons:
        errors.append("Milestone 8 incomplete state must retain explicit blocking reasons")

    for phrase in REQUIRED_SPEC_PHRASES:
        if phrase not in spec_text:
            errors.append(f"Milestone 8 preregistration lost required phrase: {phrase}")

    source_ids = [row.get("source_plan_id", "") for row in source_rows]
    if len(source_ids) != len(set(source_ids)):
        errors.append("Milestone 8 source plan contains duplicate source_plan_id values")
    if set(source_ids) != EXPECTED_SOURCE_IDS:
        errors.append("Milestone 8 source-plan ID set drift")
    for row in source_rows:
        if row.get("required_before_fit") not in {"true", "false"}:
            errors.append(f"Invalid required_before_fit flag for {row.get('source_plan_id')}")
        if not row.get("authority") or not row.get("title") or not row.get("qualification_status"):
            errors.append(f"Incomplete source-plan metadata for {row.get('source_plan_id')}")
    source_by_id = {row["source_plan_id"]: row for row in source_rows}
    if source_by_id.get("m8_usgs_shakemap", {}).get("role") != "primary_treatment_exposure":
        errors.append("USGS ShakeMap must remain the primary treatment-exposure source")
    if source_by_id.get("m8_damage_dlna", {}).get("role") != "secondary_damage_validation":
        errors.append("DLNA housing damage must remain secondary validation after Amendment 1")
    if source_by_id.get("m8_grdp_pre", {}).get("role") != "outcome_preperiod_primary":
        errors.append("Qualified Sumatera Barat Table 22 must remain the primary pre-period outcome source")
    if source_by_id.get("m8_grdp_pre", {}).get("required_before_fit") != "true":
        errors.append("Qualified Sumatera Barat Table 22 must remain required before model fit")
    if "qualified_exact_table22_19x5" not in source_by_id.get("m8_grdp_pre", {}).get("qualification_status", ""):
        errors.append("Sumatera Barat pre-period source must retain exact Table 22 qualification")
    if source_by_id.get("m8_grdp_pre_national", {}).get("role") != "outcome_preperiod_crosscheck_scan":
        errors.append("National BPS 2005-2009 scan must remain a non-primary cross-check source")
    if source_by_id.get("m8_grdp_pre_national", {}).get("required_before_fit") != "false":
        errors.append("National scanned BPS source must not remain a blocking pre-fit dependency")

    geography_ids = [row.get("geography_id", "") for row in geography_rows]
    if len(geography_rows) != 19:
        errors.append("Milestone 8 geography contract must contain exactly 19 rows")
    if len(geography_ids) != len(set(geography_ids)):
        errors.append("Milestone 8 geography contract contains duplicate geography IDs")
    if set(geography_ids) != EXPECTED_GEOGRAPHIES:
        errors.append("Milestone 8 geography footprint drift")
    for row in geography_rows:
        gid = row.get("geography_id", "")
        if row.get("analysis_start") != "2005" or row.get("analysis_end") != "2013":
            errors.append(f"Milestone 8 geography window drift for {gid}")
        if row.get("footprint_status") != "qualified_for_m8":
            errors.append(f"Milestone 8 geography not qualified: {gid}")
        if not row.get("qualification_basis"):
            errors.append(f"Milestone 8 geography lacks qualification basis: {gid}")
    geography_by_id = {row["geography_id"]: row for row in geography_rows if row.get("geography_id")}
    for gid, legal_token in LEGAL_ANCHORS_REQUIRED.items():
        if legal_token not in geography_by_id.get(gid, {}).get("legal_anchor", ""):
            errors.append(f"Milestone 8 legal anchor missing or drifted for {gid}")

    if exposure_manifest.get("schema") != "ranah-observatory/milestone8-shakemap-exposure-candidate/v1":
        errors.append("Milestone 8 ShakeMap exposure manifest schema drift")
    if exposure_manifest.get("primary_candidate") != "area_mean_pga_pct_g":
        errors.append("Milestone 8 ShakeMap primary candidate drift")
    if exposure_manifest.get("primary_candidate_selected_before_outcome_model_fit") is not True:
        errors.append("ShakeMap primary candidate must be selected before outcome-model fit")
    if exposure_manifest.get("geography_count") != 19 or exposure_manifest.get("all_19_geographies_have_grid_support") is not True:
        errors.append("Milestone 8 ShakeMap candidate must cover exact 19 geographies")
    if exposure_manifest.get("historical_boundary_continuity_claimed") is not False:
        errors.append("ShakeMap candidate must not claim historical boundary continuity")
    if exposure_manifest.get("outcome_model_fit") is not False or exposure_manifest.get("causal_effect_estimated") is not False:
        errors.append("ShakeMap candidate manifest must remain pre-model and non-causal")
    if exposure_manifest.get("output_sha256") != sha256(EXPOSURE_CSV):
        errors.append("Milestone 8 ShakeMap exposure output SHA-256 drift")
    exposure_ids = [row.get("geography_id", "") for row in exposure_rows]
    if len(exposure_rows) != 19 or set(exposure_ids) != EXPECTED_GEOGRAPHIES or len(set(exposure_ids)) != 19:
        errors.append("Milestone 8 ShakeMap exposure CSV footprint drift")

    if overlap_manifest.get("schema") != "ranah-observatory/milestone8-grdp-overlap/v1":
        errors.append("Milestone 8 overlap manifest schema drift")
    if overlap_manifest.get("overlap_2009_reconciled") is not True:
        errors.append("Milestone 8 overlap manifest no longer passes reconciliation")
    if overlap_manifest.get("failure_count") != 0:
        errors.append("Milestone 8 overlap manifest contains materiality failures")
    if float(overlap_manifest.get("materiality_threshold_percent", -1)) != 0.5:
        errors.append("Milestone 8 overlap manifest threshold drift")
    if float(overlap_manifest.get("max_absolute_relative_difference_percent", 999)) > 0.5:
        errors.append("Milestone 8 overlap manifest exceeds 0.5% materiality gate")
    if overlap_manifest.get("output_sha256") != sha256(OVERLAP_CSV):
        errors.append("Milestone 8 overlap CSV SHA-256 drift")

    if panel_manifest.get("schema") != "ranah-observatory/milestone8-grdp-panel/v1":
        errors.append("Milestone 8 GRDP panel manifest schema drift")
    if panel_manifest.get("observation_count") != 171 or panel_manifest.get("geography_count") != 19:
        errors.append("Milestone 8 GRDP panel cardinality drift")
    if panel_manifest.get("years") != list(range(2005, 2014)):
        errors.append("Milestone 8 GRDP panel year footprint drift")
    if panel_manifest.get("overlap_2009_reconciled") is not True:
        errors.append("Milestone 8 GRDP panel lost reconciled overlap state")
    if panel_manifest.get("postperiod_source_anomalies_resolved") is not False:
        errors.append("Milestone 8 GRDP panel must retain unresolved source-anomaly state at this checkpoint")
    if panel_manifest.get("anomaly_row_count") != 4:
        errors.append("Milestone 8 GRDP panel anomaly row count drift")
    if set(panel_manifest.get("anomaly_geography_ids", [])) != EXPECTED_ANOMALY_GEOGRAPHIES:
        errors.append("Milestone 8 GRDP panel anomaly geography set drift")
    if panel_manifest.get("model_ready") is not False:
        errors.append("Milestone 8 GRDP panel must remain model-blocked until source anomalies are resolved")
    if panel_manifest.get("output_sha256") != sha256(PANEL_CSV):
        errors.append("Milestone 8 GRDP panel SHA-256 drift")

    panel_keys = {(row.get("geography_id", ""), row.get("year", "")) for row in panel_rows}
    if len(panel_rows) != 171 or len(panel_keys) != 171:
        errors.append("Milestone 8 GRDP panel must contain exact 171 unique geography-year rows")
    if {row.get("geography_id", "") for row in panel_rows} != EXPECTED_GEOGRAPHIES:
        errors.append("Milestone 8 GRDP panel geography footprint drift")

    return {
        "schema": "ranah-observatory/milestone8-design-audit/v3",
        "criterion": LOCKED_DESIGN["criterion"],
        "case_study": LOCKED_DESIGN["case_study"],
        "event_date": LOCKED_DESIGN["event_date"],
        "geography_count": len(geography_rows),
        "source_plan_count": len(source_rows),
        "primary_exposure": gate.get("primary_exposure"),
        "design_amendment_count": gate.get("design_amendment_count"),
        "design_preregistered": gate.get("design_preregistered") is True,
        "amendment_applied_before_outcome_model_fit": gate.get("amendment_1_applied_before_outcome_model_fit") is True,
        "geography_2005_2013_qualified": gate.get("geography_2005_2013_qualified") is True,
        "full_exposure_19_geographies_frozen": gate.get("full_exposure_19_geographies_frozen") is True,
        "overlap_2009_reconciled": gate.get("overlap_2009_reconciled") is True,
        "outcome_panel_combined": gate.get("outcome_panel_combined") is True,
        "outcome_panel_observation_count": gate.get("outcome_panel_observation_count"),
        "postperiod_source_anomalies_resolved": gate.get("postperiod_source_anomalies_resolved") is True,
        "outcome_model_fit": gate.get("outcome_model_fit") is True,
        "quasi_causal_effect_estimated": gate.get("quasi_causal_effect_estimated") is True,
        "causal_claim_authorized": gate.get("causal_claim_authorized") is True,
        "milestone8_complete": gate.get("milestone8_complete") is True,
        "blocking_reason_count": len(blocking_reasons) if isinstance(blocking_reasons, list) else 0,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 8 preregistered quasi-causal design")
    parser.add_argument(
        "--require-preregistered",
        action="store_true",
        help="fail unless the preregistered/amended pre-fit design and reconciled outcome panel pass while causal claims remain locked",
    )
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_preregistered:
        required_true = [
            "design_preregistered",
            "amendment_applied_before_outcome_model_fit",
            "geography_2005_2013_qualified",
            "full_exposure_19_geographies_frozen",
            "overlap_2009_reconciled",
            "outcome_panel_combined",
        ]
        if any(report.get(key) is not True for key in required_true):
            return 1
        if report.get("postperiod_source_anomalies_resolved") is not False:
            return 1
        if report.get("outcome_model_fit") is not False:
            return 1
        if report.get("quasi_causal_effect_estimated") is not False:
            return 1
        if report.get("causal_claim_authorized") is not False:
            return 1
        if report.get("milestone8_complete") is not False:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
