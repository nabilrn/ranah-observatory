from __future__ import annotations

import unittest

from scripts.validate_sp1961_official_anchor import EXPECTED_SHA256, validate


class SP1961OfficialAnchorTests(unittest.TestCase):
    def test_official_anchor_contract(self) -> None:
        result = validate()
        self.assertEqual(result["rows"], 13)
        self.assertEqual(result["local_units"], 12)
        self.assertEqual(result["province_total"], 2_319_057)
        self.assertEqual(result["artifact_sha256"], EXPECTED_SHA256)


if __name__ == "__main__":
    unittest.main()
