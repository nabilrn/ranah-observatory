from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from affine import Affine
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_chirps_rainfall_panel import (  # noqa: E402
    CLAIM_TYPE,
    METHOD_REVISION,
    GeographyWeights,
    build_annual_observations,
    compute_fractional_area_weights,
    deterministic_id,
    weighted_month_value,
)


class CHIRPSRainfallPanelTests(unittest.TestCase):
    def test_fractional_weights_reconstruct_simple_polygon_area(self) -> None:
        profile = {
            "driver": "GTiff",
            "height": 4,
            "width": 4,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:4326",
            "transform": Affine(0.05, 0.0, 100.0, 0.0, -0.05, 0.0),
        }
        feature = {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [100.0, -0.025],
                        [100.075, -0.025],
                        [100.075, -0.075],
                        [100.0, -0.075],
                        [100.0, -0.025],
                    ]
                ],
            },
        }
        selected = [
            {
                "feature": feature,
                "source_code": "1371",
                "source_name": "Kota Padang",
                "geography_id": "idn.13.1371",
                "canonical_name": "Padang",
            }
        ]
        with MemoryFile() as memory:
            with memory.open(**profile) as dataset:
                weights, window = compute_fractional_area_weights(selected, dataset)
        self.assertEqual(len(weights), 1)
        self.assertGreaterEqual(len(weights[0].areas_m2), 2)
        self.assertGreater(weights[0].polygon_area_m2, 0)
        self.assertGreater(window.width, 0)
        self.assertGreater(window.height, 0)
        reconstructed = float(weights[0].areas_m2.sum()) / weights[0].polygon_area_m2
        self.assertAlmostEqual(reconstructed, 1.0, places=3)

    def test_weighted_month_value_renormalizes_valid_area(self) -> None:
        item = GeographyWeights(
            geography_id="idn.13.1371",
            canonical_name="Padang",
            source_permendagri_code="1371",
            source_name="Kota Padang",
            rows=np.asarray([10, 10, 11], dtype=np.int32),
            cols=np.asarray([20, 21, 20], dtype=np.int32),
            areas_m2=np.asarray([50.0, 25.0, 25.0], dtype=np.float64),
            polygon_area_m2=100.0,
        )
        array = np.asarray([[100.0, 200.0], [300.0, -9999.0]], dtype=np.float32)
        # The nodata cell carries only 25% of polygon area, so lower the threshold for this unit test
        import build_chirps_rainfall_panel as module

        previous = module.MIN_VALID_AREA_FRACTION
        module.MIN_VALID_AREA_FRACTION = 0.70
        try:
            value, coverage, valid_area, valid_count, total_count = weighted_month_value(
                array,
                window=module.Window(col_off=20, row_off=10, width=2, height=2),
                item=item,
            )
        finally:
            module.MIN_VALID_AREA_FRACTION = previous
        expected = (100.0 * 50.0 + 200.0 * 25.0) / 75.0
        self.assertAlmostEqual(value, expected)
        self.assertAlmostEqual(coverage, 0.75)
        self.assertEqual(valid_area, 75.0)
        self.assertEqual(valid_count, 2)
        self.assertEqual(total_count, 3)

    def test_annual_observation_requires_twelve_months_and_keeps_model_estimate(self) -> None:
        rows = [
            {
                "geography_id": "idn.13.1371",
                "year": 2025,
                "month": month,
                "spatial_mean_precipitation_mm": 100.0 + month,
                "valid_area_fraction": 0.999,
            }
            for month in range(1, 13)
        ]
        observations = build_annual_observations(
            rows,
            start_year=2025,
            end_year=2025,
            provenance_id="prov-test",
        )
        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertEqual(observation["claim_type"], CLAIM_TYPE)
        self.assertEqual(observation["methodology_version"], METHOD_REVISION)
        self.assertEqual(observation["value_numeric"], sum(100.0 + month for month in range(1, 13)))
        self.assertIn("current-boundary reconstruction", observation["notes"])

        with self.assertRaises(ValueError):
            build_annual_observations(rows[:-1], 2025, 2025, "prov-test")

    def test_deterministic_id_is_stable_and_namespaced(self) -> None:
        first = deterministic_id("chirpsobs", "annual_rainfall", "idn.13.1371", "2025")
        second = deterministic_id("chirpsobs", "annual_rainfall", "idn.13.1371", "2025")
        other = deterministic_id("chirpsobs", "annual_rainfall", "idn.13.1371", "2024")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("chirpsobs_"))


if __name__ == "__main__":
    unittest.main()
