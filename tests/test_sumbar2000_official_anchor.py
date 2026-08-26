from __future__ import annotations

import unittest

from scripts.validate_sumbar2000_official_anchor import validate


class Sumbar2000OfficialAnchorTest(unittest.TestCase):
    def test_complete_artifact_and_population_anchor_are_bounded(self) -> None:
        result = validate()
        self.assertTrue(result["artifact_complete"])
        self.assertEqual(result["artifact_pages"], 646)
        self.assertEqual(result["population_total"], 4_220_318)
        self.assertEqual(result["source_native_rows"], 1)
        self.assertFalse(result["blanket_numeric_promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
