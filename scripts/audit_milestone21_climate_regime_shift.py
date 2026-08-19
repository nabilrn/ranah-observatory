#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKTEST = ROOT / "data/analysis/engine/climate_regime_shift_v1/m21-rolling-backtest.csv"
CANDIDATES = ROOT / "data/analysis/engine/climate_regime_shift_v1/m21-breakpoint-candidates.csv"
FULL = ROOT / "data/analysis/engine/climate_regime_shift_v1/m21-full-series-regime.csv"
MANIFEST = ROOT / "data/manifests/milestone21_climate_regime_shift.json"
DESIGN = ROOT / "data/manifests/milestone21_design_gate.json"
SPEC = ROOT / "research/MILESTONE21_CLIMATE_REGIME_SHIFT_SPEC.md"
DOC = ROOT / "docs/MILESTONE21_CLIMATE_REGIME_SHIFT.md"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_bool(value: str) -> bool:
    if value not in {"True", "False"}:
        raise AssertionError(value)
    return value == "True"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    backtest = rows(BACKTEST)
    candidates = rows(CANDIDATES)
    full_rows = rows(FULL)

    assert manifest["schema"] == "ranah-observatory/milestone21-climate-regime-shift/v1"
    assert manifest["milestone21_complete"] is True
    assert len(backtest) == 20
    assert len(candidates) == 26
    assert len(full_rows) == 1
    assert [int(row["forecast_year"]) for row in backtest] == list(range(2006, 2026))

    for row in backtest:
        assert int(row["training_end_year"]) == int(row["forecast_year"]) - 1
        assert int(row["pre_segment_year_count"]) >= 10
        assert int(row["post_segment_year_count"]) >= 10

    assert sum(as_bool(row["selected_full_series_break"]) for row in candidates) == 1
    assert design["design_locked_before_model_fit"] is True
    assert design["posthoc_algorithm_search_authorized"] is False
    assert manifest["posthoc_algorithm_search_performed"] is False
    assert manifest["pettitt_role"] == "secondary_diagnostic_only"

    full = full_rows[0]
    authorized = as_bool(full["public_claim_authorized"])
    if authorized:
        assert as_bool(full["predictive_qualification_pass"])
        assert as_bool(full["rolling_break_stability_pass"])
        assert as_bool(full["full_break_within_3y_of_rolling_median"])
        assert as_bool(full["pre_post_slopes_opposite_nonzero"])
        assert full["classification"] == "predictively_supported_trend_regime_shift"
    else:
        assert full["classification"] == "regime_shift_not_qualified"

    assert full["station_observation_equivalence"] == "False"
    assert full["climate_change_attribution_performed"] == "False"
    assert full["causal_analysis_performed"] == "False"
    assert full["historical_boundary_continuity_claimed"] == "False"

    for key, path in {
        "rolling_backtest": BACKTEST,
        "breakpoint_candidates": CANDIDATES,
        "full_series_regime": FULL,
    }.items():
        assert manifest["outputs"][key]["sha256"] == sha256(path)
    assert manifest["inputs"]["design_gate"]["sha256"] == sha256(DESIGN)
    assert manifest["inputs"]["spec"]["sha256"] == sha256(SPEC)

    assert manifest["climate_change_attribution_performed"] is False
    assert manifest["causal_analysis_performed"] is False
    assert manifest["station_observation_equivalence"] is False
    assert manifest["historical_boundary_continuity_claimed"] is False

    text = DOC.read_text(encoding="utf-8").lower()
    assert "regime-shift claim not qualified" in text
    assert "does not" in text

    print(json.dumps({
        "milestone21_audit": "pass",
        "classification": manifest["classification"],
        "full_series_selected_break_year": manifest["full_series_selected_break_year"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
