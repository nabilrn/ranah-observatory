#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data/manifests/milestone57_bpbd_events_2023.json"
SOURCE_CSV = ROOT / "data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-source-native.csv"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
PRIOR_CONTEXT = ROOT / "data/processed/bpbd/disaster_context_2024/materialization.json"
OUT = ROOT / "data/processed/bpbd/disaster_events_2023/bpbd-disaster-events-2023-canonical-long.csv"
FINAL_MANIFEST = ROOT / "data/manifests/milestone57_bpbd_events_2023_final.json"

HAZARD_COLUMNS = [
    "Abrasi pantai", "Angin kencang", "Banjir", "Banjir Bandang",
    "Erupsi Gunung Api", "Gelombang Pasang", "Gempa Bumi",
    "Kebakaran Hutan & Lahan", "Kekeringan", "Longsor",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geography_map() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    with GEOGRAPHIES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["parent_geography_id"] != "idn.13" or row["status"] != "current":
                continue
            level = row["geography_level"]
            if level not in {"regency", "city"}:
                continue
            prefix = "Kabupaten" if level == "regency" else "Kota"
            result[f"{prefix} {row['canonical_name'].strip()}"] = (
                row["geography_id"].strip(), row["canonical_name"].strip()
            )
    if len(result) != 19:
        raise RuntimeError(f"expected 19 current Sumbar geographies, found {len(result)}")
    return result


def main() -> int:
    acquisition = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if acquisition.get("schema") != "ranah-observatory/milestone57-bpbd-events-2023/v1":
        raise RuntimeError("unsupported M57 acquisition manifest")
    if sha256(SOURCE_CSV) != acquisition["outputs"]["observations"]["sha256"]:
        raise RuntimeError("M57 source-native checksum drift")

    aliases = geography_map()
    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        source_rows = list(csv.DictReader(handle))
    district_rows = [r for r in source_rows if r["Kabupaten/Kota"].strip() != "Jumlah"]
    total_rows = [r for r in source_rows if r["Kabupaten/Kota"].strip() == "Jumlah"]
    if len(district_rows) != 19 or len(total_rows) != 1:
        raise RuntimeError("M57 source geography footprint drift")

    mapped_ids: set[str] = set()
    out_rows: list[dict[str, object]] = []
    for row in district_rows:
        source_name = row["Kabupaten/Kota"].strip()
        if source_name not in aliases:
            raise RuntimeError(f"unmapped M57 geography: {source_name}")
        geography_id, canonical_name = aliases[source_name]
        if geography_id in mapped_ids:
            raise RuntimeError(f"duplicate M57 geography id: {geography_id}")
        mapped_ids.add(geography_id)
        row_sum = 0
        for hazard in HAZARD_COLUMNS:
            value = int(float(row[hazard]))
            if value < 0:
                raise RuntimeError("negative event count")
            row_sum += value
            out_rows.append({
                "year": 2023,
                "geography_id": geography_id,
                "geography_name": canonical_name,
                "source_geography_name": source_name,
                "hazard_source_label": hazard,
                "event_count": value,
                "unit": "count",
                "claim_type": "observed_data",
                "source_family": "BPBD/Pusdalop Sumatera Barat Satu Data",
                "source_resource_id": acquisition["source"]["resource_id"],
            })
        if row_sum != int(float(row["Jumlah"])):
            raise RuntimeError(f"M57 row total mismatch: {source_name}")

    if len(mapped_ids) != 19 or len(out_rows) != 190:
        raise RuntimeError("M57 canonical footprint drift")

    source_total = acquisition["source_native"]["province_total_events"]
    canonical_total = sum(int(row["event_count"]) for row in out_rows)
    if canonical_total != source_total:
        raise RuntimeError(f"M57 canonical total mismatch: {canonical_total} != {source_total}")

    prior = json.loads(PRIOR_CONTEXT.read_text(encoding="utf-8"))
    social_total = prior["result_2023"]["social_totals"]["disaster_events_reported"]
    if social_total != source_total:
        raise RuntimeError(f"M57 same-producer event total mismatch: {social_total} != {source_total}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(out_rows[0].keys())
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    final = {
        "schema": "ranah-observatory/milestone57-bpbd-events-2023-final/v1",
        "milestone": 57,
        "depends_on": [54, 56],
        "source_manifest": {
            "path": SOURCE_MANIFEST.relative_to(ROOT).as_posix(),
            "sha256": sha256(SOURCE_MANIFEST),
        },
        "geography_registry": {
            "path": GEOGRAPHIES.relative_to(ROOT).as_posix(),
            "sha256": sha256(GEOGRAPHIES),
        },
        "result": {
            "district_count": 19,
            "hazard_count": len(HAZARD_COLUMNS),
            "canonical_row_count": len(out_rows),
            "province_total_events": source_total,
            "same_producer_social_event_total": social_total,
            "same_producer_total_reconciles": True,
            "geography_mapping_complete": True,
            "missing_values_inferred": False,
            "hazard_taxonomy_harmonized": False,
            "dashboard_filter_ready": True,
            "cross_source_equivalence_with_dibi_2022_authorized": False,
            "cross_source_equivalence_with_bnpb_authorized": False,
        },
        "hazard_source_labels": HAZARD_COLUMNS,
        "output": {
            "path": OUT.relative_to(ROOT).as_posix(),
            "sha256": sha256(OUT),
        },
    }
    FINAL_MANIFEST.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
