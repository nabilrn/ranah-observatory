#!/usr/bin/env python3
"""Promote qualified IRBI risk + KRB mitigation lookup into public disaster contract v4.

This step upgrades the already-promoted public disaster summary v3. It reads only
qualified M65/M64 outputs, preserves IRBI values exactly, and exposes KRB actions
only for the nine explicitly authorized lookup bridges. It does not join BPBD
hazard/event taxonomies, infer missing IRBI pairs, or create predictions.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SUMMARY = ROOT / "web/static/data/disaster-summary.json"
M65_MANIFEST = ROOT / "data/manifests/milestone65_irbi_krb_lookup_bridge.json"
M64_MANIFEST = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"
M62_MANIFEST = ROOT / "data/manifests/milestone62_irbi_hazard_risk_2024_final.json"

BASE_PUBLIC_SCHEMA = "ranah-observatory/public-disaster-summary/v3"
PUBLIC_SCHEMA = "ranah-observatory/public-disaster-summary/v4"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verified_output(manifest: dict, *keys: str) -> Path:
    node = manifest
    for key in keys:
        node = node[key]
    path = ROOT / node["path"]
    require(path.exists(), f"qualified output missing: {node['path']}")
    require(sha256(path) == node["sha256"], f"qualified output checksum mismatch: {node['path']}")
    return path


def main() -> None:
    require(PUBLIC_SUMMARY.exists(), "public disaster summary missing; run prior public promoters first")
    base = json.loads(PUBLIC_SUMMARY.read_text(encoding="utf-8"))
    require(base.get("schema") == BASE_PUBLIC_SCHEMA, f"expected {BASE_PUBLIC_SCHEMA}, got {base.get('schema')!r}")

    m65 = json.loads(M65_MANIFEST.read_text(encoding="utf-8"))
    m64 = json.loads(M64_MANIFEST.read_text(encoding="utf-8"))
    m62 = json.loads(M62_MANIFEST.read_text(encoding="utf-8"))

    require(m65.get("schema") == "ranah-observatory/milestone65-irbi-krb-lookup-bridge/v1", "unsupported M65 schema")
    require(m65.get("depends_on") == [62, 64], "M65 dependency contract drift")
    result = m65["result"]
    require(result["risk_lookup_index_row_count"] == 124, "M65 risk lookup row count drift")
    require(result["authorized_lookup_bridge_count"] == 9, "M65 authorized lookup count drift")
    require(result["unmatched_krb_hazard_count"] == 5, "M65 unmatched hazard count drift")
    require(result["all_irbi_2024_rows_have_recommendation_lookup"] is True, "M65 incomplete lookup coverage")
    require(result["lookup_join_authorized"] is True, "M65 lookup join is not authorized")
    require(result["global_taxonomy_equivalence_authorized"] is False, "global taxonomy equivalence unexpectedly authorized")
    require(result["numeric_value_equivalence_authorized"] is False, "numeric equivalence unexpectedly authorized")
    require(result["event_taxonomy_join_authorized"] is False, "event taxonomy join unexpectedly authorized")
    require(result["prediction_claim_authorized"] is False, "prediction unexpectedly authorized")

    index_path = verified_output(m65, "outputs", "risk_mitigation_lookup_index")
    action_path = verified_output(m64, "outputs", "hazard_actions")
    risk_rows = read_csv(index_path)
    actions = read_csv(action_path)
    require(len(risk_rows) == 124, "M65 public promotion expected 124 risk rows")

    authorized_hazards = sorted({row["krb_hazard_id"] for row in risk_rows})
    require(len(authorized_hazards) == 9 and all(authorized_hazards), "M65 public promotion hazard footprint drift")

    public_risk_rows: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    geography_ids: set[str] = set()
    hazard_counts: Counter[str] = Counter()
    for row in risk_rows:
        key = (row["year"], row["geography_id"], row["irbi_hazard_id"])
        require(key not in seen_keys, f"duplicate M65 public risk key: {key}")
        seen_keys.add(key)
        geography_ids.add(row["geography_id"])
        hazard_counts[row["irbi_hazard_id"]] += 1
        require(row["bridge_status"] == "authorized_lookup_bridge", f"unauthorized bridge in M65 public index: {key}")
        require(row["numeric_value_equivalence_authorized"] == "false", f"numeric equivalence drift: {key}")
        require(row["event_taxonomy_join_authorized"] == "false", f"event-taxonomy join drift: {key}")
        require(row["prediction_claim_authorized"] == "false", f"prediction drift: {key}")
        public_risk_rows.append(
            {
                "year": int(row["year"]),
                "geography_id": row["geography_id"],
                "geography_name": row["geography_name"],
                "irbi_hazard_id": row["irbi_hazard_id"],
                "irbi_source_hazard_label": row["irbi_source_hazard_label"],
                "risk_score": float(row["risk_score"]),
                "risk_class": row["risk_class"],
                "krb_hazard_id": row["krb_hazard_id"],
                "krb_source_hazard_label": row["krb_source_hazard_label"],
                "mitigation_action_count": int(row["mitigation_action_count"]),
                "recommendation_action_detail_status": row["recommendation_action_detail_status"],
                "bridge_status": row["bridge_status"],
            }
        )

    m62_coverage = m62["coverage"]
    require(len(geography_ids) == m62["result"]["current_sumbar_geography_count"] == 19, "IRBI geography union drift")
    require(dict(hazard_counts) == m62_coverage["coverage_by_hazard"], "IRBI hazard coverage drift during public promotion")

    public_actions: list[dict] = []
    action_counts: Counter[str] = Counter()
    for row in actions:
        if row["krb_hazard_id"] not in authorized_hazards:
            continue
        require(row["claim_type"] == "official_risk_reduction_recommendation", "unexpected KRB action claim type")
        require(row["observed_implementation_claimed"] == "false", "KRB action promoted as implemented")
        require(row["prediction_claim_authorized"] == "false", "KRB action promoted as prediction")
        require(row["unmitigated_loss_forecast_authorized"] == "false", "KRB action promoted as loss forecast")
        action_counts[row["krb_hazard_id"]] += 1
        public_actions.append(
            {
                "krb_hazard_id": row["krb_hazard_id"],
                "source_hazard_label": row["source_hazard_label"],
                "action_order": int(row["action_order"]),
                "action_text_source_native": row["action_text_source_native"],
                "start_pdf_page": int(row["start_pdf_page"]),
                "end_pdf_page": int(row["end_pdf_page"]),
            }
        )

    expected_action_counts = {
        hazard: int(next(row["mitigation_action_count"] for row in risk_rows if row["krb_hazard_id"] == hazard))
        for hazard in authorized_hazards
    }
    require(dict(action_counts) == expected_action_counts, "KRB action coverage does not match M65 lookup metadata")
    require(len(public_actions) == 49, "M66 expected 49 actions across nine matched hazards")

    public_risk_rows.sort(key=lambda row: (row["irbi_hazard_id"], row["geography_name"], row["geography_id"]))
    public_actions.sort(key=lambda row: (row["krb_hazard_id"], row["action_order"]))

    payload = dict(base)
    payload["schema"] = PUBLIC_SCHEMA
    payload["risk_mitigation_2024"] = {
        "source": {
            "organization": "BNPB / IRBI 2024 + InaRISK KRB Sumatera Barat 2022–2026",
            "bridge_manifest_path": M65_MANIFEST.relative_to(ROOT).as_posix(),
            "bridge_manifest_sha256": sha256(M65_MANIFEST),
            "risk_lookup_path": index_path.relative_to(ROOT).as_posix(),
            "risk_lookup_sha256": sha256(index_path),
            "recommendation_actions_path": action_path.relative_to(ROOT).as_posix(),
            "recommendation_actions_sha256": sha256(action_path),
        },
        "risk": {
            "year": 2024,
            "rows": public_risk_rows,
            "row_count": len(public_risk_rows),
            "hazard_ids": sorted(hazard_counts),
            "hazard_coverage": dict(sorted(hazard_counts.items())),
            "geography_union_count": len(geography_ids),
            "possible_full_grid_pairs": m62_coverage["possible_full_grid_pairs"],
            "absent_source_pairs": m62_coverage["absent_source_pairs"],
        },
        "recommendations": {
            "source_period": "2022–2026",
            "rows": public_actions,
            "action_count": len(public_actions),
            "hazard_count": len(authorized_hazards),
            "action_counts_by_hazard": dict(sorted(action_counts.items())),
        },
        "unmatched_krb_hazards": m65["unmatched_krb_hazards"],
        "boundaries": {
            "lookup_join_authorized": True,
            "global_taxonomy_equivalence_authorized": False,
            "numeric_value_equivalence_authorized": False,
            "event_taxonomy_join_authorized": False,
            "prediction_claim_authorized": False,
            "recommendations_are_implementation_evidence": False,
            "absent_irbi_pair_means_zero_risk": False,
        },
        "interpretation": {
            "id": "Skor dan kelas risiko berasal dari IRBI BNPB 2024. Rekomendasi berasal dari KRB Sumatera Barat 2022–2026 dan ditampilkan hanya untuk sembilan jenis ancaman yang cocok secara eksplisit. Skor risiko bukan ramalan kejadian, rekomendasi bukan bukti bahwa tindakan sudah dilaksanakan, dan kombinasi wilayah–ancaman yang tidak muncul di IRBI tidak dianggap bernilai nol.",
            "en": "Risk scores and classes come from BNPB IRBI 2024. Recommendations come from the West Sumatra 2022–2026 KRB and are shown only for nine explicitly matched hazards. Risk scores are not event forecasts, recommendations are not evidence of implementation, and absent district–hazard IRBI pairs are not treated as zero.",
        },
    }

    PUBLIC_SUMMARY.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": PUBLIC_SCHEMA,
                "risk_rows": len(public_risk_rows),
                "matched_hazards": len(authorized_hazards),
                "recommendation_actions": len(public_actions),
                "unmatched_krb_hazards": len(m65["unmatched_krb_hazards"]),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
