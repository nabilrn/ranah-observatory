#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery_contract.json"
SNAPSHOT_PATH = ROOT / "data/processed/bnpb/m26_stage2_ckan_discovery/package-metadata.json"
CATALOG_PATH = ROOT / "data/analysis/engine/disaster_risk_chain_v1/m26-stage2-ckan-resource-catalog.json"
MANIFEST_PATH = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery.json"


class CkanDiscoveryError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def classify(name: str, description: str) -> dict[str, Any]:
    text = f"{name} {description}".casefold()
    impact_terms = {
        "deaths": ("meninggal", "meninggal dunia"),
        "missing": ("hilang",),
        "injured": ("luka", "sakit"),
        "affected": ("terdampak",),
        "displaced": ("mengungsi",),
        "houses_damaged": ("rumah rusak",),
        "public_facilities_damaged": ("fasilitas", "fasum", "fasilitas umum"),
    }
    families = [family for family, terms in impact_terms.items() if any(term in text for term in terms)]
    event_level_markers = ("kejadian per kejadian", "per kejadian", "event-level", "detail kejadian")
    aggregate_markers = (
        "menurut kabupaten", "menurut provinsi", "per kabupaten", "per provinsi",
        "menurut jenis bencana", "tahun 2010-2024", "tahun 2024", "rekapitulasi",
    )
    return {
        "impact_families_from_metadata_text": families,
        "event_level_metadata_marker_present": any(marker in text for marker in event_level_markers),
        "aggregate_metadata_marker_present": any(marker in text for marker in aggregate_markers),
    }


def build() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema") != "ranah-observatory/milestone26-stage2-ckan-resource-discovery-contract/v1":
        raise CkanDiscoveryError("unexpected discovery contract schema")
    if contract.get("locked_before_ckan_package_metadata_snapshot") is not True:
        raise CkanDiscoveryError("discovery contract was not locked before package snapshot")
    for key in (
        "datastore_records_retrieval_authorized", "resource_file_download_authorized",
        "target_impact_values_inspection_authorized", "resource_selection_after_target_value_inspection_authorized",
        "event_level_identity_inference_authorized", "impact_aggregation_authorized", "blank_as_zero_authorized",
        "automatic_duplicate_collapse_authorized", "cross_component_temporal_aggregation_authorized",
        "risk_synthesis_authorized", "statistical_model_fit_authorized", "causal_claim_authorized",
        "monetary_loss_inference_authorized", "monetary_wasted_potential_estimate_authorized",
    ):
        if contract.get(key) is not False:
            raise CkanDiscoveryError(f"forbidden discovery authorization enabled: {key}")

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if snapshot.get("snapshot_schema") != "ranah-observatory/bnpb-ckan-snapshot/v1":
        raise CkanDiscoveryError("unexpected BNPB package snapshot schema")
    if snapshot.get("command") != "package":
        raise CkanDiscoveryError("snapshot is not package metadata")
    if snapshot.get("filters", {}).get("dataset_id") != contract["official_source"]["package_id"]:
        raise CkanDiscoveryError("package id drift")
    result = snapshot.get("result")
    if not isinstance(result, dict):
        raise CkanDiscoveryError("package snapshot result missing")
    if result.get("id") != contract["official_source"]["package_id"]:
        raise CkanDiscoveryError("package metadata id mismatch")
    if clean(result.get("title")) != contract["official_source"]["package_title_expected"]:
        raise CkanDiscoveryError("package title drift")
    resources = result.get("resources")
    if not isinstance(resources, list) or not resources:
        raise CkanDiscoveryError("package exposes no resources")

    catalog: list[dict[str, Any]] = []
    for resource in resources:
        if not isinstance(resource, dict):
            raise CkanDiscoveryError("resource metadata is not an object")
        rid = clean(resource.get("id"))
        if not rid:
            raise CkanDiscoveryError("resource missing id")
        name = clean(resource.get("name"))
        description = clean(resource.get("description"))
        entry = {
            "resource_id": rid,
            "name": name,
            "description": description,
            "format": clean(resource.get("format")),
            "datastore_active": bool(resource.get("datastore_active")),
            "url": clean(resource.get("url")),
            "created": clean(resource.get("created")),
            "last_modified": clean(resource.get("last_modified")),
            "metadata_modified": clean(resource.get("metadata_modified")),
            "metadata_classification": classify(name, description),
            "known_held": rid in set(contract["known_held_resource_ids"]),
            "values_inspected": False,
        }
        catalog.append(entry)
    catalog.sort(key=lambda item: (item["name"].casefold(), item["resource_id"]))

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    impact_candidates = [
        item for item in catalog
        if item["metadata_classification"]["impact_families_from_metadata_text"]
    ]
    event_level_candidates = [
        item for item in impact_candidates
        if item["metadata_classification"]["event_level_metadata_marker_present"]
    ]
    datastore_impact_candidates = [item for item in impact_candidates if item["datastore_active"]]
    manifest = {
        "schema": "ranah-observatory/milestone26-stage2-ckan-resource-discovery/v1",
        "milestone": 26,
        "stage": "stage2a_observed_impact_transport_discovery",
        "package_id": result["id"],
        "package_title": clean(result.get("title")),
        "package_metadata_modified": clean(result.get("metadata_modified")),
        "resource_count": len(catalog),
        "metadata_text_impact_candidate_count": len(impact_candidates),
        "metadata_text_event_level_candidate_count": len(event_level_candidates),
        "datastore_impact_candidate_count": len(datastore_impact_candidates),
        "metadata_text_event_level_candidate_resource_ids": [item["resource_id"] for item in event_level_candidates],
        "datastore_impact_candidate_resource_ids": [item["resource_id"] for item in datastore_impact_candidates],
        "known_held_resource_ids_present": sorted(
            set(contract["known_held_resource_ids"]) & {item["resource_id"] for item in catalog}
        ),
        "snapshot": {"path": rel(SNAPSHOT_PATH), "sha256": sha256(SNAPSHOT_PATH)},
        "catalog": {"path": rel(CATALOG_PATH), "sha256": sha256(CATALOG_PATH)},
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
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build M26 BNPB CKAN resource metadata catalog without reading target values")
    parser.parse_args()
    payload = build()
    print(json.dumps({
        "resource_count": payload["resource_count"],
        "metadata_text_impact_candidate_count": payload["metadata_text_impact_candidate_count"],
        "metadata_text_event_level_candidate_count": payload["metadata_text_event_level_candidate_count"],
        "datastore_impact_candidate_count": payload["datastore_impact_candidate_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
