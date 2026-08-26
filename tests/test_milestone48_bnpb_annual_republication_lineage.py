from __future__ import annotations

import unittest

from scripts.validate_milestone48_bnpb_annual_republication_lineage import EXPECTED, validate


class Milestone48AnnualRepublicationLineageTests(unittest.TestCase):
    def test_gate_is_complete_and_independence_fails_closed(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["years_verified"], 8)
        self.assertEqual(report["exact_locator_matches"], 8)
        self.assertEqual(report["exact_sha256_matches"], 8)
        self.assertFalse(report["independent_same_grain_counterpart_found"])
        self.assertFalse(report["canonical_historical_impact_promotion_authorized"])

    def test_expected_portal_source_objects_are_frozen(self) -> None:
        self.assertEqual(set(EXPECTED), set(range(2010, 2018)))
        self.assertEqual(EXPECTED[2010][2], "1grzKv-JYqXh8iLRXwztFOtSQL3vqiG0G")
        self.assertEqual(EXPECTED[2017][2], "1qRNz3QLxm0UERt1L_qiZNcP25tSZ25YN")
        self.assertEqual(
            EXPECTED[2010][4],
            "bc720b2e9eff0d6fc246a6df98b862b9047d3dc35b754c0b707f6e5d91918a32",
        )
        self.assertEqual(
            EXPECTED[2017][4],
            "de218de3da3c16db20442a5e9fbedac1f6b6906128160b43c3400bf5a63f266d",
        )


if __name__ == "__main__":
    unittest.main()
