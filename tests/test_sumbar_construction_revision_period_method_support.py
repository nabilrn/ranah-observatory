from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_revision_period_method_support.py"


class SumbarConstructionRevisionPeriodMethodSupportTest(unittest.TestCase):
    def test_period_method_support_strengthens_evidence_without_causal_upgrade(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["annual_2005_respondents"], 8168)
        self.assertTrue(result["period_specific_sampling_support"])
        self.assertTrue(result["period_specific_qualification_expansion_support"])
        self.assertFalse(result["frame_identity_proven"])
        self.assertFalse(result["revision_reestimation_link_proven"])
        self.assertFalse(result["causal_revision_link_proven"])


if __name__ == "__main__":
    unittest.main()
