#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone58_bpbd_events_2024_acquisition.json"
SOURCE = ROOT / "data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-source-native.csv"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
PRIOR = ROOT / "data/processed/bpbd/disaster_context_2024/materialization.json"
OUT = ROOT / "data/processed/bpbd/disaster_events_2024/bpbd-disaster-events-2024-canonical-district.csv"
FINAL = ROOT / "data/manifests/milestone58_bpbd_events_2024_final.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_by_code() -> dict[str, tuple[str, str, str]]:
    result: dict[str, tuple[str, str, str]] = {}
    with GEOGRAPHIES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["parent_geography_id"] != "idn.13" or row["status"] != "current":
                continue
            if row["geography_level"] not in {"regency", "city"}:
                continue
            code = row["bps_code"].strip()
            prefix = "KABUPATEN" if row["geography_level"] == "regency" else "KOTA"
            expected_source_name = f"{prefix} {row['canonical_name'].strip().upper()}"
            result[code] = (row["geography_id"].strip(), row["canonical_name"].strip(), expected_source_name)
    if len(result) != 19:
        raise RuntimeError(f"M58 current Sumbar registry footprint drift: {len(result)}")
    return result


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    if acq["schema"] != "ranah-observatory/milestone58-bpbd-events-2024-acquisition/v1":
        raise RuntimeError("unsupported M58 acquisition manifest")
    if sha256(SOURCE) != acq["output"]["sha256"]:
        raise RuntimeError("M58 source-native checksum drift")

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    total_rows = [r for r in rows if r["Kode Wilayah"].strip() == "None" and r["Jenis Bencana"].strip() == "Total"]
    district_rows = [r for r in rows if r not in total_rows]
    if len(total_rows) != 1 or len(district_rows) != 19:
        raise RuntimeError(f"M58 source footprint drift: districts={len(district_rows)} total={len(total_rows)}")

    source_total = int(float(total_rows[0]["Jumlah Kejadian"]))
    district_sum = sum(int(float(r["Jumlah Kejadian"])) for r in district_rows)
    allocation_gap = source_total - district_sum
    if source_total != 1175 or district_sum != 1166 or allocation_gap != 9:
        raise RuntimeError(
            f"M58 frozen district allocation footprint drift: source={source_total} sum={district_sum} gap={allocation_gap}"
        )

    registry = canonical_by_code()
    seen: set[str] = set()
    output_rows: list[dict[str, object]] = []
    for row in district_rows:
        code = row["Kode Wilayah"].strip()
        source_name = row["Jenis Bencana"].strip()
        if code not in registry:
            raise RuntimeError(f"M58 unmapped source code: {code}")
        geography_id, canonical_name, expected_source_name = registry[code]
        if source_name != expected_source_name:
            raise RuntimeError(f"M58 code/name pair mismatch: {code} {source_name!r} != {expected_source_name!r}")
        if geography_id in seen:
            raise RuntimeError(f"M58 duplicate geography: {geography_id}")
        seen.add(geography_id)
        output_rows.append({
            "year": 2024,
            "geography_id": geography_id,
            "geography_name": canonical_name,
            "source_geography_code": code,
            "source_geography_name": source_name,
            "event_count": int(float(row["Jumlah Kejadian"])),
            "unit": "count",
            "claim_type": "observed_data",
            "source_family": "BPBD/Pusdalops Sumatera Barat Satu Data",
            "source_resource_id": acq["source"]["resource_id"],
        })

    canonical_sum = sum(int(r["event_count"]) for r in output_rows)
    if len(seen) != 19 or canonical_sum != district_sum:
        raise RuntimeError("M58 canonical footprint or district-sum drift")

    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    monthly_total = prior["result_2024"]["monthly_event_total"]
    if monthly_total != source_total:
        raise RuntimeError(f"M58 same-producer monthly total drift: {monthly_total} != {source_total}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    final = {
        "schema": "ranah-observatory/milestone58-bpbd-events-2024-final/v2",
        "milestone": 58,
        "depends_on": [57],
        "source_manifest": {"path": ACQ.relative_to(ROOT).as_posix(), "sha256": sha256(ACQ)},
        "geography_registry": {"path": GEOGRAPHIES.relative_to(ROOT).as_posix(), "sha256": sha256(GEOGRAPHIES)},
        "source_schema_issue": {
            "misleading_field": "Jenis Bencana",
            "observed_role": "source_geography_name",
            "evidence": "all 19 non-total values are kabupaten/kota names and each Kode Wilayah/name pair exactly matches the current Sumatera Barat BPS geography registry",
            "source_header_rewritten_in_source_native_file": False,
        },
        "source_internal_disagreement": {
            "source_total_row_events": source_total,
            "sum_of_19_district_rows": district_sum,
            "unallocated_difference_events": allocation_gap,
            "same_producer_monthly_event_total": monthly_total,
            "district_rows_reconcile_to_source_total": False,
            "monthly_total_reconciles_to_source_total": True,
            "allocation_or_omission_explanation_available": False,
            "difference_imputed_to_any_geography": False,
        },
        "result": {
            "district_count": 19,
            "canonical_row_count": 19,
            "source_total_events": source_total,
            "canonical_district_sum_events": canonical_sum,
            "unallocated_difference_events": allocation_gap,
            "same_producer_monthly_event_total": monthly_total,
            "exact_code_name_pair_mapping_count": 19,
            "geography_mapping_complete": True,
            "dashboard_district_filter_ready": True,
            "province_total_from_district_rows_authorized": False,
            "hazard_dimension_present_in_this_resource": False,
            "cross_source_equivalence_with_bnpb_authorized": False,
            "cross_year_taxonomy_harmonization_authorized": False,
            "missing_values_imputed": False,
        },
        "output": {"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OUT)},
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
