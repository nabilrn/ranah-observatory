import csv
import json
import unittest
from pathlib import Path


MANIFEST = Path("data/manifests/milestone41_bnpb_historical_normalization_contract.json")
LINEAGE = Path("data/registries/bnpb_historical_geography_lineage.csv")


class Milestone41NormalizationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        with LINEAGE.open(encoding="utf-8", newline="") as fh:
            cls.lineage = list(csv.DictReader(fh))

    def test_normalization_contract_is_bounded(self):
        q = self.manifest["qualification"]
        self.assertTrue(q["normalization_contract_frozen"])
        self.assertTrue(q["raw_source_row_identity_required"])
        self.assertTrue(q["empty_workbook_zero_inference_forbidden"])
        self.assertTrue(q["absent_row_zero_inference_forbidden"])
        self.assertFalse(q["source_total_is_geography_observation"])
        self.assertTrue(q["source_total_reconciliation_required_when_present"])
        self.assertTrue(q["raw_code_cross_era_mapping_forbidden"])
        self.assertTrue(q["source_label_contemporaneous_legal_name_assumption_forbidden"])
        self.assertTrue(q["source_native_integer_parsing_authorized_for_staging"])
        self.assertFalse(q["historical_numeric_values_promoted"])
        self.assertFalse(q["district_city_panel_authorized"])
        self.assertFalse(q["event_level_panel_authorized"])

    def test_missingness_states_do_not_collapse_to_zero(self):
        states = self.manifest["states"]
        self.assertIn("empty_body", states["workbook"])
        self.assertIn("absent_entity_active_full_year", states["derived_presence"])
        self.assertIn("absent_entity_active_partial_year", states["derived_presence"])
        self.assertIn("source_blank", states["cell"])
        self.assertIn("observed_zero", states["cell"])

        parse = self.manifest["parse_contract"]
        self.assertIn("explicit metric cell", parse["explicit_zero_rule"])
        self.assertIn("Never synthesize zero-valued rows", parse["absent_row_rule"])
        self.assertIn("2001", parse["empty_workbook_rule"])
        self.assertIn("reconciliation-only", parse["total_row_rule"])

    def test_sample_workbooks_reconcile_without_promoting_values(self):
        audits = self.manifest["audited_workbooks"]
        self.assertEqual([a["year"] for a in audits], [2002, 2003, 2004, 2005, 2006, 2012, 2017])
        for audit in audits:
            self.assertRegex(audit["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(audit["used_range"].startswith("A1:P"))
            self.assertGreater(audit["body_row_count"], 0)
            self.assertTrue(audit["total_row_present"])
            self.assertTrue(audit["all_14_metrics_total_reconcile"])

    def test_absent_row_counterexample_is_frozen(self):
        c = self.manifest["semantic_counterexamples"]["absent_row_not_zero"]
        self.assertEqual(c["year"], 2004)
        self.assertEqual(c["legal_effective_date"], "2003-12-18")
        self.assertEqual(
            c["legally_active_full_year_entities"],
            ["Solok Selatan", "Dharmasraya", "Pasaman Barat"],
        )
        self.assertEqual(c["observed_source_rows"], [])
        self.assertIn("cannot encode", c["finding"])

    def test_source_label_and_code_regime_counterexamples_are_frozen(self):
        label = self.manifest["semantic_counterexamples"]["source_label_not_contemporaneous_legal_name"]
        self.assertEqual(label["source_year"], 2003)
        self.assertEqual(label["source_label"], "1304. SIJUNJUNG")
        self.assertEqual(label["legal_rename_effective_date"], "2008-03-10")

        examples = self.manifest["semantic_counterexamples"]["raw_code_regime_shift_examples"]
        self.assertGreaterEqual(len(examples), 3)
        for row in examples:
            self.assertNotEqual(row["historical_code"], row["current_2024_bnpb_code"])

    def test_geography_contract_blocks_unsafe_harmonization(self):
        geo = self.manifest["geography_contract"]
        self.assertFalse(geo["reuse_2024_raw_code_crosswalk_for_2000_2017"])
        self.assertFalse(geo["allocate_pre_split_parent_to_successors"])
        self.assertEqual([row["year"] for row in geo["transition_years"]], [2002, 2003, 2008])
        self.assertEqual(
            geo["mapping_key"],
            ["source_era", "source_year", "source_code_raw", "source_name_raw", "legal_lineage"],
        )

    def test_legal_lineage_registry_has_verified_anchors(self):
        self.assertEqual(len(self.lineage), 6)
        by_id = {row["event_id"]: row for row in self.lineage}

        self.assertEqual(by_id["mentawai_creation_1999"]["effective_date"], "1999-10-04")
        self.assertEqual(by_id["kota_pariaman_creation_2002"]["effective_date"], "2002-04-10")
        self.assertEqual(by_id["solok_selatan_creation_2003"]["effective_date"], "2003-12-18")
        self.assertEqual(by_id["pasaman_barat_creation_2003"]["effective_date"], "2003-12-18")
        self.assertEqual(by_id["dharmasraya_creation_2003"]["effective_date"], "2003-12-18")
        self.assertEqual(by_id["sijunjung_rename_2008"]["effective_date"], "2008-03-10")

        for row in self.lineage:
            self.assertEqual(row["verification_status"], "verified_official_legal_source")
            self.assertTrue(row["legal_basis_url"].startswith("https://peraturan.bpk.go.id/"))

    def test_metric_semantics_remain_conservative(self):
        semantics = self.manifest["metric_semantics"]
        self.assertTrue(semantics["structural_labels_observed_stable_in_audits"])
        self.assertFalse(semantics["semantic_definition_identity_all_years_proven"])
        self.assertFalse(semantics["victim_categories_unique_person_additivity_authorized"])
        self.assertFalse(semantics["monetary_loss_interpretation_authorized"])
        self.assertFalse(semantics["cross_source_event_identity_authorized"])


if __name__ == "__main__":
    unittest.main()
