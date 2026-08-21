from __future__ import annotations

import unittest

from scripts import probe_milestone26_population_empty_stats_semantics as probe


class M26PopulationEmptyStatsSemanticsTests(unittest.TestCase):
    def test_contract_targets_only_frozen_one_cell_anomaly(self):
        contract = probe.load_contract()
        self.assertEqual(contract["target"]["geography_id"], "idn.13.1377")
        self.assertEqual(contract["target"]["partition_index"], 1)
        self.assertEqual(contract["target"]["selected_cell_count"], 1)
        self.assertEqual(contract["image_server_repeat_probe"]["repeat_count"], 3)
        self.assertEqual(contract["mapserver_reference_probe"]["repeat_count"], 3)
        self.assertFalse(contract["empty_statistics_global_semantics_authorized"])
        self.assertFalse(contract["stage1_population_production_extraction_authorized"])
        self.assertFalse(contract["risk_synthesis_authorized"])

    def test_exact_center_derivation_requires_one_rerasterized_cell(self):
        partition = {
            "bbox": [1000.0, 1900.0, 1100.0, 2000.0],
            "window_width": 1,
            "window_height": 1,
            "candidate": {
                "geometry_sha256": "synthetic",
                "arcgis_geometry": {
                    "rings": [[[1000.0, 2000.0], [1100.0, 2000.0], [1100.0, 1900.0], [1000.0, 1900.0], [1000.0, 2000.0]]],
                    "spatialReference": {"wkid": 3395},
                },
            },
        }
        center, evidence = probe.derive_exact_native_center(partition)
        self.assertEqual(center, [1050.0, 1950.0])
        self.assertEqual(evidence["rerasterized_selected_cell_count"], 1)
        self.assertEqual(evidence["selected_row"], 0)
        self.assertEqual(evidence["selected_col"], 0)

    def test_decision_qualifies_exact_cell_only_when_both_transports_repeat_no_value(self):
        image = [{"transport_ok": True, "classification": "empty_statistics"} for _ in range(3)]
        maps = [
            {
                "transport_ok": True,
                "finite_accepted_pixel_value_count": 0,
                "accepted_result_geometry_matches_exact_center": True,
            }
            for _ in range(3)
        ]
        self.assertEqual(probe.decide(image, maps), "deterministic_no_valid_source_value_for_exact_native_cell")

    def test_decision_calls_mixed_image_shape_transient(self):
        image = [
            {"transport_ok": True, "classification": "empty_statistics"},
            {"transport_ok": True, "classification": "standard"},
            {"transport_ok": True, "classification": "empty_statistics"},
        ]
        maps = [
            {
                "transport_ok": True,
                "finite_accepted_pixel_value_count": 0,
                "accepted_result_geometry_matches_exact_center": True,
            }
            for _ in range(3)
        ]
        self.assertEqual(probe.decide(image, maps), "transient_image_server_empty_statistics")

    def test_decision_blocks_transport_disagreement(self):
        image = [{"transport_ok": True, "classification": "empty_statistics"} for _ in range(3)]
        maps = [
            {
                "transport_ok": True,
                "finite_accepted_pixel_value_count": count,
                "accepted_result_geometry_matches_exact_center": True,
            }
            for count in (0, 1, 1)
        ]
        self.assertEqual(probe.decide(image, maps), "transport_disagreement")

    def test_decision_fails_closed_on_transport_or_geometry_problem(self):
        image = [{"transport_ok": True, "classification": "empty_statistics"} for _ in range(3)]
        maps = [
            {
                "transport_ok": True,
                "finite_accepted_pixel_value_count": 0,
                "accepted_result_geometry_matches_exact_center": True,
            }
            for _ in range(3)
        ]
        broken_transport = [dict(row) for row in image]
        broken_transport[1]["transport_ok"] = False
        self.assertEqual(probe.decide(broken_transport, maps), "inconclusive")

        broken_geometry = [dict(row) for row in maps]
        broken_geometry[2]["accepted_result_geometry_matches_exact_center"] = False
        self.assertEqual(probe.decide(image, broken_geometry), "inconclusive")


if __name__ == "__main__":
    unittest.main()
