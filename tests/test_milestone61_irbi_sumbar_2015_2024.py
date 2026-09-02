from __future__ import annotations

import unittest

from scripts.validate_milestone61_irbi_sumbar_2015_2024 import validate


class Milestone61IRBITests(unittest.TestCase):
    def test_irbi_timeseries_and_2024_classes(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["district_count"], 19)
        self.assertEqual(report["year_count"], 10)
        self.assertEqual(report["canonical_row_count"], 190)
        self.assertEqual(report["province_2024_score"], 142.55)
        self.assertEqual(report["high_risk_2024"], 8)
        self.assertEqual(report["medium_risk_2024"], 11)


if __name__ == "__main__":
    unittest.main()
