from __future__ import annotations

import unittest

from scripts import probe_milestone26_population_stats_shape as diag


class M26PopulationStatsShapeTests(unittest.TestCase):
    def test_contract_is_transport_only_and_fail_closed(self):
        contract = diag.load_contract()
        self.assertIs(contract["locked_before_live_shape_diagnostic"], True)
        self.assertEqual(contract["partition_count_maximum"], 420)
        self.assertEqual(contract["stop_rule"], "stop_immediately_after_first_nonstandard_statistics_shape")
        self.assertIs(contract["numeric_aggregates_computed"], False)
        self.assertIs(contract["cross_geography_component_values_materialized"], False)
        self.assertIs(contract["substantive_values_promoted"], False)
        self.assertIs(contract["stage1_population_production_extraction_authorized_by_this_diagnostic"], False)
        self.assertIs(contract["aggregation_semantics_changed"], False)
        self.assertIs(contract["source_family_changed"], False)
        self.assertIs(contract["risk_synthesis_authorized"], False)

    def test_standard_shape_requires_single_object_and_all_fields(self):
        required = {"count", "sum", "mean", "min", "max", "skipX", "skipY"}
        payload = {"statistics": [{
            "count": 1,
            "sum": 2.0,
            "mean": 2.0,
            "min": 2.0,
            "max": 2.0,
            "skipX": 1,
            "skipY": 1,
        }]}
        result = diag.classify_payload(payload, required)
        self.assertEqual(result["classification"], "standard")
        self.assertEqual(result["statistics_length"], 1)
        self.assertEqual(result["missing_required_fields"], [])

    def test_empty_statistics_is_explicit_nonstandard_class(self):
        result = diag.classify_payload({"statistics": []}, {"count"})
        self.assertEqual(result["classification"], "empty_statistics")
        self.assertEqual(result["statistics_length"], 0)

    def test_missing_statistics_and_nonlist_are_distinct(self):
        missing = diag.classify_payload({}, {"count"})
        nonlist = diag.classify_payload({"statistics": {}}, {"count"})
        self.assertEqual(missing["classification"], "missing_statistics")
        self.assertEqual(nonlist["classification"], "statistics_not_list")

    def test_multiple_or_nonobject_statistics_are_distinct(self):
        multiple = diag.classify_payload({"statistics": [{}, {}]}, set())
        nonobject = diag.classify_payload({"statistics": [1]}, set())
        self.assertEqual(multiple["classification"], "multiple_statistics")
        self.assertEqual(nonobject["classification"], "statistics_item_not_object")

    def test_missing_required_fields_are_named_without_recording_values(self):
        result = diag.classify_payload({"statistics": [{"count": 1}]}, {"count", "sum", "mean"})
        self.assertEqual(result["classification"], "missing_required_fields")
        self.assertEqual(result["missing_required_fields"], ["mean", "sum"])
        self.assertNotIn("count_value", result)

    def test_arcgis_error_is_transport_class(self):
        result = diag.classify_payload({"error": {"code": 500, "message": "x"}}, {"count"})
        self.assertEqual(result["classification"], "transport_or_arcgis_error")

    def test_partition_iteration_is_deterministic(self):
        partitions = {
            "geographies": [
                {"geography_id": "b", "partitions": [{"partition_index": 2}, {"partition_index": 1}]},
                {"geography_id": "a", "partitions": [{"partition_index": 3}, {"partition_index": 1}]},
            ]
        }
        order = [(g["geography_id"], p["partition_index"]) for g, p in diag.iter_frozen_partitions(partitions)]
        self.assertEqual(order, [("a", 1), ("a", 3), ("b", 1), ("b", 2)])


if __name__ == "__main__":
    unittest.main()
