from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from probe_chirps_v3 import inspect_listing  # noqa: E402


class CHIRPSV3ProbeTests(unittest.TestCase):
    def test_listing_requires_all_months_through_2025(self) -> None:
        links = []
        for year in range(1981, 2026):
            for month in range(1, 13):
                links.append(f'<a href="chirps-v3.0.{year:04d}.{month:02d}.cog">x</a>')
        inspected = inspect_listing(
            {
                "url": "https://example.invalid/",
                "reachable": True,
                "http_status": 200,
                "content_type": "text/html",
                "bytes": 1,
                "sha256": "x",
                "text": "\n".join(links),
            }
        )
        self.assertEqual(inspected["monthly_cog_count"], 45 * 12)
        self.assertEqual(inspected["first_period"], "1981-01")
        self.assertEqual(inspected["last_period"], "2025-12")
        self.assertTrue(inspected["complete_years_through_2025"])

    def test_listing_detects_gap(self) -> None:
        text = "\n".join(
            [
                '<a href="chirps-v3.0.1981.01.cog">a</a>',
                '<a href="chirps-v3.0.2025.12.cog">b</a>',
            ]
        )
        inspected = inspect_listing(
            {
                "url": "https://example.invalid/",
                "reachable": True,
                "http_status": 200,
                "content_type": "text/html",
                "bytes": len(text),
                "sha256": "x",
                "text": text,
            }
        )
        self.assertTrue(inspected["has_1981_01"])
        self.assertTrue(inspected["has_2025_12"])
        self.assertFalse(inspected["complete_years_through_2025"])

    def test_non_200_listing_is_not_promoted(self) -> None:
        inspected = inspect_listing(
            {
                "url": "https://example.invalid/",
                "reachable": False,
                "http_status": 503,
                "error": "unavailable",
            }
        )
        self.assertEqual(inspected["monthly_cog_count"], 0)
        self.assertFalse(inspected["complete_years_through_2025"])


if __name__ == "__main__":
    unittest.main()
