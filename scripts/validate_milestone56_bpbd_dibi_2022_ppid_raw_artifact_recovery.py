#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
M53 = ROOT / "data" / "manifests" / "milestone53_bpbd_dibi_2022_source_qualification.json"
M55 = ROOT / "data" / "manifests" / "milestone55_bpbd_library_historical_media_migration.json"
M56 = ROOT / "data" / "manifests" / "milestone56_bpbd_dibi_2022_ppid_raw_artifact_recovery.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _official(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "sumbarprov.go.id" or host.endswith(".sumbarprov.go.id"))


def validate() -> dict[str, Any]:
    m53 = _read_json(M53)
    m55 = _read_json(M55)
    m56 = _read_json(M56)

    assert m56["schema"] == "ranah-observatory/milestone56-bpbd-dibi-2022-ppid-raw-artifact-recovery/v1"
    assert m56["milestone"] == 56
    assert m56["depends_on"] == [53, 55]
    assert m56["decision_date"] == "2026-09-02"

    legacy = m56["legacy_identity"]
    assert legacy["record_id"] == 20769
    assert legacy["title"] == "Buku DIBI Tahun 2022"
    assert legacy["legacy_detail_exact_title_match"] is True
    assert _official(legacy["legacy_detail_url"])
    assert _official(legacy["legacy_direct_pdf_url"])

    mapping = m56["current_ppid_mapping"]
    uuid = "faf18bd0-76d9-44b2-8092-b89f70f29e6e"
    assert mapping["uuid"] == uuid
    assert mapping["information_url"].endswith(f"/home/information/{uuid}")
    assert mapping["download_url"].endswith(f"/home/download/{uuid}")
    assert _official(mapping["information_url"])
    assert _official(mapping["download_url"])
    assert len(mapping["legacy_routes_tested"]) == 3
    assert all(_official(url) for url in mapping["legacy_routes_tested"])
    assert mapping["all_legacy_routes_resolved_to_same_uuid"] is True
    assert mapping["resolved_information_page_exact_title_match"] is True
    assert mapping["numeric_current_download_route_valid"] is False
    assert mapping["numeric_api_download_route_valid"] is False
    assert mapping["exact_title_inventory_post_returned_current_uuid"] is False

    artifact = m56["raw_artifact"]
    assert artifact["retrieval_status"] == 200
    assert artifact["content_type"] == "application/pdf"
    assert artifact["byte_count"] == 13_044_950
    assert artifact["sha256"] == "f0ce706388d54c361ecd36f7c5da2a3bd749f59b32f807c9e8c5bb25fef67ba3"
    assert artifact["pdf_version"] == "1.7"
    assert artifact["page_count"] == 154
    assert artifact["complete_pdf_magic_verified"] is True
    assert artifact["complete_pdf_eof_verified"] is True
    assert artifact["body_truncated"] is False
    assert artifact["repeat_download_same_sha256_verified"] is True
    assert artifact["raw_official_artifact_acquired"] is True
    assert artifact["artifact_committed_to_repository"] is False

    verify = m56["raw_table_verification"]
    locators = verify["table_page_locators"]
    assert locators == {
        "table_3_1": 36,
        "table_3_2": 38,
        "table_3_3": 39,
        "table_3_4": 39,
        "table_3_5": 40,
        "table_3_6": 40,
        "table_3_7": 41,
        "table_3_8": 41,
        "table_3_9": 42,
        "table_3_10": 44,
        "recapitulation_appendix_start": 90,
        "history_appendix_start": 92,
        "history_appendix_final_grand_total_page": 146,
    }
    assert verify["events_total_1021_verified"] is True
    hazards = verify["table_3_2_hazard_totals_verified"]
    assert sum(value for key, value in hazards.items() if key != "total") == 1021
    assert hazards["total"] == 1021
    assert hazards == m53["indexed_verification_targets"]["events_by_hazard_table_3_2"]

    t33 = verify["table_3_3_human_impact_verified"]
    t34 = verify["table_3_4_human_impact_verified"]
    t310 = verify["table_3_10_human_impact_monthly_verified"]
    assert t33 == {"deaths": 28, "missing": None, "injured_or_sick": 456, "evacuated": 26265}
    assert t34 == {"deaths": 28, "missing": 4, "injured_or_sick": 456, "evacuated": 26265, "event_total": 1021}
    assert t310 == {"deaths": 28, "missing": 4, "injured_or_sick": 456, "evacuated": 26265}

    months = verify["table_3_9_monthly_totals_verified"]
    assert months == m53["indexed_verification_targets"]["events_by_month_table_3_9"]
    assert sum(value for key, value in months.items() if key != "total") == 1021
    assert verify["district_event_count_disagreement_count_verified"] == 7
    assert verify["district_event_tables_and_human_impact_table_both_total_1021"] is True
    assert verify["indexed_verification_targets_materially_confirmed"] is True

    disagreement = m56["new_internal_disagreement"]
    assert disagreement["metric"] == "recorded_loss_rupiah"
    assert disagreement["table_3_1_and_narrative_page_36"] == 1_136_849_587_336
    assert disagreement["recapitulation_and_history_appendices_pages_90_146"] == 1_136_849_586_796
    assert disagreement["absolute_difference_rupiah"] == 540
    assert abs(disagreement["table_3_1_and_narrative_page_36"] - disagreement["recapitulation_and_history_appendices_pages_90_146"]) == 540
    assert disagreement["same_value"] is False
    assert disagreement["resolution_authorized"] is False

    flags = m56["confirmed_m53_quality_flags"]
    assert flags["missing_person_disagreement_table_3_3_vs_3_4"] is True
    assert flags["seven_district_event_count_disagreements"] is True
    assert flags["search_index_monetary_corruption_bypassed_by_raw_artifact"] is True
    assert flags["raw_pdf_page_count_matches_indexed_mirror_page_count_154"] is True
    assert m53["indexed_mirror"]["reported_page_count"] == artifact["page_count"]

    promotion = m56["promotion_state"]
    assert promotion["raw_artifact_gate_satisfied"] is True
    assert promotion["source_native_table_verification_authorized"] is True
    assert promotion["source_native_materialization_authorized"] is False
    assert promotion["public_dataset_catalog_promotion_authorized"] is False
    assert promotion["canonical_cross_year_disaster_timeseries_authorized"] is False

    result = m56["result"]
    assert all(result[key] is True for key in (
        "legacy_record_to_current_uuid_recovered",
        "raw_official_pdf_recovered",
        "raw_pdf_sha256_frozen",
        "raw_pdf_page_count_frozen",
        "major_m53_verification_targets_confirmed",
        "new_recorded_loss_disagreement_detected",
        "materialization_deferred_to_m57",
        "promotion_gate_fail_closed",
    ))

    # Historical milestone states remain frozen; M56 supersedes their acquisition status rather than rewriting them.
    assert m53["result"]["raw_official_artifact_acquired"] is False
    assert m55["interpretation"]["raw_dibi_2022_pdf_recovered_from_current_library"] is False
    assert m55["result"]["historical_media_migration_gap_confirmed"] is True

    return {
        "schema": "ranah-observatory/milestone56-bpbd-dibi-2022-ppid-raw-artifact-recovery-audit/v1",
        "milestone": 56,
        "uuid": mapping["uuid"],
        "bytes": artifact["byte_count"],
        "sha256": artifact["sha256"],
        "pages": artifact["page_count"],
        "verified_table_count": 10,
        "recorded_loss_difference_rupiah": disagreement["absolute_difference_rupiah"],
        "raw_artifact_gate_satisfied": True,
        "materialization_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"M56 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
