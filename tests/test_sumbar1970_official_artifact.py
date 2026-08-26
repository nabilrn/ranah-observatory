from __future__ import annotations

import unittest

from scripts.validate_sumbar1970_official_artifact import validate


class Sumbar1970OfficialArtifactTest(unittest.TestCase):
    def test_bounded_official_artifact_checkpoint(self) -> None:
        result = validate()
        self.assertEqual(result["artifact_bytes"], 46_897_865)
        self.assertEqual(result["pdf_pages"], 138)
        self.assertEqual(result["text_chars"], 28_290)
        self.assertFalse(result["numeric_promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
