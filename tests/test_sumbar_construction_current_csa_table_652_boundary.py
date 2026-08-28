from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_current_csa_table_652_boundary import validate


class SumbarConstructionCurrentCsaTable652BoundaryTest(unittest.TestCase):
    def test_boundary_stays_fail_closed_for_2005(self) -> None:
        result = validate()
        self.assertTrue(result["csa_table_verified"])
        self.assertEqual(result["available_years"], ["2016"])
        self.assertFalse(result["source_native_2005_available"])
        self.assertEqual(result["province_total_2016"], 5866)
        self.assertFalse(result["historical_comparison_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
