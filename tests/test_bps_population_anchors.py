from __future__ import annotations

import unittest

from scripts.validate_bps_population_anchors import (
    ANOMALOUS_1995_CODES,
    CURRENT_20_CODES,
    DEFAULT_CANONICAL,
    DEFAULT_QUALIFICATION,
    EXPECTED_COUNTS,
    EXPECTED_YEARS,
    OLD_15_CODES,
    build_report,
    read_csv,
    validate_qualification,
)


class BpsPopulationAnchorTests(unittest.TestCase):
    def test_qualification_covers_exact_anchor_years(self) -> None:
        rows = read_csv(DEFAULT_QUALIFICATION)
        result = validate_qualification(rows)
        self.assertEqual(result["qualification_year_count"], 9)
        self.assertEqual(result["held_source_integrity_years"], [1995])
        self.assertEqual(result["already_canonical_years"], [2020])
        self.assertFalse(result["growth_derivation_ready"])
        self.assertEqual(tuple(sorted(int(row["year"]) for row in rows)), EXPECTED_YEARS)

    def test_population_growth_stays_blocked_for_every_anchor(self) -> None:
        rows = read_csv(DEFAULT_QUALIFICATION)
        self.assertTrue(all(row["population_growth_derivation"].startswith("blocked") for row in rows))

    def test_1995_is_held_as_source_alignment_anomaly(self) -> None:
        rows = {int(row["year"]): row for row in read_csv(DEFAULT_QUALIFICATION)}
        row = rows[1995]
        self.assertEqual(row["source_code_profile"], "anomalous_shifted_15_keys")
        self.assertEqual(row["source_integrity_decision"], "hold_key_label_alignment_anomaly")
        self.assertEqual(row["population_total_promotion"], "hold_all_rows")
        self.assertNotIn("1300", ANOMALOUS_1995_CODES)
        self.assertIn("1301", ANOMALOUS_1995_CODES)
        self.assertIn("1377", ANOMALOUS_1995_CODES)

    def test_historical_and_current_code_profiles_are_not_conflated(self) -> None:
        self.assertEqual(len(OLD_15_CODES), 15)
        self.assertEqual(len(ANOMALOUS_1995_CODES), 15)
        self.assertEqual(len(CURRENT_20_CODES), 20)
        self.assertNotEqual(OLD_15_CODES, ANOMALOUS_1995_CODES)
        self.assertNotEqual(OLD_15_CODES, CURRENT_20_CODES)
        self.assertEqual(EXPECTED_COUNTS[2000], 16)
        self.assertEqual(EXPECTED_COUNTS[2005], 20)

    def test_2020_is_reused_not_duplicated(self) -> None:
        rows = {int(row["year"]): row for row in read_csv(DEFAULT_QUALIFICATION)}
        self.assertEqual(rows[2020]["population_total_promotion"], "already_canonical")
        self.assertEqual(rows[2020]["reference_date_decision"], "qualified_september_2020")
        canonical_population = [
            row for row in read_csv(DEFAULT_CANONICAL)
            if row["indicator_id"] == "population_total"
        ]
        self.assertEqual(len(canonical_population), 20)
        self.assertTrue(all(row["claim_type"] == "observed" for row in canonical_population))

    def test_offline_report_promotes_no_new_values(self) -> None:
        report = build_report(DEFAULT_QUALIFICATION, DEFAULT_CANONICAL)
        decision = report["promotion_decision"]
        self.assertEqual(decision["population_total_2020"], "already_canonical")
        self.assertEqual(decision["additional_current_population_total_rows"], 0)
        self.assertEqual(decision["population_growth_rows"], 0)
        self.assertEqual(report["live_source_validation"], "not_run")


if __name__ == "__main__":
    unittest.main()
