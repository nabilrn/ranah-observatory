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
SPEC = ROOT / "research/MILESTONE16_SPATIAL_CLIMATE_RISK_SPEC.md"
MANIFEST = ROOT / "data/manifests/milestone16_spatial_climate_risk.json"
FRAME = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-spatial-component-frame.csv"
REGISTRY = ROOT / "data/analysis/engine/spatial_climate_risk_v1/m16-evidence-component-registry.csv"

EXPECTED_REGISTRY_IDS = {
    "m16_h1_earthquake_shaking_2009",
    "m16_c1_chirps_rainfall_2024",
    "m16_o1_bnpb_flood_events_2024",
    "m16_o2_bnpb_landslide_events_2024",
    "m16_h2_inarisk_flood_hazard",
    "m16_h3_inarisk_landslide_hazard",
    "m16_v1_inarisk_flood_vulnerability",
    "m16_v2_inarisk_landslide_vulnerability",
    "m16_e1_exposure_gap",
    "m16_c2_capacity_gap",
    "m16_i1_observed_impact_gap",
    "m16_r1_modeled_risk_blocked",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def audit() -> dict[str, Any]:
    errors: list[str] = []
    for path in (SPEC, MANIFEST, FRAME, REGISTRY):
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        return {"schema": "ranah-observatory/milestone16-audit/v1", "errors": errors, "milestone16_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    frame = rows(FRAME)
    registry = rows(REGISTRY)

    required_spec_phrases = (
        "risk_synthesis_authorized=false",
        "not population exposure",
        "not event-day rainfall",
        "endpoint_verified_version_binding_unresolved",
        "no cross-event or cross-year risk aggregation",
        "no composite risk score/ranking exists",
    )
    for phrase in required_spec_phrases:
        if phrase not in spec:
            errors.append(f"M16 spec lost guardrail: {phrase}")

    if manifest.get("schema") != "ranah-observatory/milestone16-spatial-climate-risk/v1":
        errors.append("manifest schema drift")
    if manifest.get("milestone16_complete") is not True:
        errors.append("M16 completion flag false")
    if manifest.get("geography_count") != 19:
        errors.append("M16 geography count drift")
    if manifest.get("component_registry_count") != 12:
        errors.append("M16 registry count drift")
    if manifest.get("substantive_component_count") != 4 or manifest.get("blocked_or_gap_component_count") != 8:
        errors.append("M16 substantive/blocked component counts drift")
    if manifest.get("substantive_component_classes") != ["climate_context", "hazard_intensity", "recorded_event_occurrence"]:
        errors.append("M16 substantive component classes drift")
    if manifest.get("required_missing_component_classes") != ["exposure", "vulnerability", "capacity", "observed_impact"]:
        errors.append("M16 required missing component classes drift")
    if manifest.get("inarisk_endpoint_count") != 4 or manifest.get("inarisk_endpoint_state") != "endpoint_verified_version_binding_unresolved":
        errors.append("M16 InaRISK readiness state drift")

    false_guards = (
        "historical_boundary_continuity_claimed",
        "inarisk_pixels_ingested",
        "risk_synthesis_authorized",
        "composite_risk_score_created",
        "geography_risk_ranking_created",
        "cross_event_temporal_aggregation_performed",
        "causal_attribution_performed",
        "climate_change_attribution_performed",
        "monetary_wasted_potential_estimated",
    )
    for key in false_guards:
        if manifest.get(key) is not False:
            errors.append(f"M16 false guard enabled: {key}")

    for key, rec in manifest.get("inputs", {}).items():
        path = ROOT / str(rec.get("path", ""))
        if not path.exists() or sha256(path) != rec.get("sha256"):
            errors.append(f"M16 input checksum drift: {key}")
    for key, rec in manifest.get("outputs", {}).items():
        path = ROOT / str(rec.get("path", ""))
        if not path.exists() or sha256(path) != rec.get("sha256"):
            errors.append(f"M16 output checksum drift: {key}")

    if len(frame) != 19 or len({row.get("geography_id") for row in frame}) != 19:
        errors.append("M16 frame is not exact 19 unique geographies")
    forbidden_columns = {column for column in (frame[0].keys() if frame else []) if "risk_score" in column or "risk_rank" in column}
    if forbidden_columns:
        errors.append(f"M16 frame contains forbidden composite/ranking columns: {sorted(forbidden_columns)}")
    for row in frame:
        if row.get("spatial_frame") != "BIG_June_2026_fixed_current_boundary":
            errors.append("M16 frame spatial regime drift")
            break
        for column in (
            "qualified_exposure_component_present",
            "qualified_vulnerability_component_present",
            "qualified_capacity_component_present",
            "qualified_observed_impact_component_present",
            "cross_event_temporal_aggregation_authorized",
            "risk_synthesis_authorized",
        ):
            if row.get(column, "").lower() != "false":
                errors.append(f"M16 frame improperly authorizes {column}")
                break

    if len(registry) != 12 or {row.get("evidence_id") for row in registry} != EXPECTED_REGISTRY_IDS:
        errors.append("M16 registry evidence set drift")
    by_id = {row["evidence_id"]: row for row in registry}
    for evidence_id in (
        "m16_h2_inarisk_flood_hazard",
        "m16_h3_inarisk_landslide_hazard",
        "m16_v1_inarisk_flood_vulnerability",
        "m16_v2_inarisk_landslide_vulnerability",
    ):
        row = by_id.get(evidence_id, {})
        if row.get("evidence_state") != "endpoint_verified_version_binding_unresolved":
            errors.append(f"InaRISK endpoint unexpectedly promoted: {evidence_id}")
        if row.get("substantive_frame_authorized", "").lower() != "false":
            errors.append(f"InaRISK endpoint improperly authorized: {evidence_id}")
    for evidence_id in (
        "m16_h1_earthquake_shaking_2009",
        "m16_c1_chirps_rainfall_2024",
        "m16_o1_bnpb_flood_events_2024",
        "m16_o2_bnpb_landslide_events_2024",
    ):
        if by_id.get(evidence_id, {}).get("substantive_frame_authorized", "").lower() != "true":
            errors.append(f"qualified inherited evidence unexpectedly blocked: {evidence_id}")

    return {
        "schema": "ranah-observatory/milestone16-audit/v1",
        "geography_count": len(frame),
        "component_registry_count": len(registry),
        "substantive_component_count": sum(row.get("substantive_frame_authorized", "").lower() == "true" for row in registry),
        "blocked_or_gap_component_count": sum(row.get("substantive_frame_authorized", "").lower() == "false" for row in registry),
        "risk_synthesis_authorized": manifest.get("risk_synthesis_authorized"),
        "milestone16_complete": manifest.get("milestone16_complete") is True and not errors,
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
    if args.require_complete and not report["milestone16_complete"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
