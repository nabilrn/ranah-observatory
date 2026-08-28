from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_revision_mechanism_candidate.py"


class SumbarConstructionRevisionMechanismCandidateTest(unittest.TestCase):
    def test_candidate_is_operationally_linked_but_not_causal(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["evidence_rows"], 6)
        self.assertTrue(result["revision_event_confirmed"])
        self.assertEqual(
            result["candidate_mechanism"],
            "sampling_frame_refresh_plus_qualification_based_expansion_reestimation",
        )
        self.assertEqual(
            result["candidate_status"],
            "operationally_plausible_period_link_confirmed_causal_revision_link_unproven",
        )
        self.assertFalse(result["causal_revision_link_proven"])
        self.assertFalse(result["cross_vintage_bridge_authorized"])
        self.assertFalse(result["backcast_factor_authorized"])


if __name__ == "__main__":
    unittest.main()
