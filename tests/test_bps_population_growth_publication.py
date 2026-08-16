from __future__ import annotations

import unittest

from scripts.validate_bps_population_growth_publication import (
    DEFAULT_GEOGRAPHIES,
    DEFAULT_SOURCE,
    EXPECTED_SP2010_TOTAL,
    EXPECTED_SP2020_TOTAL,
    INTERVAL_MONTHS,
    build_report,
    geometric_growth_pct,
    read_csv,
    validate_source_contract,
)


class BpsPopulationGrowthPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_rows = read_csv(DEFAULT_SOURCE)
        cls.geography_rows = read_csv(DEFAULT_GEOGRAPHIES)
        cls.validation = validate_source_contract(cls.source_rows, cls.geography_rows)

    def test_contract_has_exact_current_sumbar_footprint(self) -> None:
        self.assertEqual(self.validation["source_row_count"], 19)
        self.assertEqual(self.validation["geography_count"], 19)
        self.assertEqual(self.validation["publication_number"], "13000.2106")
        self.assertEqual(self.validation["table"], "3.1.1")

    def test_publication_population_totals_match_official_census_totals(self) -> None:
        self.assertEqual(self.validation["population_2010_row_sum"], EXPECTED_SP2010_TOTAL)
        self.assertEqual(self.validation["population_2020_row_sum"], EXPECTED_SP2020_TOTAL)
        self.assertEqual(EXPECTED_SP2010_TOTAL, 4_846_909)
        self.assertEqual(EXPECTED_SP2020_TOTAL, 5_534_472)

    def test_growth_formula_uses_may_2010_to_september_2020_interval(self) -> None:
        self.assertEqual(INTERVAL_MONTHS, 124)
        self.assertEqual(self.validation["formula_match_count"], 19)
        mentawai = next(row for row in self.source_rows if row["bps_code"] == "1301")
        calculated = geometric_growth_pct(
            int(mentawai["population_2010_may"]),
            int(mentawai["population_2020_september"]),
        )
        self.assertEqual(round(calculated, 2), 1.36)
        self.assertEqual(float(mentawai["growth_2010_2020_pct_per_year"]), 1.36)

    def test_known_publication_rates_are_preserved(self) -> None:
        rates = {row["bps_code"]: float(row["growth_2010_2020_pct_per_year"]) for row in self.source_rows}
        self.assertEqual(rates["1305"], 0.91)  # Tanah Datar
        self.assertEqual(rates["1310"], 2.27)  # Solok Selatan
        self.assertEqual(rates["1371"], 0.84)  # Padang
        self.assertEqual(rates["1375"], 0.81)  # Bukittinggi
        self.assertEqual(rates["1377"], 1.71)  # Pariaman

    def test_contract_is_derived_official_statistic_not_observed_count(self) -> None:
        self.assertTrue(all(row["target_indicator"] == "population_growth" for row in self.source_rows))
        self.assertTrue(all(row["target_claim_type"] == "derived" for row in self.source_rows))
        self.assertFalse(self.validation["canonical_promotion_ready"])
        self.assertFalse(self.validation["canonical_promotion_performed"])

    def test_report_keeps_materialization_as_separate_next_step(self) -> None:
        report = build_report(DEFAULT_SOURCE, DEFAULT_GEOGRAPHIES)
        self.assertTrue(report["decision"]["source_contract_qualified"])
        self.assertEqual(report["decision"]["published_growth_values_in_scope"], 19)
        self.assertEqual(report["decision"]["canonical_growth_rows_added"], 0)
        self.assertIn("materialize", report["decision"]["next_step"])


if __name__ == "__main__":
    unittest.main()
