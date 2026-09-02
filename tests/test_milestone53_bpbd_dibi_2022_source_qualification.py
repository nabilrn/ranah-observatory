from __future__ import annotations

import unittest

from scripts.validate_milestone53_bpbd_dibi_2022_source_qualification import validate


class Milestone53BPBDDIBI2022SourceQualificationTests(unittest.TestCase):
    def test_source_is_qualified_but_materialization_remains_blocked(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["queue_rows"], 1)
        self.assertEqual(report["events"], 1021)
        self.assertEqual(report["hazard_total"], 1021)
        self.assertEqual(report["monthly_total"], 1021)
        self.assertEqual(report["district_disagreements"], 7)
        self.assertFalse(report["raw_artifact_acquired"])
        self.assertFalse(report["materialization_authorized"])
        self.assertTrue(report["m52_still_blocked"])


if __name__ == "__main__":
    unittest.main()
