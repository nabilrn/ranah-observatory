#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
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
SPEC = ROOT / "research/MILESTONE22_HIERARCHICAL_SOCIOECONOMIC_TRAJECTORY_SPEC.md"
DOC = ROOT / "docs/MILESTONE22_HIERARCHICAL_SOCIOECONOMIC_TRAJECTORY.md"


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
        raise AssertionError(f"invalid bool serialization: {value!r}")
    return value == "True"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    frame = rows(FRAME)
    predictions = rows(PRED)
    summary = rows(SUMMARY)
    trajectories = rows(TRAJ)
    loo = rows(LOO)

    assert manifest["schema"] == "ranah-observatory/milestone22-hierarchical-socioeconomic-trajectory/v1"
    assert manifest["milestone22_complete"] is True
    assert len(frame) == 1064
    assert len(predictions) == 1064
    assert len(summary) == 7
    assert len(trajectories) == 133
    assert len(loo) == 1064

    assert design["design_locked_before_model_fit"] is True
    assert design["posthoc_indicator_selection_authorized"] is False
    assert design["posthoc_model_search_authorized"] is False
    assert manifest["posthoc_indicator_selection_performed"] is False
    assert manifest["posthoc_model_search_performed"] is False

    qualified: list[str] = []
    for row in summary:
        expected = (
            float(row["hierarchical_rmse"]) < float(row["independent_ols_rmse"])
            and float(row["hierarchical_mae"]) < float(row["independent_ols_mae"])
        )
        assert as_bool(row["hierarchical_trajectory_qualified"]) is expected
        if expected:
            qualified.append(row["indicator_id"])
    assert qualified == manifest["hierarchical_trajectory_qualified_indicator_ids"]
    assert len(qualified) == manifest["hierarchical_trajectory_qualified_indicator_count"]

    class_counts = {"persistent_increase": 0, "persistent_decrease": 0, "trajectory_not_robust": 0}
    for row in trajectories:
        classification = row["trajectory_classification"]
        assert classification in class_counts
        class_counts[classification] += 1
        qualified_indicator = as_bool(row["indicator_hierarchical_trajectory_qualified"])
        slope = float(row["hierarchical_slope_per_year"])
        loo_min = float(row["loo_min_slope_per_year"])
        loo_max = float(row["loo_max_slope_per_year"])
        retention = float(row["loo_same_direction_retention"])
        if classification == "persistent_increase":
            assert qualified_indicator and slope > 0.0 and loo_min > 0.0 and retention >= 0.875
        elif classification == "persistent_decrease":
            assert qualified_indicator and slope < 0.0 and loo_max < 0.0 and retention >= 0.875
        else:
            assert classification == "trajectory_not_robust"
        assert row["stability_envelope_is_confidence_interval"] == "False"
        assert row["causal_claim_authorized"] == "False"
        assert row["guaranteed_future_trajectory_authorized"] == "False"
        assert row["historical_boundary_continuity_claimed"] == "False"
    assert class_counts == manifest["trajectory_classification_counts"]

    by_group: dict[tuple[str, str], set[int]] = {}
    for row in loo:
        by_group.setdefault((row["indicator_id"], row["geography_id"]), set()).add(int(row["outer_held_year"]))
    assert len(by_group) == 133
    assert all(years == set(range(2018, 2026)) for years in by_group.values())

    for key, path in {
        "model_frame": FRAME,
        "outer_predictions": PRED,
        "indicator_summary": SUMMARY,
        "geography_trajectories": TRAJ,
        "loo_slopes": LOO,
    }.items():
        assert manifest["outputs"][key]["sha256"] == sha256(path)
    assert manifest["inputs"]["design_gate"]["sha256"] == sha256(DESIGN)
    assert manifest["inputs"]["spec"]["sha256"] == sha256(SPEC)

    assert manifest["stability_envelope_is_confidence_interval"] is False
    assert manifest["causal_analysis_performed"] is False
    assert manifest["policy_effect_estimated"] is False
    assert manifest["historical_boundary_continuity_claimed"] is False
    assert manifest["guaranteed_future_trajectory_authorized"] is False

    doc = DOC.read_text(encoding="utf-8").lower()
    assert "4/7 indicators" in doc
    assert "not a confidence interval" in doc
    assert "does not" in doc
    assert "2018–2025" in DOC.read_text(encoding="utf-8")

    print(json.dumps({
        "milestone22_audit": "pass",
        "qualified_indicator_count": len(qualified),
        "trajectory_classification_counts": class_counts,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
