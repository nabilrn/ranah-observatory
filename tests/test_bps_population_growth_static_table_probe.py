from __future__ import annotations

import unittest

from scripts.probe_bps_population_growth_static_table import is_relevant_title, normalize_text


class BpsPopulationGrowthStaticTableProbeTests(unittest.TestCase):
    def test_relevant_title_requires_growth_and_kabupaten_kota(self) -> None:
        self.assertTrue(
            is_relevant_title(
                "Penduduk, Laju Pertumbuhan Penduduk, Distribusi Persentase Penduduk "
                "Menurut Kabupaten/Kota di Provinsi Sumatera Barat, 2020"
            )
        )
        self.assertFalse(is_relevant_title("Laju Pertumbuhan Penduduk Sumatera Barat"))
        self.assertFalse(is_relevant_title("Jumlah Penduduk Menurut Kabupaten/Kota"))

    def test_normalize_text_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_text("  laju\n  pertumbuhan  "), "laju pertumbuhan")


if __name__ == "__main__":
    unittest.main()
