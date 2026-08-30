from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_final_open_gates import validate


class FinalOpenGatesTest(unittest.TestCase):
    def test_release_blockers_are_separated_from_deferred_research(self) -> None:
        result = validate()
        self.assertEqual(result["must_close_total"], 6)
        self.assertEqual(result["must_close_satisfied"], 4)
        self.assertEqual(result["must_close_open_internal"], 2)
        self.assertEqual(result["must_close_blocked_external"], 0)
        self.assertEqual(result["deferred_research_gates"], 7)
        self.assertFalse(result["mass_workflow_deletion_authorized"])


if __name__ == "__main__":
    unittest.main()
