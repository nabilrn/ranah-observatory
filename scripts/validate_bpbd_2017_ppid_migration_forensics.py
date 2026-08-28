#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/bpbd_2017_ppid_migration_forensics.json"
PARENT = ROOT / "data/manifests/milestone51_bpbd_raw_artifact_acquisition_lane.json"
PROBE = ROOT / "scripts/probe_milestone52_bpbd_2017_ppid_migration.py"

TARGET_TITLE = "Laporan Tahunan Data Kebencanaan Pusdalops PB Sumatera Barat Tahun 2017"
TARGET_UUID = "e46ef762-5314-4f25-8a70-53de147147da"


def _official_sumbar_url(value: str) -> bool:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "sumbarprov.go.id" or host.endswith(".sumbarprov.go.id"))


def validate() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    probe_source = PROBE.read_text(encoding="utf-8")

    assert manifest["schema"] == "ranah-observatory/bpbd-2017-ppid-migration-forensics/v1"
    assert manifest["decision_date"] == "2026-08-28"
    assert manifest["depends_on_milestone"] == 51

    assert parent["schema"] == "ranah-observatory/milestone51-bpbd-raw-artifact-acquisition-lane/v3"
    ppid = parent["ppid_migration_forensics"]
    assert ppid["legacy_2017_download_audit_record_id"] == 8604
    assert ppid["legacy_2017_download_audit_title"] == TARGET_TITLE
    assert ppid["legacy_2017_download_audit_opd"] == "Badan Penanggulangan Bencana Daerah"
    assert ppid["legacy_2017_download_count"] == 24
    assert ppid["record_8604_to_current_uuid_mapping_recovered"] is False
    assert ppid["current_detail_or_download_url_for_2017_recovered"] is False
    assert ppid["raw_2017_pdf_bytes_recovered"] is False
    assert ppid["m52_trigger_satisfied"] is False

    target = manifest["target"]
    assert target["legacy_record_id"] == 8604
    assert target["title"] == TARGET_TITLE
    assert target["opd"] == "Badan Penanggulangan Bencana Daerah"
    assert target["historical_download_count"] == 24

    legacy = manifest["legacy_route_probe"]
    assert len(legacy["tested_urls"]) == 3
    assert all(_official_sumbar_url(url) for url in legacy["tested_urls"])
    assert legacy["all_resolved_http_200"] is True
    assert legacy["common_redirect_uuid"] == TARGET_UUID
    assert _official_sumbar_url(legacy["common_information_url"])
    assert _official_sumbar_url(legacy["common_download_url"])
    assert legacy["destination_visible_title"] == "SPO Cervical RPO"
    assert legacy["target_exact_title_present"] is False
    assert legacy["target_identity_tokens_present"] is False
    assert legacy["download_http_status"] == 200
    assert legacy["download_response_text"] == "File tidak ditemukan atau tidak dapat diakses."
    assert legacy["classification"] == "legacy_numeric_redirect_semantic_collision_not_valid_mapping"

    active = manifest["active_inventory_probe"]
    assert _official_sumbar_url(active["url"])
    assert active["method"] == "POST exact title using fresh public csrf token and cookie session"
    assert active["http_status"] == 200
    assert active["exact_title_present"] is False
    assert active["identity_tokens_present"] is False
    assert active["returned_information_url_count"] == 0
    assert active["exact_title_match_count"] == 0
    assert active["token_only_match_count"] == 0
    assert active["classification"] == "active_inventory_exact_title_no_hit"

    bounded = manifest["bounded_inference"]
    assert bounded["legacy_redirect_is_valid_2017_mapping"] is False
    assert bounded["active_inventory_currently_indexes_exact_title"] is False
    assert bounded["does_not_prove_artifact_deleted"] is True
    assert bounded["does_not_prove_bytes_unavailable_on_other_official_surface"] is True
    assert bounded["does_not_authorize_mirror_substitution"] is True
    assert bounded["does_not_invalidate_historical_ppid_record_existence_evidence"] is True

    trace = manifest["transient_execution_trace"]
    assert trace["workflow_run_id"] == 33153486197
    assert trace["workflow_job_id"] == 98790718012
    assert trace["artifact_id"] == 9678662866
    assert len(trace["artifact_zip_sha256"]) == 64
    assert "not canonical evidence storage" in trace["role"]

    gate = manifest["gate"]
    assert gate["legacy_redirect_destination_recovered"] is True
    for key in (
        "record_8604_to_current_uuid_mapping_recovered",
        "current_detail_or_download_url_for_2017_recovered",
        "raw_official_pdf_recovered",
        "raw_checksum_frozen",
        "source_native_2017_extraction_authorized",
        "canonical_historical_impact_promotion_authorized",
        "m52_trigger_satisfied",
    ):
        assert gate[key] is False, key

    assert "no UUID brute force" in probe_source
    assert "MAX_SEARCH_RESULTS_TO_INSPECT = 20" in probe_source
    assert "official_ppid_dip_post_exact_title" in probe_source
    assert "<redacted-volatile-csrf>" in probe_source
    assert "sumbarprov.go.id" in probe_source

    return {
        "legacy_semantic_collision_frozen": True,
        "active_inventory_exact_title_no_hit": True,
        "raw_official_pdf_recovered": False,
        "record_8604_to_current_uuid_mapping_recovered": False,
        "m52_trigger_satisfied": False,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
