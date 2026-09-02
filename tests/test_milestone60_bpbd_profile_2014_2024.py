from __future__ import annotations

import unittest

from scripts.validate_milestone60_bpbd_profile_2014_2024 import validate


class Milestone60BPBDProfileTests(unittest.TestCase):
    def test_m60_blocks_unsafe_historical_promotion(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["status"], "qualification_hold")
        self.assertTrue(report["raw_profile_frozen"])
        self.assertTrue(report["raw_book_frozen"])
        self.assertFalse(report["historical_series_materialized"])
        self.assertTrue(report["unsafe_numeric_promotion_blocked"])


if __name__ == "__main__":
    unittest.main()
