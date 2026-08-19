from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIORITIES = ROOT / "data/analysis/engine/data_value_readiness_v1/m23-data-priorities.csv"
READINESS = ROOT / "data/analysis/engine/data_value_readiness_v1/m23-model-readiness.csv"
ACTIONS = ROOT / "data/analysis/engine/data_value_readiness_v1/m23-next-actions.csv"
MANIFEST = ROOT / "data/manifests/milestone23_data_value_model_readiness.json"
SOURCES = ROOT / "data/registries/m23-official-source-candidates.csv"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_priority_structure_is_explicit_not_numeric_scoring() -> None:
    priorities = rows(PRIORITIES)
    assert len(priorities) == 7
    assert [int(row["priority_order"]) for row in priorities] == list(range(1, 8))
    assert [row["priority_tier"] for row in priorities[:3]] == ["A", "A", "A"]
    assert [row["priority_tier"] for row in priorities[3:6]] == ["B", "B", "B"]
    assert priorities[6]["priority_tier"] == "C"
    assert all(row["new_model_before_acquisition_authorized"] == "False" for row in priorities)
    assert priorities[0]["data_family"] == "national_comparable_regional_panel"
    assert priorities[1]["data_family"] == "public_finance_panel"
    assert priorities[2]["data_family"] == "complete_disaster_risk_chain"


def test_official_source_snapshot_is_dated_and_bounded() -> None:
    sources = rows(SOURCES)
    assert len(sources) == 5
    assert {row["verified_date"] for row in sources} == {"2026-08-19"}
    assert len({row["source_candidate_id"] for row in sources}) == 5
    bps = next(row for row in sources if row["source_candidate_id"] == "bps_webapi_national")
    assert bps["credential_state"] == "repository_secret_BPS_API_KEY_present"
    assert "still require discovery" in bps["known_limit"]


def test_model_readiness_blocks_algorithm_escalation_when_data_or_identification_limited() -> None:
    readiness = rows(READINESS)
    assert len(readiness) == 8
    states = {row["readiness_state"] for row in readiness}
    assert states == {"ready_with_current_data", "partially_ready", "data_limited", "identification_limited", "component_limited"}
    forecast = next(row for row in readiness if row["analytical_task"] == "one_year_ahead_socioeconomic_forecast")
    assert forecast["readiness_state"] == "data_limited"
    assert forecast["new_algorithm_priority"] == "blocked_before_data_expansion"
    causal = next(row for row in readiness if row["analytical_task"] == "rainfall_to_unemployment_causal_explanation")
    assert causal["readiness_state"] == "identification_limited"
    assert causal["new_algorithm_priority"] == "blocked_by_identification_not_predictor_count"


def test_next_action_requires_no_user_for_first_bps_probe() -> None:
    actions = rows(ACTIONS)
    assert len(actions) == 5
    assert [int(row["sequence"]) for row in actions] == [1, 2, 3, 4, 5]
    assert actions[0]["work_package"] == "national_comparator_bps_discovery_and_harvest"
    assert actions[0]["dependency"] == "BPS_API_KEY repository secret"
    assert actions[0]["model_fit_authorized_in_same_package"] == "False"
    assert actions[-1]["model_fit_authorized_in_same_package"] == "True"


def test_manifest_declares_non_model_nature_and_priority_counts() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["milestone23_complete"] is True
    assert manifest["statistical_model_fit"] is False
    assert manifest["numeric_priority_score_created"] is False
    assert manifest["posthoc_algorithm_search_authorized"] is False
    assert manifest["official_source_candidate_count"] == 5
    assert manifest["data_priority_family_count"] == 7
    assert manifest["priority_tier_counts"] == {"A": 3, "B": 3, "C": 1}
    assert manifest["model_readiness_task_count"] == 8
    assert manifest["next_action_count"] == 5
    assert manifest["first_next_action"] == "national_comparator_bps_discovery_and_harvest"
    assert manifest["bps_repository_secret_expected"] is True
    assert manifest["user_contribution_required_for_first_action"] is False
