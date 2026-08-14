from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_historical_reconstruction import validate  # noqa: E402


class HistoricalReconstructionTests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertEqual(6, counts["events"])
        self.assertGreaterEqual(counts["qualified_sources"], 10)
        self.assertEqual(2, counts["gaps"])

    def test_1945_1946_is_not_silently_filled(self) -> None:
        path = ROOT / "data" / "registries" / "historical_source_inventory.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        gap = next(row for row in rows if row["source_record_id"] == "archive_gap_1945_1946")
        self.assertEqual("gap", gap["status"])
        self.assertEqual("", gap["official_url"])
        self.assertEqual("1945", gap["reference_start"])
        self.assertEqual("1946", gap["reference_end"])

    def test_1950_event_keeps_year_precision(self) -> None:
        path = ROOT / "data" / "registries" / "historical_geography_events.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        event = next(row for row in rows if row["event_id"] == "sumatera_tengah_1950")
        self.assertEqual("1950", event["event_date"])
        self.assertEqual("year", event["event_date_precision"])

    def test_1961_boundary_warning_is_hard_constraint(self) -> None:
        path = ROOT / "data" / "registries" / "historical_geography_events.csv"
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        warning = next(row for row in rows if row["event_id"] == "census_boundary_warning_1961")
        self.assertIn("Tingkat I", warning["implication"])
        self.assertIn("area", warning["implication"])

    def test_extraction_schema_distinguishes_reconstructed_values(self) -> None:
        path = ROOT / "schemas" / "historical-extraction.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        states = schema["properties"]["reconstruction_state"]["enum"]
        self.assertIn("observed_source_era", states)
        self.assertIn("reconstructed_geography", states)
        self.assertIn("reconstructed_definition", states)
        self.assertIn("not_comparable", states)


if __name__ == "__main__":
    unittest.main()
