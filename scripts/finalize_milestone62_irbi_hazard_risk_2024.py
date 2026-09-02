#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_acquisition.json"
SOURCE = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-source-native.csv"
GEOGRAPHIES = ROOT / "data/registries/geographies.csv"
OUT = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-canonical.csv"
FINAL = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_final.json"
EXPECTED_COVERAGE = {
    "flood": 9,
    "earthquake": 19,
    "tsunami": 7,
    "volcanic_eruption": 7,
    "forest_and_land_fire": 19,
    "landslide": 19,
    "extreme_wave_and_coastal_erosion": 7,
    "drought": 18,
    "extreme_weather": 19,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geography_map() -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    with GEOGRAPHIES.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["parent_geography_id"] != "idn.13" or row["status"] != "current":
                continue
            if row["geography_level"] not in {"regency", "city"}:
                continue
            canonical = row["canonical_name"].strip()
            source_name = canonical.upper()
            if row["geography_level"] == "city":
                source_name = f"KOTA {source_name}"
            result[source_name] = (row["geography_id"].strip(), canonical)
    if len(result) != 19:
        raise RuntimeError(f"M62 Sumbar registry footprint drift: {len(result)}")
    return result


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    if acq["schema"] != "ranah-observatory/milestone62-irbi-hazard-risk-2024-acquisition/v1":
        raise RuntimeError("unsupported M62 acquisition manifest")
    if sha256(SOURCE) != acq["output"]["sha256"]:
        raise RuntimeError("M62 source-native checksum drift")
    if acq["source_native"]["coverage_by_hazard"] != EXPECTED_COVERAGE:
        raise RuntimeError(f"M62 source coverage drift: {acq['source_native']['coverage_by_hazard']}")

    with SOURCE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 124:
        raise RuntimeError(f"M62 source row-count drift: {len(rows)}")

    mapping = geography_map()
    output: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    class_counts: dict[str, dict[str, int]] = {}
    geography_coverage: dict[str, dict[str, object]] = {
        geography_id: {"geography_name": canonical_name, "hazard_count": 0}
        for geography_id, canonical_name in mapping.values()
    }

    for row in rows:
        source_name = row["source_geography_name"].strip()
        if source_name not in mapping:
            raise RuntimeError(f"M62 unmapped geography: {source_name}")
        geography_id, canonical_name = mapping[source_name]
        hazard_id = row["irbi_hazard_id"].strip()
        key = (hazard_id, geography_id)
        if key in seen:
            raise RuntimeError(f"M62 duplicate canonical key: {key}")
        seen.add(key)
        risk_class = row["risk_class"].strip().lower()
        if risk_class not in {"tinggi", "sedang", "rendah"}:
            raise RuntimeError(f"M62 unknown risk class: {risk_class}")
        class_counts.setdefault(hazard_id, {}).setdefault(risk_class, 0)
        class_counts[hazard_id][risk_class] += 1
        geography_coverage[geography_id]["hazard_count"] = int(geography_coverage[geography_id]["hazard_count"]) + 1
        output.append({
            "year": 2024,
            "geography_id": geography_id,
            "geography_name": canonical_name,
            "irbi_hazard_id": hazard_id,
            "source_hazard_label": row["source_hazard_label"].strip(),
            "risk_score": f"{float(row['score']):.2f}",
            "risk_class": risk_class,
            "source_rank_national": int(row["source_rank"]),
            "unit": "index_points",
            "claim_type": "official_hazard_risk_index",
            "source_family": "BNPB IRBI 2024",
            "source_page": int(row["source_page"]),
        })

    coverage = {
        hazard: sum(1 for row in output if row["irbi_hazard_id"] == hazard)
        for hazard in EXPECTED_COVERAGE
    }
    if coverage != EXPECTED_COVERAGE or len(output) != 124:
        raise RuntimeError(f"M62 canonical coverage drift: {coverage}")
    if len(geography_coverage) != 19:
        raise RuntimeError(f"M62 geography summary collision: {len(geography_coverage)}")
    if sum(int(item["hazard_count"]) for item in geography_coverage.values()) != 124:
        raise RuntimeError("M62 geography summary does not reconcile to canonical rows")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    output.sort(key=lambda r: (str(r["irbi_hazard_id"]), str(r["geography_id"])))
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0].keys()))
        writer.writeheader()
        writer.writerows(output)

    absent_pairs = 19 * len(EXPECTED_COVERAGE) - len(output)
    final = {
        "schema": "ranah-observatory/milestone62-irbi-hazard-risk-2024-final/v1",
        "milestone": 62,
        "depends_on": [61],
        "source_manifest": {"path": ACQ.relative_to(ROOT).as_posix(), "sha256": sha256(ACQ)},
        "geography_registry": {"path": GEOGRAPHIES.relative_to(ROOT).as_posix(), "sha256": sha256(GEOGRAPHIES)},
        "taxonomy_boundary": {
            "identifier_namespace": "irbi_hazard_id",
            "source_labels_preserved": True,
            "cross_source_taxonomy_equivalence_authorized": False,
            "bpbd_event_taxonomy_join_authorized": False,
            "absence_means_zero_risk": False,
        },
        "coverage": {
            "possible_full_grid_pairs": 171,
            "observed_source_pairs": 124,
            "absent_source_pairs": absent_pairs,
            "coverage_by_hazard": coverage,
            "risk_class_counts_by_hazard": class_counts,
            "geography_hazard_count_by_id": geography_coverage,
        },
        "result": {
            "year": 2024,
            "hazard_count": 9,
            "current_sumbar_geography_count": 19,
            "canonical_row_count": 124,
            "geography_mapping_complete_for_observed_rows": True,
            "dashboard_hazard_risk_filter_ready": True,
            "dashboard_hazard_risk_map_ready": True,
            "absence_interpreted_as_zero": False,
            "event_frequency_equivalence_authorized": False,
            "prediction_claim_authorized": False,
            "missing_values_imputed": False,
        },
        "output": {"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OUT)},
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
