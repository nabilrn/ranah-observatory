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

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE8_QUASI_CAUSAL_SPEC.md"
INFERENCE = ROOT / "research/MILESTONE8_INFERENCE_PROTOCOL.md"
SOURCE_PLAN = ROOT / "data/registries/milestone8_earthquake_source_plan.csv"
GEOGRAPHY_CONTRACT = ROOT / "data/registries/milestone8_geography_contract.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone8_design_gate.json"
EXPOSURE_MANIFEST = ROOT / "data/manifests/milestone8_shakemap_exposure_candidate.json"
EXPOSURE_CSV = ROOT / "data/analysis/quasi_causal/m8-shakemap-exposure-candidate.csv"
OVERLAP_MANIFEST = ROOT / "data/manifests/milestone8_grdp_overlap.json"
RESOLUTION_MANIFEST = ROOT / "data/manifests/milestone8_grdp_source_anomaly_resolution.json"
RESOLUTION_CSV = ROOT / "data/analysis/quasi_causal/m8-grdp-source-anomaly-resolution.csv"
RESOLVED_PANEL = ROOT / "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013-resolved.csv"

EXPECTED_GEOGRAPHIES = {
    "idn.13.1301", "idn.13.1302", "idn.13.1303", "idn.13.1304", "idn.13.1305",
    "idn.13.1306", "idn.13.1307", "idn.13.1308", "idn.13.1309", "idn.13.1310",
    "idn.13.1311", "idn.13.1312", "idn.13.1371", "idn.13.1372", "idn.13.1373",
    "idn.13.1374", "idn.13.1375", "idn.13.1376", "idn.13.1377",
}
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
LOCKED_INFERENCE = {
    "wild_cluster_bootstrap_distribution": "rademacher",
    "wild_cluster_bootstrap_draws": 1999,
    "wild_cluster_bootstrap_seed": 20090930,
    "pretrend_joint_pvalue_minimum": 0.10,
    "pretrend_max_absolute_log_point_coefficient": 0.10,
    "placebo_pvalue_minimum": 0.10,
    "placebo_max_absolute_log_point_coefficient": 0.10,
    "named_influence_max_absolute_log_point_change": 0.10,
}
REQUIRED_SPEC_PHRASES = [
    "Amendment 1 — physical shaking exposure, before outcome-model fitting",
    "area_mean_pga_pct_g",
    "2008 (`k=-1`) is the omitted baseline",
    "wild cluster bootstrap",
    "association",
]
REQUIRED_INFERENCE_PHRASES = [
    "B = 1,999",
    "20090930",
    "joint pre-trend p-value is **>= 0.10**",
    "pseudo event in 2007",
    "Kota Padang",
    "Kabupaten Padang Pariaman",
    "Kota Pariaman",
    "area-90th-percentile PGA",
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
        SPEC, INFERENCE, SOURCE_PLAN, GEOGRAPHY_CONTRACT, DESIGN_GATE,
        EXPOSURE_MANIFEST, EXPOSURE_CSV, OVERLAP_MANIFEST,
        RESOLUTION_MANIFEST, RESOLUTION_CSV, RESOLVED_PANEL,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {
            "schema": "ranah-observatory/milestone8-design-audit/v4",
            "criterion": LOCKED_DESIGN["criterion"],
            "errors": [f"missing required file: {path}" for path in missing],
            "design_preregistered": False,
            "geography_2005_2013_qualified": False,
            "quasi_causal_effect_estimated": False,
            "causal_claim_authorized": False,
            "milestone8_complete": False,
            "blocking_reason_count": 0,
        }

    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    exposure_manifest = json.loads(EXPOSURE_MANIFEST.read_text(encoding="utf-8"))
    overlap = json.loads(OVERLAP_MANIFEST.read_text(encoding="utf-8"))
    resolution = json.loads(RESOLUTION_MANIFEST.read_text(encoding="utf-8"))
    source_rows = read_csv(SOURCE_PLAN)
    geography_rows = read_csv(GEOGRAPHY_CONTRACT)
    exposure_rows = read_csv(EXPOSURE_CSV)
    resolution_rows = read_csv(RESOLUTION_CSV)
    panel_rows = read_csv(RESOLVED_PANEL)
    spec_text = SPEC.read_text(encoding="utf-8")
    inference_text = INFERENCE.read_text(encoding="utf-8")

    if gate.get("schema") != "ranah-observatory/milestone8-design-gate/v4":
        errors.append("Milestone 8 design-gate schema drift")
    for key, expected in LOCKED_DESIGN.items():
        if gate.get(key) != expected:
            errors.append(f"Milestone 8 locked design drift: {key}")
    for key, expected in LOCKED_INFERENCE.items():
        if gate.get(key) != expected:
            errors.append(f"Milestone 8 locked inference drift: {key}")

    if gate.get("design_preregistered") is not True:
        errors.append("Milestone 8 design must remain preregistered")
    if gate.get("design_amendment_count") != 1 or gate.get("amendment_1_applied_before_outcome_model_fit") is not True:
        errors.append("Milestone 8 must retain exactly one explicitly pre-fit exposure amendment")
    if gate.get("inference_protocol_path") != "research/MILESTONE8_INFERENCE_PROTOCOL.md":
        errors.append("Milestone 8 inference protocol path drift")
    if gate.get("inference_protocol_locked_before_outcome_model_fit") is not True:
        errors.append("Milestone 8 inference protocol must be locked before model fit")
    if gate.get("model_fit_authorized") is not True:
        errors.append("Milestone 8 model fit must be explicitly authorized only after source gates close")
    if gate.get("outcome_model_fit") is not False:
        errors.append("Milestone 8 design audit v4 is a pre-fit checkpoint")

    if gate.get("geography_2005_2013_qualified") is not True:
        errors.append("Milestone 8 geography gate is not qualified")
    if gate.get("geography_qualification_scope") != "M8 analytical footprint only; no general historical backcast":
        errors.append("Milestone 8 geography qualification scope drift")
    if gate.get("historical_boundary_continuity_claimed_for_exposure") is not False:
        errors.append("Milestone 8 must not claim historical-boundary continuity for exposure polygons")
    if gate.get("full_exposure_19_geographies_frozen") is not True:
        errors.append("Milestone 8 physical exposure must cover all 19 geographies")
    if gate.get("housing_damage_reporting_geography_count") != 12 or gate.get("housing_damage_zero_fill_forbidden") is not True:
        errors.append("Milestone 8 must preserve the 12-geography DLNA limitation and zero-fill prohibition")

    if gate.get("preperiod_table_value_extraction_complete") is not True or gate.get("postperiod_table_value_extraction_complete") is not True:
        errors.append("Milestone 8 pre/post table-value extraction gates are not closed")
    if gate.get("overlap_2009_reconciled") is not True:
        errors.append("Milestone 8 2009 overlap must remain reconciled")
    if float(gate.get("overlap_materiality_threshold_percent", -1)) != 0.5:
        errors.append("Milestone 8 overlap threshold drift")
    if float(gate.get("overlap_max_absolute_relative_difference_percent", 999)) > 0.5:
        errors.append("Milestone 8 overlap exceeds locked materiality gate")
    if gate.get("outcome_panel_combined") is not True or gate.get("outcome_panel_observation_count") != 171:
        errors.append("Milestone 8 exact 19x9 panel gate is not closed")
    if gate.get("resolved_outcome_panel_path") != "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013-resolved.csv":
        errors.append("Milestone 8 resolved-panel path drift")

    if gate.get("postperiod_source_anomalies_resolved") is not True:
        errors.append("Milestone 8 source anomalies are not marked resolved")
    if gate.get("source_anomaly_resolution_decision_count") != 5:
        errors.append("Milestone 8 anomaly resolution decision count drift")
    if gate.get("source_anomaly_override_count") != 4 or gate.get("source_anomaly_confirmation_count") != 1:
        errors.append("Milestone 8 anomaly resolution override/confirmation count drift")
    if gate.get("source_anomaly_original_values_preserved") is not True:
        errors.append("Milestone 8 must preserve original central source values")
    if gate.get("source_anomaly_growth_imputation_used") is not False:
        errors.append("Milestone 8 must not impute level corrections from growth arithmetic")

    if resolution.get("schema") != "ranah-observatory/milestone8-grdp-source-anomaly-resolution/v1":
        errors.append("Milestone 8 anomaly-resolution manifest schema drift")
    if resolution.get("postperiod_source_anomalies_resolved") is not True:
        errors.append("Milestone 8 anomaly-resolution manifest is not complete")
    if resolution.get("no_growth_imputed_level_corrections") is not True or resolution.get("original_central_values_preserved") is not True:
        errors.append("Milestone 8 anomaly-resolution provenance rule drift")
    if resolution.get("decision_count") != 5 or resolution.get("override_count") != 4 or resolution.get("confirmation_count") != 1:
        errors.append("Milestone 8 anomaly-resolution cardinality drift")
    if resolution.get("resolved_panel_observation_count") != 171 or resolution.get("resolved_panel_model_ready_on_source_consistency") is not True:
        errors.append("Milestone 8 resolved outcome panel is not source-ready")
    if resolution.get("resolution_sha256") != sha256(RESOLUTION_CSV):
        errors.append("Milestone 8 anomaly-resolution CSV SHA drift")
    if resolution.get("resolved_panel_sha256") != sha256(RESOLVED_PANEL):
        errors.append("Milestone 8 resolved panel SHA drift")
    if len(resolution_rows) != 5:
        errors.append("Milestone 8 anomaly-resolution CSV must contain exactly five decisions")

    if overlap.get("schema") != "ranah-observatory/milestone8-grdp-overlap/v1" or overlap.get("overlap_2009_reconciled") is not True:
        errors.append("Milestone 8 overlap manifest drift")
    if overlap.get("failure_count") != 0 or float(overlap.get("max_absolute_relative_difference_percent", 999)) > 0.5:
        errors.append("Milestone 8 overlap manifest fails the locked 0.5% gate")

    if exposure_manifest.get("primary_candidate") != "area_mean_pga_pct_g":
        errors.append("Milestone 8 primary exposure drift")
    if exposure_manifest.get("geography_count") != 19 or exposure_manifest.get("all_19_geographies_have_grid_support") is not True:
        errors.append("Milestone 8 exposure footprint drift")
    if exposure_manifest.get("historical_boundary_continuity_claimed") is not False:
        errors.append("Milestone 8 exposure must retain fixed-current-boundary caveat")
    if exposure_manifest.get("output_sha256") != sha256(EXPOSURE_CSV):
        errors.append("Milestone 8 exposure CSV SHA drift")
    if len(exposure_rows) != 19 or {row.get("geography_id", "") for row in exposure_rows} != EXPECTED_GEOGRAPHIES:
        errors.append("Milestone 8 exposure CSV must contain exact 19 geographies")

    panel_keys = {(row.get("geography_id", ""), int(row.get("year", 0))) for row in panel_rows}
    if len(panel_rows) != 171 or len(panel_keys) != 171:
        errors.append("Milestone 8 resolved panel must contain exact 171 unique geography-year observations")
    if {row.get("geography_id", "") for row in panel_rows} != EXPECTED_GEOGRAPHIES:
        errors.append("Milestone 8 resolved-panel geography footprint drift")
    for gid in EXPECTED_GEOGRAPHIES:
        years = {year for geography_id, year in panel_keys if geography_id == gid}
        if years != set(range(2005, 2014)):
            errors.append(f"Milestone 8 resolved-panel year footprint drift for {gid}")
    if any(row.get("source_internal_consistency_status") == "postperiod_level_growth_internal_mismatch_unresolved" for row in panel_rows):
        errors.append("Milestone 8 resolved panel still contains unresolved source-consistency rows")
    for row in panel_rows:
        try:
            value = float(row.get("real_grdp_constant_2000_million_rupiah", "nan"))
            logged = float(row.get("log_real_grdp", "nan"))
        except ValueError:
            errors.append(f"Milestone 8 resolved panel contains nonnumeric value for {row.get('geography_id')} {row.get('year')}")
            continue
        if not math.isfinite(value) or value <= 0 or not math.isfinite(logged) or abs(logged - math.log(value)) > 1e-10:
            errors.append(f"Milestone 8 resolved panel numeric/log consistency failure for {row.get('geography_id')} {row.get('year')}")

    source_ids = [row.get("source_plan_id", "") for row in source_rows]
    if len(source_ids) != len(set(source_ids)) or set(source_ids) != EXPECTED_SOURCE_IDS:
        errors.append("Milestone 8 source-plan ID set/cardinality drift")
    source_by_id = {row.get("source_plan_id", ""): row for row in source_rows}
    if source_by_id.get("m8_usgs_shakemap", {}).get("role") != "primary_treatment_exposure":
        errors.append("USGS ShakeMap must remain primary treatment exposure")
    if source_by_id.get("m8_damage_dlna", {}).get("role") != "secondary_damage_validation":
        errors.append("DLNA must remain secondary damage validation")
    if source_by_id.get("m8_grdp_pre", {}).get("role") != "outcome_preperiod_primary":
        errors.append("BPS Sumbar Table 22 must remain primary pre-period outcome source")

    geography_ids = [row.get("geography_id", "") for row in geography_rows]
    if len(geography_rows) != 19 or len(set(geography_ids)) != 19 or set(geography_ids) != EXPECTED_GEOGRAPHIES:
        errors.append("Milestone 8 geography-contract footprint drift")
    geography_by_id = {row.get("geography_id", ""): row for row in geography_rows}
    for gid, legal_token in LEGAL_ANCHORS_REQUIRED.items():
        if legal_token not in geography_by_id.get(gid, {}).get("legal_anchor", ""):
            errors.append(f"Milestone 8 legal anchor missing or drifted for {gid}")

    for phrase in REQUIRED_SPEC_PHRASES:
        if phrase not in spec_text:
            errors.append(f"Milestone 8 specification lost required phrase: {phrase}")
    for phrase in REQUIRED_INFERENCE_PHRASES:
        if phrase not in inference_text:
            errors.append(f"Milestone 8 inference protocol lost required phrase: {phrase}")

    if gate.get("quasi_causal_effect_estimated") is not False:
        errors.append("Milestone 8 pre-fit gate must not claim a quasi-causal estimate")
    if gate.get("causal_claim_authorized") is not False:
        errors.append("Milestone 8 pre-fit gate must not authorize causal wording")
    if gate.get("milestone8_complete") is not False:
        errors.append("Milestone 8 cannot be complete before diagnostics")
    blocking_reasons = gate.get("blocking_reasons")
    if not isinstance(blocking_reasons, list) or not blocking_reasons:
        errors.append("Milestone 8 incomplete state must retain explicit blocking reasons")

    return {
        "schema": "ranah-observatory/milestone8-design-audit/v4",
        "criterion": LOCKED_DESIGN["criterion"],
        "case_study": LOCKED_DESIGN["case_study"],
        "event_date": LOCKED_DESIGN["event_date"],
        "geography_count": len(geography_rows),
        "source_plan_count": len(source_rows),
        "design_preregistered": gate.get("design_preregistered") is True,
        "geography_2005_2013_qualified": gate.get("geography_2005_2013_qualified") is True,
        "postperiod_source_anomalies_resolved": gate.get("postperiod_source_anomalies_resolved") is True,
        "model_fit_authorized": gate.get("model_fit_authorized") is True,
        "outcome_model_fit": gate.get("outcome_model_fit") is True,
        "quasi_causal_effect_estimated": gate.get("quasi_causal_effect_estimated") is True,
        "causal_claim_authorized": gate.get("causal_claim_authorized") is True,
        "milestone8_complete": gate.get("milestone8_complete") is True,
        "blocking_reason_count": len(blocking_reasons) if isinstance(blocking_reasons, list) else 0,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Milestone 8 pre-fit design and source gates")
    parser.add_argument("--require-preregistered", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_preregistered:
        required_true = [
            "design_preregistered",
            "geography_2005_2013_qualified",
            "postperiod_source_anomalies_resolved",
            "model_fit_authorized",
        ]
        if any(report.get(key) is not True for key in required_true):
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
