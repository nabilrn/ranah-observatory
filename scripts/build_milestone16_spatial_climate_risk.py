#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
M8_MANIFEST = ROOT / "data/manifests/milestone8_shakemap_exposure_candidate.json"
M8_FRAME = ROOT / "data/analysis/quasi_causal/m8-shakemap-exposure-candidate.csv"
M9_MANIFEST = ROOT / "data/manifests/milestone9_hydroclimate_case_study.json"
M9_FRAME = ROOT / "data/analysis/climate_disaster/m9-hydroclimate-2024-geography-frame.csv"
CATALOG = ROOT / "catalog/data-catalog.csv"
OUT_DIR = ROOT / "data/analysis/engine/spatial_climate_risk_v1"
FRAME_OUT = OUT_DIR / "m16-spatial-component-frame.csv"
REGISTRY_OUT = OUT_DIR / "m16-evidence-component-registry.csv"
MANIFEST_OUT = ROOT / "data/manifests/milestone16_spatial_climate_risk.json"

INARISK_ENDPOINTS = {
    "flood_hazard": "https://gis.bnpb.go.id/server/rest/services/inarisk/layer_bahaya_banjir/ImageServer",
    "landslide_hazard": "https://gis.bnpb.go.id/server/rest/services/inarisk/layer_bahaya_tanah_longsor/ImageServer",
    "flood_vulnerability": "https://gis.bnpb.go.id/server/rest/services/inarisk/layer_kerentanan_banjir/ImageServer",
    "landslide_vulnerability": "https://gis.bnpb.go.id/server/rest/services/inarisk/layer_kerentanan_tanah_longsor/ImageServer",
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def require_bool(value: Any, expected: bool, label: str) -> None:
    if value is not expected:
        raise RuntimeError(f"{label} expected {expected}, got {value!r}")


def main() -> int:
    m8_manifest = json.loads(M8_MANIFEST.read_text(encoding="utf-8"))
    m9_manifest = json.loads(M9_MANIFEST.read_text(encoding="utf-8"))

    if m8_manifest.get("schema") != "ranah-observatory/milestone8-shakemap-exposure-candidate/v1":
        raise RuntimeError("unexpected M8 ShakeMap manifest schema")
    if m8_manifest.get("geography_count") != 19 or m8_manifest.get("primary_candidate") != "area_mean_pga_pct_g":
        raise RuntimeError("M8 physical shaking footprint drift")
    require_bool(m8_manifest.get("historical_boundary_continuity_claimed"), False, "M8 historical boundary continuity")
    require_bool(m8_manifest.get("causal_effect_estimated"), False, "M8 exposure-candidate causal effect")
    if sha256(M8_FRAME) != m8_manifest.get("output_sha256"):
        raise RuntimeError("M8 spatial candidate checksum drift")

    if m9_manifest.get("schema") != "ranah-observatory/milestone9-hydroclimate-case-study/v1":
        raise RuntimeError("unexpected M9 hydroclimate manifest schema")
    require_bool(m9_manifest.get("milestone9_complete"), True, "M9 completion")
    require_bool(m9_manifest.get("causal_attribution_performed"), False, "M9 causal attribution")
    require_bool(m9_manifest.get("climate_change_attribution_performed"), False, "M9 climate attribution")
    if m9_manifest.get("climate_claim_type") != "model_estimate":
        raise RuntimeError("M9 CHIRPS evidence must remain model_estimate")
    if m9_manifest.get("disaster_claim_type") != "observed_recorded_event_count":
        raise RuntimeError("M9 BNPB event semantics drift")
    if m9_manifest.get("independent_station_validation") != "pending":
        raise RuntimeError("M9 station-validation state unexpectedly changed")
    if sha256(M9_FRAME) != m9_manifest.get("outputs", {}).get("geography_frame", {}).get("sha256"):
        raise RuntimeError("M9 geography-frame checksum drift")

    catalog_rows = {row["source_id"]: row for row in read_csv(CATALOG)}
    inarisk_catalog = catalog_rows.get("bnpb_inarisk_sumbar")
    if not inarisk_catalog:
        raise RuntimeError("catalog lost bnpb_inarisk_sumbar source")
    if inarisk_catalog.get("status") != "discovered":
        raise RuntimeError("M16 v1 expects InaRISK source to remain discovered until exact service-vintage binding is qualified")

    m8_rows = {row["geography_id"]: row for row in read_csv(M8_FRAME)}
    m9_rows = {row["geography_id"]: row for row in read_csv(M9_FRAME)}
    if len(m8_rows) != 19 or len(m9_rows) != 19 or set(m8_rows) != set(m9_rows):
        raise RuntimeError("M8/M9 exact 19-geography alignment failed")

    frame_rows: list[dict[str, Any]] = []
    for geography_id in sorted(m9_rows):
        shaking = m8_rows[geography_id]
        hydro = m9_rows[geography_id]
        frame_rows.append(
            {
                "geography_id": geography_id,
                "geography_name": hydro["geography_name"],
                "spatial_frame": "BIG_June_2026_fixed_current_boundary",
                "earthquake_event_date": "2009-09-30",
                "earthquake_area_mean_pga_pct_g": shaking["area_mean_pga_pct_g"],
                "earthquake_area_mean_mmi": shaking["area_mean_mmi"],
                "hydroclimate_year": 2024,
                "rainfall_z_2024": hydro["rainfall_z_2024"],
                "rainfall_baseline_percentile": hydro["rainfall_baseline_percentile"],
                "flood_events_2024": hydro["flood_events"],
                "landslide_events_2024": hydro["landslide_events"],
                "qualified_exposure_component_present": False,
                "qualified_vulnerability_component_present": False,
                "qualified_capacity_component_present": False,
                "qualified_observed_impact_component_present": False,
                "cross_event_temporal_aggregation_authorized": False,
                "risk_synthesis_authorized": False,
            }
        )

    registry_rows: list[dict[str, Any]] = [
        {
            "evidence_id": "m16_h1_earthquake_shaking_2009",
            "component_class": "hazard_intensity",
            "hazard_family": "earthquake",
            "evidence_state": "qualified_inherited",
            "claim_type": "model_derived_physical_intensity",
            "temporal_scope": "2009-09-30_event",
            "substantive_frame_authorized": True,
            "source_object": str(M8_FRAME.relative_to(ROOT)),
            "blocking_reason": "",
            "interpretation_boundary": "physical shaking intensity; not population/asset exposure, damage, loss, or historical-boundary reconstruction",
        },
        {
            "evidence_id": "m16_c1_chirps_rainfall_2024",
            "component_class": "climate_context",
            "hazard_family": "hydrometeorological",
            "evidence_state": "qualified_inherited_model_estimate",
            "claim_type": "model_estimate",
            "temporal_scope": "2024_vs_1981_2023_baseline",
            "substantive_frame_authorized": True,
            "source_object": str(M9_FRAME.relative_to(ROOT)),
            "blocking_reason": "",
            "interpretation_boundary": "annual gridded rainfall context; not station observation, event-day rainfall, disaster attribution, or climate-change attribution",
        },
        {
            "evidence_id": "m16_o1_bnpb_flood_events_2024",
            "component_class": "recorded_event_occurrence",
            "hazard_family": "flood",
            "evidence_state": "qualified_inherited",
            "claim_type": "observed_recorded_event_count",
            "temporal_scope": "2024",
            "substantive_frame_authorized": True,
            "source_object": str(M9_FRAME.relative_to(ROOT)),
            "blocking_reason": "",
            "interpretation_boundary": "recorded occurrence count; not hazard probability, exposure, impact, damage, casualties, or monetary loss",
        },
        {
            "evidence_id": "m16_o2_bnpb_landslide_events_2024",
            "component_class": "recorded_event_occurrence",
            "hazard_family": "landslide",
            "evidence_state": "qualified_inherited",
            "claim_type": "observed_recorded_event_count",
            "temporal_scope": "2024",
            "substantive_frame_authorized": True,
            "source_object": str(M9_FRAME.relative_to(ROOT)),
            "blocking_reason": "",
            "interpretation_boundary": "recorded occurrence count; not hazard probability, exposure, impact, damage, casualties, or monetary loss",
        },
    ]

    endpoint_specs = [
        ("m16_h2_inarisk_flood_hazard", "hazard_intensity", "flood", INARISK_ENDPOINTS["flood_hazard"]),
        ("m16_h3_inarisk_landslide_hazard", "hazard_intensity", "landslide", INARISK_ENDPOINTS["landslide_hazard"]),
        ("m16_v1_inarisk_flood_vulnerability", "vulnerability", "flood", INARISK_ENDPOINTS["flood_vulnerability"]),
        ("m16_v2_inarisk_landslide_vulnerability", "vulnerability", "landslide", INARISK_ENDPOINTS["landslide_vulnerability"]),
    ]
    for evidence_id, component_class, hazard_family, endpoint in endpoint_specs:
        registry_rows.append(
            {
                "evidence_id": evidence_id,
                "component_class": component_class,
                "hazard_family": hazard_family,
                "evidence_state": "endpoint_verified_version_binding_unresolved",
                "claim_type": "modeled_spatial_index_not_ingested",
                "temporal_scope": "service_vintage_unresolved",
                "substantive_frame_authorized": False,
                "source_object": endpoint,
                "blocking_reason": "ImageServer metadata does not itself provide a sufficient exact vintage/methodology binding for M16 substantive aggregation",
                "interpretation_boundary": "machine-readable official BNPB spatial service retained as readiness evidence only",
            }
        )

    registry_rows.extend(
        [
            {
                "evidence_id": "m16_e1_exposure_gap",
                "component_class": "exposure",
                "hazard_family": "multi_hazard",
                "evidence_state": "qualified_component_missing",
                "claim_type": "evidence_gap",
                "temporal_scope": "not_applicable",
                "substantive_frame_authorized": False,
                "source_object": "",
                "blocking_reason": "no qualified population/asset exposure object bound to the M16 spatial-temporal regime",
                "interpretation_boundary": "PGA/MMI must not be relabeled as exposure",
            },
            {
                "evidence_id": "m16_c2_capacity_gap",
                "component_class": "capacity",
                "hazard_family": "multi_hazard",
                "evidence_state": "qualified_component_missing",
                "claim_type": "evidence_gap",
                "temporal_scope": "not_applicable",
                "substantive_frame_authorized": False,
                "source_object": "",
                "blocking_reason": "no qualified capacity object bound to the M16 spatial-temporal regime",
                "interpretation_boundary": "capacity cannot be inferred from hazard or event counts",
            },
            {
                "evidence_id": "m16_i1_observed_impact_gap",
                "component_class": "observed_impact",
                "hazard_family": "multi_hazard",
                "evidence_state": "qualified_component_missing",
                "claim_type": "evidence_gap",
                "temporal_scope": "not_applicable",
                "substantive_frame_authorized": False,
                "source_object": "",
                "blocking_reason": "qualified event counts do not measure affected people, casualties, damaged assets, or monetary losses",
                "interpretation_boundary": "recorded occurrence must remain separate from observed impact",
            },
            {
                "evidence_id": "m16_r1_modeled_risk_blocked",
                "component_class": "modeled_risk",
                "hazard_family": "multi_hazard",
                "evidence_state": "synthesis_not_authorized",
                "claim_type": "blocked_derived_object",
                "temporal_scope": "not_applicable",
                "substantive_frame_authorized": False,
                "source_object": "",
                "blocking_reason": "hazard, exposure, vulnerability, capacity, and impact evidence are not jointly qualified in one compatible regime",
                "interpretation_boundary": "no composite disaster-risk score or kabupaten/kota risk ranking may be emitted",
            },
        ]
    )

    write_csv(FRAME_OUT, frame_rows)
    write_csv(REGISTRY_OUT, registry_rows)

    substantive = [row for row in registry_rows if row["substantive_frame_authorized"] is True]
    blocked = [row for row in registry_rows if row["substantive_frame_authorized"] is False]
    manifest = {
        "schema": "ranah-observatory/milestone16-spatial-climate-risk/v1",
        "phase": "final_analytical_research_engine",
        "milestone": 16,
        "criterion": "spatial/climate evidence integration with explicit risk-synthesis limits",
        "geography_count": len(frame_rows),
        "spatial_frame": "BIG June 2026 fixed-current-boundary polygons",
        "historical_boundary_continuity_claimed": False,
        "component_registry_count": len(registry_rows),
        "substantive_component_count": len(substantive),
        "blocked_or_gap_component_count": len(blocked),
        "substantive_component_classes": sorted({row["component_class"] for row in substantive}),
        "required_missing_component_classes": ["exposure", "vulnerability", "capacity", "observed_impact"],
        "inarisk_endpoint_count": len(endpoint_specs),
        "inarisk_endpoint_state": "endpoint_verified_version_binding_unresolved",
        "inarisk_pixels_ingested": False,
        "risk_synthesis_authorized": False,
        "composite_risk_score_created": False,
        "geography_risk_ranking_created": False,
        "cross_event_temporal_aggregation_performed": False,
        "causal_attribution_performed": False,
        "climate_change_attribution_performed": False,
        "monetary_wasted_potential_estimated": False,
        "inputs": {
            "m8_manifest": {"path": str(M8_MANIFEST.relative_to(ROOT)), "sha256": sha256(M8_MANIFEST)},
            "m8_frame": {"path": str(M8_FRAME.relative_to(ROOT)), "sha256": sha256(M8_FRAME)},
            "m9_manifest": {"path": str(M9_MANIFEST.relative_to(ROOT)), "sha256": sha256(M9_MANIFEST)},
            "m9_frame": {"path": str(M9_FRAME.relative_to(ROOT)), "sha256": sha256(M9_FRAME)},
            "catalog": {"path": str(CATALOG.relative_to(ROOT)), "sha256": sha256(CATALOG)},
        },
        "outputs": {
            "component_frame": {"path": str(FRAME_OUT.relative_to(ROOT)), "sha256": sha256(FRAME_OUT)},
            "component_registry": {"path": str(REGISTRY_OUT.relative_to(ROOT)), "sha256": sha256(REGISTRY_OUT)},
        },
        "milestone16_complete": True,
    }
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
