from __future__ import annotations

import csv
import unittest
from pathlib import Path

from scripts.audit_milestone15_causal_evidence_expansion import audit

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "data/analysis/engine/causal_evidence_v1/m15-causal-evidence-library.csv"


class Milestone15Tests(unittest.TestCase):
    def test_audit_is_clean(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone15_complete"])
        self.assertEqual(report["entry_count"], 3)
        self.assertEqual(report["new_causal_model_fit_count"], 0)

    def test_blocked_candidates_remain_unfit(self) -> None:
        with LIBRARY.open("r", encoding="utf-8", newline="") as handle:
            rows = {row["entry_id"]: row for row in csv.DictReader(handle)}
        for entry_id in ("m15_e2_rainfall_unemployment", "m15_e3_covid_structural_exposure"):
            self.assertEqual(rows[entry_id]["entry_state"], "not_identification_ready")
            self.assertEqual(rows[entry_id]["model_fit_authorized"], "False")
            self.assertEqual(rows[entry_id]["new_model_fit_in_m15"], "False")
            self.assertEqual(rows[entry_id]["causal_claim_authorized"], "False")


if __name__ == "__main__":
    unittest.main()
