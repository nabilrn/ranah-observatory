from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-geography-trends.csv"
LOO = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-leave-one-year-out.csv"
REGIONAL_ANNUAL = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv"
REGIONAL_TREND = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-regional-trend.csv"
MANIFEST = ROOT / "data/manifests/milestone20_historical_climate_trend.json"
DESIGN = ROOT / "data/manifests/milestone20_design_gate.json"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_bool(value: str) -> bool:
    assert value in {"True", "False"}
    return value == "True"


def test_prefit_design_is_fail_closed() -> None:
    gate = json.loads(DESIGN.read_text(encoding="utf-8"))
    assert gate["design_locked_before_model_fit"] is True
    assert gate["primary_slope_estimator"] == "theil_sen_median_pairwise_slope"
    assert gate["primary_trend_test"] == "hamed_rao_adjusted_mann_kendall"
    assert gate["multiple_testing_method"] == "holm_familywise"
    assert gate["posthoc_method_search_authorized"] is False
    assert gate["climate_change_attribution_authorized"] is False
    assert gate["causal_analysis_authorized"] is False


def test_output_footprint_and_source_semantics() -> None:
    geo = rows(GEO)
    loo = rows(LOO)
    regional = rows(REGIONAL_ANNUAL)
    regional_trend = rows(REGIONAL_TREND)
    assert len(geo) == 19
    assert len(loo) == 19 * 45
    assert len(regional) == 45
    assert len(regional_trend) == 1
    assert {int(row["n_years"]) for row in geo} == {45}
    assert {int(row["start_year"]) for row in geo} == {1981}
    assert {int(row["end_year"]) for row in geo} == {2025}
    assert {row["claim_type"] for row in geo} == {"model_estimate"}
    assert {row["station_observation_equivalence"] for row in geo} == {"False"}
    assert {row["historical_boundary_continuity_claimed"] for row in geo} == {"False"}


def test_public_claim_gate_cannot_bypass_guardrails() -> None:
    for row in rows(GEO):
        authorized = as_bool(row["public_claim_authorized"])
        classification = row["robust_monotonic_classification"]
        if authorized:
            assert classification in {"robust_monotonic_increase", "robust_monotonic_decrease"}
            assert float(row["hr_p_holm"]) < 0.05
            assert as_bool(row["ci_excludes_zero_same_direction"])
            assert as_bool(row["split_direction_consistent"])
            assert as_bool(row["loo_stability_pass"])
            assert float(row["loo_same_direction_retention"]) >= 0.90
        else:
            assert classification == "no_robust_monotonic_trend"


def test_holm_p_values_are_valid_and_not_smaller_than_raw() -> None:
    for row in rows(GEO):
        raw = float(row["hr_p"])
        adjusted = float(row["hr_p_holm"])
        assert 0.0 <= raw <= 1.0
        assert 0.0 <= adjusted <= 1.0
        assert adjusted + 1e-15 >= raw


def test_leave_one_year_out_is_complete_per_geography() -> None:
    loo = rows(LOO)
    by_geo: dict[str, set[int]] = {}
    for row in loo:
        by_geo.setdefault(row["geography_id"], set()).add(int(row["omitted_year"]))
    assert len(by_geo) == 19
    assert all(years == set(range(1981, 2026)) for years in by_geo.values())


def test_manifest_boundaries_and_counts() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["milestone20_complete"] is True
    assert manifest["source_observation_count"] == 855
    assert manifest["geography_count"] == 19
    assert manifest["year_count"] == 45
    assert manifest["analysis_row_count"] == 19
    assert manifest["leave_one_year_out_row_count"] == 855
    assert manifest["classical_mann_kendall_primary_for_claims"] is False
    assert manifest["climate_change_attribution_performed"] is False
    assert manifest["causal_analysis_performed"] is False
    assert manifest["station_observation_equivalence"] is False
    assert manifest["historical_boundary_continuity_claimed"] is False
    assert manifest["posthoc_method_search_performed"] is False
    assert manifest["robust_monotonic_geography_count"] == len(manifest["robust_monotonic_geography_ids"])
