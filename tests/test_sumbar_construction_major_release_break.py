from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_major_release_break.py"


class SumbarConstructionMajorReleaseBreakTest(unittest.TestCase):
    def test_validator_passes_and_blocks_longitudinal_bridge(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["rows"], 12)
        self.assertFalse(result["year_2002_break_explained"])
        self.assertTrue(result["year_2003_status_transition_supported"])
        self.assertFalse(result["cross_release_longitudinal_bridge_authorized"])
        self.assertFalse(result["single_continuous_1998_2006_trajectory_authorized"])


if __name__ == "__main__":
    unittest.main()
