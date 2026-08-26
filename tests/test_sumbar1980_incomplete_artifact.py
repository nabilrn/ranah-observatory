from __future__ import annotations

import unittest

from scripts.validate_sumbar1980_incomplete_artifact import validate


class Sumbar1980IncompleteArtifactTest(unittest.TestCase):
    def test_fail_closed_incomplete_official_artifact(self) -> None:
        result = validate()
        self.assertEqual(result["artifact_bytes"], 5_361_943)
        self.assertEqual(result["pdf_pages"], 22)
        self.assertFalse(result["full_publication_artifact_acquired"])
        self.assertFalse(result["numeric_promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
