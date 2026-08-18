from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from scripts.audit_milestone14_bottleneck_association import audit

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/manifests/milestone14_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"
ASSOCIATIONS = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-feature-associations.csv"
STABLE = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-stable-association-candidates.csv"
FRAME = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-association-frame.csv"


class Milestone14BottleneckAssociationTests(unittest.TestCase):
    def test_completion_audit_has_no_errors(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone14_complete"])
        self.assertTrue(report["prefit_design_gate_preserved"])
        self.assertTrue(report["m10_complete"])
        self.assertTrue(report["m13_complete"])

    def test_prefit_gate_stays_uninspected(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertFalse(gate["association_results_computed"])
        self.assertFalse(gate["association_results_inspected"])
        self.assertFalse(gate["p_value_selection_authorized"])
        self.assertFalse(gate["candidate_selection_after_results_authorized"])
        self.assertEqual(gate["stable_abs_spearman_threshold"], 0.25)
        self.assertEqual(gate["stable_min_same_sign_annual_count"], 3)
        self.assertTrue(gate["stable_require_all_loo_same_sign"])
        self.assertEqual(gate["stable_min_support_safe_rows"], 40)

    def test_exact_candidate_and_target_footprint(self) -> None:
        with FRAME.open("r", encoding="utf-8", newline="") as handle:
            frame = list(csv.DictReader(handle))
        self.assertEqual(len(frame), 228)
        self.assertEqual({row["target_id"] for row in frame}, {"poverty_rate", "unemployment_rate", "real_grdp_growth"})
        self.assertEqual({row["target_year"] for row in frame}, {"2021", "2022", "2023", "2024"})
        self.assertEqual({row["feature_year"] for row in frame}, {"2020", "2021", "2022", "2023"})

    def test_stable_candidates_match_locked_gate_result(self) -> None:
        with STABLE.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        keys = {(row["target_id"], row["candidate_id"]) for row in rows}
        self.assertEqual(
            keys,
            {
                ("unemployment_rate", "annual_rainfall"),
                ("real_grdp_growth", "expected_years_schooling"),
                ("real_grdp_growth", "life_expectancy"),
            },
        )
        self.assertTrue(all(row["stable_association_candidate"] == "true" for row in rows))
        self.assertTrue(all(row["causal_bottleneck_interpretation_authorized"] == "false" for row in rows))
        self.assertTrue(all(row["policy_priority_interpretation_authorized"] == "false" for row in rows))

    def test_nonstable_candidates_remain_published(self) -> None:
        with ASSOCIATIONS.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 12)
        self.assertEqual(sum(row["stable_association_candidate"] == "true" for row in rows), 3)
        self.assertEqual(sum(row["stable_association_candidate"] == "false" for row in rows), 9)
        self.assertTrue(all(row["p_value_selection_used"] == "false" for row in rows))
        self.assertTrue(all(row["causal_claim"] == "false" for row in rows))
        self.assertTrue(all(row["bottleneck_causal_claim"] == "false" for row in rows))
        self.assertTrue(all(row["policy_effect_claim"] == "false" for row in rows))

    def test_underemployment_does_not_get_promoted(self) -> None:
        with ASSOCIATIONS.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        underemployment = [row for row in rows if row["candidate_id"] == "underemployment_rate"]
        self.assertEqual(len(underemployment), 3)
        self.assertTrue(all(row["stable_association_candidate"] == "false" for row in underemployment))

    def test_rainfall_semantics_remain_noncausal_model_estimate(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["annual_rainfall_claim_type"], "model_estimate")
        self.assertFalse(manifest["annual_rainfall_station_equivalence_claim"])
        self.assertFalse(manifest["annual_rainfall_climate_change_attribution_claim"])
        self.assertFalse(manifest["causal_analysis_performed"])
        self.assertFalse(manifest["bottleneck_causal_claim"])
        self.assertFalse(manifest["policy_effect_claim"])
        self.assertFalse(manifest["monetary_wasted_potential_claim"])


if __name__ == "__main__":
    unittest.main()
