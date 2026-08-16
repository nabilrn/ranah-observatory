from __future__ import annotations

import unittest

from scripts.freeze_chirps_rainfall import (
    manifests_semantically_equivalent,
    provenance_equivalent_ignoring_retrieved_at,
)


class ChirpsRainfallFreezeIdempotenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provenance_row = {
            "provenance_id": "chirpsprov_test",
            "source_id": "chirps_v3",
            "artifact_locator": "repo://data/processed/climate/rainfall/chirps-source-contract.csv#year=2000",
            "retrieved_at": "2026-08-16T06:27:40+00:00",
            "source_release": "Tue, 25 Feb 2025 18:31:00 GMT",
            "checksum_sha256": "a" * 64,
            "parser_revision": "chirps_v3_final_monthly_cog:rasterio-1.5.0",
            "transform_revision": "build_chirps_rainfall_production:v1|materialize_chirps_rainfall:v1",
            "extraction_method": "remote_cog_range_read+geodesic_area_weighted_zonal_aggregation",
            "notes": "checksum_scope=committed_source_contract_artifact_not_full_upstream_raster_bytes",
        }
        self.candidate_manifest = {
            "schema": "ranah-observatory/chirps-annual-rainfall/v1",
            "source_id": "chirps_v3",
            "indicator_id": "annual_rainfall",
            "claim_type": "model_estimate",
            "methodology_version": "chirps_v3_final_monthly_big_june_2026_fixed_boundary_v1",
            "observation_count": 855,
            "provenance_count": 45,
            "source_contract_item_count": 541,
            "observations_sha256": "b" * 64,
            "provenance_sha256": "c" * 64,
            "source_contract_sha256": "d" * 64,
            "retrieved_at": "2026-08-16T12:55:23+00:00",
            "spatial_frame": "fixed_current_boundary_june_2026",
            "independent_station_validation": "pending",
            "eligible_as_observed_station_data": False,
            "historical_boundary_continuity_claimed": False,
        }

    def test_provenance_retrieval_time_only_is_equivalent(self) -> None:
        later = dict(self.provenance_row)
        later["retrieved_at"] = "2026-08-16T12:55:23+00:00"
        self.assertTrue(
            provenance_equivalent_ignoring_retrieved_at(
                [self.provenance_row],
                [later],
            )
        )

    def test_provenance_material_change_is_not_equivalent(self) -> None:
        changed = dict(self.provenance_row)
        changed["retrieved_at"] = "2026-08-16T12:55:23+00:00"
        changed["parser_revision"] = "chirps_v3_final_monthly_cog:rasterio-9.9.9"
        self.assertFalse(
            provenance_equivalent_ignoring_retrieved_at(
                [self.provenance_row],
                [changed],
            )
        )

    def test_frozen_manifest_ignores_only_freeze_and_retrieval_fields(self) -> None:
        frozen = dict(self.candidate_manifest)
        frozen.update(
            {
                "retrieved_at": "2026-08-16T06:27:40+00:00",
                "provenance_sha256": "e" * 64,
                "freeze_status": "repository_baseline",
                "canonical_repository_path": "data/processed/climate/rainfall",
                "provenance_locator_scheme": "repo://data/processed/climate/rainfall/chirps-source-contract.csv#year=YYYY",
                "frozen_from_candidate_manifest_sha256": "f" * 64,
                "candidate_provenance_sha256": "1" * 64,
            }
        )
        self.assertTrue(manifests_semantically_equivalent(self.candidate_manifest, frozen))

        frozen["methodology_version"] = "changed-methodology"
        self.assertFalse(manifests_semantically_equivalent(self.candidate_manifest, frozen))


if __name__ == "__main__":
    unittest.main()
