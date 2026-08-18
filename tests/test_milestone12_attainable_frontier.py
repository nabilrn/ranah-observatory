from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from scripts.audit_milestone12_attainable_frontier import audit

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/manifests/milestone12_design_gate.json"
METHODS = ROOT / "data/registries/milestone12_frontier_method_qualification.csv"
MANIFEST = ROOT / "data/manifests/milestone12_attainable_frontier.json"
DISTRICT = ROOT / "data/analysis/engine/frontier_v1/m12-district-frontier.csv"
SUMMARY = ROOT / "data/analysis/engine/frontier_v1/m12-district-method-summary.csv"
SENSITIVITY = ROOT / "data/analysis/engine/frontier_v1/m12-neighbor-sensitivity.csv"
NATIONAL = ROOT / "data/analysis/engine/frontier_v1/m12-national-west-sumatra-frontier.json"


class Milestone12AttainableFrontierTests(unittest.TestCase):
    def test_completion_audit_has_no_errors(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone12_complete"])
        self.assertTrue(report["prefit_design_gate_preserved"])
        self.assertTrue(report["m11_complete"])

    def test_prefit_frontier_design_stays_uninspected(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertFalse(gate["frontier_computed"])
        self.assertFalse(gate["frontier_results_inspected"])
        self.assertEqual(gate["lower_is_favorable_quantile"], 0.1)
        self.assertEqual(gate["higher_is_favorable_quantile"], 0.9)
        self.assertEqual(gate["neighbor_k"], 6)
        self.assertEqual(gate["neighbor_favorable_count"], 2)
        self.assertEqual(gate["neighbor_k_sensitivity"], [5, 7])

    def test_method_registry_prevents_posthoc_efficiency_models(self) -> None:
        with METHODS.open("r", encoding="utf-8", newline="") as handle:
            rows = {row["method_id"]: row["qualification_status"] for row in csv.DictReader(handle)}
        self.assertEqual(rows["conditional_favorable_residual_quantile"], "qualified")
        self.assertEqual(rows["structural_neighbor_favorable_envelope"], "qualified")
        self.assertEqual(rows["national_m7_favorable_residual_quantile"], "qualified")
        self.assertEqual(rows["classic_dea"], "rejected")
        self.assertEqual(rows["classic_halfnormal_sfa"], "deferred")
        self.assertEqual(rows["linear_quantile_regression"], "deferred")

    def test_distances_are_not_artificially_truncated(self) -> None:
        with DISTRICT.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 342)
        primary = [float(row["primary_distance_to_favorable_reference"]) for row in rows]
        alternative = [float(row["alternative_distance_to_favorable_reference"]) for row in rows]
        self.assertTrue(any(value > 0 for value in primary))
        self.assertTrue(any(value < 0 for value in primary))
        self.assertTrue(any(value > 0 for value in alternative))
        self.assertTrue(any(value < 0 for value in alternative))

    def test_calibration_is_reported_without_retuning(self) -> None:
        with SUMMARY.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 3)
        for row in rows:
            rate = float(row["primary_favorable_exceedance_rate"])
            self.assertEqual(row["primary_frontier_calibrated"], str(0.04 <= rate <= 0.20).lower())
            expected_q = 0.9 if row["target_id"] == "real_grdp_growth" else 0.1
            self.assertAlmostEqual(float(row["primary_favorable_quantile"]), expected_q)

    def test_support_warning_blocks_substantive_row_interpretation(self) -> None:
        with DISTRICT.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        warning_rows = [row for row in rows if row["m11_support_warning"] == "true"]
        self.assertGreater(len(warning_rows), 0)
        self.assertTrue(all(row["primary_frontier_interpretation_authorized"] == "false" for row in warning_rows))

    def test_neighbor_sensitivity_cannot_replace_locked_method(self) -> None:
        with SENSITIVITY.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 684)
        self.assertEqual({row["k_neighbors"] for row in rows}, {"5", "7"})
        self.assertTrue(all(row["sensitivity_can_replace_locked_k6"] == "false" for row in rows))

    def test_national_anchor_is_not_a_loss_or_maximum_claim(self) -> None:
        national = json.loads(NATIONAL.read_text(encoding="utf-8"))
        self.assertEqual(national["geography_id"], "idn.13")
        self.assertEqual(national["claim_type"], "model_estimate")
        self.assertEqual(national["frontier_scope"], "empirical_favorable_peer_reference")
        self.assertFalse(national["theoretical_maximum_claim"])
        self.assertFalse(national["causal_claim"])
        self.assertFalse(national["policy_counterfactual_claim"])
        self.assertFalse(national["monetary_wasted_potential_claim"])
        self.assertFalse(national["population_aggregation_performed"])
        self.assertFalse(national["multi_year_loss_accumulation_performed"])

    def test_manifest_forbids_deferred_methods_and_loss_claims(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertFalse(manifest["classic_dea_computed"])
        self.assertFalse(manifest["classic_halfnormal_sfa_computed"])
        self.assertFalse(manifest["linear_quantile_regression_computed"])
        self.assertFalse(manifest["frontier_distance_truncated_at_zero"])
        self.assertFalse(manifest["posthoc_quantile_retuning_performed"])
        self.assertFalse(manifest["posthoc_neighbor_parameter_replacement_performed"])
        self.assertFalse(manifest["theoretical_maximum_claim"])
        self.assertFalse(manifest["monetary_wasted_potential_claim"])


if __name__ == "__main__":
    unittest.main()
