from __future__ import annotations

import csv
import unittest
from pathlib import Path

from scripts.audit_milestone17_scenario_intervention import audit

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "data/analysis/engine/scenario_intervention_v1/m17-scenario-library.csv"
MAPPINGS = ROOT / "data/analysis/engine/scenario_intervention_v1/m17-model-sensitivity-mappings.csv"


class Milestone17Tests(unittest.TestCase):
    def test_completion_audit_is_clean(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone17_complete"])
        self.assertEqual(report["scenario_count"], 7)
        self.assertEqual(report["mapping_count"], 15)
        self.assertEqual(report["blocked_scenario_count"], 2)
        self.assertFalse(report["policy_recommendation_authorized"])

    def test_all_feature_target_mappings_are_retained(self) -> None:
        with MAPPINGS.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 15)
        self.assertEqual(len({row["feature_id"] for row in rows}), 5)
        self.assertEqual(len({row["target_id"] for row in rows}), 3)
        self.assertTrue(all(row["outer_fold_count"] == "19" for row in rows))
        self.assertTrue(all(row["perturbation_standardized_units"] == "0.5" for row in rows))
        self.assertTrue(all(row["causal_interpretation_authorized"] == "False" for row in rows))
        self.assertTrue(all(row["policy_effect_interpretation_authorized"] == "False" for row in rows))

    def test_scenarios_do_not_invent_costs_or_horizons(self) -> None:
        with LIBRARY.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row["cost_information"] == "cost_not_qualified" for row in rows))
        self.assertTrue(all(row["implementation_horizon"] == "implementation_horizon_not_estimated" for row in rows))
        self.assertTrue(all(row["policy_recommendation_authorized"] == "False" for row in rows))
        self.assertTrue(all(row["forecast_authorized"] == "False" for row in rows))

    def test_upstream_blocks_remain_visible(self) -> None:
        with LIBRARY.open("r", encoding="utf-8", newline="") as handle:
            rows = {row["scenario_id"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows["m17_b1_rainfall_labor_adaptation"]["scenario_status"], "blocked_causal_mapping")
        self.assertEqual(rows["m17_b2_disaster_risk_reduction"]["scenario_status"], "blocked_risk_mapping")
        self.assertEqual(rows["m17_b1_rainfall_labor_adaptation"]["mapping_count"], "0")
        self.assertEqual(rows["m17_b2_disaster_risk_reduction"]["mapping_count"], "0")


if __name__ == "__main__":
    unittest.main()
