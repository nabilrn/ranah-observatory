from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from materialize_bps_comparative_panel import (  # noqa: E402
    EXPECTED_INDICATORS,
    EXPECTED_YEARS,
    current_provinces,
    load_series,
    transform_value,
)
from probe_bps_comparative_panel import value_of  # noqa: E402


class Milestone5ComparativePanelTests(unittest.TestCase):
    def test_current_geography_contract_is_exactly_38_provinces(self) -> None:
        by_source, by_id = current_provinces(ROOT / "data" / "registries" / "geographies.csv")
        self.assertEqual(38, len(by_source))
        self.assertEqual(38, len(by_id))
        self.assertEqual("idn.13", by_source["1300"]["geography_id"])

    def test_series_contract_is_exactly_six_2024_2025_indicators(self) -> None:
        rows = load_series(ROOT / "data" / "registries" / "bps_comparative_panel_series.csv")
        self.assertEqual(EXPECTED_INDICATORS, tuple(row["indicator_id"] for row in rows))
        self.assertEqual((2024, 2025), EXPECTED_YEARS)
        self.assertNotIn("mobile_phone_use", {row["indicator_id"] for row in rows})

    def test_zero_valued_source_selector_id_is_not_erased(self) -> None:
        self.assertEqual("0", value_of({"val": 0, "label": "Tahun"}))
        self.assertEqual("0", value_of({"val": "0", "label": "Tahun"}))

    def test_grdp_thousand_rupiah_conversion_is_exact(self) -> None:
        self.assertEqual(12.345, transform_value("12345", "divide_1000"))


if __name__ == "__main__":
    unittest.main()
