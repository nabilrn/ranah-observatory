#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone59_bpbd_hazard_totals_2024_acquisition.json"
SOURCE = ROOT / "data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-source-native.csv"
MONTHLY = ROOT / "data/processed/bpbd/disaster_context_2024/bpbd-monthly-events-by-hazard-2024.csv"
CONTEXT_MANIFEST = ROOT / "data/manifests/sumbar_bpbd_priority_context.json"
OUT = ROOT / "data/processed/bpbd/disaster_events_2024_hazard_totals/bpbd-disaster-events-2024-hazard-totals-canonical.csv"
FINAL = ROOT / "data/manifests/milestone59_bpbd_hazard_totals_2024_final.json"

HAZARD_MAP = {
    "Banjir": "flood",
    "Cuaca ekstrem": "extreme_weather",
    "Erupsi Gunung Api": "volcanic_eruption",
    "Gelombang Pasang dan abrasi": "tidal_wave_and_coastal_erosion",
    "Kebakaran Hutan dan Lahan": "forest_and_land_fire",
    "Kekeringan": "drought",
    "Tanah Longsor": "landslide",
}
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


def monthly_lineage() -> dict:
    manifest = json.loads(CONTEXT_MANIFEST.read_text(encoding="utf-8"))
    matches = [p for p in manifest["packages"] if p.get("role") == "monthly_events" and p.get("year") == 2024]
    if len(matches) != 1:
        raise RuntimeError(f"M59 monthly lineage footprint drift: {len(matches)}")
    return matches[0]


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    if acq["schema"] != "ranah-observatory/milestone59-bpbd-hazard-totals-2024-acquisition/v1":
        raise RuntimeError("unsupported M59 acquisition manifest")
    if sha256(SOURCE) != acq["output"]["sha256"]:
        raise RuntimeError("M59 source-native checksum drift")

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    total_rows = [r for r in source_rows if r["Jenis Bencana"].strip() == "Total"]
    hazard_rows = [r for r in source_rows if r not in total_rows]
    if len(total_rows) != 1 or len(hazard_rows) != 7:
        raise RuntimeError(f"M59 source footprint drift: hazards={len(hazard_rows)} total={len(total_rows)}")

    source_total = int(total_rows[0]["Jumlah Kejadian"])
    if source_total != 1175:
        raise RuntimeError(f"M59 source total drift: {source_total}")

    seen_labels = {r["Jenis Bencana"].strip() for r in hazard_rows}
    if seen_labels != set(HAZARD_MAP):
        raise RuntimeError(f"M59 hazard labels drift: {sorted(seen_labels)}")

    source_by_id: dict[str, int] = {}
    output_rows: list[dict[str, object]] = []
    for row in hazard_rows:
        label = row["Jenis Bencana"].strip()
        hazard_id = HAZARD_MAP[label]
        count = int(row["Jumlah Kejadian"])
        source_by_id[hazard_id] = count
        output_rows.append({
            "year": 2024,
            "hazard_id": hazard_id,
            "source_hazard_label": label,
            "event_count": count,
            "unit": "count",
            "claim_type": "observed_data",
            "source_family": "BPBD/Pusdalops Sumatera Barat Satu Data",
            "source_resource_id": acq["source"]["resource_id"],
        })

    if source_by_id != EXPECTED_TOTALS or sum(source_by_id.values()) != source_total:
        raise RuntimeError(f"M59 source hazard totals drift: {source_by_id}")

    monthly_sums: dict[str, int] = defaultdict(int)
    monthly_row_count = 0
    with MONTHLY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            monthly_row_count += 1
            raw = row["value_numeric"].strip()
            if raw:
                monthly_sums[row["hazard_id"]] += int(float(raw))
    if monthly_row_count != 84:
        raise RuntimeError(f"M59 monthly row-count drift: {monthly_row_count}")
    if dict(monthly_sums) != EXPECTED_TOTALS:
        raise RuntimeError(f"M59 monthly hazard totals drift: {dict(monthly_sums)}")

    monthly_source = monthly_lineage()
    if acq["source"]["producer"] != "BPBD Provinsi Sumatera Barat" or acq["source"]["source_data"] != "Pusdalop BPBD Sumatera Barat":
        raise RuntimeError("M59 aggregate source lineage drift")
    if monthly_source["producer"] != acq["source"]["producer"] or monthly_source["source_data"] != acq["source"]["source_data"]:
        raise RuntimeError("M59 aggregate/monthly source lineage mismatch")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    final = {
        "schema": "ranah-observatory/milestone59-bpbd-hazard-totals-2024-final/v1",
        "milestone": 59,
        "depends_on": [58],
        "source_manifest": {"path": ACQ.relative_to(ROOT).as_posix(), "sha256": sha256(ACQ)},
        "monthly_context": {
            "path": MONTHLY.relative_to(ROOT).as_posix(),
            "sha256": sha256(MONTHLY),
            "source_manifest": CONTEXT_MANIFEST.relative_to(ROOT).as_posix(),
            "monthly_source_resource_id": monthly_source["resource_id"],
        },
        "lineage": {
            "aggregate_producer": acq["source"]["producer"],
            "aggregate_source_data": acq["source"]["source_data"],
            "monthly_producer": monthly_source["producer"],
            "monthly_source_data": monthly_source["source_data"],
            "producer_and_source_data_match": True,
        },
        "result": {
            "hazard_count": 7,
            "canonical_row_count": 7,
            "source_total_events": source_total,
            "source_hazard_sum_events": sum(source_by_id.values()),
            "monthly_hazard_sum_events": sum(monthly_sums.values()),
            "exact_hazard_total_match_count": 7,
            "all_hazard_totals_match_monthly_table": True,
            "source_total_reconciles": True,
            "same_producer_source_data_reconciliation": True,
            "same_family_hazard_id_mapping_reused": True,
            "dashboard_hazard_filter_ready": True,
            "missing_values_imputed": False,
            "cross_source_equivalence_with_bnpb_authorized": False,
            "cross_source_taxonomy_harmonization_authorized": False,
        },
        "hazard_totals": source_by_id,
        "output": {"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OUT)},
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
