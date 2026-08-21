from __future__ import annotations

from scripts import materialize_milestone26_population_component as pop


def test_production_contract_authorizes_only_population_component_materialization():
    contract = pop.load_contract()
    assert contract["source_id"] == "inarisk_population_2020"
    assert contract["component_class"] == "exposure"
    assert contract["claim_type"] == "modeled_population_exposure_proxy"
    assert contract["reference_year"] == 2020
    assert contract["geography_count_expected"] == 19
    assert contract["stage1_population_production_extraction_authorized"] is True
    assert contract["component_value_materialization_authorized"] is True
    assert contract["cross_geography_numeric_source_extraction_authorized"] is True
    assert contract["substantive_interpretation_authorized"] is False
    assert contract["cross_component_temporal_aggregation_authorized"] is False
    assert contract["risk_synthesis_authorized"] is False
    assert contract["statistical_model_fit_authorized"] is False
    assert contract["causal_claim_authorized"] is False
    assert contract["monetary_wasted_potential_estimate_authorized"] is False


def test_frozen_transport_inputs_are_qualified_before_production():
    contract = pop.load_contract()
    partitions, equivalence, source_meta = pop.load_frozen_inputs(contract)
    assert partitions["geography_count"] == 19
    assert partitions["total_partition_count"] == 420
    assert partitions["total_inside_boundary_native_cell_count"] == 4212327
    assert partitions["all_partition_cell_counts_exact"] is True
    assert partitions["all_partition_urls_within_gate"] is True
    assert equivalence["statistics_transport_equivalent_on_complete_pilot"] is True
    assert equivalence["population_stats_production_transport_candidate_qualified"] is True
    assert equivalence["reference_mapserver"]["input_cell_count"] == 2354
    assert equivalence["candidate_image_server_statistics"]["count"] == 2354
    primary = source_meta["primary"]
    assert primary["spatialReference"]["wkid"] == 3395
    assert primary["pixelSizeX"] == 100
    assert primary["pixelSizeY"] == 100


def test_locked_aggregation_preserves_native_grid_estimand():
    contract = pop.load_contract()
    agg = contract["aggregation"]
    assert agg["estimand"] == "sum_of_nonnegative_native_grid_cell_person_values_with_centers_inside_fixed_boundary"
    assert agg["partition_combination"] == "sum_statistics_sum_across_nonoverlapping_exact_native_mask_partitions"
    assert agg["minimum_valid_fraction_inside_geography"] == 0.99
    assert agg["boundary_rule"] == "pixel_center_inside_polygon"
    assert agg["all_touched"] is False
    assert agg["resampling"] == "nearest_neighbor"
    assert agg["downsampling_authorized"] is False
    assert agg["upsampling_authorized"] is False
    assert agg["mean_as_population_total_authorized"] is False
    assert agg["area_weighted_density_integration_authorized"] is False
    assert agg["imputation_authorized"] is False


def test_semantic_contract_keeps_population_as_grid_person_count_proxy():
    contract = pop.load_contract()
    semantic = contract["semantic_evidence"]
    assert semantic["required_phrase"] == "Pij adalah jumlah penduduk pada grid/sel"
    assert semantic["evidence_role"] == "establish_population_grid_cell_value_as_person_count_not_density"
    assert contract["claim_type"] == "modeled_population_exposure_proxy"


def test_raw_partition_path_is_stable_and_scoped_by_geography():
    path = pop.raw_path("idn.13.1374", 2)
    assert path.name == "partition-0002.json"
    assert path.parent.name == "idn.13.1374"
    assert path.is_relative_to(pop.RAW_ROOT)


def test_stable_provenance_id_is_deterministic_and_input_bound():
    first = pop.stable_provenance_id("idn.13.1374", "a" * 64, "b" * 64)
    second = pop.stable_provenance_id("idn.13.1374", "a" * 64, "b" * 64)
    changed = pop.stable_provenance_id("idn.13.1374", "a" * 64, "c" * 64)
    assert first == second
    assert first.startswith("m26pop_")
    assert first != changed


def test_output_schema_retains_explicit_nonrisk_boundary():
    assert "population_exposure_proxy_2020_persons" in pop.FRAME_FIELDS
    assert "population_valid_fraction" in pop.FRAME_FIELDS
    assert "claim_type" in pop.FRAME_FIELDS
    assert "risk_synthesis_authorized" in pop.FRAME_FIELDS
    assert "semantic_evidence_sha256" in pop.PROVENANCE_FIELDS
    assert "equivalence_manifest_sha256" in pop.PROVENANCE_FIELDS
    assert "retrieval_index_sha256" in pop.PROVENANCE_FIELDS
