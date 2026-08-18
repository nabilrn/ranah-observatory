from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from scripts.audit_milestone11_expected_performance_v2 import audit

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/manifests/milestone11_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone11_expected_performance_v2.json"
SUMMARY = ROOT / "data/analysis/engine/expected_performance_v2/m11-target-summary.csv"
PREDICTIONS = ROOT / "data/analysis/engine/expected_performance_v2/m11-crossfit-predictions.csv"
SENSITIVITY = ROOT / "data/analysis/engine/expected_performance_v2/m11-sensitivity-summary.csv"


class Milestone11ExpectedPerformanceV2Tests(unittest.TestCase):
    def test_completion_audit_has_no_errors(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone11_complete"])
        self.assertTrue(report["prefit_design_gate_preserved"])
        self.assertTrue(report["m10_complete"])
        self.assertTrue(report["foundation_9_of_9_complete"])

    def test_prefit_design_snapshot_stays_prefit(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertFalse(gate["model_fit"])
        self.assertFalse(gate["residuals_inspected"])
        self.assertFalse(gate["target_benchmark_results_known"])
        self.assertEqual(
            gate["primary_feature_ids"],
            [
                "mean_years_schooling",
                "labor_force_participation",
                "agriculture_share_grdp",
                "manufacturing_share_grdp",
                "rice_yield",
            ],
        )
        self.assertEqual(gate["target_ids"], ["poverty_rate", "unemployment_rate", "real_grdp_growth"])

    def test_primary_predictions_are_crossfit_and_complete(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertTrue(manifest["primary_predictions_cross_fitted_by_geography"])
        self.assertTrue(manifest["focal_geography_excluded_from_own_model_fit"])
        self.assertTrue(manifest["nested_inner_cv_used"])
        self.assertTrue(manifest["focal_geography_excluded_from_own_uncertainty_calibration"])
        self.assertEqual(manifest["crossfit_prediction_count"], 342)
        self.assertFalse(manifest["causal_analysis_performed"])
        self.assertFalse(manifest["frontier_model_performed"])
        self.assertFalse(manifest["monetary_wasted_potential_estimated"])

    def test_benchmark_gate_is_target_specific(self) -> None:
        with SUMMARY.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row["target_id"] for row in rows}, {"poverty_rate", "unemployment_rate", "real_grdp_growth"})
        for row in rows:
            qualified = float(row["model_rmse"]) < float(row["naive_same_year_peer_mean_rmse"]) and float(row["model_mae"]) < float(row["naive_same_year_peer_mean_mae"])
            self.assertEqual(row["benchmark_qualified"], str(qualified).lower())
            self.assertEqual(row["substantive_expected_performance_interpretation_authorized"], str(qualified).lower())

    def test_support_warnings_are_not_dropped(self) -> None:
        with PREDICTIONS.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 342)
        warning_counts: dict[str, int] = {}
        for target in {row["target_id"] for row in rows}:
            target_rows = [row for row in rows if row["target_id"] == target]
            warning_counts[target] = sum(row["support_warning"] == "true" for row in target_rows)
        self.assertTrue(all(count > 0 for count in warning_counts.values()))
        self.assertTrue(all(count < 114 for count in warning_counts.values()))

    def test_rainfall_sensitivity_never_replaces_primary(self) -> None:
        with SENSITIVITY.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["sensitivity_can_replace_primary"], "false")
            self.assertEqual(row["rainfall_claim_type"], "model_estimate")
            self.assertEqual(row["causal_rainfall_interpretation_authorized"], "false")


if __name__ == "__main__":
    unittest.main()
