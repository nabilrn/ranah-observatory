from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bps_expansion_canonical import _transform_value  # noqa: E402
from validate_bps_expansion import validate  # noqa: E402


class BPSExpansionTests(unittest.TestCase):
    def test_contract_validator_passes(self) -> None:
        errors, counts = validate()
        self.assertEqual([], errors, "\n".join(errors))
        self.assertEqual(7, counts["series"])
        self.assertEqual(6, counts["qualifications"])
        self.assertEqual(41, counts["geography_mappings"])
        self.assertEqual(726, counts["expected_source_rows"])
        self.assertEqual(574, counts["expected_canonical_rows"])
        self.assertEqual(152, counts["expected_held_rows"])

    def test_share_transform_uses_same_source_numerator_and_denominator(self) -> None:
        row = {
            "expansion_row_id": "share",
            "raw_value": "25",
            "denominator_raw_value": "100",
            "transform": "share_percent",
        }
        self.assertEqual(25.0, _transform_value(row))

    def test_share_transform_rejects_zero_denominator(self) -> None:
        row = {
            "expansion_row_id": "share",
            "raw_value": "25",
            "denominator_raw_value": "0",
            "transform": "share_percent",
        }
        with self.assertRaisesRegex(ValueError, "positive"):
            _transform_value(row)

    def test_rice_transform_converts_quintal_to_tonnes_per_hectare(self) -> None:
        row = {
            "expansion_row_id": "rice",
            "raw_value": "48.6727",
            "denominator_raw_value": "",
            "transform": "quintal_per_hectare_to_tonnes_per_hectare",
        }
        self.assertAlmostEqual(4.86727, _transform_value(row))


if __name__ == "__main__":
    unittest.main()
