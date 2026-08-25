from __future__ import annotations

import unittest

from scripts.validate_milestone47_bnpb_impact_overlap_eligibility import (
    EXPECTED_RESOURCES,
    validate,
)


class Milestone47ImpactOverlapEligibilityTests(unittest.TestCase):
    def test_gate_is_complete_and_fail_closed(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["candidate_metric_count"], 5)
        self.assertEqual(report["district_overlap_eligible_metric_count"], 0)
        self.assertFalse(report["same_grain_overlap_counterpart_found"])
        self.assertFalse(report["canonical_district_impact_promotion_authorized"])

    def test_expected_retrospective_resources_are_frozen(self) -> None:
        self.assertEqual(
            EXPECTED_RESOURCES,
            {
                "meninggal": "b2fa5c46-9a07-4d30-a3bd-57e143e775f1",
                "hilang": "a19366cf-0ac4-45d1-bc6e-89a020ab45a1",
                "terluka": "ce67795b-57e4-4c84-8c2a-3bf03828ff0d",
                "menderita": "7f9e5218-bbba-4916-a2b8-13cf1764dc96",
                "mengungsi": "d7b61b56-43d5-4dcc-8d7b-45c993e1bdb0",
            },
        )


if __name__ == "__main__":
    unittest.main()
