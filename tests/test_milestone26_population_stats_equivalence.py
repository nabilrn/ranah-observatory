from __future__ import annotations

import copy
import unittest

from scripts import probe_milestone26_population_stats_equivalence as equiv


def locked_contract():
    return equiv.load_contract()


def reference_template():
    return {
        "input_cell_count": 2354,
        "batch_size": 64,
        "batch_count": 37,
        "valid_count": 2354,
        "missing_count": 0,
        "valid_fraction": 1.0,
        "sum": 100000.0004,
        "mean": 100000.0004 / 2354,
        "min": 0.123456,
        "max": 1976.123456,
        "all_returned_points_mapped_one_to_one": True,
    }


def candidate_template(reference):
    return {
        "partition_count": 2,
        "count": reference["valid_count"],
        "sum": reference["sum"] + reference["valid_count"] * 0.00000049,
        "mean": reference["mean"] + 0.00000049,
        "min": reference["min"] + 0.00000049,
        "max": reference["max"] - 0.00000049,
        "all_partition_skip_gates_passed": True,
        "all_partition_range_gates_passed": True,
    }


class M26PopulationStatsEquivalenceTests(unittest.TestCase):
    def test_contract_keeps_pilot_only_and_forbidden_promotions_closed(self):
        contract = locked_contract()
        self.assertEqual(contract["pilot"]["geography_id"], "idn.13.1374")
        self.assertEqual(contract["pilot"]["inside_native_cell_count_expected"], 2354)
        self.assertEqual(contract["pilot"]["mapserver_reference_batch_size"], 64)
        self.assertEqual(contract["pilot"]["mapserver_reference_request_count_expected"], 37)
        self.assertEqual(contract["pilot"]["image_server_partition_count_expected"], 2)
        self.assertIs(contract["pilot"]["all_inside_cells_required"], True)
        self.assertIs(contract["pilot"]["sampling_prohibited"], True)
        self.assertIs(contract["stage1_population_production_extraction_authorized"], False)
        self.assertIs(contract["substantive_value_promotion_authorized"], False)
        self.assertIs(contract["cross_geography_numeric_source_extraction_authorized"], False)
        self.assertIs(contract["risk_synthesis_authorized"], False)
        self.assertIs(contract["statistical_model_fit_authorized"], False)
        self.assertIs(contract["causal_claim_authorized"], False)
        self.assertIs(contract["monetary_wasted_potential_estimate_authorized"], False)

    def test_coordinate_association_is_one_to_one_and_tolerance_bounded(self):
        requested = [[1000.0, 2000.0], [1100.0, 2000.0]]
        parsed = [
            {"geometry": [1000.0005, 1999.9995], "value": 1.5},
            {"geometry": [1099.9995, 2000.0005], "value": 2.5},
        ]
        mapping = equiv.associate_partial_results(requested, parsed, 0.001)
        self.assertEqual(mapping[equiv.coordinate_key(requested[0])], 1.5)
        self.assertEqual(mapping[equiv.coordinate_key(requested[1])], 2.5)

        with self.assertRaises(equiv.M26PopulationStatsEquivalenceError):
            equiv.associate_partial_results(
                requested,
                [{"geometry": [1000.002, 2000.0], "value": 1.5}],
                0.001,
            )

    def test_coordinate_association_rejects_duplicate_return_geometry(self):
        requested = [[1000.0, 2000.0], [1100.0, 2000.0]]
        parsed = [
            {"geometry": [1000.0, 2000.0], "value": 1.0},
            {"geometry": [1000.0, 2000.0], "value": 2.0},
        ]
        with self.assertRaises(equiv.M26PopulationStatsEquivalenceError):
            equiv.associate_partial_results(requested, parsed, 0.001)

    def test_statistics_parser_requires_locked_fields_and_finite_values(self):
        required = {"count", "sum", "mean", "min", "max", "skipX", "skipY"}
        payload = {
            "statistics": [{
                "count": 10,
                "sum": 25.0,
                "mean": 2.5,
                "min": 0.0,
                "max": 5.0,
                "skipX": 1,
                "skipY": 1,
            }]
        }
        parsed = equiv.parse_statistics(payload, required)
        self.assertEqual(parsed, payload["statistics"][0])

        broken = copy.deepcopy(payload)
        del broken["statistics"][0]["sum"]
        with self.assertRaises(equiv.M26PopulationStatsEquivalenceError):
            equiv.parse_statistics(broken, required)

        nonfinite = copy.deepcopy(payload)
        nonfinite["statistics"][0]["mean"] = float("nan")
        with self.assertRaises(equiv.M26PopulationStatsEquivalenceError):
            equiv.parse_statistics(nonfinite, required)

    def test_compare_accepts_only_locked_six_decimal_quantization_bound(self):
        contract = locked_contract()
        reference = reference_template()
        candidate = candidate_template(reference)
        result = equiv.compare(contract, reference, candidate)
        self.assertIs(result["all_equivalence_gates_passed"], True)
        self.assertIs(result["combined_count_match"], True)
        self.assertLessEqual(result["sum_absolute_difference"], result["sum_absolute_tolerance"])

    def test_compare_fails_closed_on_count_or_quantization_excess(self):
        contract = locked_contract()
        reference = reference_template()

        wrong_count = candidate_template(reference)
        wrong_count["count"] -= 1
        self.assertIs(equiv.compare(contract, reference, wrong_count)["all_equivalence_gates_passed"], False)

        excess = candidate_template(reference)
        excess["sum"] = reference["sum"] + reference["valid_count"] * 0.0000006 + 0.01
        excess["mean"] = excess["sum"] / reference["valid_count"]
        result = equiv.compare(contract, reference, excess)
        self.assertIs(result["combined_sum_match"], False)
        self.assertIs(result["all_equivalence_gates_passed"], False)


if __name__ == "__main__":
    unittest.main()
