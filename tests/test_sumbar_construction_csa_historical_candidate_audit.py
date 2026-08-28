from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_csa_historical_candidate_audit import validate


class SumbarConstructionCsaHistoricalCandidateAuditTest(unittest.TestCase):
    def test_current_csa_catalog_has_no_2005_candidate(self) -> None:
        result = validate()
        self.assertEqual(result["catalog_rows_seen"], 19)
        self.assertEqual(result["relevant_candidates"], 2)
        self.assertEqual(result["resolved_candidates"], 2)
        self.assertEqual(result["exact_2005_candidates"], 0)
        self.assertTrue(result["csa_search_loop_closed"])
        self.assertFalse(result["historical_comparison_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
