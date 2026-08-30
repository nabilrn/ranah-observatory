from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicReadabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        self.dashboard_js = (ROOT / "site" / "dashboard.js").read_text(encoding="utf-8")
        self.dashboard_css = (ROOT / "site" / "dashboard.css").read_text(encoding="utf-8")

    def test_first_screen_is_data_first(self) -> None:
        self.assertLess(self.html.index('id="key-findings-title"'), self.html.index('id="snapshot-title"'))
        for token in (
            "Empat hal yang langsung terlihat dari data",
            "Konteks data & pengujian",
            "Detail pendukung, bukan skor Sumatera Barat",
        ):
            self.assertIn(token, self.html)

    def test_navigation_keeps_all_public_surfaces_reachable(self) -> None:
        for view in ("ringkasan", "daerah", "katalog", "riset", "latar"):
            self.assertIn(f'data-view="{view}"', self.html)
            self.assertIn(f'data-view-target="{view}"', self.html)
            self.assertIn(f'aria-controls="{view}"', self.html)
        self.assertIn('tabindex="-1"', self.html)
        self.assertIn('aria-current="page"', self.dashboard_js)

    def test_negative_and_blocked_results_remain_visible(self) -> None:
        self.assertIn('data-view="riset"', self.html)
        self.assertIn('id="batas"', self.html)
        self.assertIn("Semua hasil tetap ditampilkan, termasuk analisis yang gagal uji", self.html)
        self.assertIn('"forecast-failure"', self.dashboard_js)
        self.assertIn("Gagal uji", self.dashboard_js)
        self.assertIn("<strong>Batas:</strong>", self.dashboard_js)

    def test_loading_failure_and_local_fetch_contract(self) -> None:
        self.assertIn("Temuan utama gagal dimuat", self.dashboard_js)
        self.assertIn('setAttribute("role", "alert")', self.dashboard_js)
        self.assertIn('fetch(DASHBOARD_OVERVIEW_URL', self.dashboard_js)
        self.assertNotIn('fetch("https://', self.dashboard_js)
        self.assertNotIn("fetch('https://", self.dashboard_js)

    def test_desktop_compact_mobile_scroll_contract(self) -> None:
        self.assertIn("height: 100vh", self.dashboard_css)
        self.assertIn("overflow: hidden", self.dashboard_css)
        self.assertIn("@media (max-width: 700px)", self.dashboard_css)
        self.assertIn("min-height: 100vh", self.dashboard_css)
        self.assertIn("overflow: auto", self.dashboard_css)


if __name__ == "__main__":
    unittest.main()
