from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_public_product import DEFAULT_OVERVIEW, EXPECTED_BLOCKED, validate

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / "site" / "data" / "glossary.json"


class PublicProductTests(unittest.TestCase):
    def test_claim_gated_overview_is_valid(self) -> None:
        result = validate()
        self.assertEqual(result["blocked_boundaries"], 9)
        self.assertGreaterEqual(result["stories"], 8)
        self.assertGreaterEqual(result["headline_stats"], 4)

    def test_all_blocked_claims_are_visible(self) -> None:
        payload = json.loads(DEFAULT_OVERVIEW.read_text(encoding="utf-8"))
        actual = {row["claim_id"] for row in payload["boundaries"]}
        self.assertEqual(actual, EXPECTED_BLOCKED)

    def test_site_is_static_and_local_data_driven(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
        glossary_js = (ROOT / "site" / "glossary.js").read_text(encoding="utf-8")
        self.assertIn('src="app.js"', html)
        self.assertIn('src="glossary.js"', html)
        self.assertIn('href="styles.css"', html)
        self.assertIn('href="glossary.css"', html)
        self.assertIn('id="glosarium"', html)
        self.assertIn('data/overview.json', js)
        self.assertIn('data/glossary.json', glossary_js)
        self.assertNotIn("fetch(\"https://", js)
        self.assertNotIn("fetch('https://", js)
        self.assertNotIn("fetch(\"https://", glossary_js)
        self.assertNotIn("fetch('https://", glossary_js)

    def test_glossary_explains_core_epistemic_terms(self) -> None:
        payload = json.loads(GLOSSARY.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "ranah-observatory/public-glossary/v1")
        terms = {row["technical"]: row for row in payload["terms"]}
        required = {
            "observed",
            "model_estimate",
            "benchmark",
            "trajectory",
            "robust trajectory",
            "statistical association",
            "causal effect",
            "context_only",
            "held / not qualified",
            "empirical favorable reference",
        }
        self.assertEqual(set(terms), required)
        for row in terms.values():
            self.assertTrue(row["plain"].strip())
            self.assertTrue(row["not_mean"].strip())

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


if __name__ == "__main__":
    unittest.main()
