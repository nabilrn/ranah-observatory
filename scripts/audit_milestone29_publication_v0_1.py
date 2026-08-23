#!/usr/bin/env python3
"""Offline completeness audit for the frozen Ranah Observatory v0.1 publication package."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "publication" / "v0.1"

ALLOWED_STATES = {
    "publishable_bounded",
    "publishable_negative_result",
    "context_only",
    "blocked",
}

REQUIRED_NEGATIVE_IDS = {
    "C08_EARTHQUAKE_NULL",
    "N19_FORECAST_FAILURE",
    "N20_MONOTONIC_RAINFALL",
    "N21_REGIME_SHIFT",
    "N22_SCHOOLING_POVERTY_TRAJECTORY",
}

REQUIRED_BLOCKED_IDS = {
    "B01_MONETARY_WASTED_POTENTIAL",
    "B02_THEORETICAL_MAXIMUM",
    "B03_CAUSAL_RESIDUAL",
    "B04_GUARANTEED_POLICY_GAIN",
    "B05_CAUSAL_RAINFALL_UNEMPLOYMENT",
    "B06_EVENT_COUNTS_AS_IMPACT",
    "B07_COMPOSITE_DISASTER_RISK",
    "B08_SENSITIVITY_AS_POLICY_EFFECT",
    "B09_POLICY_RANKING",
}

REQUIRED_CONTEXT_IDS = {
    "X24_NATIONAL_COMPARATOR",
    "X25_PUBLIC_FINANCE",
    "X26_DISASTER_COMPONENTS",
    "X27_INVESTMENT_HISTORY",
    "X28_BROADER_PANEL",
}

EXPECTED_FROZEN_BASE = "e1571e63fd19222c0f6112d340b61ed5d7996e58"
CLAIM_REF_RE = re.compile(r"\[([A-Z][A-Z0-9_]+)\]")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def require_file(path: Path) -> None:
    assert path.is_file(), f"required file missing: {path.relative_to(ROOT)}"


def main() -> None:
    release = read_json(PUB / "release-manifest.json")
    assert release["schema"] == "ranah-observatory/publication-v0.1-release-manifest/v1"
    assert release["frozen_research_base_commit"] == EXPECTED_FROZEN_BASE
    assert set(release["claim_states"]) == ALLOWED_STATES
    assert release["bmkg_station_daily_validation_required_for_v0_1"] is False
    assert release["offline_completeness_certificate_required_before_release"] is True

    locked = release["locked_rules"]
    expected_false = {
        "new_source_acquisition",
        "new_statistical_or_ml_model_fit",
        "posthoc_model_search",
        "model_refit_for_headline_improvement",
        "imputation",
        "missing_as_zero",
        "geography_backcasting",
        "new_composite_score",
        "monetary_gap_aggregation",
        "causal_claim_upgrade",
        "policy_treatment_effect_interpretation",
        "cost_benefit_ranking",
    }
    expected_true = {
        "negative_results_must_remain_visible",
        "m18_blocked_claims_must_remain_blocked",
        "every_substantive_manuscript_claim_requires_claim_id",
    }
    for key in expected_false:
        assert locked[key] is False, key
    for key in expected_true:
        assert locked[key] is True, key

    for rel in release["required_publication_outputs"]:
        require_file(ROOT / rel)
    require_file(PUB / "completeness-certificate.json")

    for rel in release["upstream_manifest_paths"]:
        require_file(ROOT / rel)
    for rel in release["upstream_summary_paths"]:
        require_file(ROOT / rel)

    claims = read_csv(PUB / "claim-ledger.csv")
    assert claims, "claim ledger is empty"
    ids = [row["claim_id"] for row in claims]
    assert len(ids) == len(set(ids)), "duplicate claim IDs"
    claim_by_id = {row["claim_id"]: row for row in claims}
    assert {row["state"] for row in claims} <= ALLOWED_STATES

    for row in claims:
        assert row["statement"].strip(), row["claim_id"]
        assert row["authorized_interpretation"].strip(), row["claim_id"]
        assert row["prohibited_upgrade"].strip(), row["claim_id"]
        source = ROOT / row["source_artifact"]
        require_file(source)

    assert REQUIRED_NEGATIVE_IDS <= set(ids)
    assert REQUIRED_BLOCKED_IDS <= set(ids)
    assert REQUIRED_CONTEXT_IDS <= set(ids)
    for claim_id in REQUIRED_NEGATIVE_IDS:
        assert claim_by_id[claim_id]["state"] == "publishable_negative_result", claim_id
    for claim_id in REQUIRED_BLOCKED_IDS:
        assert claim_by_id[claim_id]["state"] == "blocked", claim_id
    for claim_id in REQUIRED_CONTEXT_IDS:
        assert claim_by_id[claim_id]["state"] == "context_only", claim_id

    state_counts = Counter(row["state"] for row in claims)
    assert state_counts == Counter(
        {
            "publishable_bounded": 11,
            "publishable_negative_result": 5,
            "context_only": 5,
            "blocked": 9,
        }
    ), state_counts

    evidence = read_csv(PUB / "evidence-table.csv")
    tables = read_csv(PUB / "table-plan.csv")
    figures = read_csv(PUB / "figure-plan.csv")
    assert len(evidence) == 17, len(evidence)
    assert len(tables) == 7, len(tables)
    assert len(figures) == 6, len(figures)
    for row in evidence:
        require_file(ROOT / row["artifact"])
        assert row["claim_state"] in ALLOWED_STATES

    manuscript = (PUB / "manuscript.md").read_text(encoding="utf-8")
    manuscript_refs = set(CLAIM_REF_RE.findall(manuscript))
    unknown_refs = manuscript_refs - set(ids)
    assert not unknown_refs, f"unknown manuscript claim IDs: {sorted(unknown_refs)}"
    missing_refs = set(ids) - manuscript_refs
    assert not missing_refs, f"ledger claims not referenced by manuscript: {sorted(missing_refs)}"

    for phrase in (
        "zero targets qualify",
        "zero of 19 current-boundary geographies pass",
        "regime_shift_not_qualified",
        "nine high-salience claims remain blocked",
    ):
        assert phrase.lower() in manuscript.lower(), f"required fail-closed wording missing: {phrase}"

    certificate = read_json(PUB / "completeness-certificate.json")
    assert certificate["schema"] == "ranah-observatory/publication-v0.1-completeness-certificate/v1"
    assert certificate["frozen_research_base_commit"] == EXPECTED_FROZEN_BASE
    assert certificate["offline_verification_passed"] is True
    assert certificate["claim_count"] == len(claims)
    assert certificate["state_counts"] == dict(sorted(state_counts.items()))
    assert certificate["evidence_row_count"] == len(evidence)
    assert certificate["table_plan_count"] == len(tables)
    assert certificate["figure_plan_count"] == len(figures)
    assert certificate["manuscript_unique_claim_reference_count"] == len(manuscript_refs)
    assert certificate["all_ledger_claims_referenced_in_manuscript"] is True
    assert certificate["required_negative_results_retained"] is True
    assert certificate["all_nine_m18_blocked_claims_retained"] is True
    assert certificate["bmkg_station_daily_validation_required_for_v0_1"] is False

    print(
        {
            "publication": "v0.1",
            "frozen_base": EXPECTED_FROZEN_BASE,
            "claims": len(claims),
            "state_counts": dict(sorted(state_counts.items())),
            "evidence_rows": len(evidence),
            "tables": len(tables),
            "figures": len(figures),
            "manuscript_claim_refs": len(manuscript_refs),
            "offline_verification": "passed",
        }
    )


if __name__ == "__main__":
    main()
