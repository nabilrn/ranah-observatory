from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_bps_historical_anchor import validate  # noqa: E402


class BPSHistoricalAnchorTests(unittest.TestCase):
    def test_frozen_1971_anchor_contract(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors)
        self.assertEqual(15, counts["source_rows"])
        self.assertEqual(14, counts["local_rows"])


if __name__ == "__main__":
    unittest.main()
