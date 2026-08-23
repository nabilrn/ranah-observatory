#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "data/manifests/milestone28_stage1b_structure_probe.json"
DECISIONS = ROOT / "data/registries/milestone28_stage1b_selector_decisions.csv"
VAR169_MAP = ROOT / "data/registries/milestone28_var169_local_geography_map.csv"
VAR169_AMENDMENT = ROOT / "data/manifests/milestone28_var169_geography_representation_amendment.json"
OUT_CSV = ROOT / "data/analysis/engine/broader_panel_v1/m28-stage1b-qualification.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone28_stage1b_qualification.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    if probe.get("schema") != "ranah-observatory/milestone28-stage1b-structure-probe/v1":
        raise ValueError("Stage 1B probe schema drift")
    decisions = read_csv(DECISIONS)
    retained = [r for r in decisions if r["decision"] == "retain_structure_pilot"]
    held = [r for r in decisions if r["decision"].startswith("held_")]
    if len(retained) != 7 or len(held) != 1:
        raise ValueError("Stage 1B decision footprint drift")

    amendment = json.loads(VAR169_AMENDMENT.read_text(encoding="utf-8"))
    if amendment.get("source_local_ids_are_not_global_bps_codes") is not True or amendment.get("cross_year_stability_assumed") is not False:
        raise ValueError("var169 amendment boundary drift")
    mapping = read_csv(VAR169_MAP)
    if len(mapping) != 19 or len({r["source_vervar_id"] for r in mapping}) != 19 or len({r["geography_id"] for r in mapping}) != 19:
        raise ValueError("var169 mapping must be 19x unique")

    redacted_by_var: dict[int, dict[str, Any]] = {}
    for item in probe["redacted_structure_files"]:
        path = ROOT / item["path"]
        if sha256(path) != item["sha256"]:
            raise ValueError(f"redacted checksum drift: {path}")
        redacted_by_var[int(item["bps_var_id"])] = json.loads(path.read_text(encoding="utf-8"))

    var169 = redacted_by_var[169]
    source_local = {str(r.get("val", "")).strip(): str(r.get("label", "")).strip() for r in var169.get("vervar", []) if str(r.get("val", "")).strip() in {str(i) for i in range(1, 20)}}
    expected_local = {r["source_vervar_id"]: r["source_label"] for r in mapping}
    var169_mapping_exact = source_local == expected_local
    aggregate_rows_exact = {str(r.get("val", "")).strip(): str(r.get("label", "")).strip() for r in var169.get("vervar", []) if str(r.get("val", "")).strip() in {"20", "21"}} == {"20": "Jumlah", "21": "Provinsi Sumatera Barat"}
    if not var169_mapping_exact or not aggregate_rows_exact:
        raise ValueError("var169 frozen 2024 local geography representation no longer matches amendment")

    rows: list[dict[str, Any]] = []
    for decision in decisions:
        var_id = int(decision["bps_var_id"])
        if decision["decision"].startswith("held_"):
            classification = decision["decision"]
            structure_qualified = False
            qualification_basis = "pre_registered_selector_hold"
        else:
            redacted = redacted_by_var[var_id]
            if var_id == 169:
                structure_qualified = bool(var169_mapping_exact and aggregate_rows_exact and redacted.get("selector_present") and redacted.get("period_present") and redacted.get("unexpected_datacontent_keys") == [])
                classification = "qualified_structure_after_typed_geography_amendment" if structure_qualified else "held_structure_after_amendment"
                qualification_basis = "frozen_2024_local_ordinal_plus_label_map"
            else:
                structure_qualified = redacted.get("classification") == "structure_pilot_pass"
                classification = "qualified_structure" if structure_qualified else "held_structure_pilot_failed"
                qualification_basis = "frozen_2024_canonical_bps_code_structure"
        rows.append({
            "candidate_id": decision["candidate_id"],
            "bps_var_id": var_id,
            "classification": classification,
            "structure_qualified": structure_qualified,
            "period_coverage": decision["period_coverage"],
            "provisional_claim_type": decision["provisional_claim_type"],
            "qualification_basis": qualification_basis,
            "hold_reason": decision["hold_reason"],
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    qualified = [r for r in rows if r["structure_qualified"]]
    held_rows = [r for r in rows if not r["structure_qualified"]]
    manifest = {
        "schema": "ranah-observatory/milestone28-stage1b-qualification/v1",
        "milestone": 28,
        "offline_only": True,
        "network_requests_performed": False,
        "original_probe_failure_preserved": True,
        "var169_typed_geography_amendment_applied": True,
        "var169_2024_mapping_exact": var169_mapping_exact,
        "var169_cross_year_stability_assumed": False,
        "candidate_count": len(rows),
        "structure_qualified_count": len(qualified),
        "held_count": len(held_rows),
        "qualified_var_ids": [r["bps_var_id"] for r in qualified],
        "held_var_ids": [r["bps_var_id"] for r in held_rows],
        "numeric_materialization_authorized": False,
        "target_values_inspected": False,
        "global_window_shortening_performed": False,
        "imputation_performed": False,
        "missing_values_coerced_to_zero": False,
        "derived_indicator_materialized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "qualification_csv": {"path": str(OUT_CSV.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(OUT_CSV)},
        "next_gate": "freeze candidate-specific Stage 2 numeric acquisition contracts; var169 must revalidate the exact local ordinal+label mapping in every acquired year",
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"qualified": len(qualified), "held": len(held_rows), "qualified_var_ids": manifest["qualified_var_ids"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
