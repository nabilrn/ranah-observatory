#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / "data/manifests/milestone26_stage2a_transport_diagnostic.json"
CKAN_PRIMARY = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery.json"
CKAN_2024 = ROOT / "data/manifests/milestone26_stage2_ckan_resource_discovery_2024.json"
STAGE2_CONTRACT = ROOT / "data/manifests/milestone26_stage2_event_impact_contract.json"
SPEC = ROOT / "research/MILESTONE26_DISASTER_RISK_CHAIN_SPEC.md"
OUT = ROOT / "data/manifests/milestone26_stage2_observed_impact_decision.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}


def main() -> int:
    transport = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    primary = json.loads(CKAN_PRIMARY.read_text(encoding="utf-8"))
    dedicated = json.loads(CKAN_2024.read_text(encoding="utf-8"))
    contract = json.loads(STAGE2_CONTRACT.read_text(encoding="utf-8"))

    assert transport["schema"] == "ranah-observatory/milestone26-stage2a-transport-diagnostic/v1"
    assert transport["classification"] == "post_filter_transport_not_proven"
    assert transport["impact_cell_values_inspected"] is False
    assert transport["row_level_impact_promotion_authorized"] is False
    assert transport["impact_aggregation_performed"] is False
    assert transport["target_contract_changed"] is False

    assert primary["schema"] == "ranah-observatory/milestone26-stage2-ckan-resource-discovery/v1"
    assert primary["package_metadata_only"] is True
    assert primary["metadata_text_event_level_candidate_count"] == 0
    assert primary["datastore_records_retrieved"] is False
    assert primary["target_impact_values_inspected"] is False
    assert primary["resource_selected_for_promotion"] is False

    assert dedicated["schema"] == "ranah-observatory/milestone26-stage2-ckan-resource-discovery-2024/v1"
    assert dedicated["package_metadata_only"] is True
    assert dedicated["metadata_text_event_level_candidate_count"] == 0
    assert dedicated["datastore_records_retrieved"] is False
    assert dedicated["target_impact_values_inspected"] is False
    assert dedicated["resource_selected_for_promotion"] is False

    assert contract["stage2a"]["impact_aggregation_authorized"] is False
    assert contract["stage2a"]["automatic_duplicate_collapse_authorized"] is False
    assert contract["stage2a"]["stage2b_promotion_authorized"] is False

    payload = {
        "schema": "ranah-observatory/milestone26-stage2-observed-impact-decision/v1",
        "milestone": 26,
        "component_class": "observed_impact",
        "target_regime": contract["target_regime"],
        "decision": "held_deterministic_event_level_transport_unqualified",
        "decision_reason": (
            "the official legacy BNPB Data Bencana table exposes the required event-impact fields but its dated POST "
            "filter transport is not deterministically qualified, while both official BNPB Satu Data CKAN package "
            "metadata surfaces expose aggregate impact resources and no metadata-qualified event-level candidate"
        ),
        "legacy_html_evidence": {
            **ref(TRANSPORT),
            "classification": transport["classification"],
            "default_get_row_count": next(x["row_count"] for x in transport["results"] if x["id"] == "get_default"),
            "post_banjir_event_only_row_count": next(x["row_count"] for x in transport["results"] if x["id"] == "post_banjir_event_only"),
            "post_banjir_2026_row_count": next(x["row_count"] for x in transport["results"] if x["id"] == "post_banjir_2026"),
            "post_tanah_longsor_2026_row_count": next(x["row_count"] for x in transport["results"] if x["id"] == "post_tanah_longsor_2026"),
            "post_banjir_2024_row_count": next(x["row_count"] for x in transport["results"] if x["id"] == "post_banjir_2024_repeat"),
            "interpretation": "zero dated-query rows are treated as transport nonqualification, not evidence of zero disasters or zero impacts"
        },
        "ckan_primary_package_evidence": {
            **ref(CKAN_PRIMARY),
            "package_id": primary["package_id"],
            "resource_count": primary["resource_count"],
            "metadata_text_impact_candidate_count": primary["metadata_text_impact_candidate_count"],
            "metadata_text_event_level_candidate_count": primary["metadata_text_event_level_candidate_count"],
            "datastore_impact_candidate_count": primary["datastore_impact_candidate_count"],
        },
        "ckan_dedicated_2024_package_evidence": {
            **ref(CKAN_2024),
            "package_id": dedicated["package_id"],
            "resource_count": dedicated["resource_count"],
            "metadata_text_impact_candidate_count": dedicated["metadata_text_impact_candidate_count"],
            "metadata_text_event_level_candidate_count": dedicated["metadata_text_event_level_candidate_count"],
            "metadata_text_kabupaten_granularity_resource_count": dedicated["metadata_text_kabupaten_granularity_resource_count"],
            "metadata_text_provinsi_granularity_resource_count": dedicated["metadata_text_provinsi_granularity_resource_count"],
        },
        "stage2_contract": ref(STAGE2_CONTRACT),
        "milestone_spec": ref(SPEC),
        "aggregate_ckan_impact_resources_promoted_as_event_rows": False,
        "zero_rows_interpreted_as_zero_disaster_occurrence": False,
        "zero_rows_interpreted_as_zero_observed_impact": False,
        "target_impact_values_inspected_for_resource_selection": False,
        "event_level_observed_impact_qualified": False,
        "stage2b_promotion_authorized": False,
        "impact_aggregation_authorized": False,
        "automatic_duplicate_collapse_authorized": False,
        "cross_component_temporal_aggregation_authorized": False,
        "risk_synthesis_authorized": False,
        "statistical_model_fit_authorized": False,
        "causal_claim_authorized": False,
        "monetary_loss_inference_authorized": False,
        "monetary_wasted_potential_estimate_authorized": False,
        "next_reconsideration_gate": (
            "a public deterministic BNPB event-level retrieval surface or an official machine-readable resource with "
            "documented event identity, target-period coverage, geography mapping, and missingness semantics"
        )
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": payload["decision"], "risk_synthesis_authorized": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
