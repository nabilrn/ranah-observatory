from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_public_readiness import DEFAULT_PUBLIC, validate

ROOT = Path(__file__).resolve().parents[1]


class PublicReadinessTests(unittest.TestCase):
    def test_readiness_contract_matches_m18(self) -> None:
        result = validate()
        self.assertEqual(result["questions"], 5)
        self.assertEqual(result["fully_resolved"], 0)
        self.assertEqual(result["not_action_ready"], 1)

    def test_action_question_stays_non_recommendation(self) -> None:
        payload = json.loads(DEFAULT_PUBLIC.read_text(encoding="utf-8"))
        action = next(row for row in payload["questions"] if row["id"] == "RQ5")
        self.assertEqual(action["readiness_state"], "not_action_ready")
        self.assertFalse(action["fully_resolved"])
        copy = " ".join(
            action[field] for field in ("current_answer", "limitation", "next_evidence")
        ).casefold()
        self.assertIn("belum", copy)
        self.assertIn("kebijakan", copy)
        self.assertTrue("ranking" in copy or "meranking" in copy)

    def test_readiness_surface_is_static_and_snapshot_count_is_current(self) -> None:
        html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "site" / "readiness.js").read_text(encoding="utf-8")
        mobile_css = (ROOT / "site" / "mobile.css").read_text(encoding="utf-8")
        self.assertIn('id="status-riset"', html)
        self.assertIn('src="readiness.js"', html)
        self.assertIn('href="readiness.css"', html)
        self.assertIn('href="mobile.css"', html)
        self.assertIn("Lima angka penting dari data yang sudah diperiksa", html)
        self.assertIn('data/readiness.json', js)
        self.assertNotIn('fetch("https://', js)
        self.assertNotIn("fetch('https://", js)
        self.assertIn("@media (max-width: 700px)", mobile_css)
        self.assertIn(".nav", mobile_css)
        self.assertIn("display: flex", mobile_css)


if __name__ == "__main__":
    unittest.main()
