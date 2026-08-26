import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


MANIFEST_PATH = Path(
    "data/manifests/milestone43_bnpb_historical_semantics_geography_gate.json"
)

EXPECTED_METRICS = {
    "jumlah_kejadian",
    "meninggal",
    "hilang",
    "terluka",
    "menderita",
    "mengungsi",
    "rumah_rusak_berat",
    "rumah_rusak_sedang",
    "rumah_rusak_ringan",
    "rumah_terendam",
    "fasilitas_pendidikan",
    "fasilitas_kesehatan",
    "fasilitas_peribadatan",
    "fasilitas_umum",
}


class Milestone43HistoricalSemanticsGeographyGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.metrics = {
            item["metric"]: item for item in cls.manifest["metric_qualification"]
        }

    def test_gate_is_frozen_without_overclaiming_promotion(self):
        q = self.manifest["qualification"]
        self.assertTrue(q["metric_semantics_gate_frozen"])
        self.assertTrue(q["temporal_geography_gate_frozen"])
        self.assertTrue(q["structural_schema_continuity_proven"])
        self.assertFalse(q["semantic_identity_all_metrics_all_years_proven"])
        self.assertFalse(q["current_boundary_equivalence_all_rows_proven"])
        self.assertFalse(q["canonical_historical_panel_promotion_authorized"])
        self.assertFalse(q["direct_current_era_comparison_authorized"])
        self.assertFalse(q["unique_person_aggregation_authorized"])
        self.assertFalse(q["parent_successor_allocation_authorized"])
        self.assertFalse(q["absent_row_zero_inference_authorized"])
        self.assertFalse(q["facility_category_arithmetic_authorized"])

    def test_all_fourteen_source_metrics_have_explicit_semantic_qualification(self):
        self.assertEqual(14, len(self.manifest["metric_qualification"]))
        self.assertEqual(EXPECTED_METRICS, set(self.metrics))

        for metric, item in self.metrics.items():
            with self.subTest(metric=metric):
                self.assertTrue(item["source_label"])
                self.assertTrue(item["unit"])
                self.assertTrue(item["semantic_state"])
                self.assertTrue(item["safe_use"])
                self.assertGreater(len(item["blocked_use"]), 0)

    def test_menderita_is_not_silently_relabelled_to_terdampak(self):
        item = self.metrics["menderita"]
        self.assertEqual("Terdampak", item["current_concept_successor"])
        self.assertEqual("candidate_successor_mapping_not_proven", item["semantic_state"])
        blocked = " ".join(item["blocked_use"]).lower()
        self.assertIn("rename", blocked)
        self.assertIn("unique people", blocked)

    def test_victim_categories_are_not_authorized_as_unique_people(self):
        for metric in ("meninggal", "hilang", "terluka", "menderita", "mengungsi"):
            blocked = " ".join(self.metrics[metric]["blocked_use"]).lower()
            if metric in {"meninggal", "hilang", "menderita", "mengungsi"}:
                self.assertIn("unique", blocked)

    def test_historical_facility_umum_remains_arithmetically_ambiguous(self):
        item = self.metrics["fasilitas_umum"]
        self.assertEqual("aggregation_role_ambiguous", item["semantic_state"])
        self.assertIsNone(item["current_concept_successor"])
        blocked = " ".join(item["blocked_use"]).lower()
        self.assertIn("fourth category", blocked)
        self.assertIn("sum", blocked)

    def test_transition_years_preserve_partial_year_boundary_ambiguity(self):
        transitions = {
            item["year"]: item for item in self.manifest["geography_qualification"]["transition_years"]
        }
        self.assertEqual({2002, 2003, 2008}, set(transitions))
        self.assertEqual("2002-04-10", transitions[2002]["effective_date"])
        self.assertEqual("partial_year_boundary_transition", transitions[2002]["state"])
        self.assertEqual("blocked", transitions[2002]["current_boundary_comparison"])
        self.assertEqual("2003-12-18", transitions[2003]["effective_date"])
        self.assertEqual("partial_year_boundary_transition", transitions[2003]["state"])
        self.assertEqual("blocked", transitions[2003]["current_boundary_comparison"])
        self.assertEqual("rename_same_entity", transitions[2008]["state"])

    def test_evidence_register_uses_https_and_expected_authorities(self):
        evidence = {item["id"]: item for item in self.manifest["evidence_register"]}
        required = {
            "bnpb_perka8_2011",
            "bnpb_perka7_2012",
            "bnpb_perban1_2023",
            "bps_sirusa_disaster_victim_metadata",
            "bnpb_satu_data_historical_2010_2024",
            "bnpb_historical_terdampak_resource",
            "bnpb_historical_mengungsi_resource",
            "bnpb_2025_combined_dictionary",
            "bnpb_data_bencana_2017",
            "uu12_2002_kota_pariaman",
            "uu38_2003_three_districts",
        }
        self.assertTrue(required.issubset(evidence))
        for item in evidence.values():
            parsed = urlparse(item["url"])
            self.assertEqual("https", parsed.scheme)
            self.assertTrue(parsed.hostname)

    def test_next_gate_requires_value_level_overlap_reconciliation(self):
        next_gate = self.manifest["next_gate"]
        self.assertEqual(44, next_gate["milestone"])
        tasks = " ".join(next_gate["tasks"]).lower()
        self.assertIn("2010-2017", tasks)
        self.assertIn("menderita", tasks)
        self.assertIn("terdampak", tasks)
        self.assertIn("umum", tasks)
        self.assertIn("revisions", tasks)


if __name__ == "__main__":
    unittest.main()
