import unittest

from scripts.probe_milestone38_bnpb_historical_district_impact import _classify_resource, _resource_record


class Milestone38TransportTests(unittest.TestCase):
    def test_direct_xlsx_resource_is_classified_without_downloading(self):
        resource = {
            "id": "r1",
            "name": "stat_by_wil_13_2000.xlsx",
            "format": "XLSX",
            "url": "https://data.bnpb.go.id/dataset/pkg/resource/r1/download/stat_by_wil_13_2000.xlsx",
            "datastore_active": False,
        }
        self.assertEqual(_classify_resource(resource), "direct_file")
        row = _resource_record(resource, 2000)
        self.assertTrue(row["sumbar_filename_candidate"])
        self.assertEqual(row["transport_class"], "direct_file")

    def test_link_only_resource_stays_link_only(self):
        resource = {
            "id": "r2",
            "name": "Jumlah Kejadian Bencana Tahun 2017",
            "format": "",
            "url": "https://dibi.bnpb.go.id/",
            "datastore_active": False,
        }
        self.assertEqual(_classify_resource(resource), "external_or_link_resource")
        row = _resource_record(resource, 2017)
        self.assertFalse(row["sumbar_filename_candidate"])

    def test_missing_url_is_not_promoted(self):
        self.assertEqual(_classify_resource({"name": "broken", "url": "", "format": ""}), "missing_url")


if __name__ == "__main__":
    unittest.main()
