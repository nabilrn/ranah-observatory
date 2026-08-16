from __future__ import annotations

import unittest

from scripts.audit_milestone6_historical_eda import (
    DEFAULT_ANALYSIS,
    DEFAULT_MANIFEST,
    TREND_QUALIFIED,
    audit,
)


class Milestone6HistoricalEdaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit(DEFAULT_ANALYSIS, DEFAULT_MANIFEST)

    def test_completion_gate(self) -> None:
        self.assertTrue(self.report["milestone6_complete"], self.report["errors"])
        self.assertEqual(self.report["errors"], [])

    def test_segmented_historical_contract(self) -> None:
        self.assertEqual(self.report["timeline_row_count"], 8)
        self.assertEqual(self.report["explicit_gap_count"], 2)
        self.assertEqual(self.report["historical_population_anchor_count"], 1)
        self.assertFalse(self.report["historical_boundary_harmonization_performed"])

    def test_modern_trajectory_contract(self) -> None:
        self.assertEqual(self.report["modern_observation_count"], 54)
        self.assertEqual(self.report["modern_series_count"], 7)
        self.assertEqual(self.report["trend_qualified_modern_series_count"], len(TREND_QUALIFIED))

    def test_climate_contract(self) -> None:
        self.assertEqual(self.report["climate_year_count"], 45)
        self.assertEqual(self.report["climate_geography_count"], 19)

    def test_milestone6_stops_before_models_and_causality(self) -> None:
        self.assertFalse(self.report["causal_analysis_performed"])
        self.assertFalse(self.report["frontier_model_performed"])


if __name__ == "__main__":
    unittest.main()
