from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from scripts.audit_milestone10_analytical_panel import audit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifests/milestone10_analytical_panel.json"
COVERAGE = ROOT / "data/analysis/engine/panel_v1/m10-indicator-coverage.csv"
WIDE = ROOT / "data/analysis/engine/panel_v1/m10-panel-wide.csv"


class Milestone10AnalyticalPanelTests(unittest.TestCase):
    def test_completion_audit_has_no_errors(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone10_complete"])
        self.assertTrue(report["foundation_9_of_9_still_complete"])

    def test_manifest_locks_phase2_regime(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["phase"], "final_analytical_research_engine")
        self.assertEqual(manifest["regime_id"], "sumbar_current_kabkota_2018_2025_v1")
        self.assertEqual(manifest["geography_count"], 19)
        self.assertEqual(manifest["year_count"], 8)
        self.assertEqual(manifest["indicator_count"], 15)
        self.assertEqual(manifest["wide_row_count"], 152)
        self.assertFalse(manifest["imputation_performed"])
        self.assertFalse(manifest["historical_boundary_harmonization_performed"])
        self.assertFalse(manifest["causal_analysis_performed"])
        self.assertFalse(manifest["frontier_model_performed"])

    def test_balanced_indicators_are_explicit(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            set(manifest["complete_2018_2025_indicator_ids"]),
            {
                "expected_years_schooling",
                "mean_years_schooling",
                "labor_force_participation",
                "unemployment_rate",
                "poverty_rate",
                "real_grdp_growth",
                "rice_yield",
                "annual_rainfall",
            },
        )

    def test_sparse_source_footprints_remain_sparse(self) -> None:
        with COVERAGE.open("r", encoding="utf-8", newline="") as handle:
            rows = {row["indicator_id"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows["population_total"]["years_present"], "2020")
        self.assertEqual(rows["population_total"]["present_cells"], "19")
        self.assertEqual(rows["flood_events"]["years_present"], "2024")
        self.assertEqual(rows["flood_events"]["present_cells"], "19")
        self.assertEqual(rows["landslide_events"]["years_present"], "2024")
        self.assertEqual(rows["landslide_events"]["present_cells"], "19")
        self.assertEqual(rows["agriculture_share_grdp"]["years_present"], "2018|2019|2020|2021|2022|2023")
        self.assertEqual(rows["manufacturing_share_grdp"]["years_present"], "2018|2019|2020|2021|2022|2023")
        self.assertEqual(rows["underemployment_rate"]["years_present"], "2018|2019|2020|2021|2022|2023|2024")
        self.assertEqual(rows["life_expectancy"]["years_present"], "2020|2021|2022|2023|2024|2025")

    def test_wide_frame_keeps_missing_cells_blank(self) -> None:
        with WIDE.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 152)
        by_key = {(row["geography_id"], row["analysis_year"]): row for row in rows}
        # SP2020 population is not forward/backward filled.
        self.assertEqual(by_key[("idn.13.1371", "2019")]["population_total"], "")
        self.assertNotEqual(by_key[("idn.13.1371", "2020")]["population_total"], "")
        self.assertEqual(by_key[("idn.13.1371", "2021")]["population_total"], "")
        # BNPB 2024 event counts are not projected into adjacent years.
        self.assertEqual(by_key[("idn.13.1302", "2023")]["flood_events"], "")
        self.assertNotEqual(by_key[("idn.13.1302", "2024")]["flood_events"], "")
        self.assertEqual(by_key[("idn.13.1302", "2025")]["flood_events"], "")


if __name__ == "__main__":
    unittest.main()
