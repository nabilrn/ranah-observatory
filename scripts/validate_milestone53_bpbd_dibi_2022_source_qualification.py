#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone53_bpbd_dibi_2022_source_qualification.json"
QUEUE = ROOT / "data" / "acquisition_requests" / "bpbd_dibi_books.csv"
M51 = ROOT / "data" / "manifests" / "milestone51_bpbd_raw_artifact_acquisition_lane.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_queue(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _is_allowed_official_url(url: str, allowed_host: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    allowed = allowed_host.lower().rstrip(".")
    return host == allowed or host.endswith("." + allowed)


def validate() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    m51 = _read_json(M51)
    rows = _read_queue(QUEUE)

    assert manifest["schema"] == "ranah-observatory/milestone53-bpbd-dibi-2022-source-qualification/v1"
    assert manifest["milestone"] == 53
    assert manifest["depends_on"] == [51]
    assert "M52 remains reserved" in manifest["parallel_gate_note"]

    assert len(rows) == 1
    row = rows[0]
    assert row["request_id"] == "bpbd_dibi_2022"
    assert row["source_record_id"] == "ppid_20769_legacy_download_audit_980"
    assert row["priority"] == "P0"
    assert row["anchor_year"] == "2022"
    assert row["exit_gate_candidate"].lower() == "yes"
    assert row["allowed_host"] == "sumbarprov.go.id"
    assert row["output_filename"] == "bpbd-dibi-sumbar-2022.pdf"
    assert _is_allowed_official_url(row["official_page_url"], row["allowed_host"])
    assert _is_allowed_official_url(row["legacy_direct_pdf_url"], row["allowed_host"])
    assert "Scribd mirror" in row["purpose"]

    source = manifest["official_source"]
    assert source["official_detail_url"] == row["official_page_url"]
    assert source["official_legacy_pdf_url"] == row["legacy_direct_pdf_url"]
    assert source["legacy_download_audit_record_id"] == 980
    assert source["legacy_download_count"] == 120
    assert source["legacy_direct_pdf_fetch_status_checked_2026_09_02"] == 404
    assert source["raw_pdf_bytes_recovered"] is False
    assert source["raw_pdf_sha256_frozen"] is False

    mirror = manifest["indexed_mirror"]
    assert mirror["may_satisfy_raw_artifact_gate"] is False
    assert mirror["reported_page_count"] == 154
    assert "verification" in mirror["role"]

    targets = manifest["indexed_verification_targets"]
    province = targets["province_totals"]
    assert province["events"] == 1021
    assert province["deaths"] == 28
    assert province["missing_table_3_3"] is None
    assert province["missing_table_3_4"] == 4
    assert province["injured_or_sick"] == 456
    assert province["evacuated"] == 26265
    assert province["recorded_loss_rupiah_attachment_grand_total"] == 1136849586796

    hazards = targets["events_by_hazard_table_3_2"]
    assert sum(value for key, value in hazards.items() if key != "total") == 1021
    assert hazards["total"] == 1021
    assert hazards["angin_kencang"] == 674
    assert hazards["banjir"] == 123
    assert hazards["longsor"] == 120

    months = targets["events_by_month_table_3_9"]
    assert sum(value for key, value in months.items() if key != "total") == 1021
    assert months["total"] == 1021
    assert months["agustus"] == 110
    assert months["desember"] == 19

    disagreements = targets["district_event_count_disagreements"]
    assert len(disagreements) == 7
    assert targets["both_district_tables_sum_to"] == 1021
    assert sum(item["table_3_4"] - item["table_3_1_or_3_2"] for item in disagreements) == 0
    assert any(item["district"] == "Kabupaten Tanah Datar" and item["table_3_1_or_3_2"] == 43 and item["table_3_4"] == 45 for item in disagreements)

    dashboard = manifest["dashboard_value"]
    for key in (
        "district_by_hazard_matrix_available",
        "district_impact_table_available",
        "hazard_impact_table_available",
        "monthly_hazard_timeseries_available",
        "housing_damage_tables_available",
        "public_facility_damage_tables_available",
        "recorded_loss_available",
        "incident_history_appendix_available",
    ):
        assert dashboard[key] is True

    result = manifest["result"]
    assert result["source_family_qualified_as_high_value"] is True
    assert result["dashboard_dimensions_confirmed_by_indexed_text"] is True
    assert result["internal_table_disagreements_detected"] is True
    assert result["raw_official_artifact_acquired"] is False
    assert result["source_native_2022_materialization_authorized"] is False
    assert result["public_dataset_catalog_promotion_authorized"] is False
    assert result["canonical_cross_year_disaster_timeseries_authorized"] is False

    assert m51["ppid_migration_forensics"]["raw_2017_pdf_bytes_recovered"] is False
    assert m51["ppid_migration_forensics"]["m52_trigger_satisfied"] is False

    return {
        "schema": "ranah-observatory/milestone53-bpbd-dibi-2022-source-qualification-audit/v1",
        "milestone": 53,
        "queue_rows": len(rows),
        "events": province["events"],
        "hazard_total": hazards["total"],
        "monthly_total": months["total"],
        "district_disagreements": len(disagreements),
        "raw_artifact_acquired": False,
        "materialization_authorized": False,
        "m52_still_blocked": True,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M53 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
