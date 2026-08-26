from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / "site" / "data" / "glossary.json"


class PublicGlossaryTests(unittest.TestCase):
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

    def test_glossary_surface_is_static_and_local(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "site" / "glossary.js").read_text(encoding="utf-8")
        self.assertIn('id="glosarium"', html)
        self.assertIn('src="glossary.js"', html)
        self.assertIn('href="glossary.css"', html)
        self.assertIn('data/glossary.json', js)
        self.assertNotIn('fetch("https://', js)
        self.assertNotIn("fetch('https://", js)


if __name__ == "__main__":
    unittest.main()
