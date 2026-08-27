from __future__ import annotations

import unittest

from scripts.validate_sumbar2000_apbd_construction_anchor import validate


class Sumbar2000ApbdConstructionAnchorTest(unittest.TestCase):
    def test_source_native_anchor_is_exact_and_semantically_bounded(self) -> None:
        result = validate()
        self.assertEqual(result["source_native_row_count"], 1)
        self.assertEqual(result["source_year"], 2000)
        self.assertEqual(result["raw_value_thousand_rupiah"], 39_956_642)
        self.assertEqual(result["normalized_nominal_idr"], 39_956_642_000)
        self.assertTrue(result["cross_publication_exact_match"])
        self.assertFalse(result["canonical_promotion_authorized"])
        self.assertFalse(result["djpk_capital_expenditure_bridge_authorized"])
        self.assertTrue(result["yearbook_public_finance_zero_hit_preserved"])


if __name__ == "__main__":
    unittest.main()
