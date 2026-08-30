from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_public_history import validate


class PublicHistoryTest(unittest.TestCase):
    def test_public_history_remains_context_only(self) -> None:
        result = validate()
        self.assertEqual(result["cards"], 3)
        self.assertEqual(result["annual_points"], 5)
        self.assertTrue(result["historical_context_display"])
        self.assertFalse(result["harmonized_series_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
