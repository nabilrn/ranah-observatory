from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_bps_held_panel import build_held  # noqa: E402


class BPSHeldPanelTests(unittest.TestCase):
    def test_builder_preserves_only_held_internet_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry.csv"
            registry.write_text(
                "panel_series_id,canonical_promotion_status\n"
                "internet_person_5plus,pending_indicator_universe_review\n"
                "labor_tpt_regency,canonical_ready\n",
                encoding="utf-8",
            )
            source = root / "source.csv"
            fields = [
                "panel_series_id", "indicator_id", "bps_var_id", "bps_turvar_id",
                "canonical_geography_id", "bps_th_label", "value",
            ]
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for year in range(2018, 2026):
                    for index in range(20):
                        writer.writerow(
                            {
                                "panel_series_id": "internet_person_5plus",
                                "indicator_id": "internet_access",
                                "bps_var_id": "320",
                                "bps_turvar_id": "595",
                                "canonical_geography_id": f"geo-{index}",
                                "bps_th_label": str(year),
                                "value": "50.0",
                            }
                        )
                writer.writerow(
                    {
                        "panel_series_id": "labor_tpt_regency",
                        "indicator_id": "unemployment_rate",
                        "bps_var_id": "139",
                        "bps_turvar_id": "0",
                        "canonical_geography_id": "geo-0",
                        "bps_th_label": "2025",
                        "value": "4.0",
                    }
                )
            rows, manifest = build_held(source, registry)
            self.assertEqual(160, len(rows))
            self.assertEqual(["internet_person_5plus"], manifest["held_series"])
            self.assertEqual(["internet_access"], manifest["indicator_ids"])
            self.assertEqual(["320"], manifest["source_var_ids"])
            self.assertEqual(20, manifest["canonical_geography_count"])


if __name__ == "__main__":
    unittest.main()
