from __future__ import annotations

import unittest

from scripts.validate_sumbar1990_incomplete_artifact import validate


class Sumbar1990IncompleteArtifactTest(unittest.TestCase):
    def test_incomplete_official_artifact_remains_fail_closed(self) -> None:
        result = validate()
        self.assertEqual(result["artifact_bytes"], 14_702_296)
        self.assertEqual(result["pdf_pages"], 58)
        self.assertFalse(result["full_publication_artifact_acquired"])
        self.assertFalse(result["numeric_promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
