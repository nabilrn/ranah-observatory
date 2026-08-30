from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_final_model_testing import validate


class FinalModelTestingTest(unittest.TestCase):
    def test_model_testing_contract_is_preserved(self) -> None:
        result = validate()
        self.assertTrue(result["model_testing_gate_passed"])
        self.assertEqual(result["m11_crossfit_predictions"], 342)
        self.assertEqual(result["m11_benchmark_qualified_targets"], 3)
        self.assertEqual(result["m19_out_of_time_predictions"], 285)
        self.assertEqual(result["m19_forecast_qualified_targets"], 0)
        self.assertEqual(result["m19_forecast_blocked_targets"], 3)
        self.assertFalse(result["posthoc_algorithm_search_performed"])


if __name__ == "__main__":
    unittest.main()
