#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.build_milestone26_stage2_ckan_resource_catalog import classify, clean

ROOT = Path(__file__).resolve().parents[1]
BASE_CONTRACT = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery_contract.json"
AMENDMENT = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery_2024_amendment.json"
SNAPSHOT = ROOT / "data/processed/bnpb/m26_stage2_ckan_discovery_2024/package-metadata.json"
CATALOG = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage2-ckan-resource-catalog-2024.json"
MANIFEST = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery_2024.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def main() -> int:
    base = json.loads(BASE_CONTRACT.read_text(encoding="utf-8"))
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    assert base["schema"] == "ranah-observatory/milestone26-stage2-ckan-resource-discovery-contract/v1"
    assert amendment["schema"] == "ranah-observatory/milestone26-stage2-ckan-resource-discovery-2024-amendment/v1"
    assert amendment["locked_before_2024_package_metadata_snapshot"] is True
    for key in (
        "datastore_records_retrieval_authorized", "resource_file_download_authorized",
        "target_impact_values_inspection_authorized", "resource_selection_after_target_value_inspection_authorized",
        "event_level_identity_inference_authorized", "impact_aggregation_authorized", "blank_as_zero_authorized",
        "automatic_duplicate_collapse_authorized", "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized", "statistical_model_fit_authorized", "causal_claim_authorized",
        "monetary_loss_inference_authorized", "monetary_wasted_potential_estimate_authorized",
    ):
        assert amendment[key] is False

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert snap["snapshot_schema"] == "ranah-observatory/bnpb-ckan-snapshot/v1"
    assert snap["command"] == "package"
    assert snap["filters"]["dataset_id"] == amendment["official_source"]["package_id"]
    result = snap["result"]
    assert result["id"] == amendment["official_source"]["package_id"]
    assert clean(result["title"]) == amendment["official_source"]["package_title_expected"]

    rows: list[dict[str, Any]] = []
    for resource in result.get("resources", []):
        name = clean(resource.get("name"))
        description = clean(resource.get("description"))
        rows.append({
            "resource_id": clean(resource.get("id")),
            "name": name,
            "description": description,
            "format": clean(resource.get("format")),
            "datastore_active": bool(resource.get("datastore_active")),
            "url": clean(resource.get("url")),
            "created": clean(resource.get("created")),
            "last_modified": clean(resource.get("last_modified")),
            "metadata_modified": clean(resource.get("metadata_modified")),
            "metadata_classification": classify(name, description),
            "values_inspected": False,
        })
    rows.sort(key=lambda item: (item["name"].casefold(), item["resource_id"]))
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    impact = [r for r in rows if r["metadata_classification"]["impact_families_from_metadata_text"]]
    event_level = [r for r in impact if r["metadata_classification"]["event_level_metadata_marker_present"]]
    kabupaten_marker = [
        r for r in rows
        if "menurut kabupaten" in f"{r['name']} {r['description']}".casefold()
    ]
    provinsi_marker = [
        r for r in rows
        if "menurut provinsi" in f"{r['name']} {r['description']}".casefold()
    ]
    payload = {
        "schema": "ranah-observatory/milestone26-stage2-ckan-resource-discovery-2024/v1",
        "milestone": 26,
        "stage": "stage2a_observed_impact_transport_discovery",
        "package_id": result["id"],
        "package_title": clean(result["title"]),
        "package_metadata_modified": clean(result.get("metadata_modified")),
        "resource_count": len(rows),
        "metadata_text_impact_candidate_count": len(impact),
        "metadata_text_event_level_candidate_count": len(event_level),
        "metadata_text_event_level_candidate_resource_ids": [r["resource_id"] for r in event_level],
        "metadata_text_kabupaten_granularity_resource_count": len(kabupaten_marker),
        "metadata_text_provinsi_granularity_resource_count": len(provinsi_marker),
        "snapshot": {"path": rel(SNAPSHOT), "sha256": digest(SNAPSHOT)},
        "catalog": {"path": rel(CATALOG), "sha256": digest(CATALOG)},
        "package_metadata_only": True,
        "datastore_records_retrieved": False,
        "resource_files_downloaded": False,
        "target_impact_values_inspected": False,
        "resource_selected_for_promotion": False,
        "impact_aggregation_performed": False,
        "blank_interpreted_as_zero": False,
        "automatic_duplicate_collapse_performed": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_loss_inferred": False,
        "monetary_wasted_potential_estimated": False,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in (
        "resource_count", "metadata_text_impact_candidate_count",
        "metadata_text_event_level_candidate_count", "metadata_text_kabupaten_granularity_resource_count",
        "metadata_text_provinsi_granularity_resource_count"
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
