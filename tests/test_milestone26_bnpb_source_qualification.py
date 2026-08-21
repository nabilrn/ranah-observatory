from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_milestone26_bnpb_sources.py"

spec = importlib.util.spec_from_file_location("m26_probe", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_preregistered_source_ids_are_locked_and_unique() -> None:
    rows = m26.read_registry()
    assert [row["source_id"] for row in rows] == m26.EXPECTED_IDS
    assert len(rows) == len(set(m26.EXPECTED_IDS)) == 9


def test_design_blocks_stage0_modeling_and_aggregation() -> None:
    design = m26.load_design()
    assert design["geography_count"] == 19
    assert design["geography_regime"] == "BIG_June_2026_fixed_current_boundary"
    assert design["stage0_numeric_spatial_aggregation_authorized"] is False
    assert design["stage0_event_panel_materialization_authorized"] is False
    assert design["risk_synthesis_authorized"] is False
    assert design["cross_component_temporal_aggregation_authorized"] is False
    assert design["statistical_model_fit_authorized"] is False
    assert design["causal_claim_authorized"] is False
    assert design["monetary_wasted_potential_estimate_authorized"] is False


def test_only_explicit_vintage_or_coverage_states_authorize_later_numeric_extraction() -> None:
    design = m26.load_design()
    assert set(design["numeric_extraction_authorized_states"]) == {
        "qualified_explicit_vintage_metadata",
        "qualified_explicit_coverage_metadata",
    }
    assert m26.EXPECTED_FINAL_STATES["inarisk_capacity_2021"] == "qualified_explicit_vintage_metadata"
    assert m26.EXPECTED_FINAL_STATES["inarisk_population_2020"] == "qualified_explicit_vintage_metadata"
    assert m26.EXPECTED_FINAL_STATES["dibi_kabupaten_hidromet_2015_2024"] == "qualified_explicit_coverage_metadata"


def test_dibi_schema_probe_accepts_either_declared_duplicate_child_layer() -> None:
    assert m26.ARC_EXTRA["dibi_kabupaten_hidromet_2015_2024"] == ["0", "1"]


def test_hazard_and_vulnerability_are_fail_closed_until_version_bound() -> None:
    for source_id in (
        "inarisk_flood_hazard",
        "inarisk_landslide_hazard",
        "inarisk_flood_vulnerability",
        "inarisk_landslide_vulnerability",
    ):
        assert m26.EXPECTED_FINAL_STATES[source_id] == "endpoint_verified_version_binding_unresolved"


def test_event_impact_field_presence_does_not_authorize_panel_materialization() -> None:
    assert m26.EXPECTED_FINAL_STATES["bnpb_event_impact_table"] == "field_surface_verified_retrieval_contract_pending"
    design = json.loads(m26.DESIGN.read_text(encoding="utf-8"))
    assert design["stage0_event_panel_materialization_authorized"] is False
    assert "field_presence_is_not_a_retrieval_contract" in design["event_impact_promotion_rule"]


def test_methodology_surface_is_framework_only() -> None:
    assert m26.EXPECTED_FINAL_STATES["inarisk_current_methodology"] == "framework_verified_current_surface"
    assert "framework_verified_current_surface" not in m26.load_design()["numeric_extraction_authorized_states"]


def test_methodology_spa_shell_can_verify_route_without_visible_text() -> None:
    body = b'<!doctype html><html><head><script src="/assets/app.js"></script></head><body><div id="app"></div></body></html>'
    qualifies, mode = m26.methodology_surface_qualifies(
        "https://inarisk2.bnpb.go.id/v4/metodologi",
        "text/html; charset=utf-8",
        body,
    )
    assert qualifies is True
    assert mode == "official_route_html_spa_shell"
    wrong_host, _ = m26.methodology_surface_qualifies(
        "https://example.com/v4/metodologi",
        "text/html",
        body,
    )
    assert wrong_host is False


def test_html_normalization_and_snapshot_serialization_are_deterministic() -> None:
    body = b"<html><style>x</style><body> InaRISK   Metodologi <script>bad()</script> Risiko </body></html>"
    assert m26.normalize_text(body) == "InaRISK Metodologi Risiko"
    payload = {"z": 1, "a": {"b": 2}}
    first = m26.canonical_snapshot(payload)
    second = m26.canonical_snapshot(payload)
    assert first == second
    assert first.startswith(b'{\n  "a"')
