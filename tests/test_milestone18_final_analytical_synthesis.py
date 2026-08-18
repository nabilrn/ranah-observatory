from __future__ import annotations

import csv
import unittest
from pathlib import Path

from scripts.audit_milestone18_final_analytical_synthesis import audit

ROOT = Path(__file__).resolve().parents[1]
RQ = ROOT / "data/analysis/engine/final_synthesis_v1/m18-research-question-readiness.csv"
CLAIMS = ROOT / "data/analysis/engine/final_synthesis_v1/m18-claim-boundary-ledger.csv"
NODES = ROOT / "data/analysis/engine/final_synthesis_v1/m18-evidence-nodes.csv"
EDGES = ROOT / "data/analysis/engine/final_synthesis_v1/m18-evidence-edges.csv"


class Milestone18Tests(unittest.TestCase):
    def test_completion_audit_is_clean(self) -> None:
        report = audit()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["milestone18_complete"])
        self.assertTrue(report["phase2_analytical_engine_complete"])
        self.assertFalse(report["scientific_research_agenda_complete"])
        self.assertEqual(report["evidence_node_count"], 9)
        self.assertEqual(report["research_question_count"], 5)
        self.assertEqual(report["blocked_claim_count"], 9)

    def test_research_questions_are_not_overclaimed(self) -> None:
        with RQ.open("r", encoding="utf-8", newline="") as handle:
            rows = {row["research_question_id"]: row for row in csv.DictReader(handle)}
        self.assertEqual(rows["RQ1"]["readiness_state"], "bounded_partial")
        self.assertEqual(rows["RQ2"]["readiness_state"], "bounded_answer")
        self.assertEqual(rows["RQ3"]["readiness_state"], "bounded_partial")
        self.assertEqual(rows["RQ4"]["readiness_state"], "bounded_answer")
        self.assertEqual(rows["RQ5"]["readiness_state"], "not_action_ready")
        self.assertTrue(all(row["fully_resolved"] == "False" for row in rows.values()))

    def test_blocked_claims_remain_blocked(self) -> None:
        with CLAIMS.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row["status"] == "not_authorized" for row in rows))
        text = "\n".join(row["blocked_claim"] for row in rows)
        self.assertIn("monetary value", text)
        self.assertIn("rainfall association causes unemployment gaps", text)
        self.assertIn("composite disaster-risk score", text)
        self.assertIn("policy treatment effect or forecast", text)

    def test_graph_dependencies_are_noncausal_and_uncertainty_annotated(self) -> None:
        with NODES.open("r", encoding="utf-8", newline="") as handle:
            nodes = list(csv.DictReader(handle))
        with EDGES.open("r", encoding="utf-8", newline="") as handle:
            edges = list(csv.DictReader(handle))
        self.assertEqual(len(nodes), 9)
        self.assertEqual(len(edges), 18)
        self.assertTrue(all(row["causal_edge"] == "False" for row in edges))
        uncertainty_edges = [row for row in edges if row["edge_type"] == "uncertainty_annotation"]
        self.assertEqual(len(uncertainty_edges), 8)
        self.assertEqual({row["from_node"] for row in uncertainty_edges}, {row["node_id"] for row in nodes} - {"uncertainty_evidence_strength"})


if __name__ == "__main__":
    unittest.main()
