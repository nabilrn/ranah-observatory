from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_milestone44_bnpb_event_overlap import build_report  # noqa: E402


MANIFEST_PATH = ROOT / "data" / "manifests" / "milestone44_bnpb_event_overlap_reconciliation.json"
HISTORICAL_PATH = ROOT / "data" / "processed" / "bnpb_historical_source_native_rows_2000_2017.csv.gz"
CURRENT_PATH = ROOT / "data" / "processed" / "bnpb" / "disaster" / "bnpb-disaster-source-native.csv"


class Milestone44EventOverlapReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.report = build_report(HISTORICAL_PATH, CURRENT_PATH)

    def test_frozen_summary_matches_recomputed_sources(self):
        expected = self.manifest["result"]
        actual = self.report["summary"]

        self.assertEqual(expected["historical_explicit_overlap_rows"], actual["historical_explicit_overlap_rows"])
        self.assertEqual(expected["modern_overlap_rows"], actual["current_overlap_rows"])
        self.assertEqual(expected["compared_rows"], actual["compared_rows"])
        self.assertEqual(expected["missing_modern_counterparts"], actual["missing_current_rows"])
        self.assertEqual(expected["exact_matches"], actual["exact_matches"])
        self.assertEqual(expected["value_disagreements"], actual["value_disagreements"])
        self.assertAlmostEqual(expected["exact_match_rate"], actual["exact_match_rate"])
        self.assertEqual(expected["distinct_disagreement_deltas"], actual["distinct_disagreement_deltas"])
        self.assertEqual(
            expected["modern_rows_without_historical_explicit_row"],
            actual["current_rows_without_historical_explicit_row"],
        )
        self.assertEqual(
            expected["modern_zero_where_historical_row_absent"],
            actual["current_zero_where_historical_row_absent"],
        )
        self.assertEqual(
            expected["modern_positive_where_historical_row_absent"],
            actual["current_positive_where_historical_row_absent"],
        )
        self.assertEqual(
            expected["modern_positive_sum_where_historical_row_absent"],
            actual["current_positive_sum_where_historical_row_absent"],
        )

    def test_year_level_frozen_results_match_recomputation(self):
        frozen = {item["year"]: item for item in self.manifest["by_year"]}
        generated = {item["year"]: item for item in self.report["by_year"]}
        self.assertEqual(set(frozen), set(generated))

        key_pairs = {
            "historical_explicit_geographies": "historical_explicit_geographies",
            "modern_matrix_geographies": "current_matrix_geographies",
            "compared_explicit_geographies": "compared_explicit_geographies",
            "exact_matches": "exact_matches",
            "value_disagreements": "value_disagreements",
            "historical_explicit_sum": "historical_explicit_sum",
            "modern_sum_on_same_explicit_geographies": "current_sum_on_same_explicit_geographies",
            "sum_delta_modern_minus_historical": "sum_delta_current_minus_historical",
            "modern_full_matrix_sum": "current_full_matrix_sum",
            "modern_rows_without_historical_explicit_row": "current_rows_without_historical_explicit_row",
            "modern_zero_where_historical_row_absent": "current_zero_where_historical_row_absent",
            "modern_positive_where_historical_row_absent": "current_positive_where_historical_row_absent",
        }
        for year in frozen:
            for frozen_key, generated_key in key_pairs.items():
                with self.subTest(year=year, field=frozen_key):
                    self.assertEqual(frozen[year][frozen_key], generated[year][generated_key])

    def test_all_six_disagreements_are_exactly_plus_one(self):
        generated = self.report["disagreements"]
        self.assertEqual(6, len(generated))
        self.assertEqual({1}, {row["delta_current_minus_historical"] for row in generated})

        frozen_keys = {
            (
                row["year"],
                row["canonical_geography_id"],
                row["historical_value"],
                row["modern_value"],
            )
            for row in self.manifest["disagreements"]
        }
        generated_keys = {
            (
                row["year"],
                row["canonical_geography_id"],
                row["historical_value"],
                row["current_value"],
            )
            for row in generated
        }
        self.assertEqual(frozen_keys, generated_keys)

    def test_historical_sparsity_is_not_rewritten_as_observed_zero(self):
        self.assertEqual(33, self.report["summary"]["current_rows_without_historical_explicit_row"])
        self.assertEqual(33, self.report["summary"]["current_zero_where_historical_row_absent"])
        self.assertEqual(0, self.report["summary"]["current_positive_where_historical_row_absent"])
        self.assertFalse(self.report["comparison_contract"]["historical_missing_rows_zero_filled"])
        self.assertFalse(self.report["comparison_contract"]["modern_zero_backfills_historical_missingness"])
        self.assertFalse(self.manifest["interpretation"]["historical_absence_can_be_relabelled_observed_zero"])

    def test_exact_and_revised_year_partition_is_frozen(self):
        generated_exact = [
            item["year"] for item in self.report["by_year"] if item["value_disagreements"] == 0
        ]
        generated_revised = [
            item["year"] for item in self.report["by_year"] if item["value_disagreements"] > 0
        ]
        self.assertEqual(self.manifest["result"]["fully_exact_years"], generated_exact)
        self.assertEqual(self.manifest["result"]["revised_years"], generated_revised)

    def test_sum_reconciliation_is_exactly_six_events(self):
        historical_sum = sum(item["historical_explicit_sum"] for item in self.report["by_year"])
        modern_sum = sum(item["current_full_matrix_sum"] for item in self.report["by_year"])
        self.assertEqual(523, historical_sum)
        self.assertEqual(529, modern_sum)
        self.assertEqual(6, modern_sum - historical_sum)
        self.assertEqual(self.manifest["result"]["net_release_delta"], modern_sum - historical_sum)

    def test_m44_does_not_silently_expand_canonical_contract(self):
        qualification = self.manifest["qualification"]
        self.assertTrue(qualification["event_count_overlap_reconciled"])
        self.assertTrue(qualification["complete_modern_matrix_2010_2017_verified"])
        self.assertTrue(qualification["release_revision_pattern_quantified"])
        self.assertTrue(qualification["historical_missingness_contract_preserved"])
        self.assertTrue(qualification["modern_total_event_context_remains_source_native"])
        self.assertFalse(qualification["canonical_total_event_panel_promotion_authorized"])
        self.assertEqual(45, self.manifest["next_gate"]["milestone"])


if __name__ == "__main__":
    unittest.main()
