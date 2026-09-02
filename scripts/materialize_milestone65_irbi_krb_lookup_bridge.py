#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IRBI = ROOT / "data/processed/bnpb/irbi_hazard_risk_2024/irbi-sumbar-hazard-risk-2024-canonical.csv"
M62 = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_final.json"
KRB_CONTEXT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-recommendation-context-2022-2026.csv"
KRB_ACTIONS = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-mitigation-actions-2022-2026.csv"
M64 = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"
CROSSWALK = ROOT / "data/mappings/milestone65_irbi_krb_hazard_lookup_crosswalk.csv"
INDEX = ROOT / "data/processed/bnpb/irbi_krb_bridge_2024/irbi-risk-mitigation-lookup-index-2024.csv"
FINAL = ROOT / "data/manifests/milestone65_irbi_krb_lookup_bridge.json"

AUTHORIZED_MATCHES = {
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
EXPECTED_KRB_ONLY = {
    "flash_flood",
    "liquefaction",
    "epidemic_and_disease_outbreak",
    "technological_failure",
    "covid_19",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalized_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> int:
    m62 = json.loads(M62.read_text(encoding="utf-8"))
    m64 = json.loads(M64.read_text(encoding="utf-8"))
    if m62["result"]["hazard_count"] != 9 or m62["result"]["canonical_row_count"] != 124:
        raise RuntimeError("M65 upstream M62 footprint drift")
    if m62["taxonomy_boundary"]["cross_source_taxonomy_equivalence_authorized"] is not False:
        raise RuntimeError("M65 requires M62 global cross-source equivalence to remain false")
    if m64["result"]["hazard_count"] != 14 or m64["result"]["specific_recommendation_action_count"] != 60:
        raise RuntimeError("M65 upstream M64 footprint drift")
    if m64["taxonomy_boundary"]["cross_source_taxonomy_equivalence_authorized"] is not False:
        raise RuntimeError("M65 requires M64 global cross-source equivalence to remain false")

    irbi_rows = read_csv(IRBI)
    krb_context = read_csv(KRB_CONTEXT)
    krb_actions = read_csv(KRB_ACTIONS)
    if len(irbi_rows) != 124 or len(krb_context) != 14 or len(krb_actions) != 60:
        raise RuntimeError("M65 input row-count drift")

    irbi_labels: dict[str, set[str]] = {}
    for row in irbi_rows:
        irbi_labels.setdefault(row["irbi_hazard_id"], set()).add(row["source_hazard_label"])
    if set(irbi_labels) != set(AUTHORIZED_MATCHES):
        raise RuntimeError(f"M65 IRBI hazard footprint drift: {sorted(irbi_labels)}")
    if any(len(labels) != 1 for labels in irbi_labels.values()):
        raise RuntimeError("M65 IRBI source label is not unique by hazard")

    krb_labels: dict[str, str] = {}
    krb_detail_status: dict[str, str] = {}
    for row in krb_context:
        hazard = row["krb_hazard_id"]
        if hazard in krb_labels:
            raise RuntimeError(f"M65 duplicate KRB context hazard: {hazard}")
        krb_labels[hazard] = row["source_hazard_label"]
        krb_detail_status[hazard] = row["action_detail_status"]
    if set(krb_labels) != set(AUTHORIZED_MATCHES) | EXPECTED_KRB_ONLY:
        raise RuntimeError(f"M65 KRB hazard footprint drift: {sorted(krb_labels)}")

    action_counts = Counter(row["krb_hazard_id"] for row in krb_actions)
    if set(action_counts) != set(AUTHORIZED_MATCHES) | {"flash_flood", "liquefaction"}:
        raise RuntimeError(f"M65 KRB action footprint drift: {sorted(action_counts)}")

    crosswalk_rows: list[dict[str, str]] = []
    for krb_hazard in sorted(krb_labels):
        if krb_hazard in AUTHORIZED_MATCHES:
            irbi_hazard = AUTHORIZED_MATCHES[krb_hazard]
            irbi_label = next(iter(irbi_labels[irbi_hazard]))
            if normalized_label(krb_labels[krb_hazard]) != normalized_label(irbi_label):
                raise RuntimeError(
                    f"M65 explicit match label drift for {krb_hazard}: "
                    f"{krb_labels[krb_hazard]!r} vs {irbi_label!r}"
                )
            if action_counts[krb_hazard] <= 0:
                raise RuntimeError(f"M65 matched hazard lacks mitigation actions: {krb_hazard}")
            crosswalk_rows.append({
                "krb_hazard_id": krb_hazard,
                "krb_source_hazard_label": krb_labels[krb_hazard],
                "irbi_hazard_id": irbi_hazard,
                "irbi_source_hazard_label": irbi_label,
                "bridge_status": "authorized_lookup_bridge",
                "bridge_basis": "explicit_same_hazard_concept_and_normalized_source_label_match",
                "risk_to_recommendation_lookup_authorized": "true",
                "numeric_value_equivalence_authorized": "false",
                "event_taxonomy_join_authorized": "false",
                "causal_prediction_authorized": "false",
                "unmatched_reason": "",
            })
        else:
            crosswalk_rows.append({
                "krb_hazard_id": krb_hazard,
                "krb_source_hazard_label": krb_labels[krb_hazard],
                "irbi_hazard_id": "",
                "irbi_source_hazard_label": "",
                "bridge_status": "no_irbi_2024_hazard_table_match",
                "bridge_basis": "none",
                "risk_to_recommendation_lookup_authorized": "false",
                "numeric_value_equivalence_authorized": "false",
                "event_taxonomy_join_authorized": "false",
                "causal_prediction_authorized": "false",
                "unmatched_reason": "KRB recommendation section has no corresponding hazard table in the M62 IRBI 2024 Sumatera Barat layer",
            })

    if sum(row["bridge_status"] == "authorized_lookup_bridge" for row in crosswalk_rows) != 9:
        raise RuntimeError("M65 authorized bridge count drift")
    if sum(row["bridge_status"] != "authorized_lookup_bridge" for row in crosswalk_rows) != 5:
        raise RuntimeError("M65 unmatched bridge count drift")

    CROSSWALK.parent.mkdir(parents=True, exist_ok=True)
    with CROSSWALK.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(crosswalk_rows[0].keys()))
        writer.writeheader()
        writer.writerows(crosswalk_rows)

    bridge_by_irbi = {
        row["irbi_hazard_id"]: row
        for row in crosswalk_rows
        if row["bridge_status"] == "authorized_lookup_bridge"
    }
    index_rows: list[dict[str, str]] = []
    for row in irbi_rows:
        hazard = row["irbi_hazard_id"]
        bridge = bridge_by_irbi.get(hazard)
        if not bridge:
            raise RuntimeError(f"M65 IRBI row lacks authorized KRB bridge: {hazard}")
        krb_hazard = bridge["krb_hazard_id"]
        index_rows.append({
            "year": row["year"],
            "geography_id": row["geography_id"],
            "geography_name": row["geography_name"],
            "irbi_hazard_id": hazard,
            "irbi_source_hazard_label": row["source_hazard_label"],
            "risk_score": row["risk_score"],
            "risk_class": row["risk_class"],
            "krb_hazard_id": krb_hazard,
            "krb_source_hazard_label": bridge["krb_source_hazard_label"],
            "mitigation_action_count": str(action_counts[krb_hazard]),
            "recommendation_action_detail_status": krb_detail_status[krb_hazard],
            "bridge_status": "authorized_lookup_bridge",
            "claim_type": "official_risk_index_with_recommendation_lookup",
            "numeric_value_equivalence_authorized": "false",
            "event_taxonomy_join_authorized": "false",
            "prediction_claim_authorized": "false",
        })
    if len(index_rows) != 124:
        raise RuntimeError("M65 product lookup index row-count drift")

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with INDEX.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_rows[0].keys()))
        writer.writeheader()
        writer.writerows(index_rows)

    final = {
        "schema": "ranah-observatory/milestone65-irbi-krb-lookup-bridge/v1",
        "milestone": 65,
        "depends_on": [62, 64],
        "inputs": {
            "m62_manifest": {"path": M62.relative_to(ROOT).as_posix(), "sha256": sha256(M62)},
            "irbi_risk": {"path": IRBI.relative_to(ROOT).as_posix(), "sha256": sha256(IRBI)},
            "m64_manifest": {"path": M64.relative_to(ROOT).as_posix(), "sha256": sha256(M64)},
            "krb_context": {"path": KRB_CONTEXT.relative_to(ROOT).as_posix(), "sha256": sha256(KRB_CONTEXT)},
            "krb_actions": {"path": KRB_ACTIONS.relative_to(ROOT).as_posix(), "sha256": sha256(KRB_ACTIONS)},
        },
        "result": {
            "krb_hazard_count": 14,
            "irbi_hazard_count": 9,
            "authorized_lookup_bridge_count": 9,
            "unmatched_krb_hazard_count": 5,
            "risk_lookup_index_row_count": 124,
            "all_irbi_2024_rows_have_recommendation_lookup": True,
            "lookup_join_authorized": True,
            "global_taxonomy_equivalence_authorized": False,
            "numeric_value_equivalence_authorized": False,
            "event_taxonomy_join_authorized": False,
            "prediction_claim_authorized": False,
        },
        "unmatched_krb_hazards": sorted(EXPECTED_KRB_ONLY),
        "outputs": {
            "crosswalk": {"path": CROSSWALK.relative_to(ROOT).as_posix(), "sha256": sha256(CROSSWALK)},
            "risk_mitigation_lookup_index": {"path": INDEX.relative_to(ROOT).as_posix(), "sha256": sha256(INDEX)},
        },
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
