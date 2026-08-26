from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC = ROOT / "site" / "data" / "readiness.json"
M18_MANIFEST = ROOT / "data" / "manifests" / "milestone18_final_analytical_synthesis.json"
M18_READINESS = ROOT / "data" / "analysis" / "engine" / "final_synthesis_v1" / "m18-research-question-readiness.csv"

EXPECTED_SOURCE = {
    "manifest_path": "data/manifests/milestone18_final_analytical_synthesis.json",
    "readiness_path": "data/analysis/engine/final_synthesis_v1/m18-research-question-readiness.csv",
}
EXPECTED_STATES = {
    "RQ1": "bounded_partial",
    "RQ2": "bounded_answer",
    "RQ3": "bounded_partial",
    "RQ4": "bounded_answer",
    "RQ5": "not_action_ready",
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {row["research_question_id"]: row for row in rows}
    assert len(result) == len(rows), "duplicate M18 research question id"
    return result


def validate(public_path: Path = DEFAULT_PUBLIC) -> dict[str, int]:
    public = load_json(public_path)
    manifest = load_json(M18_MANIFEST)
    source_rows = load_rows(M18_READINESS)

    assert public["schema"] == "ranah-observatory/public-research-readiness/v1"
    assert public["version"] == "0.1.0"
    assert public["language"] == "id"
    assert public["source"] == EXPECTED_SOURCE

    assert manifest["milestone"] == 18
    assert manifest["milestone18_complete"] is True
    assert manifest["phase2_analytical_engine_complete"] is True
    assert manifest["research_question_count"] == 5
    assert manifest["fully_resolved_research_question_count"] == 0
    assert manifest["research_question_readiness_counts"] == {
        "bounded_answer": 2,
        "bounded_partial": 2,
        "not_action_ready": 1,
    }
    assert manifest["policy_ranking_performed"] is False
    assert manifest["definitive_monetary_wasted_potential_estimated"] is False

    summary = public["summary"]
    assert summary == {
        "question_count": 5,
        "fully_resolved_count": 0,
        "bounded_answer_count": 2,
        "bounded_partial_count": 2,
        "not_action_ready_count": 1,
        "policy_ranking_performed": False,
    }

    questions = public["questions"]
    assert isinstance(questions, list) and len(questions) == 5
    public_by_id = {row["id"]: row for row in questions}
    assert set(public_by_id) == set(EXPECTED_STATES) == set(source_rows)

    for question_id, expected_state in EXPECTED_STATES.items():
        row = public_by_id[question_id]
        source = source_rows[question_id]
        assert row["readiness_state"] == expected_state == source["readiness_state"]
        assert row["evidence_basis"] == source["evidence_basis"]
        assert row["fully_resolved"] is False
        assert source["fully_resolved"] == "False"
        for field in ("title", "current_answer", "limitation", "next_evidence"):
            assert str(row.get(field, "")).strip(), f"{question_id}: missing {field}"
        forbidden = {"recommended_policy", "policy_rank", "expected_policy_impact", "cost_benefit"}
        assert not forbidden.intersection(row), f"{question_id}: unauthorized policy field"

    action_copy = " ".join(
        str(public_by_id["RQ5"][field])
        for field in ("current_answer", "limitation", "next_evidence")
    ).casefold()
    assert "belum" in action_copy
    assert "ranking" in action_copy or "meranking" in action_copy
    assert "kebijakan" in action_copy

    return {
        "questions": len(questions),
        "fully_resolved": summary["fully_resolved_count"],
        "not_action_ready": summary["not_action_ready_count"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
