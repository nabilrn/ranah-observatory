#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_acquisition.json"
FINAL = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_final.json"
SOURCE = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-source-native.csv"
CANONICAL = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-canonical.csv"
CATALOG = ROOT / "catalog/public-datasets.csv"
CATALOG_ID = "bnpb-irbi-hazard-risk-sumbar-2024"
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(FINAL.read_text(encoding="utf-8"))

    require(acq["schema"] == "ranah-observatory/milestone62-irbi-hazard-risk-2024-acquisition/v1", "M62 acquisition schema drift")
    require(final["schema"] == "ranah-observatory/milestone62-irbi-hazard-risk-2024-final/v1", "M62 final schema drift")
    require(acq["output"]["sha256"] == sha256(SOURCE), "M62 source-native checksum drift")
    require(final["output"]["sha256"] == sha256(CANONICAL), "M62 canonical checksum drift")
    require(final["source_manifest"]["sha256"] == sha256(ACQ), "M62 source manifest checksum drift")

    native = acq["source_native"]
    require(native["hazard_count"] == 9, "M62 source hazard count drift")
    require(native["record_count"] == 124, "M62 source row count drift")
    require(native["coverage_by_hazard"] == EXPECTED_COVERAGE, "M62 source coverage drift")
    require(native["pages_scanned_count"] == 136, "M62 source page-scan footprint drift")
    require(native["absence_interpreted_as_zero"] is False, "M62 absence must not become zero")
    require(native["cross_source_taxonomy_equivalence_authorized"] is False, "M62 cross-source taxonomy equivalence must remain blocked")
    require(native["missing_values_inferred"] is False, "M62 must not infer missing rows")

    with CANONICAL.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == 124, "M62 canonical row count drift")
    require(len({(row["irbi_hazard_id"], row["geography_id"]) for row in rows}) == 124, "M62 duplicate canonical hazard/geography keys")
    require(len({row["irbi_hazard_id"] for row in rows}) == 9, "M62 canonical hazard footprint drift")
    require(len({row["geography_id"] for row in rows}) == 19, "M62 canonical geography union drift")
    require({row["risk_class"] for row in rows} <= {"tinggi", "sedang", "rendah"}, "M62 unknown risk class")
    require(all(row["year"] == "2024" for row in rows), "M62 year drift")
    require(all(row["claim_type"] == "official_hazard_risk_index" for row in rows), "M62 claim type drift")
    require(all(row["source_family"] == "BNPB IRBI 2024" for row in rows), "M62 source family drift")

    coverage = final["coverage"]
    require(coverage["possible_full_grid_pairs"] == 171, "M62 possible-grid count drift")
    require(coverage["observed_source_pairs"] == 124, "M62 observed-pair count drift")
    require(coverage["absent_source_pairs"] == 47, "M62 absent-pair count drift")
    require(coverage["coverage_by_hazard"] == EXPECTED_COVERAGE, "M62 final hazard coverage drift")
    geo_summary = coverage["geography_hazard_count_by_id"]
    require(len(geo_summary) == 19, "M62 geography summary collision or omission")
    require("idn.13.1303" in geo_summary and "idn.13.1372" in geo_summary, "M62 Kabupaten/Kota Solok identity split lost")
    require(geo_summary["idn.13.1303"]["geography_name"] == "Solok", "M62 Kabupaten Solok summary drift")
    require(geo_summary["idn.13.1372"]["geography_name"] == "Solok", "M62 Kota Solok summary drift")
    require(sum(int(item["hazard_count"]) for item in geo_summary.values()) == 124, "M62 geography summary does not reconcile")

    boundary = final["taxonomy_boundary"]
    require(boundary["cross_source_taxonomy_equivalence_authorized"] is False, "M62 taxonomy bridge unexpectedly authorized")
    require(boundary["bpbd_event_taxonomy_join_authorized"] is False, "M62 BPBD event join unexpectedly authorized")
    require(boundary["absence_means_zero_risk"] is False, "M62 absent pair must not mean zero risk")

    result = final["result"]
    require(result["dashboard_hazard_risk_filter_ready"] is True, "M62 dashboard hazard filter not authorized")
    require(result["dashboard_hazard_risk_map_ready"] is True, "M62 dashboard hazard map not authorized")
    require(result["prediction_claim_authorized"] is False, "M62 prediction claim must remain blocked")
    require(result["event_frequency_equivalence_authorized"] is False, "M62 event-frequency equivalence must remain blocked")
    require(result["missing_values_imputed"] is False, "M62 imputation must remain blocked")

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        catalog_rows = [row for row in csv.DictReader(handle) if row["id"] == CATALOG_ID]
    require(len(catalog_rows) == 1, "M62 public catalog registration missing or duplicated")
    entry = catalog_rows[0]
    require(entry["status"] == "materialized", "M62 catalog status drift")
    require(entry["source_path"] == CANONICAL.relative_to(ROOT).as_posix(), "M62 catalog path drift")

    print(json.dumps({
        "status": "ok",
        "canonical_rows": len(rows),
        "hazards": 9,
        "geographies_in_union": 19,
        "observed_pairs": 124,
        "absent_pairs": 47,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
