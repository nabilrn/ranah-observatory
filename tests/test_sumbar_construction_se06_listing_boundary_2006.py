from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_sumbar_construction_se06_listing_boundary_2006 import validate


class SumbarConstructionSE06ListingBoundary2006Test(unittest.TestCase):
    def test_se06_population_partitions_do_not_identify_annual_frame(self) -> None:
        result = validate()
        self.assertEqual(result["se06_full_construction_population"], 4504)
        self.assertEqual(result["se06_legal_status_construction"], 1379)
        self.assertEqual(result["se06_nonlegal_status_construction"], 3125)
        self.assertEqual(result["annual_2006_count"], 2664)
        self.assertFalse(result["annual_matches_full_population"])
        self.assertFalse(result["annual_matches_legal_only"])
        self.assertFalse(result["annual_matches_nonlegal_only"])
        self.assertFalse(result["exact_annual_frame_mapping_recovered"])
        self.assertFalse(result["causal_claim_authorized"])


if __name__ == "__main__":
    unittest.main()
