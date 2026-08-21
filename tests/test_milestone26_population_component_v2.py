from __future__ import annotations

import unittest

from scripts import materialize_milestone26_population_component_v2 as v2


class M26PopulationComponentV2Tests(unittest.TestCase):
    def test_amendment_is_locked_and_preserves_scientific_boundaries(self):
        amendment = v2.load_amendment()
        self.assertTrue(amendment["production_restart_authorized_under_this_amendment"])
        self.assertTrue(amendment["empty_partition_reference_confirmation"]["required_for_every_empty_partition"])
        self.assertEqual(amendment["empty_partition_reference_confirmation"]["maximum_batch_size"], 64)
        self.assertEqual(amendment["quality_gates_unchanged"]["minimum_valid_fraction_inside_geography"], 0.99)
        self.assertFalse(amendment["qualified_empty_partition_contribution"]["imputation"])
        self.assertTrue(amendment["qualified_empty_partition_contribution"]["must_not_be_labeled_population_zero"])
        self.assertFalse(amendment["empty_statistics_global_semantics_authorized_without_partition_reference"])
        self.assertFalse(amendment["risk_synthesis_authorized"])

    def test_exact_cell_semantics_evidence_is_required_before_restart(self):
        amendment = v2.load_amendment()
        v2.verify_amendment_evidence(amendment)

    def test_only_exact_empty_statistics_shape_activates_fallback(self):
        self.assertTrue(v2.is_exact_empty_statistics({"statistics": []}))
        self.assertFalse(v2.is_exact_empty_statistics({"statistics": [], "extra": 1}))
        self.assertFalse(v2.is_exact_empty_statistics({"statistics": [{}]}))
        self.assertFalse(v2.is_exact_empty_statistics({}))

    def test_nodata_batch_requires_one_raw_result_per_center_and_no_finite_value(self):
        requested = [[1000.0, 2000.0], [1100.0, 2000.0]]
        payload = {
            "results": [
                {
                    "layerId": 0,
                    "attributes": {"Stretch.Pixel Value": "NoData"},
                    "geometry": {"x": 1000.0, "y": 2000.0},
                },
                {
                    "layerId": 0,
                    "attributes": {"Stretch.Pixel Value": "NoData"},
                    "geometry": {"x": 1100.0, "y": 2000.0},
                },
            ]
        }
        result = v2.validate_nodata_batch(
            requested,
            payload,
            field_name="Stretch.Pixel Value",
            tolerance=0.001,
        )
        self.assertEqual(result["raw_result_count"], 2)
        self.assertEqual(result["finite_accepted_pixel_value_count"], 0)
        self.assertTrue(result["all_result_geometries_one_to_one"])
        self.assertTrue(result["all_requested_centers_explicit_nonfinite"])
        self.assertEqual(result["nonfinite_value_labels"], ["NoData"])

    def test_nodata_batch_fails_closed_if_mapserver_exposes_any_finite_value(self):
        requested = [[1000.0, 2000.0]]
        payload = {
            "results": [
                {
                    "layerId": 0,
                    "attributes": {"Stretch.Pixel Value": "12.5"},
                    "geometry": {"x": 1000.0, "y": 2000.0},
                }
            ]
        }
        with self.assertRaises(v2.M26PopulationProductionV2Error):
            v2.validate_nodata_batch(
                requested,
                payload,
                field_name="Stretch.Pixel Value",
                tolerance=0.001,
            )

    def test_nodata_batch_fails_closed_on_missing_or_misaligned_raw_result(self):
        requested = [[1000.0, 2000.0]]
        missing = {"results": []}
        with self.assertRaises(v2.M26PopulationProductionV2Error):
            v2.validate_nodata_batch(
                requested,
                missing,
                field_name="Stretch.Pixel Value",
                tolerance=0.001,
            )

        misaligned = {
            "results": [
                {
                    "layerId": 0,
                    "attributes": {"Stretch.Pixel Value": "NoData"},
                    "geometry": {"x": 1001.0, "y": 2000.0},
                }
            ]
        }
        with self.assertRaises(v2.M26PopulationProductionV2Error):
            v2.validate_nodata_batch(
                requested,
                misaligned,
                field_name="Stretch.Pixel Value",
                tolerance=0.001,
            )


if __name__ == "__main__":
    unittest.main()
