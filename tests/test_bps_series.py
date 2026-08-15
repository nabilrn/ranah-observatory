from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from harvest_bps_series import resolve_periods, year_labels  # noqa: E402


class BPSPeriodSeriesTests(unittest.TestCase):
    def test_resolve_periods_uses_source_metadata_ids(self) -> None:
        rows = [
            {"th": "2025", "th_id": 125},
            {"th": "1971", "th_id": 71},
            {"th": "2020", "th_id": 120},
        ]
        self.assertEqual(
            [("1971", "71"), ("2025", "125")],
            resolve_periods(rows, ["1971", "2025"]),
        )

    def test_resolve_periods_rejects_missing_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "unavailable"):
            resolve_periods([{"th": "2025", "th_id": 125}], ["2024"])

    def test_resolve_periods_rejects_ambiguous_label(self) -> None:
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            resolve_periods(
                [{"th": "2025", "th_id": 125}, {"th": "2025", "th_id": 999}],
                ["2025"],
            )

    def test_year_labels_are_inclusive(self) -> None:
        self.assertEqual(["2023", "2024", "2025"], year_labels(2023, 2025))

    def test_year_labels_reject_reverse_range(self) -> None:
        with self.assertRaisesRegex(ValueError, "end year"):
            year_labels(2025, 2023)


if __name__ == "__main__":
    unittest.main()
