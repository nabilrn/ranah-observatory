from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_sumbar_construction_qualification_pre_post_update_boundary.py"


class SumbarConstructionQualificationPrePostUpdateBoundaryTest(unittest.TestCase):
    def test_pre_update_baseline_is_frozen_without_premature_comparison(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["pre_update_district_rows"], 16)
        self.assertEqual(result["pre_update_total_establishments"], 2882)
        self.assertEqual(result["post_update_opac_record_id"], "111.0614.1380")
        self.assertFalse(result["post_update_raw_pdf_acquired"])
        self.assertFalse(result["pre_post_comparison_authorized"])
        self.assertFalse(result["causal_revision_link_proven"])


if __name__ == "__main__":
    unittest.main()
