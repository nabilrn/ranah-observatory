from __future__ import annotations

import unittest

from scripts.validate_milestone49_bpbd_local_taxonomy_compatibility import (
    EXPECTED_LARGEST,
    validate,
)


class Milestone49BpbdLocalTaxonomyCompatibilityTests(unittest.TestCase):
    def test_gate_is_complete_and_fail_closed(self) -> None:
        report = validate()
        self.assertTrue(report["complete"])
        self.assertEqual(report["m42_2015_explicit_geography_rows"], 14)
        self.assertEqual(report["m42_2015_event_sum"], 89)
        self.assertEqual(report["bpbd_operational_category_count"], 21)
        self.assertEqual(report["bpbd_operational_incident_total"], 686)
        self.assertEqual(report["arithmetic_difference"], 597)
        self.assertFalse(report["independent_same_concept_crosscheck_qualified"])
        self.assertFalse(report["canonical_historical_impact_promotion_authorized"])

    def test_largest_operational_classes_are_frozen(self) -> None:
        self.assertEqual(
            EXPECTED_LARGEST,
            {
                "Kebakaran": 285,
                "Longsor": 130,
                "Angin Kencang": 116,
                "Banjir": 68,
            },
        )


if __name__ == "__main__":
    unittest.main()
