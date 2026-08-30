from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_release_readiness import validate


class ReleaseReadinessTest(unittest.TestCase):
    def test_internal_release_surface_is_consistent(self) -> None:
        result = validate()
        self.assertTrue(result["internal_release_readiness_passed"])
        self.assertEqual(result["frozen_claims"], 30)
        self.assertEqual(result["blocked_claims_retained"], 9)
        self.assertEqual(result["public_stories"], 9)
        self.assertEqual(result["research_questions"], 5)
        self.assertEqual(result["fully_resolved_questions"], 0)
        self.assertEqual(result["historical_context_cards"], 3)
        self.assertTrue(result["model_testing_gate_passed"])
        self.assertEqual(result["m11_benchmark_qualified_targets"], 3)
        self.assertEqual(result["m19_forecast_qualified_targets"], 0)
        self.assertEqual(result["m19_forecast_blocked_targets"], 3)
        self.assertEqual(result["must_close_gates_total"], 6)
        self.assertEqual(result["must_close_gates_satisfied"], 3)
        self.assertEqual(result["must_close_gates_open_internal"], 3)
        self.assertEqual(result["deferred_research_gates"], 7)
        self.assertEqual(result["external_manual_blockers"], 0)
        self.assertEqual(result["public_product_url"], "https://nabilrn.github.io/ranah-observatory/")


if __name__ == "__main__":
    unittest.main()
