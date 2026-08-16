from __future__ import annotations

import unittest

try:
    from scripts.build_chirps_rainfall_production import (
        EXPECTED_ANNUAL_ROWS,
        EXPECTED_COG_COUNT,
        EXPECTED_MONTHLY_ROWS,
        MIN_VALID_AREA_FRACTION,
        PRODUCTION_YEARS,
        annualize_monthly,
    )
except ModuleNotFoundError as exc:  # dedicated climate workflows install these deps
    raise unittest.SkipTest(f"optional geospatial test dependencies unavailable: {exc}") from exc


class ChirpsRainfallProductionTests(unittest.TestCase):
    def test_production_scope_is_exactly_1981_through_2025(self) -> None:
        self.assertEqual(PRODUCTION_YEARS[0], 1981)
        self.assertEqual(PRODUCTION_YEARS[-1], 2025)
        self.assertEqual(len(PRODUCTION_YEARS), 45)
        self.assertEqual(EXPECTED_COG_COUNT, 540)
        self.assertEqual(EXPECTED_MONTHLY_ROWS, 10260)
        self.assertEqual(EXPECTED_ANNUAL_ROWS, 855)

    def test_coverage_threshold_retains_margin_below_sample_minimum(self) -> None:
        self.assertEqual(MIN_VALID_AREA_FRACTION, 0.995)
        self.assertLess(MIN_VALID_AREA_FRACTION, 0.99877921)

    def test_annualization_preserves_model_estimate_contract(self) -> None:
        rows = [
            {
                "geography_id": "idn.13.1371",
                "geography_name": "Padang",
                "year": 1981,
                "month": month,
                "monthly_rainfall_mm": 100.0,
                "valid_area_fraction": 0.999,
            }
            for month in range(1, 13)
        ]
        annual = annualize_monthly(rows)
        self.assertEqual(len(annual), 1)
        self.assertEqual(annual[0]["annual_rainfall_mm"], 1200.0)
        self.assertEqual(annual[0]["claim_type"], "model_estimate")
        self.assertEqual(annual[0]["spatial_frame"], "fixed_current_boundary_june_2026")
        self.assertEqual(annual[0]["months_complete"], 12)

    def test_annualization_rejects_duplicate_or_incomplete_month_set(self) -> None:
        rows = [
            {
                "geography_id": "idn.13.1371",
                "geography_name": "Padang",
                "year": 1981,
                "month": month,
                "monthly_rainfall_mm": 100.0,
                "valid_area_fraction": 1.0,
            }
            for month in range(1, 12)
        ]
        rows.append({
            "geography_id": "idn.13.1371",
            "geography_name": "Padang",
            "year": 1981,
            "month": 11,
            "monthly_rainfall_mm": 100.0,
            "valid_area_fraction": 1.0,
        })
        with self.assertRaises(RuntimeError):
            annualize_monthly(rows)


if __name__ == "__main__":
    unittest.main()
