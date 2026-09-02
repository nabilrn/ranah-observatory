from __future__ import annotations

import unittest

from scripts.validate_milestone56_bpbd_dibi_2022_ppid_raw_artifact_recovery import validate


class Milestone56BPBDDIBI2022PPIDRawArtifactRecoveryTests(unittest.TestCase):
    def test_raw_artifact_is_recovered_but_materialization_remains_gated(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["uuid"], "faf18bd0-76d9-44b2-8092-b89f70f29e6e")
        self.assertEqual(report["bytes"], 13_044_950)
        self.assertEqual(report["pages"], 154)
        self.assertEqual(report["verified_table_count"], 10)
        self.assertEqual(report["recorded_loss_difference_rupiah"], 540)
        self.assertTrue(report["raw_artifact_gate_satisfied"])
        self.assertFalse(report["materialization_authorized"])


if __name__ == "__main__":
    unittest.main()
