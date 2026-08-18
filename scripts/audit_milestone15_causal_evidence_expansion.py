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
SPEC = ROOT / "research/MILESTONE15_CAUSAL_EVIDENCE_EXPANSION_SPEC.md"
MANIFEST = ROOT / "data/manifests/milestone15_causal_evidence_expansion.json"
LIBRARY = ROOT / "data/analysis/engine/causal_evidence_v1/m15-causal-evidence-library.csv"

EXPECTED_IDS = {"m15_e1_earthquake_2009", "m15_e2_rainfall_unemployment", "m15_e3_covid_structural_exposure"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    for path in (SPEC, MANIFEST, LIBRARY):
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        return {"schema": "ranah-observatory/milestone15-audit/v1", "errors": errors, "milestone15_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    library = rows(LIBRARY)
    for phrase in (
        "Failed identification attempts are first-class research outputs",
        "forbids fitting a new causal rainfall-unemployment model in v1",
        "at least **three complete pre-event annual outcome years**",
        "not_identification_ready",
    ):
        if phrase not in spec:
            errors.append(f"M15 spec lost guardrail: {phrase}")

    if manifest.get("schema") != "ranah-observatory/milestone15-causal-evidence-expansion/v1":
        errors.append("manifest schema drift")
    if manifest.get("milestone15_complete") is not True:
        errors.append("M15 completion flag false")
    if manifest.get("entry_count") != 3 or manifest.get("completed_quasi_causal_study_count") != 1 or manifest.get("not_identification_ready_count") != 2:
        errors.append("M15 library summary counts drift")
    if manifest.get("new_causal_model_fit_count") != 0:
        errors.append("M15 unexpectedly fit a new causal model")
    if manifest.get("same_data_m14_signal_upgraded_to_causal_model") is not False or manifest.get("causal_claim_created_from_m14_association") is not False:
        errors.append("M14 association improperly upgraded to causal evidence")
    if manifest.get("covid_complete_pre_event_years") != [2018, 2019] or manifest.get("minimum_covid_pre_event_years_required") != 3:
        errors.append("COVID readiness gate drift")
    if manifest.get("genuinely_new_post_m14_unemployment_years") != [2025]:
        errors.append("rainfall independent-confirmation footprint drift")
    if manifest.get("monetary_wasted_potential_estimated") is not False:
        errors.append("M15 monetary wasted-potential claim enabled")

    for key, rec in manifest.get("inputs", {}).items():
        path = ROOT / str(rec.get("path", ""))
        if not path.exists() or sha256(path) != rec.get("sha256"):
            errors.append(f"input checksum drift: {key}")
    output = manifest.get("output", {})
    path = ROOT / str(output.get("path", ""))
    if not path.exists() or sha256(path) != output.get("sha256"):
        errors.append("library output checksum drift")

    if len(library) != 3 or {row["entry_id"] for row in library} != EXPECTED_IDS:
        errors.append("library entry set drift")
    by_id = {row["entry_id"]: row for row in library}
    if by_id.get("m15_e1_earthquake_2009", {}).get("entry_state") != "completed_quasi_causal_study":
        errors.append("M8 library entry state drift")
    for entry_id in ("m15_e2_rainfall_unemployment", "m15_e3_covid_structural_exposure"):
        row = by_id.get(entry_id, {})
        if row.get("entry_state") != "not_identification_ready":
            errors.append(f"blocked candidate state drift: {entry_id}")
        if row.get("model_fit_authorized", "").lower() != "false" or row.get("new_model_fit_in_m15", "").lower() != "false":
            errors.append(f"blocked candidate improperly authorized: {entry_id}")
    if any(row.get("causal_claim_authorized", "").lower() != "false" for row in library):
        errors.append("M15 library emits causal claim authorization")
    if any(row.get("monetary_wasted_potential_claim", "").lower() != "false" for row in library):
        errors.append("M15 library emits monetary wasted-potential claim")

    return {
        "schema": "ranah-observatory/milestone15-audit/v1",
        "entry_count": len(library),
        "completed_quasi_causal_study_count": sum(row["entry_state"] == "completed_quasi_causal_study" for row in library),
        "not_identification_ready_count": sum(row["entry_state"] == "not_identification_ready" for row in library),
        "new_causal_model_fit_count": sum(row["new_model_fit_in_m15"].lower() == "true" for row in library),
        "milestone15_complete": manifest.get("milestone15_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_complete and not report["milestone15_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
