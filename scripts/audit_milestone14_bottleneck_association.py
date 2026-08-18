#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "research/MILESTONE14_BOTTLENECK_ASSOCIATION_SPEC.md"
MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"
SCREEN = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-association-screen.csv"
GEO = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-geography-loo.csv"
YEAR = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-year-loo.csv"
FAV = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-favorable-peer-sensitivity.csv"
ADJ = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-outcome-adjacent-sensitivity.csv"

EXPECTED_PAIRS = {
    ("poverty_rate", "expected_years_schooling"),
    ("poverty_rate", "underemployment_rate"),
    ("poverty_rate", "annual_rainfall"),
    ("unemployment_rate", "expected_years_schooling"),
    ("unemployment_rate", "annual_rainfall"),
    ("real_grdp_growth", "expected_years_schooling"),
    ("real_grdp_growth", "underemployment_rate"),
    ("real_grdp_growth", "annual_rainfall"),
    ("poverty_rate", "life_expectancy"),
    ("unemployment_rate", "life_expectancy"),
    ("real_grdp_growth", "life_expectancy"),
}
FORBIDDEN_PRIMARY = {
    "mean_years_schooling", "labor_force_participation", "agriculture_share_grdp",
    "manufacturing_share_grdp", "rice_yield",
}
REQUIRED_SPEC = [
    "association engine",
    "does **not** use these same five variables as primary bottleneck candidates",
    "4,999 permutations",
    "stable_association_signal=true",
    "does **not** mean the candidate causes the gap",
    "Why no SHAP in v1",
]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def truth(v: str) -> bool:
    return v.lower() in {"1", "true", "yes"}


def audit() -> dict[str, Any]:
    errors: list[str] = []
    required = [SPEC, MANIFEST, SCREEN, GEO, YEAR, FAV, ADJ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if errors:
        return {"schema": "ranah-observatory/milestone14-audit/v1", "errors": errors, "milestone14_complete": False}

    spec = SPEC.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    screen, geo, years, fav, adj = rows(SCREEN), rows(GEO), rows(YEAR), rows(FAV), rows(ADJ)

    for phrase in REQUIRED_SPEC:
        if phrase not in spec:
            errors.append(f"spec lost required guardrail: {phrase}")

    if manifest.get("schema") != "ranah-observatory/milestone14-bottleneck-association/v1":
        errors.append("manifest schema drift")
    if manifest.get("milestone14_complete") is not True:
        errors.append("milestone14 completion flag false")
    for key in (
        "m11_primary_feature_reuse_in_primary_screen", "outcome_adjacent_underemployment_unemployment_primary_authorized",
        "shap_or_black_box_feature_importance_performed", "causal_analysis_performed", "policy_priority_claim_authorized",
        "technical_efficiency_claim_authorized", "monetary_wasted_potential_estimated",
    ):
        if manifest.get(key) is not False:
            errors.append(f"forbidden M14 claim/method flag enabled: {key}")
    if manifest.get("permutation_seed") != 140014 or manifest.get("permutation_count") != 4999:
        errors.append("permutation contract drift")

    for key, record in manifest.get("inputs", {}).items():
        path = ROOT / str(record.get("path", ""))
        if not path.exists() or sha256(path) != record.get("sha256"):
            errors.append(f"input checksum drift: {key}")
    for key, record in manifest.get("outputs", {}).items():
        path = ROOT / str(record.get("path", ""))
        if not path.exists() or sha256(path) != record.get("sha256"):
            errors.append(f"output checksum drift: {key}")

    pairs = {(r["target_id"], r["candidate_id"]) for r in screen}
    if len(screen) != 11 or pairs != EXPECTED_PAIRS:
        errors.append("association screen pair set drift")
    if any(r["candidate_id"] in FORBIDDEN_PRIMARY for r in screen):
        errors.append("M11 primary feature leaked into M14 primary screen")
    if sum(r["screen_type"] == "core" for r in screen) != 8 or sum(r["screen_type"] == "health_extension" for r in screen) != 3:
        errors.append("core/health screen counts drift")

    stable_pairs: list[tuple[str, str]] = []
    for r in screen:
        try:
            assoc = float(r["within_year_rank_association"])
            p = float(r["geography_block_permutation_p_two_sided"])
            geo_ret = float(r["geo_loo_sign_retention"])
            year_ret = float(r["year_loo_sign_retention"])
            n = int(r["primary_row_count"])
            ny = int(r["primary_target_year_count"])
        except ValueError:
            errors.append(f"invalid numeric screen row: {r.get('target_id')} x {r.get('candidate_id')}")
            continue
        expected_stable = n >= 60 and ny >= 4 and abs(assoc) >= 0.20 and p <= 0.10 and geo_ret >= 0.90 and year_ret >= 0.80
        if truth(r["stable_association_signal"]) != expected_stable:
            errors.append(f"stable-signal classification mismatch: {r['target_id']} x {r['candidate_id']}")
        if truth(r["stable_association_signal"]):
            stable_pairs.append((r["target_id"], r["candidate_id"]))
        if r["causal_claim"].lower() != "false" or r["policy_priority_claim"].lower() != "false" or r["monetary_wasted_potential_claim"].lower() != "false":
            errors.append(f"forbidden interpretation enabled in screen: {r['target_id']} x {r['candidate_id']}")
        if int(r["permutation_count"]) != 4999 or int(r["permutation_seed"]) != 140014:
            errors.append(f"row permutation contract drift: {r['target_id']} x {r['candidate_id']}")
        if not all(math.isfinite(float(r[key])) for key in ("within_year_pearson", "within_year_rank_association", "geography_block_permutation_p_two_sided")):
            errors.append(f"non-finite primary statistic: {r['target_id']} x {r['candidate_id']}")

    manifest_signals = {(r["target_id"], r["candidate_id"]) for r in manifest.get("stable_association_signals", [])}
    if set(stable_pairs) != manifest_signals or len(stable_pairs) != manifest.get("stable_association_signal_count"):
        errors.append("manifest stable-signal summary drift")

    geo_by_pair: dict[tuple[str, str], int] = {}
    for r in geo:
        key = (r["target_id"], r["candidate_id"])
        geo_by_pair[key] = geo_by_pair.get(key, 0) + 1
        if r["claim_scope"] != "association_stability_not_causal":
            errors.append("geography LOO claim-scope drift")
    year_by_pair: dict[tuple[str, str], int] = {}
    for r in years:
        key = (r["target_id"], r["candidate_id"])
        year_by_pair[key] = year_by_pair.get(key, 0) + 1
        if r["claim_scope"] != "association_stability_not_causal":
            errors.append("year LOO claim-scope drift")
    screen_by_pair = {(r["target_id"], r["candidate_id"]): r for r in screen}
    for pair, r in screen_by_pair.items():
        if geo_by_pair.get(pair) != int(r["primary_geography_count"]):
            errors.append(f"geography LOO coverage mismatch: {pair}")
        if year_by_pair.get(pair) != int(r["primary_target_year_count"]):
            errors.append(f"year LOO coverage mismatch: {pair}")

    if len(fav) != 11 or {(r["target_id"], r["candidate_id"]) for r in fav} != EXPECTED_PAIRS:
        errors.append("favorable-peer sensitivity pair set drift")
    if any(r["can_replace_primary_expected_gap_screen"].lower() != "false" or r["causal_claim"].lower() != "false" for r in fav):
        errors.append("favorable-peer sensitivity upgraded beyond authorization")
    if len(adj) != 1 or (adj[0].get("target_id"), adj[0].get("candidate_id")) != ("unemployment_rate", "underemployment_rate"):
        errors.append("outcome-adjacent sensitivity drift")
    elif adj[0].get("stable_association_signal_authorized", "").lower() != "false" or adj[0].get("causal_claim", "").lower() != "false":
        errors.append("outcome-adjacent sensitivity improperly authorized")

    return {
        "schema": "ranah-observatory/milestone14-audit/v1",
        "criterion": manifest.get("criterion"),
        "screen_pair_count": len(screen),
        "core_pair_count": sum(r["screen_type"] == "core" for r in screen),
        "health_extension_pair_count": sum(r["screen_type"] == "health_extension" for r in screen),
        "stable_association_signal_count": len(stable_pairs),
        "stable_association_pairs": [f"{a}:{b}" for a, b in sorted(stable_pairs)],
        "causal_analysis_performed": manifest.get("causal_analysis_performed") is True,
        "milestone14_complete": manifest.get("milestone14_complete") is True and not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = audit()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["errors"]:
        return 1
    if args.require_complete and report.get("milestone14_complete") is not True:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
