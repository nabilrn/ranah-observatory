from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_bps_panel import validate  # noqa: E402


class BPSNormalizedPanelTests(unittest.TestCase):
    def test_panel_registry_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertEqual(8, counts["series"])
        self.assertEqual(8, counts["indicators"])

    def test_internet_source_is_not_silently_household_measure(self) -> None:
        path = ROOT / "data" / "registries" / "bps_panel_series.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["bps_var_id"] == "320")
        self.assertEqual("595", row["selected_turvar_id"])
        self.assertEqual("pending_indicator_universe_review", row["canonical_promotion_status"])
        self.assertIn("Person age 5+", row["comparability_notes"])

    def test_tpak_unit_gap_is_a_promotion_blocker(self) -> None:
        path = ROOT / "data" / "registries" / "bps_panel_series.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["bps_var_id"] == "141")
        self.assertEqual("pending_unit_crosscheck", row["canonical_promotion_status"])


if __name__ == "__main__":
    unittest.main()
