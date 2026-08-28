from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_post_update_opac_detail_transport_boundary.py"


class SumbarConstructionPostUpdateOPACDetailTransportBoundaryTest(unittest.TestCase):
    def test_sso_boundary_keeps_comparison_closed(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["detail_route_sso_gated"])
        self.assertTrue(result["read_route_sso_gated"])
        self.assertFalse(result["alternate_public_transport_recovered"])
        self.assertFalse(result["post_update_comparison_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
