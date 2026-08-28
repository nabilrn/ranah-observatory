from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_revision_persistence_release_lifecycle.py"


class SumbarConstructionRevisionPersistenceReleaseLifecycleTest(unittest.TestCase):
    def test_persistence_and_release_maturation_are_separated(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["persistent_revised_years"], [2002, 2003])
        self.assertEqual(result["release_maturation_years"], [2004, 2005])
        self.assertTrue(result["revised_values_persist_exactly"])
        self.assertFalse(result["single_yearbook_anomaly"])
        self.assertFalse(result["causal_revision_link_proven"])
        self.assertFalse(result["cross_vintage_bridge_authorized"])


if __name__ == "__main__":
    unittest.main()
