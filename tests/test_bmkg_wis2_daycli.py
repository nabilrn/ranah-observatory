from __future__ import annotations

import unittest

from scripts.probe_bmkg_wis2_daycli import (
    MINANGKABAU_WIGOS,
    feature_properties,
    inspect_feature_collection,
    normalize_property_name,
    precipitation_candidates,
)


class BmkgWis2DayCliTests(unittest.TestCase):
    def test_feature_properties_extracts_only_mapping_properties(self) -> None:
        payload = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"name": "rainfall", "value": 12.3}},
                {"type": "Feature", "properties": None},
                "not-a-feature",
                {"type": "Feature", "properties": {"wigos_station_identifier": MINANGKABAU_WIGOS}},
            ],
        }
        rows = feature_properties(payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "rainfall")
        self.assertEqual(rows[1]["wigos_station_identifier"], MINANGKABAU_WIGOS)

    def test_inspect_feature_collection_records_counts_and_property_names(self) -> None:
        result = {
            "url": "https://example.invalid/items",
            "reachable": True,
            "http_status": 200,
            "payload": {
                "type": "FeatureCollection",
                "numberMatched": 12,
                "numberReturned": 2,
                "features": [
                    {"type": "Feature", "properties": {"name": "rainfall", "value": 10}},
                    {"type": "Feature", "properties": {"units": "mm", "value": 20}},
                ],
            },
        }
        inspected = inspect_feature_collection(result)
        self.assertTrue(inspected["is_feature_collection"])
        self.assertEqual(inspected["number_matched"], 12)
        self.assertEqual(inspected["number_returned"], 2)
        self.assertEqual(inspected["feature_count"], 2)
        self.assertEqual(inspected["property_names"], ["name", "units", "value"])
        self.assertNotIn("payload", inspected)

    def test_precipitation_candidate_detects_name_description_or_mm_units(self) -> None:
        rows = [
            {"name": "total precipitation", "description": "", "units": "kg m-2"},
            {"name": "daily temperature", "description": "rainfall amount", "units": "degC"},
            {"name": "unknown", "description": "", "units": "mm"},
            {"name": "air temperature", "description": "", "units": "degC"},
        ]
        candidates = precipitation_candidates(rows)
        self.assertEqual(len(candidates), 3)
        self.assertNotIn(rows[3], candidates)

    def test_normalize_property_name_is_case_and_space_insensitive(self) -> None:
        self.assertEqual(normalize_property_name(" Total Precipitation "), "total_precipitation")
        self.assertEqual(normalize_property_name(None), "")

    def test_non_feature_collection_is_rejected_by_inspector(self) -> None:
        inspected = inspect_feature_collection({
            "url": "https://example.invalid/items",
            "reachable": True,
            "http_status": 200,
            "payload": {"type": "Feature", "properties": {}},
        })
        self.assertFalse(inspected["is_feature_collection"])
        self.assertEqual(inspected["feature_count"], 0)
        self.assertEqual(inspected["property_names"], [])


if __name__ == "__main__":
    unittest.main()
