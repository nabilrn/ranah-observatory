from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
M11 = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
M19 = ROOT / "data/manifests/milestone19_dynamic_forecast_engine.json"
PUBLIC_OVERVIEW = ROOT / "site/data/overview.json"
M11_WORKFLOW = ROOT / ".github/workflows/milestone11-expected-performance-repro.yml"
M19_WORKFLOW = ROOT / ".github/workflows/milestone19-dynamic-forecast-repro.yml"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def validate() -> dict[str, Any]:
    m11 = load_json(M11)
    assert m11["milestone11_complete"] is True
    assert m11["crossfit_prediction_count"] == 342
    assert m11["expected_crossfit_prediction_count"] == 342
    assert m11["geography_count"] == 19
    assert m11["target_year_count"] == 6
    assert m11["benchmark_qualified_target_count"] == 3
    assert set(m11["benchmark_qualified_target_ids"]) == {
        "poverty_rate",
        "unemployment_rate",
        "real_grdp_growth",
    }
    assert m11["benchmark_failed_target_ids"] == []
    assert m11["nested_inner_cv_used"] is True
    assert m11["primary_predictions_cross_fitted_by_geography"] is True
    assert m11["focal_geography_excluded_from_own_model_fit"] is True
    assert m11["focal_geography_excluded_from_own_uncertainty_calibration"] is True
    assert m11["features_selected_before_model_fit"] is True
    assert m11["target_specific_feature_search_performed"] is False
    assert m11["posthoc_model_replacement_performed"] is False
    assert m11["causal_analysis_performed"] is False

    for target_id, metrics in m11["target_metrics"].items():
        assert metrics["benchmark_qualified"] is True, target_id
        assert metrics["model_rmse"] < metrics["naive_rmse"], target_id
        assert metrics["model_mae"] < metrics["naive_mae"], target_id

    m19 = load_json(M19)
    assert m19["milestone19_complete"] is True
    assert m19["strictly_out_of_time_backtest"] is True
    assert m19["backtest_prediction_count"] == 285
    assert m19["backtest_prediction_count_per_target"] == 95
    assert m19["geography_count"] == 19
    assert m19["outer_forecast_years"] == [2021, 2022, 2023, 2024, 2025]
    assert m19["forecast_qualified_target_count"] == 0
    assert m19["forecast_qualified_target_ids"] == []
    assert set(m19["forecast_blocked_target_ids"]) == {
        "poverty_rate",
        "unemployment_rate",
        "real_grdp_growth",
    }
    assert m19["forecast_blocked_target_count"] == 3
    assert m19["persistence_benchmark_used"] is True
    assert m19["qualification_requires_rmse_and_mae_improvement"] is True
    assert m19["posthoc_algorithm_search_performed"] is False
    assert m19["causal_claim_authorized"] is False

    for result in m19["target_results"]:
        assert result["forecast_qualified"] is False, result["target_id"]
        assert result["dynamic_ridge_rmse"] >= result["persistence_rmse"], result["target_id"]
        assert result["dynamic_ridge_mae"] >= result["persistence_mae"], result["target_id"]

    overview = load_json(PUBLIC_OVERVIEW)
    headline = next(
        item for item in overview["headline_stats"]
        if "N19_FORECAST_FAILURE" in item.get("source_claim_ids", [])
    )
    assert headline["value"] == "0 / 3"
    forecast_story = next(item for item in overview["stories"] if item["id"] == "forecast-failure")
    assert forecast_story["evidence_state"] == "negative_result"
    assert "persistence" in forecast_story["plain_language"]
    assert "forecast substantif" in forecast_story["plain_language"]

    m11_workflow = M11_WORKFLOW.read_text(encoding="utf-8")
    for token in (
        "Rebuild Milestone 11 cross-fitted engine",
        "Enforce Milestone 11 completion audit",
        "Run Milestone 11 focused tests",
        "Require byte-identical committed M11 outputs",
    ):
        assert token in m11_workflow, f"M11 reproducibility workflow lost token: {token}"

    m19_workflow = M19_WORKFLOW.read_text(encoding="utf-8")
    for token in (
        "Rebuild M19 artifacts",
        "Audit M19 outputs",
        "Run focused M19 tests",
        "Verify byte-identical outputs",
    ):
        assert token in m19_workflow, f"M19 reproducibility workflow lost token: {token}"

    return {
        "model_testing_gate_passed": True,
        "m11_crossfit_predictions": m11["crossfit_prediction_count"],
        "m11_benchmark_qualified_targets": m11["benchmark_qualified_target_count"],
        "m19_out_of_time_predictions": m19["backtest_prediction_count"],
        "m19_forecast_qualified_targets": m19["forecast_qualified_target_count"],
        "m19_forecast_blocked_targets": m19["forecast_blocked_target_count"],
        "posthoc_algorithm_search_performed": m19["posthoc_algorithm_search_performed"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
