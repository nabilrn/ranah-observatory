from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from scripts.audit_milestone14_bottleneck_association import audit

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/analysis/engine/bottleneck_association_v1/m14-association-screen.csv"
MANIFEST = ROOT / "data/manifests/milestone14_bottleneck_association.json"


class Milestone14Tests(unittest.TestCase):
    def test_audit_is_clean_and_complete(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone14_complete"])
        self.assertFalse(report["causal_analysis_performed"])

    def test_expected_screen_shape_and_guardrails(self) -> None:
        with SCREEN.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 11)
        self.assertEqual(sum(row["screen_type"] == "core" for row in rows), 8)
        self.assertEqual(sum(row["screen_type"] == "health_extension" for row in rows), 3)
        self.assertTrue(all(row["causal_claim"] == "False" for row in rows))
        self.assertTrue(all(row["policy_priority_claim"] == "False" for row in rows))
        self.assertTrue(all(row["monetary_wasted_potential_claim"] == "False" for row in rows))

    def test_manifest_keeps_association_not_causation_boundary(self) -> None:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertTrue(payload["milestone14_complete"])
        self.assertFalse(payload["causal_analysis_performed"])
        self.assertFalse(payload["shap_or_black_box_feature_importance_performed"])
        self.assertFalse(payload["policy_priority_claim_authorized"])
        self.assertFalse(payload["monetary_wasted_potential_estimated"])
        self.assertEqual(payload["permutation_count"], 4999)
        self.assertEqual(payload["permutation_seed"], 140014)


if __name__ == "__main__":
    unittest.main()
