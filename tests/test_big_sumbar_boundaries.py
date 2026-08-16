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
        "content_type": "application/geo+json",
        "bytes": len(body),
        "sha256": "example",
        "body": body,
    }


def crosswalk() -> dict[str, dict[str, str]]:
    return {
        "1309": {
            "source_name_expected": "KEPULAUAN MENTAWAI",
            "canonical_geography_id": "idn.13.1301",
        },
        "1371": {
            "source_name_expected": "KOTA PADANG",
            "canonical_geography_id": "idn.13.1371",
        },
    }


def canonical() -> dict[str, dict[str, str]]:
    return {
        "idn.13.1301": {"canonical_name": "Kepulauan Mentawai"},
        "idn.13.1371": {"canonical_name": "Padang"},
    }


class BIGSumbarBoundaryTests(unittest.TestCase):
    def test_normalize_code_accepts_dotted_or_plain_permendagri_codes(self) -> None:
        self.assertEqual(normalize_code("13.09"), "1309")
        self.assertEqual(normalize_code("1371"), "1371")
        self.assertEqual(normalize_code(1371), "1371")

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

    def test_geojson_maps_kdpkab_and_excludes_blank_artifacts(self) -> None:
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "OBJECTID": 1,
                        "NAMOBJ": "Kepulauan Mentawai",
                        "KDBBPS": " ",
                        "KDPBPS": " ",
                        "KDPKAB": "13.09",
                        "KDPPUM": "13",
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
                        "OBJECTID": 2,
                        "NAMOBJ": "Kota Padang",
                        "KDBBPS": " ",
                        "KDPBPS": " ",
                        "KDPKAB": "13.71",
                        "KDPPUM": "13",
                        "WADMKK": "Kota Padang",
                        "WADMPR": "Sumatera Barat",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[100.0, -1.0], [100.1, -1.0], [100.0, -1.0]]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "OBJECTID": 3,
                        "NAMOBJ": "Sumatera Barat",
                        "KDBBPS": " ",
                        "KDPBPS": " ",
                        "KDPKAB": " ",
                        "KDPPUM": "13",
                        "WADMKK": " ",
                        "WADMPR": "Sumatera Barat",
                        "REMARK": "province/island artifact",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[100.2, -1.1], [100.3, -1.1], [100.2, -1.1]]],
                    },
                },
            ],
        }
        inspected = inspect_geojson(result(payload), crosswalk(), canonical())
        self.assertTrue(inspected["is_geojson_feature_collection"])
        self.assertEqual(inspected["raw_source_feature_count"], 3)
        self.assertEqual(inspected["excluded_non_kabkota_artifact_count"], 1)
        self.assertEqual(inspected["selected_kabkota_count"], 2)
        self.assertEqual(inspected["source_permendagri_codes"], ["1309", "1371"])
        self.assertEqual(inspected["missing_source_codes"], [])
        self.assertEqual(inspected["unexpected_source_codes"], [])
        self.assertEqual(inspected["mapped_canonical_geography_ids"], ["idn.13.1301", "idn.13.1371"])
        self.assertEqual(inspected["name_mismatches"], [])
        self.assertEqual(inspected["source_kdbbps_nonblank_count"], 0)
        self.assertEqual(inspected["source_kdpbps_nonblank_count"], 0)
        self.assertTrue(inspected["all_selected_geometries_polygonal"])
        self.assertTrue(inspected["all_selected_geometries_nonempty"])
        self.assertTrue(inspected["all_selected_features_sumatera_barat"])

    def test_geojson_rejects_duplicate_code_name_mismatch_and_wrong_province(self) -> None:
        payload = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "KDPKAB": "13.09",
                        "WADMKK": "Wrong Name",
                        "WADMPR": "Sumatera Barat",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[99.0, -2.0], [99.1, -2.0], [99.0, -2.0]]],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {
                        "KDPKAB": "13.09",
                        "WADMKK": "Kepulauan Mentawai",
                        "WADMPR": "Sumatera Utara",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[99.0, -2.0], [99.1, -2.0], [99.0, -2.0]]],
                    },
                },
            ],
        }
        inspected = inspect_geojson(result(payload), crosswalk(), canonical())
        self.assertEqual(inspected["duplicate_source_codes"], ["1309"])
        self.assertTrue(inspected["name_mismatches"])
        self.assertFalse(inspected["all_selected_features_sumatera_barat"])
        self.assertIn("1371", inspected["missing_source_codes"])
        self.assertIn("idn.13.1371", inspected["missing_canonical_geography_ids"])


if __name__ == "__main__":
    unittest.main()
