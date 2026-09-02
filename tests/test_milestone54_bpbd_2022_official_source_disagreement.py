from __future__ import annotations

import unittest

from scripts.validate_milestone54_bpbd_2022_official_source_disagreement import validate


class Milestone54BPBD2022OfficialSourceDisagreementTests(unittest.TestCase):
    def test_official_source_disagreement_remains_explicit_and_fail_closed(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["dibi_events"], 1021)
        self.assertEqual(report["lkj_events"], 1047)
        self.assertEqual(report["event_gap"], 26)
        self.assertEqual(report["dibi_hazard_categories"], 7)
        self.assertEqual(report["lkj_hazard_categories"], 13)
        self.assertEqual(report["bridge_difference"], 20)
        self.assertEqual(report["unmatched_lkj_events"], 6)
        self.assertFalse(report["unified_series_authorized"])


if __name__ == "__main__":
    unittest.main()
