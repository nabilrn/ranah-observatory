from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.build_public_district_explorer import DEFAULT_OUTPUT, INDICATORS, SOURCE, build

ROOT = Path(__file__).resolve().parents[1]


class PublicDistrictExplorerTests(unittest.TestCase):
    def test_builder_selects_only_four_qualified_m22_indicators(self) -> None:
        payload = build(SOURCE)
        self.assertEqual(payload["schema"], "ranah-observatory/public-district-explorer/v1")
        self.assertEqual(len(payload["districts"]), 19)
        self.assertEqual(len(payload["indicator_summary"]), 4)
        self.assertEqual(
            set(payload["interpretation"]["not_qualified_for_hierarchical_explorer"]),
            {"expected_years_schooling", "mean_years_schooling", "poverty_rate"},
        )
        for district in payload["districts"]:
            self.assertEqual(set(district["indicators"]), set(INDICATORS))

    def test_frozen_public_json_matches_deterministic_builder(self) -> None:
        expected = build(SOURCE)
        actual = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_real_grdp_growth_never_gets_geography_robust_label(self) -> None:
        payload = build(SOURCE)
        for district in payload["districts"]:
            growth = district["indicators"]["real_grdp_growth"]
            self.assertFalse(growth["trajectory_robust"])
            self.assertEqual(growth["trajectory_classification"], "trajectory_not_robust")

    def test_unemployment_trajectory_counts_match_m22(self) -> None:
        payload = build(SOURCE)
        summary = next(row for row in payload["indicator_summary"] if row["id"] == "unemployment_rate")
        self.assertEqual(
            summary["classification_counts"],
            {
                "persistent_increase": 5,
                "persistent_decrease": 11,
                "trajectory_not_robust": 3,
            },
        )

    def test_site_exposes_district_explorer_without_external_chart_library(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="daerah"', html)
        self.assertIn('id="district-select"', html)
        self.assertIn("data/districts.json", js)
        self.assertIn("<svg", js)
        self.assertNotIn("chart.js", js.casefold())
        self.assertNotIn("d3.js", js.casefold())


if __name__ == "__main__":
    unittest.main()
