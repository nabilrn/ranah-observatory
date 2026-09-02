#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone59_bpbd_hazard_totals_2024_acquisition.json"
FINAL = ROOT / "data/manifests/milestone59_bpbd_hazard_totals_2024_final.json"
SOURCE = ROOT / "data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-source-native.csv"
CANONICAL = ROOT / "data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-canonical.csv"
MONTHLY = ROOT / "data/processed/bpbd/disaster_context_2024/bpbd-monthly-events-by-hazard-2024.csv"
CATALOG = ROOT / "catalog/public-datasets.csv"

EXPECTED_TOTALS = {
    "flood": 253,
    "extreme_weather": 587,
    "volcanic_eruption": 9,
    "tidal_wave_and_coastal_erosion": 14,
    "forest_and_land_fire": 25,
    "drought": 2,
    "landslide": 285,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, object]:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))

    assert acq["schema"] == "ranah-observatory/milestone59-bpbd-hazard-totals-2024-acquisition/v1"
    assert acq["milestone"] == 59 and acq["depends_on"] == [58]
    assert acq["source"]["package_id"] == "fd77b7eb-a2e4-4ee7-8a6a-78df1b15e4c6"
    assert acq["source"]["resource_id"] == "43fc1b1b-bd4e-4a8e-887d-754029f0b074"
    assert acq["source"]["producer"] == "BPBD Provinsi Sumatera Barat"
    assert acq["source"]["source_data"] == "Pusdalop BPBD Sumatera Barat"
    assert acq["source"]["datastore_active"] is True
    assert acq["source_native"]["record_count"] == 8
    assert acq["source_native"]["field_names"] == ["Jenis Bencana", "Jumlah Kejadian"]
    assert acq["source_native"]["missing_values_inferred"] is False
    assert sha256(SOURCE) == acq["output"]["sha256"]

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    total_rows = [r for r in source_rows if r["Jenis Bencana"] == "Total"]
    hazard_rows = [r for r in source_rows if r not in total_rows]
    assert len(total_rows) == 1 and len(hazard_rows) == 7
    assert int(total_rows[0]["Jumlah Kejadian"]) == 1175
    assert sum(int(r["Jumlah Kejadian"]) for r in hazard_rows) == 1175

    assert final["schema"] == "ranah-observatory/milestone59-bpbd-hazard-totals-2024-final/v1"
    assert final["lineage"]["aggregate_producer"] == "BPBD Provinsi Sumatera Barat"
    assert final["lineage"]["aggregate_source_data"] == "Pusdalop BPBD Sumatera Barat"
    assert final["lineage"]["producer_and_source_data_match"] is True

    result = final["result"]
    assert result["hazard_count"] == 7
    assert result["canonical_row_count"] == 7
    assert result["source_total_events"] == 1175
    assert result["source_hazard_sum_events"] == 1175
    assert result["monthly_hazard_sum_events"] == 1175
    assert result["exact_hazard_total_match_count"] == 7
    assert result["all_hazard_totals_match_monthly_table"] is True
    assert result["source_total_reconciles"] is True
    assert result["same_producer_source_data_reconciliation"] is True
    assert result["same_family_hazard_id_mapping_reused"] is True
    assert result["dashboard_hazard_filter_ready"] is True
    assert result["missing_values_imputed"] is False
    assert result["cross_source_equivalence_with_bnpb_authorized"] is False
    assert result["cross_source_taxonomy_harmonization_authorized"] is False
    assert final["hazard_totals"] == EXPECTED_TOTALS
    assert sha256(CANONICAL) == final["output"]["sha256"]

    with CANONICAL.open(newline="", encoding="utf-8") as handle:
        canonical = list(csv.DictReader(handle))
    assert len(canonical) == 7
    assert {r["hazard_id"] for r in canonical} == set(EXPECTED_TOTALS)
    assert {r["hazard_id"]: int(r["event_count"]) for r in canonical} == EXPECTED_TOTALS
    assert all(r["claim_type"] == "observed_data" for r in canonical)
    assert all(r["source_resource_id"] == "43fc1b1b-bd4e-4a8e-887d-754029f0b074" for r in canonical)

    monthly_sums: dict[str, int] = defaultdict(int)
    monthly_rows = 0
    with MONTHLY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            monthly_rows += 1
            raw = row["value_numeric"].strip()
            if raw:
                monthly_sums[row["hazard_id"]] += int(float(raw))
    assert monthly_rows == 84
    assert dict(monthly_sums) == EXPECTED_TOTALS

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        catalog_rows = list(csv.DictReader(handle))
    entries = [r for r in catalog_rows if r["id"] == "bpbd-disaster-hazard-totals-2024"]
    assert len(entries) == 1
    assert entries[0]["source_path"] == "data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-canonical.csv"

    return {
        "milestone": 59,
        "hazard_count": 7,
        "source_total_events": 1175,
        "exact_hazard_total_match_count": 7,
        "dashboard_hazard_filter_ready": True,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M59 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
