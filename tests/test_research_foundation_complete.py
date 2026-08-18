from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/research_foundation_complete.json"


class ResearchFoundationCompleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_exact_nine_of_nine(self):
        self.assertEqual(self.payload["criterion_count"], 9)
        self.assertEqual(self.payload["completed_criterion_count"], 9)
        self.assertTrue(self.payload["initial_research_foundation_complete"])
        self.assertEqual(self.payload["errors"], [])

    def test_every_criterion_is_evidenced_and_complete(self):
        rows = self.payload["criteria"]
        self.assertEqual([row["criterion_number"] for row in rows], list(range(1, 10)))
        self.assertTrue(all(row["complete"] for row in rows))
        self.assertTrue(all(row["errors"] == [] for row in rows))
        self.assertTrue(all(row["evidence"] for row in rows))

    def test_foundation_is_not_mislabeled_as_final_product(self):
        self.assertFalse(self.payload["final_ranah_observatory_product_complete"])
        self.assertFalse(self.payload["dashboard_required_for_foundation"])
        self.assertFalse(self.payload["definitive_monetary_wasted_potential_required_for_foundation"])

    def test_core_counts(self):
        by_number = {row["criterion_number"]: row for row in self.payload["criteria"]}
        self.assertEqual(by_number[1]["details"]["current_sumbar_child_count"], 19)
        self.assertEqual(by_number[3]["details"]["domain_count"], 12)
        self.assertGreaterEqual(by_number[3]["details"]["indicator_definition_count"], 40)
        self.assertGreaterEqual(by_number[4]["details"]["qualified_indicator_count"], 40)
        self.assertLessEqual(by_number[4]["details"]["qualified_indicator_count"], 60)
        self.assertEqual(by_number[9]["details"]["geography_count"], 19)


if __name__ == "__main__":
    unittest.main()
