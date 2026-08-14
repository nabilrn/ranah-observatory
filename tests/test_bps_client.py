from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bps_client import BPSApiError, BPSClient, parse_list_response  # noqa: E402
from harvest_bps import write_snapshot  # noqa: E402


class BPSClientTests(unittest.TestCase):
    def test_parse_list_response(self) -> None:
        info, rows = parse_list_response(
            {
                "status": "OK",
                "data-availability": "available",
                "data": [
                    {"page": 1, "pages": 2, "per_page": 10, "count": 2, "total": 12},
                    [{"pub_id": "a"}, {"pub_id": "b"}],
                ],
            }
        )
        self.assertEqual(2, info.pages)
        self.assertEqual(12, info.total)
        self.assertEqual(["a", "b"], [row["pub_id"] for row in rows])

    def test_parse_unavailable_list_is_empty(self) -> None:
        info, rows = parse_list_response(
            {"status": "OK", "data-availability": "not-available", "data": []}
        )
        self.assertEqual(0, info.pages)
        self.assertEqual([], rows)

    def test_pagination_and_query_parameters(self) -> None:
        seen_urls: list[str] = []

        def transport(url: str, timeout: float):
            self.assertEqual(30.0, timeout)
            seen_urls.append(url)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            page = int(query["page"][0])
            self.assertEqual(["publication"], query["model"])
            self.assertEqual(["1300"], query["domain"])
            self.assertEqual(["secret-token"], query["key"])
            return {
                "status": "OK",
                "data-availability": "available",
                "data": [
                    {"page": page, "pages": 2, "per_page": 1, "count": 1, "total": 2},
                    [{"pub_id": f"p{page}", "title": f"Publication {page}"}],
                ],
            }

        client = BPSClient("secret-token", transport=transport)
        rows = client.list_publications(domain="1300", year=2026, keyword="Sumatera Barat")
        self.assertEqual(["p1", "p2"], [row["pub_id"] for row in rows])
        self.assertEqual(2, len(seen_urls))

    def test_max_pages_stops_pagination(self) -> None:
        calls = 0

        def transport(url: str, timeout: float):
            nonlocal calls
            calls += 1
            query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            page = int(query["page"][0])
            return {
                "status": "OK",
                "data-availability": "available",
                "data": [
                    {"page": page, "pages": 5, "per_page": 1, "count": 1, "total": 5},
                    [{"var_id": page}],
                ],
            }

        client = BPSClient("secret-token", transport=transport)
        rows = client.list_variables(domain="1300", max_pages=2)
        self.assertEqual(2, len(rows))
        self.assertEqual(2, calls)

    def test_dynamic_data_requires_available_payload(self) -> None:
        def transport(url: str, timeout: float):
            return {"status": "OK", "data-availability": "not-available"}

        client = BPSClient("secret-token", transport=transport)
        with self.assertRaises(BPSApiError):
            client.get_dynamic_data(domain="1300", var=145, th=100)

    def test_snapshot_has_stable_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "snapshot.json"
            _, checksum_path = write_snapshot(
                output,
                {
                    "snapshot_schema": "ranah-observatory/bps-webapi-snapshot/v1",
                    "source_id": "bps_webapi",
                    "result": [{"pub_id": "p1"}],
                },
            )
            parsed = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("bps_webapi", parsed["source_id"])
            checksum_line = checksum_path.read_text(encoding="utf-8").strip()
            digest, filename = checksum_line.split("  ", 1)
            self.assertEqual(64, len(digest))
            self.assertEqual("snapshot.json", filename)


if __name__ == "__main__":
    unittest.main()
