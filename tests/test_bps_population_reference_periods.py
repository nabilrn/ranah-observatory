from __future__ import annotations

import unittest

from scripts.validate_bps_population_reference_periods import (
    DEFAULT_ANCHOR_QUALIFICATION,
    DEFAULT_CANONICAL,
    DEFAULT_REFERENCE_PERIODS,
    build_report,
    read_csv,
    validate_reference_periods,
)


class BpsPopulationReferencePeriodTests(unittest.TestCase):
    def test_reference_period_registry_covers_only_modern_review_slice(self) -> None:
        rows = read_csv(DEFAULT_REFERENCE_PERIODS)
        self.assertEqual({int(row["year"]) for row in rows}, {2010, 2015, 2020})
        result = validate_reference_periods(rows)
        self.assertEqual(result["qualified_point_reference_years"], [2010])
        self.assertEqual(result["qualified_window_only_years"], [2015, 2020])
        self.assertFalse(result["custom_population_growth_ready"])

    def test_sp2010_uses_official_census_day(self) -> None:
        rows = {int(row["year"]): row for row in read_csv(DEFAULT_REFERENCE_PERIODS)}
        row = rows[2010]
        self.assertEqual(row["fieldwork_start"], "2010-05-01")
        self.assertEqual(row["fieldwork_end"], "2010-05-31")
        self.assertEqual(row["point_reference_date"], "2010-05-15")
        self.assertEqual(row["reference_start"], "2010-05-15")
        self.assertEqual(row["reference_end"], "2010-05-15")

    def test_supas2015_does_not_invent_point_date(self) -> None:
        rows = {int(row["year"]): row for row in read_csv(DEFAULT_REFERENCE_PERIODS)}
        row = rows[2015]
        self.assertEqual(row["reference_start"], "2015-05-01")
        self.assertEqual(row["reference_end"], "2015-05-31")
        self.assertEqual(row["point_reference_date"], "")
        self.assertEqual(row["qualification_status"], "qualified_window_only")

    def test_sp2020_matches_existing_canonical_september_bounds(self) -> None:
        report = build_report(DEFAULT_REFERENCE_PERIODS, DEFAULT_ANCHOR_QUALIFICATION, DEFAULT_CANONICAL)
        crosscheck = report["sp2020_canonical_crosscheck"]
        self.assertEqual(crosscheck["canonical_population_rows"], 20)
        self.assertEqual(crosscheck["canonical_time_start"], "2020-09-01")
        self.assertEqual(crosscheck["canonical_time_end"], "2020-09-30")
        self.assertTrue(crosscheck["matches_qualified_reference_window"])

    def test_custom_growth_remains_blocked(self) -> None:
        report = build_report(DEFAULT_REFERENCE_PERIODS, DEFAULT_ANCHOR_QUALIFICATION, DEFAULT_CANONICAL)
        decision = report["growth_decision"]
        self.assertEqual(decision["custom_derived_growth_rows_ready"], 0)
        self.assertTrue(decision["status"].startswith("blocked"))
        self.assertEqual(decision["official_bps_growth_lane"], "separate_future_qualification")

    def test_all_reference_sources_are_official_bps_hosts(self) -> None:
        rows = read_csv(DEFAULT_REFERENCE_PERIODS)
        for row in rows:
            self.assertIn("bps.go.id", row["official_source_url"])
            if row["supporting_source_url"]:
                self.assertIn("bps.go.id", row["supporting_source_url"])


if __name__ == "__main__":
    unittest.main()
