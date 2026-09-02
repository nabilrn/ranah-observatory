#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web/static/data/disaster-summary.json"
M65 = ROOT / "data/manifests/milestone65_irbi_krb_lookup_bridge.json"
M64 = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"
PACKAGE = ROOT / "web/package.json"
PAGE_TS = ROOT / "web/src/routes/[lang]/explore/disaster/+page.ts"
PAGE_SVELTE = ROOT / "web/src/routes/[lang]/explore/disaster/+page.svelte"
PANEL = ROOT / "web/src/lib/components/RiskMitigationPanel.svelte"
PUBLIC_TYPES = ROOT / "web/src/lib/public-data.ts"

PUBLIC_SCHEMA_PREFIX = "ranah-observatory/public-disaster-summary/v"
EXPECTED_MATCHED = {
    "drought": 5,
    "earthquake": 2,
    "extreme_wave_and_coastal_erosion": 6,
    "extreme_weather": 6,
    "flood": 7,
    "forest_and_land_fire": 4,
    "landslide": 4,
    "tsunami": 8,
    "volcanic_eruption": 7,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(PUBLIC.exists(), "M66 public artifact missing; run web data/build chain first")
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    schema = public.get("schema", "")
    require(schema.startswith(PUBLIC_SCHEMA_PREFIX), f"M66 public schema namespace drift: {schema!r}")
    require(int(schema.removeprefix(PUBLIC_SCHEMA_PREFIX)) >= 4, f"M66 risk layer requires public schema v4+, got {schema!r}")
    require(public.get("missing_values_inferred") is False, "M66 inherited missing-value boundary drift")
    rm = public.get("risk_mitigation_2024")
    require(isinstance(rm, dict), "M66 risk_mitigation_2024 payload missing")

    m65 = json.loads(M65.read_text(encoding="utf-8"))
    m64 = json.loads(M64.read_text(encoding="utf-8"))
    index_meta = m65["outputs"]["risk_mitigation_lookup_index"]
    action_meta = m64["outputs"]["hazard_actions"]
    index_path = ROOT / index_meta["path"]
    action_path = ROOT / action_meta["path"]
    require(sha256(index_path) == index_meta["sha256"], "M66 upstream M65 index checksum drift")
    require(sha256(action_path) == action_meta["sha256"], "M66 upstream M64 action checksum drift")

    source = rm["source"]
    require(source["bridge_manifest_path"] == M65.relative_to(ROOT).as_posix(), "M66 M65 manifest path drift")
    require(source["bridge_manifest_sha256"] == sha256(M65), "M66 M65 manifest checksum drift")
    require(source["risk_lookup_path"] == index_path.relative_to(ROOT).as_posix(), "M66 risk lookup path drift")
    require(source["risk_lookup_sha256"] == sha256(index_path), "M66 risk lookup checksum drift")
    require(source["recommendation_actions_path"] == action_path.relative_to(ROOT).as_posix(), "M66 action path drift")
    require(source["recommendation_actions_sha256"] == sha256(action_path), "M66 action checksum drift")

    risk = rm["risk"]
    require(risk["year"] == 2024, "M66 risk year drift")
    require(risk["row_count"] == len(risk["rows"]) == 124, "M66 risk row count drift")
    require(len(risk["hazard_ids"]) == 9, "M66 risk hazard count drift")
    require(risk["geography_union_count"] == 19, "M66 geography union drift")
    require(risk["possible_full_grid_pairs"] == 171, "M66 possible-grid count drift")
    require(risk["absent_source_pairs"] == 47, "M66 absent-source count drift")

    source_rows = read_csv(index_path)
    public_keys = set()
    public_coverage: Counter[str] = Counter()
    source_keyed = {(row["year"], row["geography_id"], row["irbi_hazard_id"]): row for row in source_rows}
    require(len(source_keyed) == 124, "M66 upstream M65 index duplicate keys")
    for row in risk["rows"]:
        key = (str(row["year"]), row["geography_id"], row["irbi_hazard_id"])
        require(key not in public_keys, f"M66 duplicate public risk key: {key}")
        public_keys.add(key)
        require(key in source_keyed, f"M66 public risk row not present in M65: {key}")
        src = source_keyed[key]
        require(row["geography_name"] == src["geography_name"], f"M66 geography name drift: {key}")
        require(row["irbi_source_hazard_label"] == src["irbi_source_hazard_label"], f"M66 IRBI label drift: {key}")
        require(row["risk_score"] == float(src["risk_score"]), f"M66 risk score changed: {key}")
        require(row["risk_class"] == src["risk_class"], f"M66 risk class changed: {key}")
        require(row["krb_hazard_id"] == src["krb_hazard_id"], f"M66 KRB lookup changed: {key}")
        require(row["mitigation_action_count"] == int(src["mitigation_action_count"]), f"M66 mitigation count changed: {key}")
        require(row["recommendation_action_detail_status"] == "flat_actions_materialized", f"M66 unsupported recommendation structure: {key}")
        require(row["bridge_status"] == "authorized_lookup_bridge", f"M66 unauthorized bridge row: {key}")
        public_coverage[row["irbi_hazard_id"]] += 1
    require(public_keys == set(source_keyed), "M66 public risk footprint differs from M65")
    require(dict(sorted(public_coverage.items())) == risk["hazard_coverage"], "M66 risk coverage summary drift")

    recommendations = rm["recommendations"]
    require(recommendations["source_period"] == "2022–2026", "M66 recommendation period drift")
    require(recommendations["action_count"] == len(recommendations["rows"]) == 49, "M66 action count drift")
    require(recommendations["hazard_count"] == 9, "M66 recommendation hazard count drift")
    require(recommendations["action_counts_by_hazard"] == EXPECTED_MATCHED, "M66 action coverage drift")

    upstream_actions = {
        (row["krb_hazard_id"], int(row["action_order"])): row
        for row in read_csv(action_path)
        if row["krb_hazard_id"] in EXPECTED_MATCHED
    }
    require(len(upstream_actions) == 49, "M66 expected 49 matched upstream KRB actions")
    public_action_keys = set()
    for row in recommendations["rows"]:
        key = (row["krb_hazard_id"], row["action_order"])
        require(key not in public_action_keys, f"M66 duplicate public action: {key}")
        public_action_keys.add(key)
        require(key in upstream_actions, f"M66 action not present in M64: {key}")
        src = upstream_actions[key]
        require(row["source_hazard_label"] == src["source_hazard_label"], f"M66 action label drift: {key}")
        require(row["action_text_source_native"] == src["action_text_source_native"], f"M66 action text changed: {key}")
        require(row["start_pdf_page"] == int(src["start_pdf_page"]), f"M66 action start page drift: {key}")
        require(row["end_pdf_page"] == int(src["end_pdf_page"]), f"M66 action end page drift: {key}")
    require(public_action_keys == set(upstream_actions), "M66 public action footprint differs from matched M64 actions")

    require(set(rm["unmatched_krb_hazards"]) == set(m65["unmatched_krb_hazards"]), "M66 unmatched KRB hazards drift")
    require(len(rm["unmatched_krb_hazards"]) == 5, "M66 unmatched KRB hazard count drift")
    boundaries = rm["boundaries"]
    require(boundaries["lookup_join_authorized"] is True, "M66 lookup join not authorized")
    for key in (
        "global_taxonomy_equivalence_authorized",
        "numeric_value_equivalence_authorized",
        "event_taxonomy_join_authorized",
        "prediction_claim_authorized",
        "recommendations_are_implementation_evidence",
        "absent_irbi_pair_means_zero_risk",
    ):
        require(boundaries[key] is False, f"M66 unsafe boundary enabled: {key}")

    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    data_script = package["scripts"]["data"]
    require("python3 ../scripts/promote_public_disaster_risk_mitigation.py" in data_script, "M66 promoter missing from web data chain")
    require("promote_public_disaster_context.py" in data_script, "M66 v3 prerequisite promoter missing")
    require(PUBLIC_SCHEMA_PREFIX in PAGE_TS.read_text(encoding="utf-8"), "M66 page loader schema guard missing")
    require("risk_mitigation_2024: PublicRiskMitigation2024" in PUBLIC_TYPES.read_text(encoding="utf-8"), "M66 public TypeScript contract missing")
    page_text = PAGE_SVELTE.read_text(encoding="utf-8")
    require("RiskMitigationPanel" in page_text and "summary.risk_mitigation_2024" in page_text, "M66 disaster page does not mount risk panel")
    panel_text = PANEL.read_text(encoding="utf-8")
    for phrase in (
        "Ini bukan berarti risikonya nol.",
        "bukan peringkat efektivitas",
        "indeks risiko, bukan peluang kejadian",
    ):
        require(phrase in panel_text, f"M66 public safety copy missing: {phrase}")

    print(json.dumps({
        "status": "ok",
        "schema": public["schema"],
        "risk_rows": 124,
        "matched_hazards": 9,
        "recommendation_actions": 49,
        "unmatched_krb_hazards": 5,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
