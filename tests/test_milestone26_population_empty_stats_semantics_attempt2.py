from __future__ import annotations

import unittest

from scripts import probe_milestone26_population_empty_stats_semantics_attempt2 as probe


class M26PopulationEmptyStatsAttempt2Tests(unittest.TestCase):
    def test_contract_preserves_exact_target_and_closed_boundaries(self):
        contract = probe.load_contract()
        self.assertEqual(contract["target"]["geography_id"], "idn.13.1377")
        self.assertEqual(contract["target"]["partition_index"], 1)
        self.assertEqual(contract["target"]["selected_cell_count"], 1)
        self.assertEqual(contract["recovery_gate"]["repeat_count_per_service"], 2)
        self.assertEqual(contract["semantic_probe"]["image_server_repeat_count"], 3)
        self.assertEqual(contract["semantic_probe"]["mapserver_repeat_count"], 3)
        self.assertFalse(contract["stage1_population_production_extraction_authorized"])
        self.assertFalse(contract["empty_statistics_global_semantics_authorized"])
        self.assertFalse(contract["risk_synthesis_authorized"])

    def test_prior_attempt_is_exactly_the_frozen_521_outage(self):
        prior = probe.verify_prior_attempt(probe.load_contract())
        self.assertEqual(prior["decision"], "inconclusive")
        self.assertEqual([row["response"]["status"] for row in prior["image_server_repeats"]], [521, 521, 521])
        self.assertEqual([row["response"]["status"] for row in prior["mapserver_repeats"]], [521, 521, 521])
        self.assertFalse(prior["stage1_population_production_extraction_authorized"])

    def test_recovery_gate_requires_exact_two_successes_from_each_service(self):
        rows = [
            {"service": "image-server", "transport_ok": True},
            {"service": "image-server", "transport_ok": True},
            {"service": "mapserver", "transport_ok": True},
            {"service": "mapserver", "transport_ok": True},
        ]
        self.assertTrue(probe.recovery_gate_passed(rows, 2))

        incomplete = rows[:-1]
        self.assertFalse(probe.recovery_gate_passed(incomplete, 2))

        failed = [dict(row) for row in rows]
        failed[2]["transport_ok"] = False
        self.assertFalse(probe.recovery_gate_passed(failed, 2))

    def test_attempt2_decision_space_keeps_no_global_semantics_promotion(self):
        contract = probe.load_contract()
        self.assertEqual(
            set(contract["attempt2_decisions"]),
            {
                "service_not_recovered",
                "deterministic_no_valid_source_value_for_exact_native_cell",
                "transient_image_server_empty_statistics",
                "transport_disagreement",
                "inconclusive",
            },
        )
        self.assertFalse(contract["substantive_value_promotion_authorized"])
        self.assertFalse(contract["numeric_aggregation_authorized"])


if __name__ == "__main__":
    unittest.main()
