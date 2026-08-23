from __future__ import annotations

import csv
import io
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts import build_milestone36_station_overlap as m36


def synthetic_year(year: int, *, prcp: float = 1.0, missing_offsets: set[int] | None = None) -> bytes:
    missing_offsets = missing_offsets or set()
    out = io.StringIO(newline="")
    fields = ["STATION", "DATE", "LATITUDE", "LONGITUDE", "NAME", "PRCP", "PRCP_ATTRIBUTES"]
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    start = date(year, 1, 1)
    days = 366 if m36.calendar.isleap(year) else 365
    for offset in range(days):
        day = start + timedelta(days=offset)
        writer.writerow({
            "STATION": m36.STATION_ID,
            "DATE": day.isoformat(),
            "LATITUDE": "-0.874989",
            "LONGITUDE": "100.351881",
            "NAME": "TABING, ID",
            "PRCP": "99.99" if offset in missing_offsets else f"{prcp:.2f}",
            "PRCP_ATTRIBUTES": "A",
        })
    return out.getvalue().encode()


class Milestone36StationOverlapTests(unittest.TestCase):
    def test_complete_year_passes(self) -> None:
        result = m36.analyze_year_bytes(1997, synthetic_year(1997, prcp=0.10))
        self.assertTrue(result["identity_valid"])
        self.assertTrue(result["completeness_pass"])
        self.assertEqual(result["valid_prcp_days"], 365)
        self.assertAlmostEqual(result["annual_prcp_inches"], 36.5)

    def test_missing_sentinel_is_never_zero_rain(self) -> None:
        result = m36.analyze_year_bytes(1997, synthetic_year(1997, prcp=0.10, missing_offsets={10}))
        self.assertEqual(result["valid_prcp_days"], 364)
        self.assertEqual(result["present_rows_missing_prcp_days"], 1)
        self.assertAlmostEqual(result["annual_prcp_inches"], 36.4)

    def test_exact_90_percent_day_gate_is_locked(self) -> None:
        # 36 missing days leaves 329 valid days, exactly the preregistered minimum.
        missing = set(range(0, 36, 1))
        result = m36.analyze_year_bytes(1997, synthetic_year(1997, missing_offsets=missing))
        # It still fails because the same missing days form a >31-day streak.
        self.assertEqual(result["valid_prcp_days"], 329)
        self.assertEqual(result["minimum_valid_prcp_days"], 329)
        self.assertFalse(result["completeness_pass"])
        self.assertGreater(result["maximum_consecutive_days_without_valid_prcp"], 31)

    def test_scattered_missing_days_can_pass_90_percent_gate(self) -> None:
        missing = set(range(0, 360, 10))  # 36 isolated missing days => 329 valid days.
        result = m36.analyze_year_bytes(1997, synthetic_year(1997, missing_offsets=missing))
        self.assertEqual(result["valid_prcp_days"], 329)
        self.assertLessEqual(result["maximum_consecutive_days_without_valid_prcp"], 31)
        self.assertTrue(result["completeness_pass"])

    def test_wrong_station_fails_closed(self) -> None:
        data = synthetic_year(1997).decode().replace(m36.STATION_ID, "99999999999").encode()
        result = m36.analyze_year_bytes(1997, data)
        self.assertFalse(result["identity_valid"])
        self.assertFalse(result["completeness_pass"])
        self.assertIsNone(result["annual_prcp_inches"])

    def test_classification_is_direction_only(self) -> None:
        years = {
            1997: m36.analyze_year_bytes(1997, synthetic_year(1997, prcp=0.10)),
            1998: m36.analyze_year_bytes(1998, synthetic_year(1998, prcp=0.20)),
        }
        classification, delta, pct = m36.classify(years)
        self.assertEqual(classification, "station_overlap_directionally_supportive")
        self.assertGreater(delta, 0)
        self.assertGreater(pct, 0)

    def test_incomplete_year_forces_held_classification(self) -> None:
        years = {
            1997: m36.analyze_year_bytes(1997, synthetic_year(1997, prcp=0.10)),
            1998: m36.analyze_year_bytes(1998, synthetic_year(1998, missing_offsets=set(range(100)))),
        }
        classification, delta, pct = m36.classify(years)
        self.assertEqual(classification, "station_overlap_incomplete_or_noncomparable")
        self.assertIsNone(delta)
        self.assertIsNone(pct)


if __name__ == "__main__":
    unittest.main()
