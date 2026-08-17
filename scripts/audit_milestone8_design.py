#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE8_QUASI_CAUSAL_SPEC.md"
SOURCE_PLAN = ROOT / "data/registries/milestone8_earthquake_source_plan.csv"
GEOGRAPHY_CONTRACT = ROOT / "data/registries/milestone8_geography_contract.csv"
DESIGN_GATE = ROOT / "data/manifests/milestone8_design_gate.json"

EXPECTED_GEOGRAPHIES = {
    "idn.13.1301",
    "idn.13.1302",
    "idn.13.1303",
    "idn.13.1304",
    "idn.13.1305",
    "idn.13.1306",
    "idn.13.1307",
    "idn.13.1308",
    "idn.13.1309",
    "idn.13.1310",
    "idn.13.1311",
    "idn.13.1312",
    "idn.13.1371",
    "idn.13.1372",
    "idn.13.1373",
    "idn.13.1374",
    "idn.13.1375",
    "idn.13.1376",
    "idn.13.1377",
}

EXPECTED_SOURCE_IDS = {
    "m8_event_bnpb",
    "m8_damage_dlna",
    "m8_damage_dlna_mirror",
    "m8_grdp_pre",
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
    "primary_exposure": "heavy_housing_damage_share",
    "secondary_exposure": "any_housing_damage_share",
    "primary_design": "continuous_intensity_two_way_fixed_effects_event_study",
    "baseline_year": 2008,
    "partial_treatment_year": 2009,
}

REQUIRED_SPEC_PHRASES = [
    "30 September 2009",
    "continuous-intensity two-way fixed-effects event study",
    "2008 (`k=-1`) is the omitted baseline",
    "partial-treatment year",
    "wild cluster bootstrap",
    "quasi-causal estimate",
    "association",
    "No causal or quasi-causal effect has yet been estimated.",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [SPEC, SOURCE_PLAN, GEOGRAPHY_CONTRACT, DESIGN_GATE]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return {
            "schema": "ranah-observatory/milestone8-design-audit/v1",
            "criterion": "one focused causal or quasi-causal case study",
            "errors": [f"missing required file: {path}" for path in missing],
            "design_preregistered": False,
            "milestone8_complete": False,
        }

    gate = json.loads(DESIGN_GATE.read_text(encoding="utf-8"))
    spec_text = SPEC.read_text(encoding="utf-8")
    source_rows = read_csv(SOURCE_PLAN)
    geography_rows = read_csv(GEOGRAPHY_CONTRACT)

    if gate.get("schema") != "ranah-observatory/milestone8-design-gate/v1":
        errors.append("Milestone 8 design-gate schema drift")

    for key, expected in LOCKED_DESIGN.items():
        if gate.get(key) != expected:
            errors.append(f"Milestone 8 locked design drift: {key}")

    if gate.get("design_preregistered") is not True:
        errors.append("Milestone 8 design must remain preregistered")
    if gate.get("geography_2005_2013_qualified") is not True:
        errors.append("Milestone 8 geography gate is not qualified")
    if gate.get("geography_qualification_scope") != "M8 analytical footprint only; no general historical backcast":
        errors.append("Milestone 8 geography qualification scope drift")

    # This audit intentionally protects the current pre-estimation state. Once the
    # data and identification gates are closed, update this contract in the same PR
    # as the model implementation rather than silently upgrading claim strength.
    if gate.get("quasi_causal_effect_estimated") is not False:
        errors.append("Milestone 8 foundation must not yet claim an estimated quasi-causal effect")
    if gate.get("causal_claim_authorized") is not False:
        errors.append("Milestone 8 foundation must not yet authorize causal language")
    if gate.get("milestone8_complete") is not False:
        errors.append("Milestone 8 cannot be complete at the preregistration-only stage")

    unresolved_data_gates = [
        "preperiod_outcome_frozen",
        "postperiod_outcome_frozen",
        "overlap_2009_reconciled",
        "full_exposure_19_geographies_frozen",
        "pretrend_diagnostics_passed",
        "placebo_checks_passed",
        "influence_sensitivity_passed",
        "small_cluster_inference_implemented",
    ]
    if all(gate.get(key) is True for key in unresolved_data_gates):
        errors.append("Milestone 8 foundation audit expected unresolved downstream gates")
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
        anchor = geography_by_id.get(gid, {}).get("legal_anchor", "")
        if legal_token not in anchor:
            errors.append(f"Milestone 8 legal anchor missing or drifted for {gid}")

    return {
        "schema": "ranah-observatory/milestone8-design-audit/v1",
        "criterion": LOCKED_DESIGN["criterion"],
        "case_study": LOCKED_DESIGN["case_study"],
        "event_date": LOCKED_DESIGN["event_date"],
        "geography_count": len(geography_rows),
        "source_plan_count": len(source_rows),
        "design_preregistered": gate.get("design_preregistered") is True,
        "geography_2005_2013_qualified": gate.get("geography_2005_2013_qualified") is True,
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
        help="fail unless the preregistered design and geography contract pass while causal claims remain locked",
    )
    args = parser.parse_args()

    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))

    if report["errors"]:
        return 1
    if args.require_preregistered:
        if report.get("design_preregistered") is not True:
            return 1
        if report.get("geography_2005_2013_qualified") is not True:
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
