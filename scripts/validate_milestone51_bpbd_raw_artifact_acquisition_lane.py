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

    assert manifest["milestone"] == 51
    assert manifest["depends_on"] == [50]
    assert DEFAULT_ALLOWED_HOST == "bps.go.id"
    assert official_bps_url("https://sumbar.bps.go.id/id/publication/example")
    assert not official_bps_url("https://bps.go.id.evil.example/publication")

    assert len(rows) == 3
    by_id = {row["request_id"].strip(): row for row in rows}
    assert set(by_id) == {
        "bpbd_pusdalops_2015",
        "bpbd_pusdalops_2017",
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

    assert by_id["bpbd_pusdalops_2015"]["priority"].strip() == "P1"
    assert by_id["bpbd_pusdalops_2018"]["priority"].strip() == "P2"

    assert official_source_url("https://bpbd.sumbarprov.go.id/ppid", "sumbarprov.go.id")
    assert official_source_url("https://www.sumbarprov.go.id/file.pdf", "sumbarprov.go.id")
    assert not official_source_url("https://sumbarprov.go.id.evil.example/file.pdf", "sumbarprov.go.id")
    assert not official_source_url("http://bpbd.sumbarprov.go.id/ppid", "sumbarprov.go.id")

    result = manifest["result"]
    assert result["bpbd_acquisition_queue_materialized"] is True
    assert result["collector_generalized_without_removing_bps_wrapper"] is True
    assert result["bpbd_official_host_allowlisted"] is True
    assert result["raw_2017_artifact_acquired"] is False
    assert result["raw_2017_checksum_frozen"] is False
    assert result["source_native_2017_extraction_authorized"] is False
    assert result["canonical_historical_impact_promotion_authorized"] is False

    qualification = manifest["qualification"]
    assert qualification["external_artifact_blocker_converted_to_executable_queue"] is True
    assert qualification["bps_default_security_behavior_preserved"] is True
    assert qualification["host_suffix_spoofing_rejected"] is True
    assert qualification["raw_official_artifact_still_required"] is True
    assert qualification["promotion_gate_fail_closed"] is True

    assert m50["result"]["official_2017_raw_artifact_acquired"] is False
    assert m50["qualification"]["raw_official_artifact_required_for_source_native_ingestion"] is True

    return {
        "schema": "ranah-observatory/milestone51-bpbd-raw-artifact-acquisition-lane-audit/v1",
        "milestone": 51,
        "queue_rows": len(rows),
        "p0_exit_gate_request": "bpbd_pusdalops_2017",
        "allowed_host": "sumbarprov.go.id",
        "legacy_bps_default_host": DEFAULT_ALLOWED_HOST,
        "raw_2017_artifact_acquired": False,
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
