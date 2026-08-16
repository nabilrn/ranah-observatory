from __future__ import annotations

import unittest

from scripts.check_chirps_rainfall_drift import (
    compare_big_identity,
    compare_chirps_identity,
    select_chirps_rows,
)


def frozen_contract_rows() -> list[dict[str, str]]:
    rows = []
    for year in range(1981, 2026):
        for month in range(1, 13):
            rows.append({
                "contract_item_id": f"chirps_v3_final_{year:04d}_{month:02d}",
                "source_id": "chirps_v3",
                "role": "monthly_rainfall_source_cog",
                "year": str(year),
                "month": str(month),
                "locator": f"https://example.invalid/chirps-v3.0.{year:04d}.{month:02d}.cog",
                "source_release": "Tue, 25 Feb 2025 18:21:00 GMT",
                "transport_identity": '"etag"',
                "identity_sha256": "a" * 64,
                "identity_scope": "sha256_first_16384_bytes_not_full_file_checksum",
                "content_length_bytes": "30142896",
                "notes": "content_range=bytes 0-16383/30142896; bytes_read=16384",
            })
    return rows


class ChirpsRainfallDriftTests(unittest.TestCase):
    def test_annual_anchor_selection_checks_every_year_plus_last_complete_month(self) -> None:
        selected = select_chirps_rows(frozen_contract_rows(), "annual-anchors")
        self.assertEqual(len(selected), 46)
        self.assertEqual({int(row["year"]) for row in selected if row["month"] == "1"}, set(range(1981, 2026)))
        self.assertTrue(any(row["year"] == "2025" and row["month"] == "12" for row in selected))

    def test_full_selection_covers_all_540_months(self) -> None:
        selected = select_chirps_rows(frozen_contract_rows(), "full")
        self.assertEqual(len(selected), 540)
        self.assertEqual((selected[0]["year"], selected[0]["month"]), ("1981", "1"))
        self.assertEqual((selected[-1]["year"], selected[-1]["month"]), ("2025", "12"))

    def test_chirps_identity_stable_when_all_frozen_identity_fields_match(self) -> None:
        row = frozen_contract_rows()[0]
        current = {
            "reachable": True,
            "http_status": 206,
            "bytes_read": 16384,
            "content_range": "bytes 0-16383/30142896",
            "etag": '"etag"',
            "last_modified": "Tue, 25 Feb 2025 18:21:00 GMT",
            "prefix_sha256": "a" * 64,
            "is_tiff": True,
        }
        result = compare_chirps_identity(row, current)
        self.assertEqual(result["status"], "stable")
        self.assertEqual(result["differences"], [])

    def test_chirps_prefix_or_metadata_change_is_drift(self) -> None:
        row = frozen_contract_rows()[0]
        current = {
            "reachable": True,
            "http_status": 206,
            "bytes_read": 16384,
            "content_range": "bytes 0-16383/30142897",
            "etag": '"changed"',
            "last_modified": "Wed, 26 Feb 2025 00:00:00 GMT",
            "prefix_sha256": "b" * 64,
            "is_tiff": True,
        }
        result = compare_chirps_identity(row, current)
        self.assertEqual(result["status"], "drift")
        fields = {item["field"] for item in result["differences"]}
        self.assertEqual(fields, {"content_length_bytes", "etag", "source_release", "identity_sha256"})

    def test_chirps_transport_failure_is_not_mislabeled_as_content_drift(self) -> None:
        row = frozen_contract_rows()[0]
        result = compare_chirps_identity(row, {"reachable": False, "error": "timeout"})
        self.assertEqual(result["status"], "transport_error")

    def test_big_identity_uses_full_response_hash_and_length(self) -> None:
        row = {
            "contract_item_id": "big_sumbar_kabkota_june_2026_snapshot",
            "locator": "https://example.invalid/big.geojson",
            "content_length_bytes": "1234",
            "identity_sha256": "c" * 64,
        }
        stable = compare_big_identity(row, {
            "reachable": True,
            "http_status": 200,
            "bytes": 1234,
            "sha256": "c" * 64,
        })
        self.assertEqual(stable["status"], "stable")
        drift = compare_big_identity(row, {
            "reachable": True,
            "http_status": 200,
            "bytes": 1235,
            "sha256": "d" * 64,
        })
        self.assertEqual(drift["status"], "drift")
        self.assertEqual({item["field"] for item in drift["differences"]}, {"content_length_bytes", "identity_sha256"})


if __name__ == "__main__":
    unittest.main()
