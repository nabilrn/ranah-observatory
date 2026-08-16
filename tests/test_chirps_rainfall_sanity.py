from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_chirps_rainfall_sanity import (
    ROOT,
    build_report,
    percentile,
    read_csv,
)


OBSERVATIONS = ROOT / "data" / "processed" / "climate" / "rainfall" / "chirps-annual-rainfall-observations.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"


class ChirpsRainfallSanityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.observations = read_csv(OBSERVATIONS)
        cls.geographies = read_csv(GEOGRAPHIES)
        cls.report = build_report(cls.observations, cls.geographies)

    def test_percentile_uses_linear_interpolation(self) -> None:
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.25), 1.75)
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.75), 3.25)

    def test_frozen_baseline_footprint_remains_exact(self) -> None:
        baseline = self.report["baseline"]
        self.assertEqual(baseline["observation_count"], 855)
        self.assertEqual(baseline["geography_count"], 19)
        self.assertEqual(baseline["first_year"], 1981)
        self.assertEqual(baseline["last_year"], 2025)
        self.assertGreaterEqual(baseline["minimum_valid_area_fraction"], 0.995)

    def test_1997_1998_transition_is_spatially_synchronous(self) -> None:
        transition = self.report["diagnostics"]["transition_1997_1998"]
        self.assertEqual(transition["geography_count"], 19)
        self.assertEqual(transition["positive_geography_count"], 19)
        self.assertTrue(transition["directionally_synchronous"])
        self.assertGreater(transition["minimum_change_pct"], 0.0)
        self.assertEqual(
            transition["classification"],
            "plausible_regional_climate_signal_pending_independent_station_validation",
        )

    def test_spatial_iqr_profile_is_stable_but_not_rejection_logic(self) -> None:
        spatial = self.report["diagnostics"]["spatial_iqr"]
        self.assertEqual(spatial["flag_count"], 28)
        expected = {
            "idn.13.1377": 15,  # Pariaman
            "idn.13.1306": 7,   # Padang Pariaman
            "idn.13.1371": 4,   # Padang
            "idn.13.1375": 1,   # Bukittinggi
            "idn.13.1376": 1,   # Payakumbuh
        }
        actual = {gid: item["count"] for gid, item in spatial["counts_by_geography"].items()}
        self.assertEqual(actual, expected)
        self.assertIn("descriptive review flag only", spatial["method"])

    def test_focus_local_magnitudes_remain_unresolved_without_station_evidence(self) -> None:
        focus = self.report["review_classifications"]["focus_local_magnitudes"]
        self.assertEqual({item["geography_name"] for item in focus}, {"Pariaman", "Padang Pariaman", "Padang"})
        self.assertTrue(
            all(
                item["classification"] == "unresolved_local_magnitude_pending_independent_station_validation"
                for item in focus
            )
        )
        self.assertTrue(all(item["internal_processing_concern_detected"] is False for item in focus))
        self.assertFalse(self.report["review_classifications"]["safe_to_upgrade_claim_type_to_observed"])

    def test_evidence_class_does_not_move_beyond_model_estimate(self) -> None:
        self.assertEqual(self.report["baseline"]["claim_type"], "model_estimate")
        self.assertEqual(self.report["review_classifications"]["independent_station_validation"], "pending")
        self.assertTrue(self.report["gates"]["claim_type_remains_model_estimate"])
        self.assertTrue(self.report["gates"]["station_validation_still_pending"])


if __name__ == "__main__":
    unittest.main()
