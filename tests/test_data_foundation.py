from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_data_foundation import DOMAINS, validate  # noqa: E402


class DataFoundationTests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertGreaterEqual(counts["geographies"], 21)
        # The registry is the ontology/backlog, not the Milestone 4 completion
        # count. Milestone 4 separately requires 40-60 indicators with
        # canonical observations and resolved provenance.
        self.assertGreaterEqual(counts["indicators"], 40)
        self.assertEqual(12, counts["domains"])

    def test_current_sumbar_bps_codes_are_seeded(self) -> None:
        expected = {
            "13",
            "1301",
            "1302",
            "1303",
            "1304",
            "1305",
            "1306",
            "1307",
            "1308",
            "1309",
            "1310",
            "1311",
            "1312",
            "1371",
            "1372",
            "1373",
            "1374",
            "1375",
            "1376",
            "1377",
        }
        with (ROOT / "data" / "registries" / "geographies.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        actual = {row["bps_code"].strip() for row in rows if row["bps_code"].strip()}
        self.assertEqual(expected, actual)
        current_seed = [row for row in rows if row["status"].strip() == "current"]
        self.assertEqual(21, len(current_seed))

    def test_indicator_registry_covers_all_domains(self) -> None:
        with (ROOT / "data" / "registries" / "indicators.csv").open(
            "r", encoding="utf-8", newline=""
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(DOMAINS, {row["domain"].strip() for row in rows})

    def test_schema_contains_observation_and_provenance_contracts(self) -> None:
        with (ROOT / "schemas" / "data-foundation.schema.json").open(
            "r", encoding="utf-8"
        ) as handle:
            schema = json.load(handle)
        self.assertIn("observation", schema["$defs"])
        self.assertIn("provenance", schema["$defs"])
        self.assertIn("geographyCrosswalk", schema["$defs"])


if __name__ == "__main__":
    unittest.main()
