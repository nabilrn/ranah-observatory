from __future__ import annotations

import unittest

from scripts.validate_milestone58_bpbd_events_2024 import validate


class Milestone58BPBDEvents2024Tests(unittest.TestCase):
    def test_district_slice_preserves_unallocated_gap(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["district_count"], 19)
        self.assertEqual(report["source_total_events"], 1175)
        self.assertEqual(report["mapped_district_events"], 1166)
        self.assertEqual(report["unallocated_difference_events"], 9)
        self.assertTrue(report["dashboard_district_filter_ready"])


if __name__ == "__main__":
    unittest.main()
