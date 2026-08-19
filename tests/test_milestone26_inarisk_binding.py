from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/probe_milestone26_inarisk_binding.py"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("m26", SCRIPT)
assert spec and spec.loader
m26 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m26)


def test_m16_committed_evidence_exposes_official_inarisk_services() -> None:
    services = m26.discover_services()
    assert services
    assert len({row["service_url"] for row in services}) == len(services)
    assert all(row["m16_status"] == "endpoint_verified_version_binding_unresolved" for row in services)
    assert all(row["pixel_ingestion_authorized"] is False for row in services)
    assert all(m26.official_service(row["service_url"]) for row in services)


def test_canonical_service_url_strips_layer_id_but_preserves_service_type() -> None:
    assert m26.canonical_service_url("https://example.bnpb.go.id/arcgis/rest/services/Flood/MapServer/0") == "https://example.bnpb.go.id/arcgis/rest/services/Flood/MapServer"
    assert m26.canonical_service_url("https://example.bnpb.go.id/arcgis/rest/services/Risk/ImageServer") == "https://example.bnpb.go.id/arcgis/rest/services/Risk/ImageServer"


def test_modified_and_copyright_years_never_become_dataset_vintage() -> None:
    result = m26.classify_binding(
        [
            (
                "service_root",
                {
                    "currentVersion": 11.2,
                    "documentInfo": {"Author": "BNPB", "Comments": "Updated 2024", "CopyrightText": "2024 BNPB"},
                    "modified": 1710000000000,
                },
            )
        ]
    )
    assert result["vintage_binding_status"] == "year_tokens_present_binding_unresolved"
    assert result["metadata_binding_qualified_for_future_ingestion"] is False


def test_time_info_is_not_treated_as_dataset_vintage() -> None:
    result = m26.classify_binding(
        [
            (
                "service_root",
                {
                    "timeInfo": {"startTimeField": "DATE", "timeExtent": [1609459200000, 1640995200000]},
                    "description": "InaRISK hazard service",
                },
            )
        ]
    )
    assert result["vintage_binding_status"] == "time_enabled_not_dataset_vintage"
    assert result["metadata_binding_qualified_for_future_ingestion"] is False


def test_explicit_dataset_vintage_and_methodology_fields_can_qualify_metadata_only() -> None:
    result = m26.classify_binding(
        [
            (
                "layer_0",
                {
                    "dataYear": "2024",
                    "methodologyVersion": "InaRISK Methodology 2024 v1",
                    "description": "Qualified synthetic fixture",
                },
            )
        ]
    )
    assert result["vintage_binding_status"] == "explicit_dataset_vintage_bound"
    assert result["methodology_binding_status"] == "explicit_methodology_version_bound"
    assert result["metadata_binding_qualified_for_future_ingestion"] is True


def test_methodology_mention_without_explicit_field_stays_unresolved() -> None:
    result = m26.classify_binding(
        [("iteminfo", {"description": "See the InaRISK methodology documentation for details; copyright 2024."})]
    )
    assert result["methodology_binding_status"] == "methodology_reference_present_binding_unresolved"
    assert result["metadata_binding_qualified_for_future_ingestion"] is False
