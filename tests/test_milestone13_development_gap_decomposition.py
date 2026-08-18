from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from scripts.audit_milestone13_development_gap_decomposition import audit

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/manifests/milestone13_design_gate.json"
MANIFEST = ROOT / "data/manifests/milestone13_development_gap_decomposition.json"
GAP = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-gap-panel.csv"
PERSISTENCE = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-persistence-by-geography-target.csv"
PROFILES = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-geography-profiles.csv"
NATIONAL = ROOT / "data/analysis/engine/gap_decomposition_v1/m13-national-income-anchor.json"


class Milestone13DevelopmentGapDecompositionTests(unittest.TestCase):
    def test_completion_audit_has_no_errors(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone13_complete"])
        self.assertTrue(report["prefit_design_gate_preserved"])
        self.assertTrue(report["m11_complete"])
        self.assertTrue(report["m12_complete"])

    def test_design_gate_forbids_composite_and_ranking(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertFalse(gate["weighted_composite_score_authorized"])
        self.assertFalse(gate["cross_target_ranking_authorized"])
        self.assertFalse(gate["clipping_authorized"])
        self.assertFalse(gate["winsorization_authorized"])
        self.assertFalse(gate["gap_values_computed"])
        self.assertFalse(gate["persistence_results_inspected"])

    def test_gap_panel_keeps_three_parallel_dimensions(self) -> None:
        with GAP.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 342)
        self.assertEqual(
            {(row["target_id"], row["dimension_id"]) for row in rows},
            {
                ("poverty_rate", "living_standards_inclusion"),
                ("unemployment_rate", "labor_market"),
                ("real_grdp_growth", "economic_dynamism"),
            },
        )
        self.assertTrue(any(float(row["expected_adverse_gap"]) > 0 for row in rows))
        self.assertTrue(any(float(row["expected_adverse_gap"]) < 0 for row in rows))
        self.assertTrue(any(float(row["favorable_peer_gap"]) > 0 for row in rows))
        self.assertTrue(any(float(row["favorable_peer_gap"]) < 0 for row in rows))

    def test_persistence_uses_locked_support_thresholds(self) -> None:
        with PERSISTENCE.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 57)
        allowed_labels = {
            "persistent_less_favorable_than_favorable_reference",
            "mostly_meets_or_exceeds_favorable_reference",
            "mixed_relative_to_favorable_reference",
            "insufficient_supported_years",
        }
        self.assertTrue(all(row["persistence_label"] in allowed_labels for row in rows))
        for row in rows:
            self.assertEqual(row["minimum_authorized_years_for_label"], "4")
            self.assertAlmostEqual(float(row["persistent_positive_gap_rate_threshold"]), 2 / 3)
            self.assertAlmostEqual(float(row["mostly_meets_or_exceeds_rate_threshold"]), 1 / 3)

    def test_profile_score_and_rank_columns_are_blank(self) -> None:
        with PROFILES.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(row["weighted_composite_score"] == "" for row in rows))
        self.assertTrue(all(row["cross_target_rank"] == "" for row in rows))

    def test_national_anchor_remains_separate_context(self) -> None:
        anchor = json.loads(NATIONAL.read_text(encoding="utf-8"))
        self.assertEqual(anchor["dimension_id"], "income_productivity_national_anchor")
        self.assertFalse(anchor["anchor_combined_with_district_gap_score"])
        self.assertFalse(anchor["population_aggregation_performed"])
        self.assertFalse(anchor["multi_year_accumulation_performed"])
        self.assertFalse(anchor["causal_claim"])
        self.assertFalse(anchor["theoretical_maximum_claim"])
        self.assertFalse(anchor["monetary_wasted_potential_claim"])

    def test_manifest_preserves_no_score_no_loss_contract(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertFalse(manifest["weighted_composite_score_computed"])
        self.assertFalse(manifest["cross_target_ranking_computed"])
        self.assertFalse(manifest["clipping_performed"])
        self.assertFalse(manifest["winsorization_performed"])
        self.assertFalse(manifest["national_anchor_combined_with_district_gaps"])
        self.assertFalse(manifest["population_aggregation_performed"])
        self.assertFalse(manifest["multi_year_monetary_accumulation_performed"])
        self.assertFalse(manifest["monetary_wasted_potential_claim"])


if __name__ == "__main__":
    unittest.main()
