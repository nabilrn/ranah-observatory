from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_milestone26_event_impact_transport_candidate.py"


class Milestone26EventImpactTransportCandidateTest(unittest.TestCase):
    def test_machine_readable_transport_stays_fail_closed(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["source_id"], "bnpb_event_impact_table")
        self.assertEqual(
            result["candidate_status"],
            "official_machine_readable_transport_verified_retrieval_contract_pending",
        )
        self.assertTrue(result["official_machine_readable_surface_verified"])
        self.assertTrue(result["query_operation_exposed"])
        self.assertFalse(result["event_rows_retrieved"])
        self.assertFalse(result["numeric_extraction_authorized"])
        self.assertFalse(result["event_panel_materialization_authorized"])
        self.assertFalse(result["risk_synthesis_authorized"])
        self.assertEqual(result["unresolved_contract_count"], 8)


if __name__ == "__main__":
    unittest.main()
