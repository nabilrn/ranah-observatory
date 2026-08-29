from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_legacy_var216_retention_boundary import validate


class SumbarConstructionLegacyVar216RetentionBoundaryTest(unittest.TestCase):
    def test_legacy_2005_total_is_source_bound_but_components_remain_blocked(self) -> None:
        result = validate()
        self.assertTrue(result["source_snapshot_verified"])
        self.assertTrue(result["legacy_variable_verified"])
        self.assertEqual(result["source_native_2005_th_id"], 105)
        self.assertEqual(result["sumbar_2005_total"], 2435)
        self.assertFalse(result["component_strata_2005_recovered"])
        self.assertEqual(result["current_csa_earliest_year"], 2016)
        self.assertFalse(result["historical_comparison_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
