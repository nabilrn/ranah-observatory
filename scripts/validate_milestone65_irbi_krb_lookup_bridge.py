#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M62 = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_final.json"
IRBI = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-canonical.csv"
M64 = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"
KRB_CONTEXT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-recommendation-context-2022-2026.csv"
KRB_ACTIONS = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-mitigation-actions-2022-2026.csv"
CROSSWALK = ROOT / "data/mappings/milestone65_irbi_krb_hazard_lookup_crosswalk.csv"
INDEX = ROOT / "data/processed/bnpb/irbi_krb_bridge_2024/irbi-risk-mitigation-lookup-index-2024.csv"
FINAL = ROOT / "data/manifests/milestone65_irbi_krb_lookup_bridge.json"
CATALOG = ROOT / "catalog/public-datasets.csv"

AUTHORIZED = {
    "flood": "flood",
    "earthquake": "earthquake",
    "tsunami": "tsunami",
    "volcanic_eruption": "volcanic_eruption",
    "forest_and_land_fire": "forest_and_land_fire",
    "landslide": "landslide",
    "extreme_wave_and_coastal_erosion": "extreme_wave_and_coastal_erosion",
    "drought": "drought",
    "extreme_weather": "extreme_weather",
}
UNMATCHED = {
    "flash_flood",
    "liquefaction",
    "epidemic_and_disease_outbreak",
    "technological_failure",
    "covid_19",
}
EXPECTED_ACTION_COUNTS = {
    "flood": 7,
    "earthquake": 2,
    "tsunami": 8,
    "volcanic_eruption": 7,
    "forest_and_land_fire": 4,
    "landslide": 4,
    "extreme_wave_and_coastal_erosion": 6,
    "drought": 5,
    "extreme_weather": 6,
}
CATALOG_ID = "bnpb-irbi-krb-risk-mitigation-lookup-2024"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def normalized_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> int:
    final = json.loads(FINAL.read_text(encoding="utf-8"))
    require(final["schema"] == "ranah-observatory/milestone65-irbi-krb-lookup-bridge/v1", "M65 schema drift")
    require(final["milestone"] == 65 and final["depends_on"] == [62, 64], "M65 dependency contract drift")

    expected_inputs = {
        "m62_manifest": M62,
        "irbi_risk": IRBI,
        "m64_manifest": M64,
        "krb_context": KRB_CONTEXT,
        "krb_actions": KRB_ACTIONS,
    }
    for key, path in expected_inputs.items():
        meta = final["inputs"][key]
        require(meta["path"] == path.relative_to(ROOT).as_posix(), f"M65 input path drift: {key}")
        require(meta["sha256"] == sha256(path), f"M65 input checksum drift: {key}")

    require(final["outputs"]["crosswalk"]["path"] == CROSSWALK.relative_to(ROOT).as_posix(), "M65 crosswalk path drift")
    require(final["outputs"]["crosswalk"]["sha256"] == sha256(CROSSWALK), "M65 crosswalk checksum drift")
    require(final["outputs"]["risk_mitigation_lookup_index"]["path"] == INDEX.relative_to(ROOT).as_posix(), "M65 index path drift")
    require(final["outputs"]["risk_mitigation_lookup_index"]["sha256"] == sha256(INDEX), "M65 index checksum drift")

    result = final["result"]
    require(result["krb_hazard_count"] == 14, "M65 KRB hazard count drift")
    require(result["irbi_hazard_count"] == 9, "M65 IRBI hazard count drift")
    require(result["authorized_lookup_bridge_count"] == 9, "M65 authorized bridge count drift")
    require(result["unmatched_krb_hazard_count"] == 5, "M65 unmatched count drift")
    require(result["risk_lookup_index_row_count"] == 124, "M65 lookup index count drift")
    require(result["all_irbi_2024_rows_have_recommendation_lookup"] is True, "M65 incomplete IRBI lookup coverage")
    require(result["lookup_join_authorized"] is True, "M65 lookup join not authorized")
    require(result["global_taxonomy_equivalence_authorized"] is False, "M65 global taxonomy equivalence unexpectedly authorized")
    require(result["numeric_value_equivalence_authorized"] is False, "M65 numeric equivalence unexpectedly authorized")
    require(result["event_taxonomy_join_authorized"] is False, "M65 event taxonomy join unexpectedly authorized")
    require(result["prediction_claim_authorized"] is False, "M65 prediction claim unexpectedly authorized")
    require(set(final["unmatched_krb_hazards"]) == UNMATCHED, "M65 unmatched hazard footprint drift")

    crosswalk = read_csv(CROSSWALK)
    require(len(crosswalk) == 14, "M65 crosswalk row-count drift")
    require(len({row["krb_hazard_id"] for row in crosswalk}) == 14, "M65 duplicate KRB crosswalk IDs")
    require({row["krb_hazard_id"] for row in crosswalk} == set(AUTHORIZED) | UNMATCHED, "M65 crosswalk hazard footprint drift")

    authorized_rows = [row for row in crosswalk if row["bridge_status"] == "authorized_lookup_bridge"]
    unmatched_rows = [row for row in crosswalk if row["bridge_status"] == "no_irbi_2024_hazard_table_match"]
    require(len(authorized_rows) == 9 and len(unmatched_rows) == 5, "M65 crosswalk status counts drift")

    for row in authorized_rows:
        krb = row["krb_hazard_id"]
        require(krb in AUTHORIZED, f"M65 unauthorized bridge: {krb}")
        require(row["irbi_hazard_id"] == AUTHORIZED[krb], f"M65 bridge target drift: {krb}")
        require(normalized_label(row["krb_source_hazard_label"]) == normalized_label(row["irbi_source_hazard_label"]), f"M65 matched label drift: {krb}")
        require(row["bridge_basis"] == "explicit_same_hazard_concept_and_normalized_source_label_match", f"M65 bridge basis drift: {krb}")
        require(row["risk_to_recommendation_lookup_authorized"] == "true", f"M65 lookup authorization drift: {krb}")
        require(row["numeric_value_equivalence_authorized"] == "false", f"M65 numeric equivalence drift: {krb}")
        require(row["event_taxonomy_join_authorized"] == "false", f"M65 event taxonomy boundary drift: {krb}")
        require(row["causal_prediction_authorized"] == "false", f"M65 causal prediction boundary drift: {krb}")
        require(row["unmatched_reason"] == "", f"M65 matched row contains unmatched reason: {krb}")

    for row in unmatched_rows:
        krb = row["krb_hazard_id"]
        require(krb in UNMATCHED, f"M65 unexpected unmatched hazard: {krb}")
        require(row["irbi_hazard_id"] == "" and row["irbi_source_hazard_label"] == "", f"M65 unmatched row has IRBI identity: {krb}")
        require(row["bridge_basis"] == "none", f"M65 unmatched bridge basis drift: {krb}")
        require(row["risk_to_recommendation_lookup_authorized"] == "false", f"M65 unmatched lookup unexpectedly authorized: {krb}")
        require(row["numeric_value_equivalence_authorized"] == "false", f"M65 unmatched numeric equivalence drift: {krb}")
        require(row["event_taxonomy_join_authorized"] == "false", f"M65 unmatched event join drift: {krb}")
        require(row["causal_prediction_authorized"] == "false", f"M65 unmatched prediction drift: {krb}")
        require(bool(row["unmatched_reason"]), f"M65 unmatched reason missing: {krb}")

    irbi_rows = read_csv(IRBI)
    index_rows = read_csv(INDEX)
    require(len(irbi_rows) == 124 and len(index_rows) == 124, "M65 index/input row-count drift")

    irbi_keyed = {
        (row["year"], row["geography_id"], row["irbi_hazard_id"]): row
        for row in irbi_rows
    }
    index_keyed = {
        (row["year"], row["geography_id"], row["irbi_hazard_id"]): row
        for row in index_rows
    }
    require(len(irbi_keyed) == 124 and len(index_keyed) == 124, "M65 duplicate risk lookup keys")
    require(set(index_keyed) == set(irbi_keyed), "M65 risk lookup footprint differs from M62 IRBI")

    observed_counts = Counter()
    for key, source in irbi_keyed.items():
        row = index_keyed[key]
        hazard = source["irbi_hazard_id"]
        require(row["geography_name"] == source["geography_name"], f"M65 geography name drift: {key}")
        require(row["irbi_source_hazard_label"] == source["source_hazard_label"], f"M65 IRBI source label drift: {key}")
        require(row["risk_score"] == source["risk_score"], f"M65 risk score changed during lookup join: {key}")
        require(row["risk_class"] == source["risk_class"], f"M65 risk class changed during lookup join: {key}")
        require(row["krb_hazard_id"] == AUTHORIZED[hazard], f"M65 KRB lookup target drift: {key}")
        require(row["bridge_status"] == "authorized_lookup_bridge", f"M65 index bridge status drift: {key}")
        require(row["claim_type"] == "official_risk_index_with_recommendation_lookup", f"M65 claim type drift: {key}")
        require(row["recommendation_action_detail_status"] == "flat_actions_materialized", f"M65 matched recommendation detail not flat: {key}")
        require(int(row["mitigation_action_count"]) == EXPECTED_ACTION_COUNTS[hazard], f"M65 mitigation action count drift: {key}")
        require(row["numeric_value_equivalence_authorized"] == "false", f"M65 index numeric equivalence drift: {key}")
        require(row["event_taxonomy_join_authorized"] == "false", f"M65 index event join drift: {key}")
        require(row["prediction_claim_authorized"] == "false", f"M65 index prediction drift: {key}")
        observed_counts[hazard] += 1

    m62 = json.loads(M62.read_text(encoding="utf-8"))
    require(dict(observed_counts) == m62["coverage"]["coverage_by_hazard"], "M65 hazard coverage no longer matches M62")

    action_counts = Counter(row["krb_hazard_id"] for row in read_csv(KRB_ACTIONS))
    for hazard, expected in EXPECTED_ACTION_COUNTS.items():
        require(action_counts[hazard] == expected, f"M65 upstream KRB action count drift: {hazard}")

    with CATALOG.open(newline="", encoding="utf-8") as handle:
        matches = [row for row in csv.DictReader(handle) if row["id"] == CATALOG_ID]
    require(len(matches) == 1, "M65 public catalog entry missing or duplicated")
    catalog = matches[0]
    require(catalog["status"] == "materialized", "M65 public catalog status drift")
    require(catalog["source_path"] == INDEX.relative_to(ROOT).as_posix(), "M65 public catalog path drift")

    print(json.dumps({
        "status": "ok",
        "crosswalk_rows": 14,
        "authorized_bridges": 9,
        "unmatched_krb_hazards": 5,
        "risk_lookup_rows": 124,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
