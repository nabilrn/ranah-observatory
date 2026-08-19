from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKTEST = ROOT / "data/analysis/engine/climate_regime_shift_v1/m21-rolling-backtest.csv"
CANDIDATES = ROOT / "data/analysis/engine/climate_regime_shift_v1/m21-breakpoint-candidates.csv"
FULL = ROOT / "data/analysis/engine/climate_regime_shift_v1/m21-full-series-regime.csv"
MANIFEST = ROOT / "data/manifests/milestone21_climate_regime_shift.json"
DESIGN = ROOT / "data/manifests/milestone21_design_gate.json"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_bool(value: str) -> bool:
    assert value in {"True", "False"}
    return value == "True"


def test_prefit_design_is_locked_and_noncausal() -> None:
    gate = json.loads(DESIGN.read_text(encoding="utf-8"))
    assert gate["design_locked_before_model_fit"] is True
    assert gate["minimum_segment_years"] == 10
    assert gate["outer_forecast_count"] == 20
    assert gate["breakpoint_selection_loss"] == "training_mae"
    assert gate["posthoc_algorithm_search_authorized"] is False
    assert gate["climate_change_attribution_authorized"] is False
    assert gate["causal_analysis_authorized"] is False


def test_backtest_is_strictly_out_of_time() -> None:
    backtest = rows(BACKTEST)
    assert len(backtest) == 20
    assert [int(row["forecast_year"]) for row in backtest] == list(range(2006, 2026))
    for row in backtest:
        assert int(row["training_end_year"]) == int(row["forecast_year"]) - 1
        assert int(row["training_start_year"]) == 1981
        assert int(row["pre_segment_year_count"]) >= 10
        assert int(row["post_segment_year_count"]) >= 10
        assert int(row["selected_break_year"]) < int(row["training_end_year"])


def test_candidate_breaks_respect_minimum_segments() -> None:
    candidates = rows(CANDIDATES)
    assert len(candidates) == 26
    selected = [row for row in candidates if as_bool(row["selected_full_series_break"])]
    assert len(selected) == 1
    for row in candidates:
        assert int(row["pre_segment_year_count"]) >= 10
        assert int(row["post_segment_year_count"]) >= 10


def test_public_authorization_requires_all_gates() -> None:
    row = rows(FULL)[0]
    authorized = as_bool(row["public_claim_authorized"])
    if authorized:
        assert as_bool(row["predictive_qualification_pass"])
        assert as_bool(row["rolling_break_stability_pass"])
        assert as_bool(row["full_break_within_3y_of_rolling_median"])
        assert as_bool(row["pre_post_slopes_opposite_nonzero"])
        assert row["classification"] == "predictively_supported_trend_regime_shift"
    else:
        assert row["classification"] == "regime_shift_not_qualified"


def test_pettitt_is_secondary_only_and_claim_boundaries_hold() -> None:
    row = rows(FULL)[0]
    assert row["pettitt_role"] == "secondary_diagnostic_only"
    assert row["station_observation_equivalence"] == "False"
    assert row["climate_change_attribution_performed"] == "False"
    assert row["causal_analysis_performed"] == "False"
    assert row["historical_boundary_continuity_claimed"] == "False"


def test_manifest_matches_outputs() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["milestone21_complete"] is True
    assert manifest["input_year_count"] == 45
    assert manifest["outer_forecast_count"] == 20
    assert manifest["minimum_segment_years"] == 10
    assert manifest["pettitt_role"] == "secondary_diagnostic_only"
    assert manifest["posthoc_algorithm_search_performed"] is False
    assert manifest["climate_change_attribution_performed"] is False
    assert manifest["causal_analysis_performed"] is False
    assert manifest["station_observation_equivalence"] is False
    assert manifest["historical_boundary_continuity_claimed"] is False
