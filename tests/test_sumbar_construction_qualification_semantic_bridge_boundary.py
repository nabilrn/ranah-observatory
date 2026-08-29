from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_qualification_semantic_bridge_boundary import validate


class SumbarConstructionQualificationSemanticBridgeBoundaryTest(unittest.TestCase):
    def test_arithmetic_candidate_does_not_open_semantic_bridge(self) -> None:
        result = validate()
        self.assertTrue(result["detailed_2003_composition_confirmed"])
        self.assertEqual(result["arithmetic_small_2003"], 2732)
        self.assertEqual(result["arithmetic_medium_2003"], 150)
        self.assertEqual(result["arithmetic_large_2003"], 0)
        self.assertEqual(result["arithmetic_total_2003"], 2882)
        self.assertEqual(result["sumbar_total_2005"], 2435)
        self.assertFalse(result["period_specific_semantic_mapping_verified"])
        self.assertFalse(result["pre_post_composition_comparison_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
