from __future__ import annotations

import unittest

from scripts.validate_milestone59_bpbd_hazard_totals_2024 import validate


class Milestone59BPBDHazardTotals2024Tests(unittest.TestCase):
    def test_aggregate_hazard_totals_match_monthly_table(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["hazard_count"], 7)
        self.assertEqual(report["source_total_events"], 1175)
        self.assertEqual(report["exact_hazard_total_match_count"], 7)
        self.assertTrue(report["dashboard_hazard_filter_ready"])


if __name__ == "__main__":
    unittest.main()
