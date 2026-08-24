import json
import re
import unittest
from pathlib import Path


MANIFEST = Path("data/manifests/milestone39_bnpb_drive_archive_qualification.json")


class Milestone39DriveArchiveQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_research_boundary_keeps_numeric_promotion_blocked(self):
        q = self.manifest["qualification"]
        self.assertFalse(q["numeric_values_promoted"])
        self.assertFalse(q["district_city_panel_authorized"])
        self.assertFalse(q["event_level_panel_authorized"])

    def test_initial_tranche_has_one_sumbar_candidate_per_year(self):
        years = self.manifest["years"]
        self.assertEqual([row["year"] for row in years], list(range(2002, 2007)))
        self.assertEqual(len({row["sumbar_file"]["file_id"] for row in years}), 5)
        for row in years:
            year = row["year"]
            f = row["sumbar_file"]
            self.assertEqual(f["name"], f"stat_by_wil_13_{year}.xlsx")
            self.assertTrue(f["downloadable"])
            self.assertEqual(row["folder_listing_file_count"], 38)
            self.assertRegex(row["folder_url"], r"^https://drive\.google\.com/drive/folders/")

    def test_schema_audited_workbooks_have_source_native_sumbar_label(self):
        audited = [row for row in self.manifest["years"] if row["year"] in (2002, 2003)]
        self.assertEqual(len(audited), 2)
        for row in audited:
            f = row["sumbar_file"]
            self.assertEqual(f["sheet"], "statistik")
            self.assertEqual(f["province_label"], f"Propinsi : 13. Sumatera Barat, {row['year']}")
            self.assertRegex(f["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(f["body_row_count"], 0)
            self.assertTrue(f["total_row_present"])
            self.assertFalse(f["impact_values_promoted"])

    def test_manifest_contains_no_promoted_impact_values(self):
        forbidden_keys = {
            "jumlah_kejadian_value",
            "meninggal_value",
            "hilang_value",
            "terluka_value",
            "menderita_value",
            "mengungsi_value",
            "impact_value",
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
