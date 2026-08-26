#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "milestone47_bnpb_impact_overlap_eligibility.json"
REGISTRY = ROOT / "data" / "registries" / "bnpb_impact_overlap_candidates.csv"
M43 = ROOT / "data" / "manifests" / "milestone43_bnpb_historical_semantics_geography_gate.json"
M46 = ROOT / "data" / "manifests" / "milestone46_total_events_panel_integration.json"
DISASTER_SOURCES = ROOT / "data" / "registries" / "disaster_sources.csv"

EXPECTED_RESOURCES = {
    "meninggal": "b2fa5c46-9a07-4d30-a3bd-57e143e775f1",
    "hilang": "a19366cf-0ac4-45d1-bc6e-89a020ab45a1",
    "terluka": "ce67795b-57e4-4c84-8c2a-3bf03828ff0d",
    "menderita": "7f9e5218-bbba-4916-a2b8-13cf1764dc96",
    "mengungsi": "d7b61b56-43d5-4dcc-8d7b-45c993e1bdb0",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def validate() -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    rows = _read_csv(REGISTRY)
    m43 = _read_json(M43)
    m46 = _read_json(M46)
    disaster_sources = _read_csv(DISASTER_SOURCES)

    assert manifest["milestone"] == 47
    assert manifest["depends_on"] == [43, 44, 45, 46]
    assert manifest["archive_contract"]["candidate_overlap_years"] == [2010, 2017]
    assert manifest["archive_contract"]["missing_rows_zero_filled"] is False

    assert len(rows) == 5
    by_metric = {row["archive_metric"]: row for row in rows}
    assert set(by_metric) == set(EXPECTED_RESOURCES)
    for metric, resource_id in EXPECTED_RESOURCES.items():
        row = by_metric[metric]
        assert row["resource_id"] == resource_id
        assert row["current_grain"] == "national_by_disaster_type"
        assert row["current_key"] == "JENIS BENCANA"
        assert row["temporal_scope"] == "2010-2024"
        assert row["district_overlap_eligible"] == "false"
        assert row["semantic_state"]

    result = manifest["result"]
    assert result["candidate_metric_count"] == 5
    assert result["district_overlap_eligible_metric_count"] == 0
    assert result["district_overlap_eligible_metrics"] == []
    assert result["blocked_metric_count"] == 5
    assert result["national_hazard_totals_may_be_joined_to_district_archive"] is False
    assert result["district_values_may_be_allocated_from_national_hazard_totals"] is False
    assert result["menderita_may_be_silently_relabelled_terdampak"] is False
    assert result["canonical_district_impact_promotion_authorized"] is False

    qualification = manifest["qualification"]
    assert qualification["official_retrospective_resources_identified"] is True
    assert qualification["same_grain_overlap_counterpart_found"] is False
    assert qualification["value_level_reconciliation_performed"] is False
    assert qualification["promotion_gate_fail_closed"] is True

    assert m43["qualification"]["canonical_historical_panel_promotion_authorized"] is False
    assert m46["integration_success"] is True
    assert m46["added_indicator_id"] == "total_disaster_events"

    affected_2024 = [
        row for row in disaster_sources
        if row.get("source_record_id") == "bnpb_affected_by_type_kab_2024"
    ]
    assert len(affected_2024) == 1
    assert affected_2024[0]["resource_id"] == "89eb9dac-a891-477e-b264-2265f72f4e56"
    assert affected_2024[0]["geography_grain"] == "kabupaten_kota"
    assert affected_2024[0]["temporal_scope"] == "2024"

    return {
        "schema": "ranah-observatory/milestone47-bnpb-impact-overlap-eligibility-audit/v1",
        "milestone": 47,
        "candidate_metric_count": len(rows),
        "district_overlap_eligible_metric_count": 0,
        "same_grain_overlap_counterpart_found": False,
        "canonical_district_impact_promotion_authorized": False,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M47 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
