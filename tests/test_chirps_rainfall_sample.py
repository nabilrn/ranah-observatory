from __future__ import annotations

import unittest

try:
    import numpy as np
    from affine import Affine
    from shapely.geometry import box

    from scripts.build_chirps_rainfall_sample import (
        CHIRPS_MISSING_SENTINEL,
        SAMPLE_YEARS,
        annualize_monthly,
        build_area_weights,
        build_diagnostics,
        weighted_mean_with_coverage,
    )
except ModuleNotFoundError as exc:  # dedicated climate workflows install these deps
    raise unittest.SkipTest(f"optional geospatial test dependencies unavailable: {exc}") from exc


class ChirpsRainfallSampleTests(unittest.TestCase):
    def test_area_weighting_preserves_uniform_field(self) -> None:
        weights = build_area_weights(
            box(0.0, 0.0, 2.0, 2.0),
            Affine(1.0, 0.0, 0.0, 0.0, -1.0, 2.0),
            height=2,
            width=2,
        )
        values = np.full((2, 2), 25.0, dtype=float)
        mean, coverage, valid_cells = weighted_mean_with_coverage(values, weights, None)
        self.assertAlmostEqual(mean, 25.0)
        self.assertAlmostEqual(coverage, 1.0)
        self.assertEqual(valid_cells, 4)

    def test_explicit_chirps_missing_sentinel_is_excluded_without_gdal_nodata(self) -> None:
        weights = build_area_weights(
            box(0.0, 0.0, 2.0, 2.0),
            Affine(1.0, 0.0, 0.0, 0.0, -1.0, 2.0),
            height=2,
            width=2,
        )
        values = np.array([[20.0, CHIRPS_MISSING_SENTINEL], [20.0, CHIRPS_MISSING_SENTINEL]])
        mean, coverage, valid_cells = weighted_mean_with_coverage(values, weights, None)
        self.assertAlmostEqual(mean, 20.0, places=6)
        self.assertAlmostEqual(coverage, 0.5, places=4)
        self.assertEqual(valid_cells, 2)

    def test_other_negative_values_fail_closed(self) -> None:
        with self.assertRaises(RuntimeError):
            weighted_mean_with_coverage(np.array([[-0.5]]), [(0, 0, 1.0)], None)

    def test_annualization_supports_multiple_sample_years(self) -> None:
        rows = []
        for year in SAMPLE_YEARS:
            for month in range(1, 13):
                rows.append({
                    "geography_id": "idn.13.1371",
                    "geography_name": "Padang",
                    "year": year,
                    "month": month,
                    "monthly_rainfall_mm": 100.0,
                    "valid_area_fraction": 0.99,
                })
        annual = annualize_monthly(rows)
        self.assertEqual(len(annual), len(SAMPLE_YEARS))
        self.assertEqual({row["year"] for row in annual}, set(SAMPLE_YEARS))
        self.assertTrue(all(row["annual_rainfall_mm"] == 1200.0 for row in annual))
        self.assertTrue(all(row["claim_type"] == "model_estimate" for row in annual))

    def test_annualization_rejects_incomplete_year(self) -> None:
        rows = [
            {
                "geography_id": "idn.13.1371",
                "geography_name": "Padang",
                "year": 2000,
                "month": month,
                "monthly_rainfall_mm": 100.0,
                "valid_area_fraction": 1.0,
            }
            for month in range(1, 12)
        ]
        with self.assertRaises(RuntimeError):
            annualize_monthly(rows)

    def test_diagnostics_report_iqr_flags_without_rejecting_them(self) -> None:
        monthly = []
        annual = []
        for year in SAMPLE_YEARS:
            for index in range(19):
                gid = f"g{index:02d}"
                annual_value = 2500.0 + index * 10.0
                if index == 18:
                    annual_value = 6000.0
                annual.append({
                    "geography_id": gid,
                    "geography_name": gid,
                    "year": year,
                    "annual_rainfall_mm": annual_value,
                })
                for month in range(1, 13):
                    monthly.append({
                        "geography_id": gid,
                        "geography_name": gid,
                        "year": year,
                        "month": month,
                        "valid_area_fraction": 0.95,
                    })
        diagnostics = build_diagnostics(monthly, annual)
        self.assertTrue(diagnostics["annual_rainfall"]["iqr_flags_are_diagnostic_not_rejections"])
        self.assertGreaterEqual(len(diagnostics["annual_rainfall"]["by_year"]["1981"]["iqr_flags"]), 1)


if __name__ == "__main__":
    unittest.main()
