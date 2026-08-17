from __future__ import annotations

import unittest

from scripts.audit_milestone7_expected_performance import EXPECTED_FEATURES, EXPECTED_LAMBDAS, audit


class Milestone7ExpectedPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit()

    def test_completion_gate(self) -> None:
        self.assertTrue(self.report["milestone7_complete"], self.report["errors"])
        self.assertEqual(self.report["errors"], [])

    def test_exact_model_contract(self) -> None:
        self.assertEqual(self.report["feature_count"], len(EXPECTED_FEATURES))
        self.assertEqual(self.report["model_geography_count"], 38)
        self.assertEqual(self.report["training_geography_count"], 37)
        self.assertEqual(self.report["focal_holdout"], "idn.13")
        self.assertEqual(self.report["cv_penalty_count"], len(EXPECTED_LAMBDAS))
        self.assertIn(self.report["selected_penalty"], EXPECTED_LAMBDAS)

    def test_validation_beats_naive(self) -> None:
        self.assertTrue(self.report["beats_naive_benchmark"])
        self.assertLess(self.report["selected_loocv_rmse_log"], self.report["naive_loocv_rmse_log"])

    def test_west_sumatra_is_within_marginal_support(self) -> None:
        self.assertTrue(self.report["west_sumatra_all_features_inside_training_minmax"])
        self.assertGreater(self.report["west_sumatra_actual_level"], 0.0)
        self.assertGreater(self.report["west_sumatra_expected_level"], 0.0)

    def test_claim_taxonomy_stops_before_causality_and_frontier(self) -> None:
        self.assertFalse(self.report["causal_analysis_performed"])
        self.assertFalse(self.report["frontier_model_performed"])
        self.assertFalse(self.report["monetary_wasted_potential_estimated"])


if __name__ == "__main__":
    unittest.main()
