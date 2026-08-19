#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIORITIES = ROOT / "data/analysis/engine/data_value_readiness_v1/m23-data-priorities.csv"
READINESS = ROOT / "data/analysis/engine/data_value_readiness_v1/m23-model-readiness.csv"
ACTIONS = ROOT / "data/analysis/engine/data_value_readiness_v1/m23-next-actions.csv"
MANIFEST = ROOT / "data/manifests/milestone23_data_value_model_readiness.json"
SOURCES = ROOT / "data/registries/m23-official-source-candidates.csv"
SPEC = ROOT / "research/MILESTONE23_DATA_VALUE_MODEL_READINESS_SPEC.md"
DOC = ROOT / "docs/MILESTONE23_DATA_VALUE_MODEL_READINESS.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    priorities = rows(PRIORITIES)
    readiness = rows(READINESS)
    actions = rows(ACTIONS)
    sources = rows(SOURCES)

    assert manifest["schema"] == "ranah-observatory/milestone23-data-value-model-readiness/v1"
    assert manifest["milestone23_complete"] is True
    assert manifest["statistical_model_fit"] is False
    assert manifest["numeric_priority_score_created"] is False
    assert manifest["posthoc_algorithm_search_authorized"] is False

    assert len(priorities) == 7
    assert len(readiness) == 8
    assert len(actions) == 5
    assert len(sources) == 5
    assert [row["priority_tier"] for row in priorities] == ["A", "A", "A", "B", "B", "B", "C"]
    assert [int(row["priority_order"]) for row in priorities] == list(range(1, 8))
    assert all(row["new_model_before_acquisition_authorized"] == "False" for row in priorities)

    source_ids = {row["source_candidate_id"] for row in sources}
    for row in priorities[:6]:
        assert row["primary_source_candidate_id"] in source_ids
    assert {row["verified_date"] for row in sources} == {"2026-08-19"}

    blocked_states = {"data_limited", "identification_limited", "component_limited"}
    for row in readiness:
        if row["readiness_state"] in blocked_states:
            assert row["new_algorithm_priority"].startswith("blocked_")

    assert actions[0]["work_package"] == "national_comparator_bps_discovery_and_harvest"
    assert actions[0]["dependency"] == "BPS_API_KEY repository secret"
    assert actions[0]["model_fit_authorized_in_same_package"] == "False"
    assert actions[-1]["model_fit_authorized_in_same_package"] == "True"

    assert manifest["priority_tier_counts"] == {"A": 3, "B": 3, "C": 1}
    assert manifest["first_next_action"] == actions[0]["work_package"]
    assert manifest["bps_repository_secret_expected"] is True
    assert manifest["user_contribution_required_for_first_action"] is False

    for key, path in {
        "data_priorities": PRIORITIES,
        "model_readiness": READINESS,
        "next_actions": ACTIONS,
    }.items():
        assert manifest["outputs"][key]["sha256"] == sha256(path)
    assert manifest["inputs"]["source_registry"]["sha256"] == sha256(SOURCES)
    assert manifest["inputs"]["spec"]["sha256"] == sha256(SPEC)

    doc = DOC.read_text(encoding="utf-8").lower()
    assert "evidence acquisition rather than algorithm escalation" in doc
    assert "does not guarantee" in doc
    assert "continuous 1945" in doc

    print(json.dumps({
        "milestone23_audit": "pass",
        "priority_tier_counts": manifest["priority_tier_counts"],
        "first_next_action": manifest["first_next_action"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
