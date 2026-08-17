from __future__ import annotations

import unittest

from scripts.audit_milestone8_design import EXPECTED_GEOGRAPHIES, EXPECTED_SOURCE_IDS, audit


class Milestone8DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit()

    def test_preregistered_foundation_passes(self) -> None:
        self.assertEqual(self.report["errors"], [])
        self.assertTrue(self.report["design_preregistered"])
        self.assertTrue(self.report["geography_2005_2013_qualified"])

    def test_exact_geography_and_source_contract(self) -> None:
        self.assertEqual(self.report["geography_count"], len(EXPECTED_GEOGRAPHIES))
        self.assertEqual(self.report["source_plan_count"], len(EXPECTED_SOURCE_IDS))
        self.assertEqual(self.report["event_date"], "2009-09-30")

    def test_claim_strength_remains_locked_before_estimation(self) -> None:
        self.assertFalse(self.report["quasi_causal_effect_estimated"])
        self.assertFalse(self.report["causal_claim_authorized"])
        self.assertFalse(self.report["milestone8_complete"])
        self.assertGreater(self.report["blocking_reason_count"], 0)

    def test_case_study_identity_is_stable(self) -> None:
        self.assertEqual(
            self.report["case_study"],
            "2009 West Sumatra earthquake differential economic trajectory",
        )
        self.assertEqual(
            self.report["criterion"],
            "one focused causal or quasi-causal case study",
        )


if __name__ == "__main__":
    unittest.main()
