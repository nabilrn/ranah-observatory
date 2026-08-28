from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_se06_listing_boundary_2006 import validate


class SumbarConstructionSE06ListingBoundary2006Test(unittest.TestCase):
    def test_se06_listing_diverges_without_opening_frame_gate(self) -> None:
        result = validate()
        self.assertEqual(result["se06_construction_listing"], 4504)
        self.assertEqual(result["annual_2006_count"], 2664)
        self.assertEqual(result["same_year_difference"], -1840)
        self.assertFalse(result["annual_count_equals_full_se06_listing"])
        self.assertFalse(result["annual_count_as_sampling_frame_authorized"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
