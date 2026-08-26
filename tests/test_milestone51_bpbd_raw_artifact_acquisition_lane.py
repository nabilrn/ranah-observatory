from __future__ import annotations

import unittest

from scripts.validate_milestone51_bpbd_raw_artifact_acquisition_lane import validate


class Milestone51BPBDRawArtifactAcquisitionLaneTests(unittest.TestCase):
    def test_lane_is_complete_but_artifact_remains_unacquired(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["queue_rows"], 5)
        self.assertEqual(report["companion_rows"], 4)
        self.assertEqual(report["p0_exit_gate_request"], "bpbd_pusdalops_2017")
        self.assertEqual(report["allowed_host"], "sumbarprov.go.id")
        self.assertEqual(report["legacy_bps_default_host"], "bps.go.id")
        self.assertEqual(report["active_ppid_inventory"], "https://ppid.sumbarprov.go.id/home/dip")
        self.assertEqual(report["legacy_2017_download_audit_record_id"], 8604)
        self.assertFalse(report["record_8604_to_current_uuid_mapping_recovered"])
        self.assertFalse(report["raw_2017_artifact_acquired"])
        self.assertFalse(report["m52_trigger_satisfied"])


if __name__ == "__main__":
    unittest.main()
