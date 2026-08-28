from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_revision_localization.py"


class SumbarConstructionRevisionLocalizationTest(unittest.TestCase):
    def test_validator_confirms_revision_but_not_mechanism(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["rows"], 4)
        self.assertTrue(result["revision_event_confirmed"])
        self.assertFalse(result["revision_mechanism_explained"])
        self.assertTrue(result["year_2001_and_2002_common_scaling_pattern"])
        self.assertEqual(
            result["refined_2002_classification"],
            "major_release_break_explicit_revision_cause_unexplained",
        )
        self.assertFalse(result["single_continuous_1998_2006_trajectory_authorized"])


if __name__ == "__main__":
    unittest.main()
