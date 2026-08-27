from __future__ import annotations

import unittest

from scripts.validate_sumbar_construction_financing_revision_audit import validate


class SumbarConstructionFinancingRevisionAuditTest(unittest.TestCase):
    def test_release_specific_revision_history_is_preserved(self) -> None:
        result = validate()
        self.assertEqual(result["rows"], 36)
        self.assertEqual(result["measures"], 6)
        self.assertEqual(result["years"], 6)
        self.assertEqual(result["overlap_years"], 4)
        self.assertEqual(result["revised_cells"], 6)
        self.assertEqual(result["year_2000_stable_measures"], 6)
        self.assertEqual(result["primary_exact_reconciliation_years"], 2)
        self.assertEqual(result["crosscheck_exact_reconciliation_years"], 4)
        self.assertFalse(result["silent_latest_value_overwrite_authorized"])
        self.assertFalse(result["canonical_fiscal_mapping_authorized"])


if __name__ == "__main__":
    unittest.main()
