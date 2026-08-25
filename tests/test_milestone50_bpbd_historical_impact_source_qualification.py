from __future__ import annotations

import unittest

from scripts.validate_milestone50_bpbd_historical_impact_source_qualification import validate


class Milestone50BPBDHistoricalImpactSourceQualificationTests(unittest.TestCase):
    def test_gate_is_complete_and_fail_closed(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["candidate_source_count"], 2)
        self.assertTrue(report["impact_capable_source_family"])
        self.assertFalse(report["official_2017_raw_artifact_acquired"])
        self.assertFalse(report["bpbd_source_native_impact_ingestion_authorized"])
        self.assertFalse(report["canonical_historical_impact_promotion_authorized"])

    def test_raw_artifact_is_required_before_ingestion(self) -> None:
        report = validate()
        self.assertFalse(report["official_2017_raw_artifact_acquired"])
        self.assertFalse(report["bpbd_source_native_impact_ingestion_authorized"])


if __name__ == "__main__":
    unittest.main()
