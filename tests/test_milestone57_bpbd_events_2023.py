from __future__ import annotations

import unittest

from scripts.validate_milestone57_bpbd_events_2023 import validate


class Milestone57BPBDEvents2023Tests(unittest.TestCase):
    def test_materialization_is_dashboard_filter_ready_without_cross_source_upgrade(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["district_count"], 19)
        self.assertEqual(report["hazard_count"], 10)
        self.assertEqual(report["canonical_row_count"], 190)
        self.assertEqual(report["province_total_events"], 1031)
        self.assertTrue(report["same_producer_total_reconciles"])
        self.assertTrue(report["dashboard_filter_ready"])


if __name__ == "__main__":
    unittest.main()
