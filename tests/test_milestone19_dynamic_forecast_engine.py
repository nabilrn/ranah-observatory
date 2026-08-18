from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data/analysis/engine/dynamic_forecast_v1"
MANIFEST = ROOT / "data/manifests/milestone19_dynamic_forecast_engine.json"
GATE = ROOT / "data/manifests/milestone19_design_gate.json"


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUT_DIR / name).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_prefit_gate_is_locked_and_fail_closed() -> None:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    assert gate["schema"] == "ranah-observatory/milestone19-design-gate/v1"
    assert gate["model_fit"] is False
    assert gate["backtest_results_known"] is False
    assert gate["forecast_results_known"] is False
    assert gate["posthoc_algorithm_search_authorized"] is False
    assert gate["outer_forecast_years"] == [2021, 2022, 2023, 2024, 2025]
    assert gate["target_ids"] == ["poverty_rate", "unemployment_rate", "real_grdp_growth"]


def test_output_footprints_and_temporal_contract() -> None:
    frame = read_csv("m19-model-frame.csv")
    backtest = read_csv("m19-backtest-predictions.csv")
    summary = read_csv("m19-target-summary.csv")
    forecasts = read_csv("m19-forecast-2026.csv")

    assert len(frame) == 133
    assert len(backtest) == 285
    assert len(summary) == 3
    assert len(forecasts) == 57

    assert {int(row["forecast_year"]) for row in backtest} == {2021, 2022, 2023, 2024, 2025}
    assert all(row["strictly_out_of_time"] == "True" for row in backtest)
    assert all(int(row["training_end_year"]) < int(row["forecast_year"]) for row in backtest)
    assert all(int(row["information_cutoff_year"]) == int(row["forecast_year"]) - 1 for row in backtest)

    assert {int(row["forecast_year"]) for row in forecasts} == {2026}
    assert all(int(row["information_cutoff_year"]) == 2025 for row in forecasts)
    assert all(row["claim_type"] == "one_year_ahead_model_forecast_not_causal" for row in forecasts)


def test_persistence_benchmark_is_exact_own_lag() -> None:
    backtest = read_csv("m19-backtest-predictions.csv")
    frame = read_csv("m19-model-frame.csv")
    by_key = {
        (row["geography_id"], int(row["target_year"])): row
        for row in frame
    }
    for row in backtest:
        source = by_key[(row["geography_id"], int(row["forecast_year"]))]
        target = row["target_id"]
        assert float(row["persistence_prediction"]) == float(source[f"lag1_{target}"])


def test_target_qualification_is_fail_closed() -> None:
    summary = read_csv("m19-target-summary.csv")
    forecasts = read_csv("m19-forecast-2026.csv")
    qualification = {}
    for row in summary:
        expected = (
            float(row["dynamic_ridge_rmse"]) < float(row["persistence_rmse"])
            and float(row["dynamic_ridge_mae"]) < float(row["persistence_mae"])
        )
        actual = row["forecast_qualified"] == "True"
        assert actual == expected
        qualification[row["target_id"]] = actual

    for row in forecasts:
        authorized = row["public_substantive_use_authorized"] == "True"
        assert authorized == qualification[row["target_id"]]


def test_manifest_claim_boundaries() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema"] == "ranah-observatory/milestone19-dynamic-forecast-engine/v1"
    assert manifest["milestone19_complete"] is True
    assert manifest["strictly_out_of_time_backtest"] is True
    assert manifest["persistence_benchmark_used"] is True
    assert manifest["posthoc_algorithm_search_performed"] is False
    assert manifest["causal_analysis_performed"] is False
    assert manifest["causal_claim_authorized"] is False
    assert manifest["policy_counterfactual_authorized"] is False
    assert manifest["forecast_is_guaranteed_future"] is False
    assert manifest["backtest_prediction_count"] == 285
    assert manifest["forecast_2026_row_count"] == 57
