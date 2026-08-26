#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.historical_batch_collect import (
        DEFAULT_ALLOWED_HOST,
        official_bps_url,
        official_source_url,
        queue_allowed_host,
        read_queue,
    )
except ModuleNotFoundError:  # direct `python scripts/...py` execution
    from historical_batch_collect import (  # type: ignore[no-redef]
        DEFAULT_ALLOWED_HOST,
        official_bps_url,
        official_source_url,
        queue_allowed_host,
        read_queue,
    )

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone51_bpbd_raw_artifact_acquisition_lane.json"
QUEUE = ROOT / "data" / "acquisition_requests" / "bpbd_publications.csv"
M50 = ROOT / "data" / "manifests" / "milestone50_bpbd_historical_impact_source_qualification.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    m50 = _read_json(M50)
    rows = read_queue(QUEUE)

    assert manifest["schema"] == "ranah-observatory/milestone51-bpbd-raw-artifact-acquisition-lane/v3"
    assert manifest["milestone"] == 51
    assert manifest["depends_on"] == [50]
    assert DEFAULT_ALLOWED_HOST == "bps.go.id"
    assert official_bps_url("https://sumbar.bps.go.id/id/publication/example")
    assert not official_bps_url("https://bps.go.id.evil.example/publication")

    assert len(rows) == 5
    by_id = {row["request_id"].strip(): row for row in rows}
    assert set(by_id) == {
        "bpbd_pusdalops_2015",
        "bpbd_pusdalops_2017",
        "bpbd_data_kebencanaan_2015_2016",
        "bpbd_lakip_2017",
        "bpbd_pusdalops_2018",
    }

    for request_id, row in by_id.items():
        assert row["source_record_id"].strip()
        assert row["allowed_host"].strip() == "sumbarprov.go.id"
        assert queue_allowed_host(row) == "sumbarprov.go.id"
        assert official_source_url(row["official_page_url"].strip(), queue_allowed_host(row)), request_id
        assert row["output_filename"].strip().endswith(".pdf")
        assert row["purpose"].strip()

    p0 = by_id["bpbd_pusdalops_2017"]
    assert p0["priority"].strip() == "P0"
    assert p0["anchor_year"].strip() == "2017"
    assert p0["exit_gate_candidate"].strip().lower() == "yes"
    assert p0["output_filename"].strip() == "bpbd-pusdalops-sumbar-2017.pdf"
    assert p0["official_page_url"].strip() == "https://ppid.sumbarprov.go.id/home/dip"
    assert "record 8604" in p0["purpose"]

    companion_ids = {
        "bpbd_pusdalops_2015",
        "bpbd_data_kebencanaan_2015_2016",
        "bpbd_lakip_2017",
        "bpbd_pusdalops_2018",
    }
    assert all(by_id[item]["exit_gate_candidate"].strip().lower() == "no" for item in companion_ids)
    assert by_id["bpbd_pusdalops_2015"]["priority"].strip() == "P1"
    assert by_id["bpbd_data_kebencanaan_2015_2016"]["priority"].strip() == "P1"
    assert by_id["bpbd_lakip_2017"]["priority"].strip() == "P1"
    assert by_id["bpbd_pusdalops_2018"]["priority"].strip() == "P2"

    assert by_id["bpbd_data_kebencanaan_2015_2016"]["official_page_url"].strip().endswith("/2017_90.pdf")
    assert "LAKIP%20BPBD%20Prov%20Sumbar%20Tahun%202017.pdf" in by_id["bpbd_lakip_2017"]["official_page_url"]

    assert official_source_url("https://ppid.sumbarprov.go.id/home/dip", "sumbarprov.go.id")
    assert official_source_url("https://www.sumbarprov.go.id/file.pdf", "sumbarprov.go.id")
    assert not official_source_url("https://sumbarprov.go.id.evil.example/file.pdf", "sumbarprov.go.id")
    assert not official_source_url("http://ppid.sumbarprov.go.id/home/dip", "sumbarprov.go.id")

    queue_manifest = manifest["queue"]
    assert queue_manifest["request_count"] == 5
    assert queue_manifest["p0_request_id"] == "bpbd_pusdalops_2017"
    assert queue_manifest["p0_exit_gate_candidate"] is True
    assert queue_manifest["p0_active_inventory_url"] == p0["official_page_url"].strip()
    assert queue_manifest["companion_requests_may_satisfy_2017_exit_gate"] is False
    assert set(queue_manifest["companion_requests"]) == companion_ids

    migration = manifest["ppid_migration_forensics"]
    assert migration["active_inventory_url"] == "https://ppid.sumbarprov.go.id/home/dip"
    assert migration["active_information_route_template"].endswith("/home/information/<uuid>")
    assert migration["active_download_route_template"].endswith("/home/download/<uuid>")
    assert migration["indexed_api_download_wrapper_also_observed"] is True
    assert "/api/download/?id=<uuid>" in migration["indexed_api_download_route_template"]
    assert migration["legacy_2018_detail_url"].endswith("/home/details/7526-laporan-tahunan-pusdalops-pb.html")
    assert migration["legacy_2018_direct_pdf_url"].endswith("/images/2019/07/file/Laporan_Tahunan_PUSDALOPS_PB.pdf")
    assert migration["legacy_2017_download_audit_record_id"] == 8604
    assert migration["legacy_2017_download_audit_opd"] == "Badan Penanggulangan Bencana Daerah"
    assert migration["legacy_2017_download_count"] == 24
    assert migration["record_8604_to_current_uuid_mapping_recovered"] is False
    assert migration["current_detail_or_download_url_for_2017_recovered"] is False
    assert migration["raw_2017_pdf_bytes_recovered"] is False
    assert migration["m52_trigger_satisfied"] is False

    companions = manifest["companion_evidence"]
    assert companions["bpbd_data_kebencanaan_2015_2016"]["substitutes_for_2017_annual_report"] is False
    assert companions["bpbd_lakip_2017"]["substitutes_for_2017_annual_report"] is False

    result = manifest["result"]
    assert result["bpbd_acquisition_queue_materialized"] is True
    assert result["collector_generalized_without_removing_bps_wrapper"] is True
    assert result["bpbd_official_host_allowlisted"] is True
    assert result["official_companion_surfaces_added"] == 2
    assert result["ppid_active_route_shape_frozen"] is True
    assert result["legacy_2017_download_record_reconfirmed"] is True
    assert result["raw_2017_artifact_acquired"] is False
    assert result["raw_2017_checksum_frozen"] is False
    assert result["source_native_2017_extraction_authorized"] is False
    assert result["canonical_historical_impact_promotion_authorized"] is False

    qualification = manifest["qualification"]
    assert qualification["external_artifact_blocker_converted_to_executable_queue"] is True
    assert qualification["bps_default_security_behavior_preserved"] is True
    assert qualification["host_suffix_spoofing_rejected"] is True
    assert qualification["active_ppid_inventory_confirmed"] is True
    assert qualification["active_uuid_detail_and_download_routes_confirmed"] is True
    assert qualification["legacy_2018_ppid_detail_and_direct_pdf_confirmed"] is True
    assert qualification["legacy_2017_download_audit_record_confirmed"] is True
    assert qualification["record_8604_to_current_uuid_mapping_recovered"] is False
    assert qualification["official_2017_lakip_companion_available"] is True
    assert qualification["official_2015_2016_data_companion_available"] is True
    assert qualification["companions_do_not_replace_p0_exit_gate"] is True
    assert qualification["raw_official_artifact_still_required"] is True
    assert qualification["promotion_gate_fail_closed"] is True

    assert m50["result"]["official_2017_raw_artifact_acquired"] is False
    assert m50["qualification"]["raw_official_artifact_required_for_source_native_ingestion"] is True

    return {
        "schema": "ranah-observatory/milestone51-bpbd-raw-artifact-acquisition-lane-audit/v3",
        "milestone": 51,
        "queue_rows": len(rows),
        "companion_rows": len(companion_ids),
        "p0_exit_gate_request": "bpbd_pusdalops_2017",
        "allowed_host": "sumbarprov.go.id",
        "legacy_bps_default_host": DEFAULT_ALLOWED_HOST,
        "active_ppid_inventory": migration["active_inventory_url"],
        "legacy_2017_download_audit_record_id": migration["legacy_2017_download_audit_record_id"],
        "record_8604_to_current_uuid_mapping_recovered": False,
        "raw_2017_artifact_acquired": False,
        "m52_trigger_satisfied": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M51 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
