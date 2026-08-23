from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from scripts import probe_milestone36_station_archive as m36


class Milestone36StationArchiveTests(unittest.TestCase):
    def test_historical_identity_guards(self) -> None:
        self.assertTrue(m36.historical_name_ok("PADANG/TABING"))
        self.assertTrue(m36.historical_name_ok("PADANG / TABING"))
        self.assertFalse(m36.historical_name_ok("PADANG PARIAMAN/MINANGKABAU"))
        self.assertTrue(m36.coordinate_ok(-0.8833, 100.35))
        self.assertFalse(m36.coordinate_ok(-0.7936, 100.2892))

    def test_current_minangkabau_identity_triggers_break_guard(self) -> None:
        payload = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [100.2892, -0.7936]},
            "properties": {
                "traditional_station_identifier": "96163",
                "name": "PADANG PARIAMAN/MINANGKABAU",
                "status": "operational",
            },
        }
        fake = {
            "url": m36.BMKG_CURRENT_STATION_URL,
            "reachable": True,
            "http_status": 200,
            "content_type": "application/geo+json",
            "content_range": None,
            "bytes": 10,
            "sha256": "0" * 64,
            "body": json.dumps(payload).encode(),
        }
        with patch.object(m36, "fetch", return_value=fake):
            result = m36.probe_current_bmkg_station()
        self.assertTrue(result["current_minangkabau_identity_qualified"])
        self.assertTrue(result["station_history_break_guard_triggered"])

    def test_gsod_identity_never_parses_precipitation(self) -> None:
        csv_body = (
            'STATION,DATE,LATITUDE,LONGITUDE,ELEVATION,NAME,PRCP,PRCP_ATTRIBUTES\n'
            '96163099999,1997-01-01,-0.883,100.350,3.0,"PADANG/TABING",999.9,"A"\n'
        ).encode()
        fake = {
            "url": "https://example.invalid",
            "reachable": True,
            "http_status": 206,
            "content_type": "text/csv",
            "content_range": "bytes 0-100/1000",
            "bytes": len(csv_body),
            "sha256": "1" * 64,
            "body": csv_body,
        }
        with patch.object(m36, "fetch", return_value=fake):
            result = m36.probe_gsod_year(1997)
        self.assertTrue(result["historical_padang_tabing_identity_qualified"])
        self.assertFalse(result["precipitation_values_inspected"])
        self.assertNotIn("PRCP", json.dumps(result["identity_sample"]))

    def test_wrong_site_is_fail_closed(self) -> None:
        csv_body = (
            'STATION,DATE,LATITUDE,LONGITUDE,NAME,PRCP\n'
            '96163099999,1998-01-01,-0.794,100.289,"PADANG PARIAMAN/MINANGKABAU",123.4\n'
        ).encode()
        fake = {
            "url": "https://example.invalid",
            "reachable": True,
            "http_status": 200,
            "content_type": "text/csv",
            "content_range": None,
            "bytes": len(csv_body),
            "sha256": "2" * 64,
            "body": csv_body,
        }
        with patch.object(m36, "fetch", return_value=fake):
            result = m36.probe_gsod_year(1998)
        self.assertFalse(result["historical_padang_tabing_identity_qualified"])


if __name__ == "__main__":
    unittest.main()
