#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-geography-trends.csv"
LOO = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-leave-one-year-out.csv"
REGIONAL_ANNUAL = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-regional-annual-mean.csv"
REGIONAL_TREND = ROOT / "data/analysis/engine/historical_climate_trend_v1/m20-regional-trend.csv"
MANIFEST = ROOT / "data/manifests/milestone20_historical_climate_trend.json"
DESIGN = ROOT / "data/manifests/milestone20_design_gate.json"
SPEC = ROOT / "research/MILESTONE20_HISTORICAL_CLIMATE_TREND_SPEC.md"
DOC = ROOT / "docs/MILESTONE20_HISTORICAL_CLIMATE_TREND.md"


def read_csv(path: Path) -> list[dict[str, str]]:
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
        raise AssertionError(f"invalid bool serialization: {value!r}")
    return value == "True"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    geo = read_csv(GEO)
    loo = read_csv(LOO)
    regional_annual = read_csv(REGIONAL_ANNUAL)
    regional_trend = read_csv(REGIONAL_TREND)

    assert manifest["schema"] == "ranah-observatory/milestone20-historical-climate-trend/v1"
    assert manifest["milestone20_complete"] is True
    assert manifest["source_observation_count"] == 855
    assert manifest["geography_count"] == 19
    assert manifest["year_count"] == 45
    assert len(geo) == 19
    assert len(loo) == 855
    assert len(regional_annual) == 45
    assert len(regional_trend) == 1

    assert design["design_locked_before_model_fit"] is True
    assert design["posthoc_method_search_authorized"] is False
    assert manifest["posthoc_method_search_performed"] is False
    assert manifest["classical_mann_kendall_primary_for_claims"] is False
    assert manifest["multiple_testing_method"] == "holm_familywise"

    for row in geo:
        authorized = as_bool(row["public_claim_authorized"])
        if authorized:
            assert float(row["hr_p_holm"]) < 0.05
            assert as_bool(row["ci_excludes_zero_same_direction"])
            assert as_bool(row["split_direction_consistent"])
            assert as_bool(row["loo_stability_pass"])
            assert float(row["loo_same_direction_retention"]) >= 0.90
            assert row["robust_monotonic_classification"] in {
                "robust_monotonic_increase",
                "robust_monotonic_decrease",
            }
        else:
            assert row["robust_monotonic_classification"] == "no_robust_monotonic_trend"
        assert row["claim_type"] == "model_estimate"
        assert row["station_observation_equivalence"] == "False"
        assert row["historical_boundary_continuity_claimed"] == "False"

    robust = [row["geography_id"] for row in geo if as_bool(row["public_claim_authorized"])]
    assert robust == manifest["robust_monotonic_geography_ids"]
    assert len(robust) == manifest["robust_monotonic_geography_count"]

    regional = regional_trend[0]
    assert regional["station_observation_equivalence"] == "False"
    assert regional["historical_boundary_continuity_claimed"] == "False"
    if as_bool(regional["public_claim_authorized"]):
        assert float(regional["hr_p"]) < 0.05
        assert as_bool(regional["ci_excludes_zero_same_direction"])
        assert as_bool(regional["split_direction_consistent"])
        assert as_bool(regional["loo_stability_pass"])

    for key, path in {
        "geography_trends": GEO,
        "leave_one_year_out": LOO,
        "regional_annual_mean": REGIONAL_ANNUAL,
        "regional_trend": REGIONAL_TREND,
    }.items():
        assert manifest["outputs"][key]["sha256"] == sha256(path)

    assert manifest["inputs"]["design_gate"]["sha256"] == sha256(DESIGN)
    assert manifest["inputs"]["spec"]["sha256"] == sha256(SPEC)

    forbidden_authorizations = [
        manifest["climate_change_attribution_performed"],
        manifest["causal_analysis_performed"],
        manifest["station_observation_equivalence"],
        manifest["historical_boundary_continuity_claimed"],
    ]
    assert forbidden_authorizations == [False, False, False, False]

    spec_text = SPEC.read_text(encoding="utf-8").lower()
    doc_text = DOC.read_text(encoding="utf-8").lower()
    assert "does not" in spec_text
    assert "not station-equivalent" in doc_text
    assert "change-point / regime-shift" in doc_text

    print(json.dumps({
        "milestone20_audit": "pass",
        "robust_monotonic_geography_count": manifest["robust_monotonic_geography_count"],
        "regional_public_claim_authorized": manifest["regional_public_claim_authorized"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
