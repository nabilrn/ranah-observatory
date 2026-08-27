from __future__ import annotations

import unittest

from scripts.validate_sumbar2000_construction_financing_composition import validate


class Sumbar2000ConstructionFinancingCompositionTest(unittest.TestCase):
    def test_financing_components_reconcile_exactly_to_total(self) -> None:
        result = validate()
        self.assertEqual(result["source_native_rows"], 6)
        self.assertEqual(result["financing_components"], 5)
        self.assertEqual(result["total_thousand_rupiah"], 345_371_439)
        self.assertEqual(result["component_sum_thousand_rupiah"], 345_371_439)
        self.assertTrue(result["exact_reconciliation"])
        self.assertTrue(result["all_2000_cross_publication_values_match"])
        self.assertTrue(result["apbd_anchor_consistent"])
        self.assertFalse(result["canonical_fiscal_mapping_authorized"])
        self.assertTrue(result["yearbook_public_finance_zero_hit_preserved"])


if __name__ == "__main__":
    unittest.main()
