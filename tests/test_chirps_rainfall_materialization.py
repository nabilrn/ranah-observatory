from __future__ import annotations

import unittest

from scripts.materialize_chirps_rainfall import (
    EXPECTED_OBSERVATIONS,
    EXPECTED_PROVENANCE,
    EXPECTED_SOURCE_ITEMS,
    INDICATOR_ID,
    METHODOLOGY_VERSION,
    SPATIAL_FRAME,
    build_canonical,
)


def synthetic_manifest() -> dict:
    source_files = []
    for year in range(1981, 2026):
        for month in range(1, 13):
            source_files.append({
                "url": f"https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/chirps-v3.0.{year:04d}.{month:02d}.cog",
                "http_status": 206,
                "is_tiff": True,
                "bytes_read": 16384,
                "content_range": f"bytes 0-16383/{30_000_000 + year * 100 + month}",
                "etag": f'"etag-{year}-{month:02d}"',
                "last_modified": f"Mon, {month:02d} Jan 2026 00:00:00 GMT",
                "prefix_sha256": (f"{year:04d}{month:02d}" * 11)[:64].ljust(64, "0"),
            })
    return {
        "generated_at": "2026-08-16T05:48:50+00:00",
        "scope": {
            "first_year": 1981,
            "last_year": 2025,
            "geography_count": 19,
            "annual_row_count": 855,
        },
        "gates": {"a": True, "b": True},
        "chirps_source_files": source_files,
        "big_geometry": {
            "url": "https://example.invalid/big.geojson",
            "sha256": "a" * 64,
            "bytes": 12345,
            "etag": '"big-etag"',
            "source_edition": "Juni 2026",
        },
    }


def synthetic_annual_rows() -> list[dict[str, str]]:
    rows = []
    for geography_index in range(19):
        gid = f"idn.13.synthetic{geography_index:02d}"
        for year in range(1981, 2026):
            rows.append({
                "geography_id": gid,
                "geography_name": f"Synthetic {geography_index:02d}",
                "year": str(year),
                "annual_rainfall_mm": f"{2000 + geography_index * 10 + (year - 1981):.6f}",
                "months_complete": "12",
                "min_valid_area_fraction": "0.99877921",
                "mean_valid_area_fraction": "0.99950000",
                "claim_type": "model_estimate",
                "spatial_frame": SPATIAL_FRAME,
            })
    return rows


class ChirpsRainfallMaterializationTests(unittest.TestCase):
    def test_materialization_emits_exact_canonical_footprint(self) -> None:
        observations, provenance, source_contract, manifest = build_canonical(
            synthetic_annual_rows(), synthetic_manifest()
        )
        self.assertEqual(len(observations), EXPECTED_OBSERVATIONS)
        self.assertEqual(len(provenance), EXPECTED_PROVENANCE)
        self.assertEqual(len(source_contract), EXPECTED_SOURCE_ITEMS)
        self.assertEqual(manifest["observation_count"], EXPECTED_OBSERVATIONS)
        self.assertEqual(manifest["provenance_count"], EXPECTED_PROVENANCE)
        self.assertEqual(manifest["source_contract_item_count"], EXPECTED_SOURCE_ITEMS)

    def test_observations_preserve_model_estimate_and_fixed_boundary_semantics(self) -> None:
        observations, _, _, _ = build_canonical(synthetic_annual_rows(), synthetic_manifest())
        row = observations[0]
        self.assertEqual(row["indicator_id"], INDICATOR_ID)
        self.assertEqual(row["claim_type"], "model_estimate")
        self.assertEqual(row["unit"], "millimetres")
        self.assertEqual(row["frequency"], "annual")
        self.assertEqual(row["methodology_version"], METHODOLOGY_VERSION)
        self.assertIn(f"spatial_frame={SPATIAL_FRAME}", row["notes"])
        self.assertIn("historical_boundary_continuity=false", row["notes"])
        self.assertIn("observed_station_equivalence=false", row["notes"])
        self.assertIn("independent_station_validation=pending", row["notes"])

    def test_source_contract_does_not_call_prefix_hash_full_file_checksum(self) -> None:
        _, provenance, source_contract, _ = build_canonical(synthetic_annual_rows(), synthetic_manifest())
        chirps_rows = [row for row in source_contract if row["source_id"] == "chirps_v3"]
        self.assertEqual(len(chirps_rows), 540)
        self.assertTrue(all(row["identity_scope"] == "sha256_first_16384_bytes_not_full_file_checksum" for row in chirps_rows))
        self.assertTrue(all("not_full_upstream_raster_bytes" in row["notes"] for row in provenance))

    def test_big_geometry_uses_full_response_sha256(self) -> None:
        _, _, source_contract, manifest = build_canonical(synthetic_annual_rows(), synthetic_manifest())
        big = [row for row in source_contract if row["source_id"] == "big_admin_boundaries_june_2026"]
        self.assertEqual(len(big), 1)
        self.assertEqual(big[0]["identity_scope"], "sha256_full_geojson_query_response")
        self.assertEqual(big[0]["identity_sha256"], "a" * 64)
        self.assertEqual(manifest["big_geometry_response_sha256"], "a" * 64)

    def test_rejects_candidate_below_coverage_gate(self) -> None:
        annual = synthetic_annual_rows()
        annual[0]["min_valid_area_fraction"] = "0.90"
        with self.assertRaises(ValueError):
            build_canonical(annual, synthetic_manifest())

    def test_rejects_observed_claim_masquerading_as_chirps(self) -> None:
        annual = synthetic_annual_rows()
        annual[0]["claim_type"] = "observed"
        with self.assertRaises(ValueError):
            build_canonical(annual, synthetic_manifest())


if __name__ == "__main__":
    unittest.main()
