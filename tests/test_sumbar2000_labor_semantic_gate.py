from __future__ import annotations

import unittest

from scripts.validate_sumbar2000_labor_semantic_gate import validate


class Sumbar2000LaborSemanticGateTest(unittest.TestCase):
    def test_historical_labor_remains_fail_closed(self) -> None:
        result = validate()
        self.assertTrue(result["artifact_bound"])
        self.assertEqual(result["candidate_indicator_count"], 2)
        self.assertFalse(result["historical_table_identity_resolved"])
        self.assertFalse(result["canonical_promotion_authorized"])
        self.assertFalse(result["panel_v3_backfill_authorized"])


if __name__ == "__main__":
    unittest.main()
