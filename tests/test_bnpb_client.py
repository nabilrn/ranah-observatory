from __future__ import annotations

import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bnpb_client import BNPBApiError, BNPBClient  # noqa: E402


class BNPBClientTests(unittest.TestCase):
    def test_package_show_unwraps_ckan_result(self) -> None:
        def transport(url: str, timeout: float):
            self.assertIn("package_show", url)
            self.assertEqual(timeout, 30.0)
            return {"success": True, "result": {"id": "dataset-1", "title": "Example"}}

        client = BNPBClient(transport=transport, retries=0)
        result = client.package_show("dataset-1")
        self.assertEqual(result["id"], "dataset-1")

    def test_datastore_search_all_paginates_without_credentials(self) -> None:
        calls: list[int] = []
        records = [{"_id": index, "value": index} for index in range(5)]

        def transport(url: str, timeout: float):
            query = parse_qs(urlparse(url).query)
            self.assertNotIn("key", query)
            offset = int(query["offset"][0])
            limit = int(query["limit"][0])
            calls.append(offset)
            return {
                "success": True,
                "result": {
                    "resource_id": query["resource_id"][0],
                    "total": len(records),
                    "fields": [{"id": "_id", "type": "int"}, {"id": "value", "type": "int"}],
                    "records": records[offset : offset + limit],
                },
            }

        client = BNPBClient(transport=transport, retries=0)
        result = client.datastore_search_all("resource-1", page_size=2)
        self.assertEqual(calls, [0, 2, 4])
        self.assertEqual(result["returned"], 5)
        self.assertEqual([row["value"] for row in result["records"]], list(range(5)))

    def test_unsuccessful_ckan_payload_raises(self) -> None:
        client = BNPBClient(
            transport=lambda url, timeout: {"success": False, "error": {"message": "nope"}},
            retries=0,
        )
        with self.assertRaises(BNPBApiError):
            client.package_show("dataset-1")

    def test_datastore_rejects_invalid_shape(self) -> None:
        client = BNPBClient(
            transport=lambda url, timeout: {"success": True, "result": {"total": 1}},
            retries=0,
        )
        with self.assertRaises(BNPBApiError):
            client.datastore_search_page("resource-1")


if __name__ == "__main__":
    unittest.main()
