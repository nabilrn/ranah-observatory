#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/research_foundation_complete.json"

EXPECTED = {
    1: "canonical geography registry",
    2: "source catalog",
    3: "indicator framework",
    4: "40-60 high-value indicators with provenance",
    5: "a comparative Indonesian panel where feasible",
    6: "exploratory historical analysis",
    7: "one baseline expected-performance/frontier model",
    8: "one focused causal or quasi-causal case study",
    9: "one climate/disaster case study relevant to West Sumatra",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit() -> dict[str, Any]:
    errors: list[str] = []
    if not MANIFEST.exists():
        return {"schema": "ranah-observatory/research-foundation-audit/v1", "initial_research_foundation_complete": False, "errors": ["closure manifest missing"]}
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != "ranah-observatory/research-foundation-complete/v1":
        errors.append("research foundation closure schema drift")
    if payload.get("scope") != "initial research foundation defined by research/RESEARCH_CHARTER.md":
        errors.append("research foundation scope drift")
    if payload.get("criterion_count") != 9 or payload.get("completed_criterion_count") != 9:
        errors.append("research foundation must report exact 9/9 completion")
    if payload.get("initial_research_foundation_complete") is not True:
        errors.append("initial research foundation completion flag is false")
    if payload.get("final_ranah_observatory_product_complete") is not False:
        errors.append("foundation closure must not claim final Ranah Observatory product completion")
    if payload.get("dashboard_required_for_foundation") is not False:
        errors.append("foundation closure incorrectly requires a dashboard")
    if payload.get("definitive_monetary_wasted_potential_required_for_foundation") is not False:
        errors.append("foundation closure incorrectly requires a definitive monetary wasted-potential estimate")
    if payload.get("errors") != []:
        errors.append("research foundation closure contains errors")

    criteria = payload.get("criteria")
    if not isinstance(criteria, list) or len(criteria) != 9:
        errors.append("research foundation criteria array must contain exactly nine rows")
        criteria = []
    seen: set[int] = set()
    for row in criteria:
        number = row.get("criterion_number")
        if not isinstance(number, int) or number not in EXPECTED:
            errors.append(f"invalid foundation criterion number: {number!r}")
            continue
        if number in seen:
            errors.append(f"duplicate foundation criterion number: {number}")
        seen.add(number)
        if row.get("criterion") != EXPECTED[number]:
            errors.append(f"criterion {number} label drift")
        if row.get("complete") is not True:
            errors.append(f"criterion {number} is incomplete")
        if row.get("errors") != []:
            errors.append(f"criterion {number} retains errors")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"criterion {number} lacks evidence references")
            continue
        for record in evidence:
            path = ROOT / str(record.get("path", ""))
            if not path.exists():
                errors.append(f"criterion {number} evidence missing: {record.get('path')}")
            elif sha256(path) != record.get("sha256"):
                errors.append(f"criterion {number} evidence SHA-256 drift: {record.get('path')}")
    if seen != set(EXPECTED):
        errors.append("foundation criterion-number set drift")

    by_number = {row.get("criterion_number"): row for row in criteria if isinstance(row.get("criterion_number"), int)}
    if by_number.get(1, {}).get("details", {}).get("current_sumbar_child_count") != 19:
        errors.append("criterion 1 lost exact 19 current West Sumatra child geographies")
    if by_number.get(2, {}).get("details", {}).get("required_source_families_present") is not True:
        errors.append("criterion 2 required source families are not all present")
    if by_number.get(3, {}).get("details", {}).get("domain_count") != 12:
        errors.append("criterion 3 must cover the 12-domain indicator ontology")
    indicator_definitions = by_number.get(3, {}).get("details", {}).get("indicator_definition_count", 0)
    if not isinstance(indicator_definitions, int) or indicator_definitions < 40:
        errors.append("criterion 3 indicator framework is unexpectedly small")
    qualified = by_number.get(4, {}).get("details", {}).get("qualified_indicator_count", 0)
    if not isinstance(qualified, int) or not 40 <= qualified <= 60:
        errors.append("criterion 4 qualified indicator count outside charter range")
    if by_number.get(9, {}).get("details", {}).get("geography_count") != 19:
        errors.append("criterion 9 climate/disaster case study lost 19-geography footprint")

    return {
        "schema": "ranah-observatory/research-foundation-audit/v1",
        "criterion_count": len(criteria),
        "completed_criterion_count": sum(row.get("complete") is True for row in criteria),
        "initial_research_foundation_complete": payload.get("initial_research_foundation_complete") is True and not errors,
        "final_ranah_observatory_product_complete": payload.get("final_ranah_observatory_product_complete") is True,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Ranah Observatory initial research foundation closure")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_complete and report.get("initial_research_foundation_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
