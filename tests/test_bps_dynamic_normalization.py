from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from normalize_bps_dynamic import (  # noqa: E402
    BPSDynamicNormalizationError,
    normalize_dynamic_payload,
)


class BPSDynamicNormalizationTests(unittest.TestCase):
    def test_reconstructs_keys_from_metadata_without_fixed_width_parsing(self) -> None:
        payload = {
            "status": "OK",
            "data-availability": "available",
            "labelvervar": "Kabupaten/Kota",
            "var": [
                {
                    "val": 320,
                    "label": "Internet access",
                    "unit": "Persen",
                    "decimal": 2,
                    "def": "",
                    "note": "Susenas",
                    "subj": "Komunikasi",
                }
            ],
            "vervar": [
                {"val": 1301, "label": "Kab. Kepulauan Mentawai"},
                {"val": 1378, "label": "Provinsi Sumatera Barat"},
            ],
            "turvar": [
                {"val": 595, "label": "Pernah Mengakses Internet"},
                {"val": 596, "label": "Tidak Pernah Mengakses Internet"},
            ],
            "tahun": [{"val": 125, "label": "2025"}],
            "turtahun": [{"val": 0, "label": "Tahun"}],
            "datacontent": {
                "13013205951250": 54.01,
                "13013205961250": 45.99,
                "13783205951250": 80.47,
                "13783205961250": 19.53,
            },
        }
        records, diagnostics = normalize_dynamic_payload(payload)
        self.assertEqual(4, len(records))
        self.assertEqual(0, diagnostics["missing_combinations"])
        mentawai_yes = next(
            row
            for row in records
            if row["bps_vervar_id"] == "1301" and row["bps_turvar_id"] == "595"
        )
        self.assertEqual(54.01, mentawai_yes["value"])
        self.assertEqual("2025", mentawai_yes["bps_th_label"])
        self.assertEqual("13013205951250", mentawai_yes["source_key"])

    def test_preserves_subperiod_dimension(self) -> None:
        payload = {
            "status": "OK",
            "data-availability": "available",
            "labelvervar": "Provinsi",
            "var": [{"val": 129, "label": "TPT", "unit": "Persen"}],
            "vervar": [{"val": 1, "label": "Sumatera Barat"}],
            "turvar": [{"val": "0", "label": "Tidak ada"}],
            "tahun": [{"val": 125, "label": "2025"}],
            "turtahun": [
                {"val": 66, "label": "Februari"},
                {"val": 67, "label": "Agustus"},
            ],
            "datacontent": {"1129012566": 5.69, "1129012567": 5.62},
        }
        records, diagnostics = normalize_dynamic_payload(payload)
        self.assertEqual(["Februari", "Agustus"], [row["bps_turth_label"] for row in records])
        self.assertEqual([5.69, 5.62], [row["value"] for row in records])
        self.assertEqual(2, diagnostics["observed_values"])

    def test_missing_combinations_are_diagnostic_not_fabricated(self) -> None:
        payload = {
            "status": "OK",
            "data-availability": "available",
            "labelvervar": "Kabupaten/Kota",
            "var": [{"val": 141, "label": "TPAK", "unit": ""}],
            "vervar": [{"val": 1301, "label": "Mentawai"}, {"val": 1302, "label": "Pesisir Selatan"}],
            "turvar": [{"val": 0, "label": "Tidak ada"}],
            "tahun": [{"val": 116, "label": "2016"}],
            "turtahun": [{"val": 0, "label": "Tahun"}],
            "datacontent": {},
        }
        records, diagnostics = normalize_dynamic_payload(payload)
        self.assertEqual([], records)
        self.assertEqual(2, diagnostics["missing_combinations"])

    def test_rejects_unexplained_datacontent_keys(self) -> None:
        payload = {
            "status": "OK",
            "data-availability": "available",
            "labelvervar": "Provinsi",
            "var": [{"val": 1, "label": "X", "unit": ""}],
            "vervar": [{"val": 1, "label": "Y"}],
            "turvar": [{"val": 0, "label": "None"}],
            "tahun": [{"val": 1, "label": "Year"}],
            "turtahun": [{"val": 0, "label": "Year"}],
            "datacontent": {"not-a-reconstructed-key": 1},
        }
        with self.assertRaises(BPSDynamicNormalizationError):
            normalize_dynamic_payload(payload)


if __name__ == "__main__":
    unittest.main()
