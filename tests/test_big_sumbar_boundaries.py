from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from probe_big_sumbar_boundaries import (  # noqa: E402
    inspect_geojson,
    inspect_service,
    normalize_code,
)


def result(payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload).encode("utf-8")
    return {
        "url": "https://example.invalid",
        "reachable": True,
        "http_status": 200,
        "content_type": "application/json",
        "bytes": len(body),
        "sha256": "example",
        "body": body,
    }


class BIGSumbarBoundaryTests(unittest.TestCase):
    def test_normalize_code_accepts_dotted_or_plain_bps_codes(self) -> None:
        self.assertEqual(normalize_code("13.01"), "1301")
        self.assertEqual(normalize_code("1301"), "1301")
        self.assertEqual(normalize_code(1301), "1301")

    def test_service_requires_pinned_june_2026_edition(self) -> None:
        inspected = inspect_service(
            result(
                {
                    "serviceDescription": "Geodatabase data batas wilayah administrasi nasional edisi Juni 2026",
                    "copyrightText": "Badan Informasi Geospasial",
                    "spatialReference": {"wkid": 4326},
                    "supportedQueryFormats": "JSON, geoJSON",
                }
            )
        )
        self.assertTrue(inspected["is_arcgis_map_service"])
        self.assertTrue(inspected["edition_matches_expected"])
        self.assertEqual(inspected["spatial_reference_wkid"], 4326)

    def test_geojson_requires_exact_codes_and_polygon_geometry(self) -> None:
        expected = {
            "1301": {"canonical_name": "Kepulauan Mentawai"},
            "1371": {"canonical_name": "Padang"},
        }
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "KDBBPS": "13.01",
                        "KDPBPS": "13",
                        "WADMKK": "Kepulauan Mentawai",
                        "WADMPR": "Sumatera Barat",
                    },
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[[[99.0, -2.0], [99.1, -2.0], [99.0, -2.0]]]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "KDBBPS": "1371",
                        "KDPBPS": "13",
                        "WADMKK": "Padang",
                        "WADMPR": "Sumatera Barat",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[100.0, -1.0], [100.1, -1.0], [100.0, -1.0]]],
                    },
                },
            ],
        }
        inspected = inspect_geojson(result(payload), expected)
        self.assertTrue(inspected["is_geojson_feature_collection"])
        self.assertEqual(inspected["feature_count"], 2)
        self.assertEqual(inspected["bps_codes"], ["1301", "1371"])
        self.assertEqual(inspected["missing_bps_codes"], [])
        self.assertEqual(inspected["unexpected_bps_codes"], [])
        self.assertTrue(inspected["all_geometries_polygonal"])
        self.assertTrue(inspected["all_geometries_nonempty"])
        self.assertTrue(inspected["all_features_sumatera_barat"])

    def test_geojson_rejects_duplicate_or_wrong_province(self) -> None:
        expected = {"1301": {"canonical_name": "Kepulauan Mentawai"}}
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"KDBBPS": "1301", "KDPBPS": "13", "WADMKK": "A", "WADMPR": "Sumatera Barat"},
                    "geometry": {"type": "Polygon", "coordinates": [[[99.0, -2.0], [99.1, -2.0], [99.0, -2.0]]]},
                },
                {
                    "type": "Feature",
                    "properties": {"KDBBPS": "1301", "KDPBPS": "12", "WADMKK": "A", "WADMPR": "Sumatera Utara"},
                    "geometry": {"type": "Polygon", "coordinates": [[[99.0, -2.0], [99.1, -2.0], [99.0, -2.0]]]},
                },
            ],
        }
        inspected = inspect_geojson(result(payload), expected)
        self.assertEqual(inspected["duplicate_bps_codes"], ["1301"])
        self.assertFalse(inspected["all_features_sumatera_barat"])


if __name__ == "__main__":
    unittest.main()
