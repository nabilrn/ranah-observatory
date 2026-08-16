import unittest

import numpy as np
from affine import Affine
from shapely.geometry import box

from scripts.build_chirps_rainfall_poc import (
    POC_YEAR,
    annualize_monthly,
    build_area_weights,
    weighted_mean_with_coverage,
)


class ChirpsRainfallPocTests(unittest.TestCase):
    def test_uniform_values_remain_uniform_after_geodesic_area_weighting(self) -> None:
        weights = build_area_weights(
            box(0.0, 0.0, 2.0, 2.0),
            Affine(1.0, 0.0, 0.0, 0.0, -1.0, 2.0),
            height=2,
            width=2,
        )
        values = np.full((2, 2), 10.0, dtype=float)
        mean, coverage, valid_cells = weighted_mean_with_coverage(values, weights, None)
        self.assertAlmostEqual(mean, 10.0)
        self.assertAlmostEqual(coverage, 1.0)
        self.assertEqual(valid_cells, 4)

    def test_chirps_missing_sentinel_is_excluded_even_without_gdal_nodata(self) -> None:
        weights = build_area_weights(
            box(0.0, 0.0, 2.0, 2.0),
            Affine(1.0, 0.0, 0.0, 0.0, -1.0, 2.0),
            height=2,
            width=2,
        )
        values = np.array([[20.0, -9999.0], [20.0, -9999.0]], dtype=float)
        mean, coverage, valid_cells = weighted_mean_with_coverage(values, weights, None)
        self.assertAlmostEqual(mean, 20.0)
        self.assertAlmostEqual(coverage, 0.5, places=6)
        self.assertEqual(valid_cells, 2)

    def test_negative_rainfall_fails_closed(self) -> None:
        weights = [(0, 0, 1.0)]
        with self.assertRaises(RuntimeError):
            weighted_mean_with_coverage(np.array([[-1.0]]), weights, None)

    def test_annualization_requires_all_twelve_months(self) -> None:
        rows = [
            {
                "geography_id": "idn.13.1371",
                "geography_name": "Padang",
                "year": POC_YEAR,
                "month": month,
                "monthly_rainfall_mm": 100.0,
                "valid_area_fraction": 1.0,
            }
            for month in range(1, 12)
        ]
        with self.assertRaises(RuntimeError):
            annualize_monthly(rows)

    def test_annualization_sums_monthly_totals_and_preserves_claim_contract(self) -> None:
        rows = [
            {
                "geography_id": "idn.13.1371",
                "geography_name": "Padang",
                "year": POC_YEAR,
                "month": month,
                "monthly_rainfall_mm": 100.0,
                "valid_area_fraction": 0.95,
            }
            for month in range(1, 13)
        ]
        annual = annualize_monthly(rows)
        self.assertEqual(len(annual), 1)
        self.assertAlmostEqual(annual[0]["annual_rainfall_mm"], 1200.0)
        self.assertEqual(annual[0]["months_complete"], 12)
        self.assertEqual(annual[0]["claim_type"], "model_estimate")
        self.assertEqual(annual[0]["spatial_frame"], "fixed_current_boundary_june_2026")


if __name__ == "__main__":
    unittest.main()
