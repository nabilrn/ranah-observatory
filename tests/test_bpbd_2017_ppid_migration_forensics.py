from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_bpbd_2017_ppid_migration_forensics.py"


class BPBD2017PPIDMigrationForensicsTest(unittest.TestCase):
    def test_forensics_preserve_m52_block(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["legacy_semantic_collision_frozen"])
        self.assertTrue(result["active_inventory_exact_title_no_hit"])
        self.assertFalse(result["raw_official_pdf_recovered"])
        self.assertFalse(result["record_8604_to_current_uuid_mapping_recovered"])
        self.assertFalse(result["m52_trigger_satisfied"])


if __name__ == "__main__":
    unittest.main()
