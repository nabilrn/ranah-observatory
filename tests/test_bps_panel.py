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
        self.assertEqual(7, counts["canonical_ready"])
        self.assertEqual(1, counts["held_source_native"])
        self.assertEqual(8, counts["qualifications"])

    def test_internet_source_is_not_silently_household_measure(self) -> None:
        path = ROOT / "data" / "registries" / "bps_panel_series.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        row = next(item for item in rows if item["bps_var_id"] == "320")
        self.assertEqual("595", row["selected_turvar_id"])
        self.assertEqual("pending_indicator_universe_review", row["canonical_promotion_status"])
        self.assertIn("Person age 5+", row["comparability_notes"])

    def test_tpak_unit_gap_is_closed_by_official_qualification(self) -> None:
        series_path = ROOT / "data" / "registries" / "bps_panel_series.csv"
        qualifications_path = ROOT / "data" / "registries" / "bps_panel_qualification.csv"
        with series_path.open("r", encoding="utf-8", newline="") as handle:
            series = list(csv.DictReader(handle))
        with qualifications_path.open("r", encoding="utf-8", newline="") as handle:
            qualifications = list(csv.DictReader(handle))
        row = next(item for item in series if item["bps_var_id"] == "141")
        qualification = next(item for item in qualifications if item["qualification_id"] == row["qualification_id"])
        self.assertEqual("canonical_ready", row["canonical_promotion_status"])
        self.assertEqual("percent", qualification["canonical_unit"])
        self.assertEqual("calendar_month_august", qualification["reference_period_rule"])

    def test_only_person_level_internet_source_remains_held(self) -> None:
        path = ROOT / "data" / "registries" / "bps_panel_series.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        held = [row for row in rows if row["canonical_promotion_status"] != "canonical_ready"]
        self.assertEqual(["internet_person_5plus"], [row["panel_series_id"] for row in held])


if __name__ == "__main__":
    unittest.main()
