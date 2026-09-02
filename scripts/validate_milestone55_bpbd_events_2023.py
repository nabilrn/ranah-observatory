#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone55_bpbd_events_2023.json"
FINAL = ROOT / "data/manifests/milestone55_bpbd_events_2023_final.json"
SOURCE = ROOT / "data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-source-native.csv"
CANONICAL = ROOT / "data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-canonical-long.csv"
PRIOR = ROOT / "data/processed/bpbd/disaster_context_2024/materialization.json"

EXPECTED_HAZARDS = {
    "Abrasi pantai": 8,
    "Angin kencang": 562,
    "Banjir": 144,
    "Banjir Bandang": 10,
    "Erupsi Gunung Api": 44,
    "Gelombang Pasang": 1,
    "Gempa Bumi": 1,
    "Kebakaran Hutan & Lahan": 76,
    "Kekeringan": 19,
    "Longsor": 166,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))

    assert acq["schema"] == "ranah-observatory/milestone55-bpbd-events-2023/v2"
    assert acq["milestone"] == 55
    assert acq["source"]["package_id"] == "e953d109-88d4-4be7-a0ad-ffc720b3c4a4"
    assert acq["source"]["resource_id"] == "e5d974eb-95a0-4570-93d1-9ca45c9fb77b"
    assert acq["source"]["datastore_active"] is True
    native = acq["source_native"]
    assert native["row_count"] == 20
    assert native["district_row_count"] == 19
    assert native["total_row_count"] == 1
    assert native["province_total_events"] == 1031
    assert native["district_sum_events"] == 1031
    assert native["hazard_total_sum_events"] == 1031
    assert native["hazard_totals"] == EXPECTED_HAZARDS
    assert native["missing_values_inferred"] is False
    assert native["zero_values_reinterpreted"] is False
    assert native["hazard_taxonomy_harmonized"] is False
    assert sha256(SOURCE) == acq["outputs"]["observations"]["sha256"]

    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        source_rows = list(csv.DictReader(handle))
    district_rows = [r for r in source_rows if r["Kabupaten/Kota"] != "Jumlah"]
    total_rows = [r for r in source_rows if r["Kabupaten/Kota"] == "Jumlah"]
    assert len(district_rows) == 19
    assert len(total_rows) == 1
    assert sum(int(float(r["Jumlah"])) for r in district_rows) == 1031
    assert int(float(total_rows[0]["Jumlah"])) == 1031

    assert final["schema"] == "ranah-observatory/milestone55-bpbd-events-2023-final/v1"
    result = final["result"]
    assert result["district_count"] == 19
    assert result["hazard_count"] == 10
    assert result["canonical_row_count"] == 190
    assert result["province_total_events"] == 1031
    assert result["same_producer_social_event_total"] == 1031
    assert result["same_producer_total_reconciles"] is True
    assert result["geography_mapping_complete"] is True
    assert result["missing_values_inferred"] is False
    assert result["hazard_taxonomy_harmonized"] is False
    assert result["dashboard_filter_ready"] is True
    assert result["cross_source_equivalence_with_dibi_2022_authorized"] is False
    assert result["cross_source_equivalence_with_bnpb_authorized"] is False
    assert final["hazard_source_labels"] == list(EXPECTED_HAZARDS)
    assert sha256(CANONICAL) == final["output"]["sha256"]

    with CANONICAL.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 190
    assert len({r["geography_id"] for r in rows}) == 19
    assert len({r["hazard_source_label"] for r in rows}) == 10
    assert sum(int(r["event_count"]) for r in rows) == 1031
    assert all(r["claim_type"] == "observed_data" for r in rows)
    assert all(r["source_resource_id"] == "e5d974eb-95a0-4570-93d1-9ca45c9fb77b" for r in rows)

    assert prior["result_2023"]["social_totals"]["disaster_events_reported"] == 1031

    return {
        "milestone": 55,
        "district_count": 19,
        "hazard_count": 10,
        "canonical_row_count": 190,
        "province_total_events": 1031,
        "same_producer_total_reconciles": True,
        "dashboard_filter_ready": True,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M55 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
