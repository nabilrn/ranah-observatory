#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone58_bpbd_events_2024_acquisition.json"
FINAL = ROOT / "data/manifests/milestone58_bpbd_events_2024_final.json"
SOURCE = ROOT / "data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-source-native.csv"
CANONICAL = ROOT / "data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-canonical-district.csv"
PRIOR = ROOT / "data/processed/bpbd/disaster_context_2024/materialization.json"
CATALOG = ROOT / "catalog/public-datasets.csv"
EXPECTED_CODES = {"1301","1302","1303","1304","1305","1306","1307","1308","1309","1310","1311","1312","1371","1372","1373","1374","1375","1376","1377"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, object]:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))

    assert acq["schema"] == "ranah-observatory/milestone58-bpbd-events-2024-acquisition/v1"
    assert acq["milestone"] == 58 and acq["depends_on"] == [57]
    assert acq["source"]["package_id"] == "24704fb3-6b59-4a67-94a3-ab585a33f303"
    assert acq["source"]["resource_id"] == "9d99b5ed-a005-4b35-880c-7e9954c9ade5"
    assert acq["source"]["organization"] == "Badan Penanggulangan Bencana Daerah"
    assert acq["source"]["datastore_active"] is True
    assert acq["source_native"]["record_count"] == 20
    assert acq["source_native"]["field_names"] == ["Kode Wilayah", "Jenis Bencana", "Jumlah Kejadian"]
    assert set(acq["source_native"]["source_codes"]) == EXPECTED_CODES | {"None"}
    assert acq["source_native"]["geography_semantics_interpreted"] is False
    assert acq["source_native"]["missing_values_inferred"] is False
    assert sha256(SOURCE) == acq["output"]["sha256"]

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    total_rows = [r for r in source_rows if r["Kode Wilayah"] == "None" and r["Jenis Bencana"] == "Total"]
    district_rows = [r for r in source_rows if r not in total_rows]
    assert len(total_rows) == 1 and len(district_rows) == 19
    assert int(total_rows[0]["Jumlah Kejadian"]) == 1175
    assert sum(int(r["Jumlah Kejadian"]) for r in district_rows) == 1166
    assert int(total_rows[0]["Jumlah Kejadian"]) - sum(int(r["Jumlah Kejadian"]) for r in district_rows) == 9
    assert {r["Kode Wilayah"] for r in district_rows} == EXPECTED_CODES
    assert all(r["Jenis Bencana"].startswith(("KABUPATEN ", "KOTA ")) for r in district_rows)

    assert final["schema"] == "ranah-observatory/milestone58-bpbd-events-2024-final/v3"
    issue = final["source_schema_issue"]
    assert issue["misleading_field"] == "Jenis Bencana"
    assert issue["observed_role"] == "source_geography_name"
    assert issue["source_header_rewritten_in_source_native_file"] is False

    disagreement = final["source_internal_disagreement"]
    assert disagreement["source_total_row_events"] == 1175
    assert disagreement["sum_of_19_district_rows"] == 1166
    assert disagreement["unallocated_difference_events"] == 9
    assert disagreement["bpbd_monthly_event_total"] == 1175
    assert disagreement["district_rows_reconcile_to_source_total"] is False
    assert disagreement["bpbd_monthly_total_reconciles_to_source_total"] is True
    assert disagreement["allocation_or_omission_explanation_available"] is False
    assert disagreement["difference_imputed_to_any_geography"] is False

    lineage = final["lineage_boundary"]
    assert lineage["district_resource_organization"] == "Badan Penanggulangan Bencana Daerah"
    assert lineage["district_resource_source_data_declared"] is False
    assert lineage["monthly_table_is_bpbd_context"] is True
    assert lineage["same_producer_asserted"] is False

    result = final["result"]
    assert result["district_count"] == 19
    assert result["canonical_row_count"] == 19
    assert result["source_total_events"] == 1175
    assert result["canonical_district_sum_events"] == 1166
    assert result["unallocated_difference_events"] == 9
    assert result["bpbd_monthly_event_total"] == 1175
    assert result["exact_code_name_pair_mapping_count"] == 19
    assert result["geography_mapping_complete"] is True
    assert result["dashboard_district_filter_ready"] is True
    assert result["province_total_from_district_rows_authorized"] is False
    assert result["hazard_dimension_present_in_this_resource"] is False
    assert result["cross_source_equivalence_with_bnpb_authorized"] is False
    assert result["cross_year_taxonomy_harmonization_authorized"] is False
    assert result["missing_values_imputed"] is False
    assert sha256(CANONICAL) == final["output"]["sha256"]

    with CANONICAL.open(newline="", encoding="utf-8") as handle:
        canonical = list(csv.DictReader(handle))
    assert len(canonical) == 19
    assert {r["source_geography_code"] for r in canonical} == EXPECTED_CODES
    assert len({r["geography_id"] for r in canonical}) == 19
    assert sum(int(r["event_count"]) for r in canonical) == 1166
    assert all(r["claim_type"] == "observed_data" for r in canonical)
    assert all(r["source_family"] == "BPBD Sumatera Barat Satu Data" for r in canonical)
    assert all(r["source_resource_id"] == "9d99b5ed-a005-4b35-880c-7e9954c9ade5" for r in canonical)

    assert prior["result_2024"]["monthly_event_total"] == 1175

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        catalog_rows = list(csv.DictReader(handle))
    entries = [r for r in catalog_rows if r["id"] == "bpbd-disaster-events-district-2024"]
    assert len(entries) == 1
    assert entries[0]["source_path"] == "data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-canonical-district.csv"

    return {
        "milestone": 58,
        "district_count": 19,
        "source_total_events": 1175,
        "mapped_district_events": 1166,
        "unallocated_difference_events": 9,
        "dashboard_district_filter_ready": True,
        "complete": True,
    }


def main() -> int:
    try:
        report = validate()
    except (AssertionError, OSError, ValueError, KeyError, csv.Error, json.JSONDecodeError) as exc:
        print(f"M58 validation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
