from __future__ import annotations

import copy

import pytest

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


def test_contract_keeps_pilot_only_and_forbidden_promotions_closed():
    contract = locked_contract()
    assert contract["pilot"]["geography_id"] == "idn.13.1374"
    assert contract["pilot"]["inside_native_cell_count_expected"] == 2354
    assert contract["pilot"]["mapserver_reference_batch_size"] == 64
    assert contract["pilot"]["mapserver_reference_request_count_expected"] == 37
    assert contract["pilot"]["image_server_partition_count_expected"] == 2
    assert contract["pilot"]["all_inside_cells_required"] is True
    assert contract["pilot"]["sampling_prohibited"] is True
    assert contract["stage1_population_production_extraction_authorized"] is False
    assert contract["substantive_value_promotion_authorized"] is False
    assert contract["cross_geography_numeric_source_extraction_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False
    assert contract["statistical_model_fit_authorized"] is False
    assert contract["causal_claim_authorized"] is False
    assert contract["monetary_wasted_potential_estimate_authorized"] is False


def test_coordinate_association_is_one_to_one_and_tolerance_bounded():
    requested = [[1000.0, 2000.0], [1100.0, 2000.0]]
    parsed = [
        {"geometry": [1000.0005, 1999.9995], "value": 1.5},
        {"geometry": [1099.9995, 2000.0005], "value": 2.5},
    ]
    mapping = equiv.associate_partial_results(requested, parsed, 0.001)
    assert mapping[equiv.coordinate_key(requested[0])] == 1.5
    assert mapping[equiv.coordinate_key(requested[1])] == 2.5

    with pytest.raises(equiv.M26PopulationStatsEquivalenceError):
        equiv.associate_partial_results(
            requested,
            [{"geometry": [1000.002, 2000.0], "value": 1.5}],
            0.001,
        )


def test_coordinate_association_rejects_duplicate_return_geometry():
    requested = [[1000.0, 2000.0], [1100.0, 2000.0]]
    parsed = [
        {"geometry": [1000.0, 2000.0], "value": 1.0},
        {"geometry": [1000.0, 2000.0], "value": 2.0},
    ]
    with pytest.raises(equiv.M26PopulationStatsEquivalenceError):
        equiv.associate_partial_results(requested, parsed, 0.001)


def test_statistics_parser_requires_locked_fields_and_finite_values():
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
    assert parsed == payload["statistics"][0]

    broken = copy.deepcopy(payload)
    del broken["statistics"][0]["sum"]
    with pytest.raises(equiv.M26PopulationStatsEquivalenceError):
        equiv.parse_statistics(broken, required)

    nonfinite = copy.deepcopy(payload)
    nonfinite["statistics"][0]["mean"] = float("nan")
    with pytest.raises(equiv.M26PopulationStatsEquivalenceError):
        equiv.parse_statistics(nonfinite, required)


def test_compare_accepts_only_locked_six_decimal_quantization_bound():
    contract = locked_contract()
    reference = reference_template()
    candidate = candidate_template(reference)
    result = equiv.compare(contract, reference, candidate)
    assert result["all_equivalence_gates_passed"] is True
    assert result["combined_count_match"] is True
    assert result["sum_absolute_difference"] <= result["sum_absolute_tolerance"]


def test_compare_fails_closed_on_count_or_quantization_excess():
    contract = locked_contract()
    reference = reference_template()

    wrong_count = candidate_template(reference)
    wrong_count["count"] -= 1
    assert equiv.compare(contract, reference, wrong_count)["all_equivalence_gates_passed"] is False

    excess = candidate_template(reference)
    excess["sum"] = reference["sum"] + reference["valid_count"] * 0.0000006 + 0.01
    excess["mean"] = excess["sum"] / reference["valid_count"]
    result = equiv.compare(contract, reference, excess)
    assert result["combined_sum_match"] is False
    assert result["all_equivalence_gates_passed"] is False
