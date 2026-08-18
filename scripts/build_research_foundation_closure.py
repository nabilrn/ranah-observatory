#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.audit_milestone9_hydroclimate_case_study import audit as audit_m9

ROOT = Path(__file__).resolve().parents[1]
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
CATALOG = ROOT / "catalog/data-catalog.csv"
INDICATORS = ROOT / "data/registries/indicators.csv"
M4 = ROOT / "data/manifests/milestone4_indicator_inventory.json"
M5 = ROOT / "data/manifests/milestone5_comparative_panel_audit.json"
M6 = ROOT / "data/manifests/milestone6_historical_eda_audit.json"
M7 = ROOT / "data/manifests/milestone7_expected_performance_audit.json"
M8 = ROOT / "data/manifests/milestone8_complete_audit.json"
M9 = ROOT / "data/manifests/milestone9_hydroclimate_case_study.json"
OUT = ROOT / "data/manifests/research_foundation_complete.json"

EXPECTED_CRITERIA = [
    (1, "canonical geography registry"),
    (2, "source catalog"),
    (3, "indicator framework"),
    (4, "40-60 high-value indicators with provenance"),
    (5, "a comparative Indonesian panel where feasible"),
    (6, "exploratory historical analysis"),
    (7, "one baseline expected-performance/frontier model"),
    (8, "one focused causal or quasi-causal case study"),
    (9, "one climate/disaster case study relevant to West Sumatra"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def evidence(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}


def main() -> int:
    errors: list[str] = []
    criterion_rows: list[dict[str, Any]] = []

    # Criterion 1 — canonical geography registry.
    geo = rows(GEOGRAPHIES)
    geo_ids = [row.get("geography_id", "") for row in geo]
    current_sumbar_children = [
        row for row in geo
        if row.get("parent_geography_id") == "idn.13"
        and row.get("status") == "current"
        and row.get("geography_id", "").startswith("idn.13.")
    ]
    c1_errors: list[str] = []
    if not geo or len(geo_ids) != len(set(geo_ids)) or any(not gid for gid in geo_ids):
        c1_errors.append("canonical geography IDs are empty or duplicated")
    if "idn" not in set(geo_ids) or "idn.13" not in set(geo_ids):
        c1_errors.append("Indonesia/West Sumatra canonical anchors are missing")
    if len(current_sumbar_children) != 19:
        c1_errors.append(f"expected 19 current West Sumatra children, got {len(current_sumbar_children)}")
    criterion_rows.append({
        "criterion_number": 1,
        "criterion": EXPECTED_CRITERIA[0][1],
        "complete": not c1_errors,
        "evidence": [evidence(GEOGRAPHIES)],
        "details": {"registry_row_count": len(geo), "current_sumbar_child_count": len(current_sumbar_children)},
        "errors": c1_errors,
    })
    errors.extend(f"criterion 1: {item}" for item in c1_errors)

    # Criterion 2 — source catalog.
    catalog = rows(CATALOG)
    source_ids = [row.get("source_id", "") for row in catalog]
    required_sources = {"bps_webapi", "bnpb_satu_data", "chirps_v3", "big_admin_boundaries_june_2026"}
    c2_errors: list[str] = []
    if not catalog or len(source_ids) != len(set(source_ids)) or any(not sid for sid in source_ids):
        c2_errors.append("source catalog IDs are empty or duplicated")
    missing_sources = sorted(required_sources - set(source_ids))
    if missing_sources:
        c2_errors.append(f"required qualified source families missing: {missing_sources}")
    for row in catalog:
        if not row.get("organization") or not row.get("dataset_family") or not row.get("access_mode") or not row.get("status"):
            c2_errors.append(f"incomplete source-catalog metadata: {row.get('source_id')}")
            break
    criterion_rows.append({
        "criterion_number": 2,
        "criterion": EXPECTED_CRITERIA[1][1],
        "complete": not c2_errors,
        "evidence": [evidence(CATALOG)],
        "details": {"source_count": len(catalog), "required_source_families_present": not missing_sources},
        "errors": c2_errors,
    })
    errors.extend(f"criterion 2: {item}" for item in c2_errors)

    # Criterion 3 — indicator framework.
    indicators = rows(INDICATORS)
    indicator_ids = [row.get("indicator_id", "") for row in indicators]
    c3_errors: list[str] = []
    if len(indicators) < 40:
        c3_errors.append(f"indicator framework unexpectedly small: {len(indicators)} definitions")
    if len(indicator_ids) != len(set(indicator_ids)) or any(not iid for iid in indicator_ids):
        c3_errors.append("indicator framework IDs are empty or duplicated")
    required_columns = {"name", "domain", "definition", "unit", "frequency", "allowed_claim_types", "comparability_notes"}
    for row in indicators:
        if any(not row.get(column) for column in required_columns):
            c3_errors.append(f"incomplete indicator semantics: {row.get('indicator_id')}")
            break
    criterion_rows.append({
        "criterion_number": 3,
        "criterion": EXPECTED_CRITERIA[2][1],
        "complete": not c3_errors,
        "evidence": [evidence(INDICATORS)],
        "details": {"indicator_definition_count": len(indicators), "domain_count": len({row.get('domain') for row in indicators if row.get('domain')})},
        "errors": c3_errors,
    })
    errors.extend(f"criterion 3: {item}" for item in c3_errors)

    # Criterion 4 — qualified high-value indicator inventory.
    m4 = json.loads(M4.read_text(encoding="utf-8"))
    qualified_count = int(m4.get("qualified_indicator_count", 0))
    c4_errors: list[str] = []
    if m4.get("milestone4_complete") is not True:
        c4_errors.append("Milestone 4 completion flag is false")
    if not 40 <= qualified_count <= 60:
        c4_errors.append(f"qualified indicator count outside charter range: {qualified_count}")
    if m4.get("duplicate_observation_ids", []) or m4.get("missing_observation_ids", []) or m4.get("unresolved_provenance", []):
        c4_errors.append("Milestone 4 integrity/provenance errors remain")
    criterion_rows.append({"criterion_number": 4, "criterion": EXPECTED_CRITERIA[3][1], "complete": not c4_errors, "evidence": [evidence(M4)], "details": {"qualified_indicator_count": qualified_count}, "errors": c4_errors})
    errors.extend(f"criterion 4: {item}" for item in c4_errors)

    def manifest_criterion(number: int, expected_label: str, path: Path, complete_key: str) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        local_errors: list[str] = []
        if payload.get("criterion") != expected_label:
            local_errors.append(f"criterion label drift: {payload.get('criterion')!r}")
        if payload.get(complete_key) is not True:
            local_errors.append(f"{complete_key} is false")
        if payload.get("errors", []) not in ([], None):
            local_errors.append("authoritative audit contains errors")
        criterion_rows.append({
            "criterion_number": number,
            "criterion": expected_label,
            "complete": not local_errors,
            "evidence": [evidence(path)],
            "details": {"schema": payload.get("schema")},
            "errors": local_errors,
        })
        errors.extend(f"criterion {number}: {item}" for item in local_errors)

    manifest_criterion(5, EXPECTED_CRITERIA[4][1], M5, "milestone5_complete")
    manifest_criterion(6, EXPECTED_CRITERIA[5][1], M6, "milestone6_complete")
    manifest_criterion(7, EXPECTED_CRITERIA[6][1], M7, "milestone7_complete")
    manifest_criterion(8, EXPECTED_CRITERIA[7][1], M8, "milestone8_complete")

    # Criterion 9 uses the live audit function because its final manifest is produced in this PR.
    m9_report = audit_m9()
    c9_errors = list(m9_report.get("errors", []))
    if m9_report.get("criterion") != EXPECTED_CRITERIA[8][1]:
        c9_errors.append("Milestone 9 criterion label drift")
    if m9_report.get("milestone9_complete") is not True:
        c9_errors.append("Milestone 9 audit is not complete")
    criterion_rows.append({
        "criterion_number": 9,
        "criterion": EXPECTED_CRITERIA[8][1],
        "complete": not c9_errors,
        "evidence": [evidence(M9)],
        "details": {"case_study": m9_report.get("case_study"), "geography_count": m9_report.get("geography_count")},
        "errors": c9_errors,
    })
    errors.extend(f"criterion 9: {item}" for item in c9_errors)

    completed = sum(row["complete"] is True for row in criterion_rows)
    manifest = {
        "schema": "ranah-observatory/research-foundation-complete/v1",
        "scope": "initial research foundation defined by research/RESEARCH_CHARTER.md",
        "criterion_count": 9,
        "completed_criterion_count": completed,
        "criteria": criterion_rows,
        "initial_research_foundation_complete": completed == 9 and not errors,
        "final_ranah_observatory_product_complete": False,
        "dashboard_required_for_foundation": False,
        "definitive_monetary_wasted_potential_required_for_foundation": False,
        "errors": errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["initial_research_foundation_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
