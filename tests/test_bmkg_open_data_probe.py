from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from probe_bmkg_open_data import (  # noqa: E402
    inspect_cap_alert,
    inspect_earthquake,
    inspect_forecast,
    inspect_nowcast_feed,
)


def result(body: bytes, content_type: str = "application/octet-stream") -> dict[str, object]:
    return {
        "url": "https://example.invalid",
        "reachable": True,
        "http_status": 200,
        "content_type": content_type,
        "bytes": len(body),
        "sha256": "example",
        "body_prefix": body[:20].decode("utf-8", errors="replace"),
        "body": body,
    }


class BMKGOpenDataProbeTests(unittest.TestCase):
    def test_forecast_is_explicitly_prospective_and_flattens_records(self) -> None:
        payload = {
            "lokasi": {
                "adm4": "13.71.01.1001",
                "provinsi": "Sumatera Barat",
                "kotkab": "Kota Padang",
                "kecamatan": "Padang Selatan",
                "desa": "Belakang Pondok",
            },
            "data": [
                {
                    "cuaca": [
                        [
                            {"local_datetime": "2026-08-16 12:00:00", "t": 29, "analysis_date": "2026-08-16T00:00:00Z"},
                            {"local_datetime": "2026-08-16 15:00:00", "t": 28, "analysis_date": "2026-08-16T00:00:00Z"},
                        ],
                        [{"local_datetime": "2026-08-17 00:00:00", "t": 26, "analysis_date": "2026-08-16T00:00:00Z"}],
                    ]
                }
            ],
        }
        inspected = inspect_forecast(result(json.dumps(payload).encode(), "application/json"), "13.71.01.1001")
        self.assertTrue(inspected["is_forecast_payload"])
        self.assertEqual(inspected["source_role"], "prospective_forecast_only")
        self.assertEqual(inspected["forecast_days"], 2)
        self.assertEqual(inspected["forecast_record_count"], 3)
        self.assertIn("t", inspected["record_keys"])

    def test_nowcast_feed_finds_sumatera_barat_detail_url(self) -> None:
        xml = b"""<?xml version='1.0'?>
        <rss version='2.0'><channel>
          <item><title>Peringatan Dini Cuaca Sumatera Barat</title><link>https://www.bmkg.go.id/alerts/nowcast/id/SUMBAR_alert.xml</link></item>
          <item><title>Peringatan Dini Cuaca Riau</title><link>https://www.bmkg.go.id/alerts/nowcast/id/RIAU_alert.xml</link></item>
        </channel></rss>"""
        inspected, link = inspect_nowcast_feed(result(xml, "application/xml"))
        self.assertTrue(inspected["is_rss_or_atom"])
        self.assertEqual(inspected["active_alert_count"], 2)
        self.assertEqual(inspected["sumatera_barat_alert_count"], 1)
        self.assertEqual(link, "https://www.bmkg.go.id/alerts/nowcast/id/SUMBAR_alert.xml")

    def test_cap_parser_records_temporal_and_polygon_metadata_without_promoting_history(self) -> None:
        xml = b"""<?xml version='1.0'?>
        <alert xmlns='urn:oasis:names:tc:emergency:cap:1.2'>
          <identifier>ID-1</identifier><sender>bmkg@example.invalid</sender><sent>2026-08-16T01:00:00+00:00</sent>
          <status>Actual</status><msgType>Alert</msgType><scope>Public</scope>
          <info><event>Hujan Lebat</event><effective>2026-08-16T08:00:00+07:00</effective><expires>2026-08-16T10:00:00+07:00</expires>
            <area><areaDesc>Kota Padang</areaDesc><polygon>-0.9,100.3 -1.0,100.4 -0.9,100.3</polygon>
              <geocode><valueName>Kode Wilayah</valueName><value>13.71</value></geocode>
            </area>
          </info>
        </alert>"""
        inspected = inspect_cap_alert(result(xml, "application/xml"))
        self.assertTrue(inspected["is_cap_alert"])
        self.assertEqual(inspected["identifier"], "ID-1")
        self.assertEqual(inspected["events"], ["Hujan Lebat"])
        self.assertEqual(inspected["area_count"], 1)
        self.assertEqual(inspected["polygon_count"], 1)
        self.assertEqual(inspected["source_role"], "active_nowcast_alert_detail")

    def test_earthquake_feed_is_marked_latest_event_not_historical_archive(self) -> None:
        payload = {
            "Infogempa": {
                "gempa": {
                    "DateTime": "2026-08-16T02:00:00+00:00",
                    "Magnitude": "5.1",
                    "Coordinates": "-1.0,100.0",
                    "Wilayah": "Example",
                }
            }
        }
        inspected = inspect_earthquake(result(json.dumps(payload).encode(), "application/json"))
        self.assertTrue(inspected["is_earthquake_payload"])
        self.assertEqual(inspected["event_count"], 1)
        self.assertEqual(inspected["source_role"], "latest_event_feed_not_historical_archive")


if __name__ == "__main__":
    unittest.main()
