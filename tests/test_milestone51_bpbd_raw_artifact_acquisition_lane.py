from __future__ import annotations

import unittest

from scripts.validate_milestone51_bpbd_raw_artifact_acquisition_lane import validate


class Milestone51BPBDRawArtifactAcquisitionLaneTests(unittest.TestCase):
    def test_lane_is_complete_but_artifact_remains_unacquired(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["queue_rows"], 3)
        self.assertEqual(report["p0_exit_gate_request"], "bpbd_pusdalops_2017")
        self.assertEqual(report["allowed_host"], "sumbarprov.go.id")
        self.assertEqual(report["legacy_bps_default_host"], "bps.go.id")
        self.assertFalse(report["raw_2017_artifact_acquired"])


if __name__ == "__main__":
    unittest.main()
