from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_public_product import (
    DEFAULT_OVERVIEW,
    DISASTER_SOURCE_PATHS,
    EXPECTED_BLOCKED,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]


class PublicProductTests(unittest.TestCase):
    def test_claim_gated_overview_is_valid(self) -> None:
        result = validate()
        self.assertEqual(result["blocked_boundaries"], 9)
        self.assertGreaterEqual(result["stories"], 8)
        self.assertGreaterEqual(result["headline_stats"], 5)

    def test_all_blocked_claims_are_visible(self) -> None:
        payload = json.loads(DEFAULT_OVERVIEW.read_text(encoding="utf-8"))
        actual = {row["claim_id"] for row in payload["boundaries"]}
        self.assertEqual(actual, EXPECTED_BLOCKED)

    def test_site_is_static_and_local_data_driven(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        self.assertIn('src="app.js"', html)
        self.assertIn('href="styles.css"', html)
        self.assertIn('data/overview.json', js)
        self.assertNotIn("fetch(\"https://", js)
        self.assertNotIn("fetch('https://", js)

    def test_public_copy_keeps_monetary_boundary_prominent(self) -> None:
        payload = json.loads(DEFAULT_OVERVIEW.read_text(encoding="utf-8"))
        hero = " ".join(payload["hero"].values()).casefold()
        self.assertIn("rupiah", hero)
        self.assertIn("belum", hero)
        monetary = next(
            row for row in payload["boundaries"]
            if row["claim_id"] == "B01_MONETARY_WASTED_POTENTIAL"
        )
        self.assertIn("belum", monetary["title"].casefold())
        self.assertIn("rupiah", monetary["title"].casefold())

    def test_disaster_public_context_uses_m45_m46_and_keeps_impact_boundary(self) -> None:
        payload = json.loads(DEFAULT_OVERVIEW.read_text(encoding="utf-8"))
        story = next(row for row in payload["stories"] if row["id"] == "disaster-components")
        self.assertEqual("context", story["evidence_state"])
        self.assertEqual(DISASTER_SOURCE_PATHS, set(story["source_paths"]))
        self.assertNotIn("source_claim_ids", story)
        copy = " ".join(
            story[field] for field in ("title", "plain_language", "why_it_matters", "caveat")
        ).casefold()
        self.assertIn("285", copy)
        self.assertIn("133", copy)
        self.assertIn("2025", copy)
        self.assertIn("bukan nol", copy)
        self.assertIn("bukan", copy)
        self.assertIn("kerugian", copy)

        stat = next(
            row for row in payload["headline_stats"]
            if set(row.get("source_paths", [])) == DISASTER_SOURCE_PATHS
        )
        self.assertEqual("285", stat["value"])
        self.assertIn("19", stat["detail"])
        self.assertIn("15", stat["detail"])
        self.assertIn("2025", stat["detail"])
        self.assertIn("bukan nol", stat["detail"].casefold())


if __name__ == "__main__":
    unittest.main()
