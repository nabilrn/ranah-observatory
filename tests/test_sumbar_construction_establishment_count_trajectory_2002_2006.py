from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_establishment_count_trajectory_2002_2006 import validate


class SumbarConstructionEstablishmentCountTrajectory2002To2006Test(unittest.TestCase):
    def test_published_counts_bind_2003_without_opening_frame_gate(self) -> None:
        result = validate()
        self.assertTrue(result["published_establishment_trajectory_confirmed"])
        self.assertEqual(result["sumbar_2003_count"], 2882)
        self.assertEqual(result["sumbar_2005_count"], 2435)
        self.assertTrue(result["qualification_2003_exact_match"])
        self.assertEqual(result["delta_2003_to_2005"], -447)
        self.assertFalse(result["sampling_frame_equivalence_authorized"])
        self.assertFalse(result["frame_change_quantification_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
