from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from discover_bps_candidate_series import select_latest_numeric_period  # noqa: E402


class BPSCandidateDiscoveryTests(unittest.TestCase):
    def test_latest_numeric_period_uses_label_not_internal_id(self) -> None:
        rows = [
            {"th": "2020", "th_id": 900},
            {"th": "2025", "th_id": 125},
            {"th": "2024", "th_id": 999},
        ]
        self.assertEqual(("2025", "125"), select_latest_numeric_period(rows))

    def test_non_numeric_period_labels_are_ignored(self) -> None:
        rows = [
            {"th": "Semester I", "th_id": 1},
            {"th": "2023", "th_id": 123},
        ]
        self.assertEqual(("2023", "123"), select_latest_numeric_period(rows))

    def test_no_numeric_period_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "no numeric period"):
            select_latest_numeric_period([{"th": "Semester I", "th_id": 1}])


if __name__ == "__main__":
    unittest.main()
