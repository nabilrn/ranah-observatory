import json
import re
import unittest
from pathlib import Path


MANIFEST = Path("data/manifests/milestone40_bnpb_drive_archive_complete.json")


class Milestone40ArchiveCompleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_full_drive_year_identity_is_frozen(self):
        years = self.manifest["years"]
        self.assertEqual([row["year"] for row in years], list(range(2002, 2018)))
        self.assertEqual(len(years), 16)
        self.assertEqual(len({row["sumbar_file_id"] for row in years}), 16)
        self.assertEqual(len({row["folder_id"] for row in years}), 16)

        for row in years:
            year = row["year"]
            self.assertEqual(row["sumbar_file_name"], f"stat_by_wil_13_{year}.xlsx")
            self.assertEqual(row["folder_listing_file_count"], 38)
            self.assertTrue(row["downloadable"])
            self.assertGreater(row["size_bytes"], 0)

    def test_transport_gate_closed_but_numeric_gates_remain_closed(self):
        q = self.manifest["qualification"]
        self.assertTrue(q["transport_file_identity_gate_closed"])
        self.assertTrue(q["all_year_folders_listable"])
        self.assertTrue(q["all_years_have_one_sumbar_candidate"])
        self.assertTrue(q["all_sumbar_candidates_downloadable"])
        self.assertFalse(q["full_per_year_schema_identity_proven"])
        self.assertFalse(q["numeric_values_promoted"])
        self.assertFalse(q["district_city_panel_authorized"])
        self.assertFalse(q["event_level_panel_authorized"])

    def test_start_mid_end_schema_samples_are_source_native(self):
        samples = self.manifest["schema_samples"]
        self.assertEqual([row["year"] for row in samples], [2002, 2003, 2012, 2017])
        for row in samples:
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(row["sheet"], "statistik")
            self.assertEqual(row["province_label"], f"Propinsi : 13. Sumatera Barat, {row['year']}")
            self.assertRegex(row["used_range"], r"^A1:P\d+$")
            self.assertGreater(row["body_row_count"], 0)
            self.assertTrue(row["total_row_present"])
            self.assertFalse(row["impact_values_promoted"])

    def test_expected_schema_has_sixteen_columns(self):
        columns = self.manifest["expected_source_columns"]
        self.assertEqual(len(columns), 16)
        self.assertEqual(columns[0], "No")
        self.assertEqual(columns[1], "Wilayah")
        self.assertEqual(columns[2], "Jumlah Kejadian")
        self.assertEqual(columns[-1], "Fasilitas Umum")

    def test_manifest_contains_no_promoted_metric_values(self):
        forbidden_keys = {
            "jumlah_kejadian_value",
            "meninggal_value",
            "hilang_value",
            "terluka_value",
            "menderita_value",
            "mengungsi_value",
            "impact_value",
            "total_impact",
        }

        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys.intersection(value.keys()))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.manifest)


if __name__ == "__main__":
    unittest.main()
