from __future__ import annotations

# This test module is also the non-analytical trigger for the temporary artifact freezer.
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAME = ROOT / "data/analysis/engine/hierarchical_trajectory_v1/m22-model-frame.csv"
PRED = ROOT / "data/analysis/engine/hierarchical_trajectory_v1/m22-outer-predictions.csv"
SUMMARY = ROOT / "data/analysis/engine/hierarchical_trajectory_v1/m22-indicator-summary.csv"
TRAJ = ROOT / "data/analysis/engine/hierarchical_trajectory_v1/m22-geography-trajectories.csv"
LOO = ROOT / "data/analysis/engine/hierarchical_trajectory_v1/m22-loo-slopes.csv"
MANIFEST = ROOT / "data/manifests/milestone22_hierarchical_socioeconomic_trajectory.json"
DESIGN = ROOT / "data/manifests/milestone22_design_gate.json"

INDICATORS = {
    "expected_years_schooling",
    "mean_years_schooling",
    "labor_force_participation",
    "unemployment_rate",
    "poverty_rate",
    "real_grdp_growth",
    "rice_yield",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_bool(value: str) -> bool:
    assert value in {"True", "False"}
    return value == "True"


def test_prefit_design_is_locked() -> None:
    gate = json.loads(DESIGN.read_text(encoding="utf-8"))
    assert gate["design_locked_before_model_fit"] is True
    assert set(gate["indicator_ids"]) == INDICATORS
    assert gate["indicator_count"] == 7
    assert gate["random_effect_penalty_grid"] == [0.01, 0.1, 1.0, 10.0, 100.0]
    assert gate["posthoc_indicator_selection_authorized"] is False
    assert gate["posthoc_model_search_authorized"] is False
    assert gate["causal_analysis_authorized"] is False


def test_output_footprints() -> None:
    frame = rows(FRAME)
    pred = rows(PRED)
    summary = rows(SUMMARY)
    traj = rows(TRAJ)
    loo = rows(LOO)
    assert len(frame) == 7 * 19 * 8
    assert len(pred) == 7 * 19 * 8
    assert len(summary) == 7
    assert len(traj) == 7 * 19
    assert len(loo) == 7 * 19 * 8
    assert {row["indicator_id"] for row in summary} == INDICATORS


def test_outer_predictions_are_exact_leave_one_calendar_year_out() -> None:
    pred = rows(PRED)
    by_indicator_year: dict[tuple[str, int], list[dict[str, str]]] = {}
    for row in pred:
        key = (row["indicator_id"], int(row["outer_held_year"]))
        by_indicator_year.setdefault(key, []).append(row)
        assert int(row["training_year_count"]) == 7
        assert float(row["selected_penalty"]) in {0.01, 0.1, 1.0, 10.0, 100.0}
    assert len(by_indicator_year) == 7 * 8
    assert all(len(group) == 19 for group in by_indicator_year.values())


def test_qualification_matches_both_metric_rule() -> None:
    for row in rows(SUMMARY):
        expected = (
            float(row["hierarchical_rmse"]) < float(row["independent_ols_rmse"])
            and float(row["hierarchical_mae"]) < float(row["independent_ols_mae"])
        )
        assert as_bool(row["hierarchical_trajectory_qualified"]) is expected


def test_public_trajectory_classification_is_fail_closed() -> None:
    for row in rows(TRAJ):
        classification = row["trajectory_classification"]
        qualified = as_bool(row["indicator_hierarchical_trajectory_qualified"])
        slope = float(row["hierarchical_slope_per_year"])
        minimum = float(row["loo_min_slope_per_year"])
        maximum = float(row["loo_max_slope_per_year"])
        retention = float(row["loo_same_direction_retention"])
        if classification == "persistent_increase":
            assert qualified
            assert slope > 0.0
            assert minimum > 0.0
            assert retention >= 0.875
        elif classification == "persistent_decrease":
            assert qualified
            assert slope < 0.0
            assert maximum < 0.0
            assert retention >= 0.875
        else:
            assert classification == "trajectory_not_robust"
        assert row["stability_envelope_is_confidence_interval"] == "False"
        assert row["causal_claim_authorized"] == "False"
        assert row["guaranteed_future_trajectory_authorized"] == "False"
        assert row["historical_boundary_continuity_claimed"] == "False"


def test_loo_slopes_complete_for_every_geography_indicator() -> None:
    loo = rows(LOO)
    groups: dict[tuple[str, str], set[int]] = {}
    for row in loo:
        groups.setdefault((row["indicator_id"], row["geography_id"]), set()).add(int(row["outer_held_year"]))
    assert len(groups) == 7 * 19
    assert all(years == set(range(2018, 2026)) for years in groups.values())


def test_manifest_boundaries() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["milestone22_complete"] is True
    assert manifest["indicator_count"] == 7
    assert manifest["geography_count"] == 19
    assert manifest["year_count"] == 8
    assert manifest["model_frame_row_count"] == 1064
    assert manifest["outer_prediction_count"] == 1064
    assert manifest["loo_slope_row_count"] == 1064
    assert manifest["geography_trajectory_row_count"] == 133
    assert manifest["stability_envelope_is_confidence_interval"] is False
    assert manifest["posthoc_indicator_selection_performed"] is False
    assert manifest["posthoc_model_search_performed"] is False
    assert manifest["causal_analysis_performed"] is False
    assert manifest["policy_effect_estimated"] is False
    assert manifest["historical_boundary_continuity_claimed"] is False
    assert manifest["guaranteed_future_trajectory_authorized"] is False
