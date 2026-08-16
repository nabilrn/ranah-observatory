from __future__ import annotations

import unittest

from scripts.materialize_bps_population_growth import (
    DEFAULT_GEOGRAPHIES,
    DEFAULT_SOURCE,
    INDICATOR_ID,
    METHODOLOGY_VERSION,
    TIME_END,
    TIME_START,
    build_canonical_candidate,
    file_sha256,
    read_csv,
)


class BpsPopulationGrowthMaterializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_rows = read_csv(DEFAULT_SOURCE)
        cls.geography_rows = read_csv(DEFAULT_GEOGRAPHIES)
        cls.source_sha = file_sha256(DEFAULT_SOURCE)
        cls.observations, cls.provenance, cls.manifest = build_canonical_candidate(
            cls.source_rows, cls.geography_rows, cls.source_sha
        )

    def test_candidate_has_exact_19_row_footprint(self) -> None:
        self.assertEqual(len(self.observations), 19)
        self.assertEqual(len({row["observation_id"] for row in self.observations}), 19)
        self.assertEqual(len({row["geography_id"] for row in self.observations}), 19)
        self.assertEqual(self.manifest["observation_count"], 19)
        self.assertEqual(self.manifest["provenance_count"], 1)

    def test_candidate_preserves_official_derived_semantics(self) -> None:
        self.assertTrue(all(row["indicator_id"] == INDICATOR_ID for row in self.observations))
        self.assertTrue(all(row["claim_type"] == "derived" for row in self.observations))
        self.assertTrue(all(row["frequency"] == "annual" for row in self.observations))
        self.assertTrue(all(row["unit"] == "percent" for row in self.observations))
        self.assertTrue(all(row["methodology_version"] == METHODOLOGY_VERSION for row in self.observations))
        self.assertTrue(all(row["time_start"] == TIME_START for row in self.observations))
        self.assertTrue(all(row["time_end"] == TIME_END for row in self.observations))
        self.assertTrue(all("official_BPS_derived_population_growth_rate" in row["notes"] for row in self.observations))
        self.assertTrue(all("not_Ranah_model_estimate=true" in row["notes"] for row in self.observations))

    def test_source_contract_checksum_is_provenance_checksum(self) -> None:
        self.assertEqual(len(self.provenance), 1)
        row = self.provenance[0]
        self.assertEqual(row["checksum_sha256"], self.source_sha)
        self.assertEqual(self.manifest["source_contract_sha256"], self.source_sha)
        self.assertEqual(row["extraction_method"], "manual_transcription")
        self.assertIn("not_official_pdf_bytes", row["notes"])
        self.assertIn("crosscheck=official_SP2010_counts+official_SP2020_counts+BPS_geometric_formula", row["notes"])

    def test_known_rates_survive_materialization_without_recalculation_replacement(self) -> None:
        by_gid = {row["geography_id"]: row for row in self.observations}
        self.assertEqual(by_gid["idn.13.1310"]["value_numeric"], "2.27")
        self.assertEqual(by_gid["idn.13.1375"]["value_numeric"], "0.81")
        self.assertEqual(by_gid["idn.13.1377"]["value_numeric"], "1.71")

    def test_manifest_keeps_freeze_separate(self) -> None:
        self.assertFalse(self.manifest["canonical_freeze_performed"])
        validation = self.manifest["source_contract_validation"]
        self.assertEqual(validation["formula_match_count"], 19)
        self.assertFalse(validation["canonical_promotion_performed"])


if __name__ == "__main__":
    unittest.main()
