from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone26_event_impact_transport_candidate.json"
REGISTRY = ROOT / "data" / "registries" / "m26-bnpb-source-candidates.csv"
QUALIFICATION = ROOT / "data" / "analysis" / "engine" / "disaster_risk_chain_v1" / "m26-source-qualification.csv"

SOURCE_ID = "bnpb_event_impact_table"
EXPECTED_STATUS = "official_machine_readable_transport_verified_retrieval_contract_pending"
REQUIRED_IDENTITY_FIELDS = {"objectid", "id", "xdibi", "serial", "kib"}
REQUIRED_HUMAN_IMPACT_FIELDS = {"meninggal", "hilang", "terluka", "menderita", "mengungsi"}
REQUIRED_HOUSING_FIELDS = {"rumah_rusak_berat", "rumah_rusak_sedang", "rumah_rusak_ringan", "rumah_rusak", "terendam"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _row_by_source(rows: list[dict[str, str]], source_id: str) -> dict[str, str]:
    matches = [row for row in rows if row.get("source_id") == source_id]
    assert len(matches) == 1, f"expected exactly one {source_id} row, got {len(matches)}"
    return matches[0]


def _official_bnpb_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "bnpb.go.id" or host.endswith(".bnpb.go.id"))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry_row = _row_by_source(_read_csv(REGISTRY), SOURCE_ID)
    qualification_row = _row_by_source(_read_csv(QUALIFICATION), SOURCE_ID)

    assert manifest["schema"] == "ranah-observatory/milestone26-event-impact-transport-candidate/v1"
    assert manifest["source_id"] == SOURCE_ID
    assert manifest["component_class"] == "observed_impact"
    assert manifest["hazard_family"] == "multi_hazard"
    assert manifest["official_owner"] == "BNPB"
    assert manifest["discovery_date"] == "2026-08-28"

    upstream = manifest["upstream_stage0_binding"]
    assert upstream["registry_path"] == REGISTRY.relative_to(ROOT).as_posix()
    assert upstream["qualification_path"] == QUALIFICATION.relative_to(ROOT).as_posix()
    assert upstream["original_surface_url"] == registry_row["source_url"]
    assert upstream["original_qualification_state"] == qualification_row["qualification_state"]
    assert upstream["original_qualification_state"] == "field_surface_verified_retrieval_contract_pending"
    assert upstream["numeric_extraction_authorized"] is False
    assert qualification_row["numeric_extraction_authorized"].casefold() == "false"

    transport = manifest["candidate_transport"]
    assert _official_bnpb_url(transport["url"])
    assert _official_bnpb_url(transport["query_url"])
    assert transport["url"].endswith("/Hosted/Data_Bencana_Dashboard/FeatureServer/0")
    assert transport["query_url"] == transport["url"] + "/query"
    assert transport["service_item_id"] == "cc34bb232b504e279ee1c94c081e3860"
    assert transport["layer_id"] == 0
    assert transport["layer_name"] == "Sheet2"
    assert transport["layer_type"] == "Feature Layer"
    assert transport["geometry_type"] == "esriGeometryPoint"
    assert transport["object_id_field"] == "objectid"
    assert transport["max_record_count"] == 2000
    assert set(transport["supported_query_formats"]) == {"JSON", "geoJSON", "PBF"}
    for key in (
        "supports_query",
        "supports_advanced_queries",
        "supports_order_by",
        "supports_pagination",
        "supports_statistics",
        "uses_standardized_queries",
    ):
        assert transport[key] is True

    fields = manifest["field_surface"]
    assert REQUIRED_IDENTITY_FIELDS.issubset(fields["identity_candidates"])
    assert {"nprop", "nkab"}.issubset(fields["geography_fields"])
    assert {"id_jenis_bencana", "kejadian", "tahun", "bulan", "tanggal"}.issubset(fields["event_fields"])
    assert REQUIRED_HUMAN_IMPACT_FIELDS.issubset(fields["human_impact_fields"])
    assert REQUIRED_HOUSING_FIELDS.issubset(fields["housing_impact_fields"])
    assert "kerugian_juta" in fields["economic_context_fields"]
    assert {"sumber", "link_dokumentasi", "tanggal_update"}.issubset(fields["provenance_fields"])

    hazards = {item["field"]: item for item in manifest["type_hazards"]}
    assert hazards["terluka"]["declared_type"] == "esriFieldTypeString"
    assert hazards["pabrik_rusak_sedang"]["declared_type"] == "esriFieldTypeString"
    assert "zero" in hazards["terluka"]["blocking_implication"]

    classification = manifest["transport_classification"]
    assert classification["official_machine_readable_surface_verified"] is True
    assert classification["query_operation_exposed"] is True
    assert classification["same_official_owner"] is True
    assert classification["same_component_class"] is True
    assert classification["source_family_changed"] is False
    assert classification["scientific_design_changed"] is False
    assert classification["posthoc_transport_discovery_performed"] is True
    assert classification["posthoc_source_family_search_performed"] is False
    assert classification["candidate_status"] == EXPECTED_STATUS

    unresolved = manifest["unresolved_contracts"]
    assert unresolved
    assert all(value is False for value in unresolved.values())

    next_audit = manifest["proposed_next_audit"]
    assert list(next_audit) == [f"stage_{index}" for index in range(1, 9)]
    assert "distinct source-native province labels" in next_audit["stage_2"]
    assert "objectid ordering" in next_audit["stage_3"]
    assert "SHA-256" in next_audit["stage_4"]
    assert "without deduplication" in next_audit["stage_5"]

    gate = manifest["gate"]
    assert gate
    assert all(value is False for value in gate.values())

    boundary = manifest["evidence_boundary"]
    assert boundary["metadata_surface_verified_from_official_arcgis_rest"] is True
    assert boundary["metadata_snapshot_bytes_stored_in_repository"] is False
    assert boundary["event_rows_retrieved"] is False
    assert boundary["event_values_inspected"] is False
    assert "identity" in boundary["reason_for_hold"]
    assert "typing" in boundary["reason_for_hold"]

    return {
        "source_id": SOURCE_ID,
        "candidate_status": EXPECTED_STATUS,
        "official_machine_readable_surface_verified": True,
        "query_operation_exposed": True,
        "event_rows_retrieved": False,
        "numeric_extraction_authorized": False,
        "event_panel_materialization_authorized": False,
        "risk_synthesis_authorized": False,
        "unresolved_contract_count": len(unresolved),
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
