from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.build_public_indicator_catalog import DEFAULT_OUTPUT, build

ROOT = Path(__file__).resolve().parents[1]


class PublicIndicatorCatalogTests(unittest.TestCase):
    def test_frozen_catalog_matches_canonical_panel_v3_inputs(self) -> None:
        frozen = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(frozen, build())

    def test_catalog_is_complete_and_bounded(self) -> None:
        payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "ranah-observatory/public-indicator-catalog/v1")
        self.assertEqual(payload["summary"]["indicator_count"], 23)
        self.assertEqual(payload["summary"]["domain_count"], 9)
        self.assertEqual(payload["summary"]["geography_count"], 19)
        self.assertEqual(len(payload["indicators"]), 23)
        self.assertEqual(len({row["id"] for row in payload["indicators"]}), 23)
        self.assertTrue(all(row["public_name"].strip() for row in payload["indicators"]))

        forbidden = {
            "score",
            "rank",
            "causal_effect",
            "recommended_policy",
            "expected_policy_impact",
            "wasted_potential",
        }
        for row in payload["indicators"]:
            self.assertFalse(forbidden & set(row))
            coverage = row["coverage"]
            self.assertEqual(
                coverage["present_cells"] + coverage["missing_cells"],
                coverage["total_possible_cells"],
            )
            self.assertGreaterEqual(coverage["rate"], 0)
            self.assertLessEqual(coverage["rate"], 1)

    def test_sensitive_indicator_semantics_stay_explicit(self) -> None:
        payload = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in payload["indicators"]}

        rainfall = rows["annual_rainfall"]
        self.assertIn("model_estimate", rainfall["present_claim_types"])
        self.assertIn("not BMKG station-observation equivalence", rainfall["semantic_caution"])

        water = rows["adequate_drinking_water_access"]
        self.assertIn("backcast_estimate", water["present_claim_types"])
        self.assertIn("2019-2020", water["semantic_caution"])

        dependency = rows["dependency_ratio"]
        self.assertIn("model_estimate_projection", dependency["present_claim_types"])
        self.assertIn("never relabel projection years as observed", dependency["semantic_caution"])

        disasters = rows["total_disaster_events"]
        self.assertEqual(disasters["coverage"]["last_year"], 2024)
        self.assertIn("2025 is missing, not zero", disasters["semantic_caution"])

    def test_catalog_ui_is_static_and_local_data_driven(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "site" / "catalog.js").read_text(encoding="utf-8")
        self.assertIn('id="katalog"', html)
        self.assertIn('src="catalog.js"', html)
        self.assertIn('href="catalog.css"', html)
        self.assertIn('data/indicators.json', js)
        self.assertNotIn('fetch("https://', js)
        self.assertNotIn("fetch('https://", js)


if __name__ == "__main__":
    unittest.main()
