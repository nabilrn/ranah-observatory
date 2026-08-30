from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRAJECTORY_PATH = ROOT / "data/validation/historical/public_finance_2000/bps_construction_establishment_count_trajectory_2002_2006.json"
SE06_PATH = ROOT / "data/validation/historical/public_finance_2000/bps_construction_se06_listing_boundary_2006.json"
SEMANTIC_PATH = ROOT / "data/validation/historical/public_finance_2000/bps_construction_qualification_semantic_bridge_boundary_2003_2005.json"
DEFAULT_OUTPUT = ROOT / "site/data/history.json"

SOURCE_PATHS = [
    "data/validation/historical/public_finance_2000/bps_construction_establishment_count_trajectory_2002_2006.json",
    "data/validation/historical/public_finance_2000/bps_construction_se06_listing_boundary_2006.json",
    "data/validation/historical/public_finance_2000/bps_construction_qualification_semantic_bridge_boundary_2003_2005.json",
]


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object JSON: {path}")
    return payload


def build_payload() -> dict[str, Any]:
    trajectory = load_json(TRAJECTORY_PATH)
    se06 = load_json(SE06_PATH)
    semantic = load_json(SEMANTIC_PATH)

    assert trajectory["schema"] == "ranah-observatory/bps-construction-establishment-count-trajectory-2002-2006/v1"
    assert se06["schema"] == "ranah-observatory/bps-construction-se06-listing-boundary-2006/v2"
    assert semantic["schema"] == "ranah-observatory/bps-construction-qualification-semantic-bridge-boundary-2003-2005/v1"

    annual = trajectory["sumatera_barat"]
    series = [
        {
            "year": int(year),
            "value": int(annual[year]["count"]),
            "source_status": annual[year]["status"],
        }
        for year in ("2002", "2003", "2004", "2005", "2006")
    ]

    same_year = se06["same_year_2006_comparison"]
    qualification_2003 = semantic["official_bps_2003_source"]["province_total"]
    candidate_2003 = semantic["arithmetic_three_group_candidate_2003"]["candidate_values"]
    digital_2005 = semantic["official_bps_2005_digital_surface"]

    return {
        "schema": "ranah-observatory/public-history/v1",
        "version": "0.1.0-post",
        "language": "id",
        "scope": "Arsip BPS memberi beberapa potongan sejarah sektor konstruksi Sumatera Barat. Angka di bawah ditampilkan sesuai definisi sumbernya; kami tidak menyambungkannya menjadi satu seri panjang jika dasar perbandingannya belum jelas.",
        "source_paths": SOURCE_PATHS,
        "cards": [
            {
                "id": "construction-annual-2002-2006",
                "evidence_state": "context",
                "eyebrow": "Perusahaan konstruksi · 2002–2006",
                "title": "Jumlah perusahaan konstruksi yang dipublikasikan BPS turun dari 2.882 pada 2003 menjadi 2.435 pada 2005.",
                "series": series,
                "unit": "perusahaan",
                "key_fact": {
                    "label": "Perubahan 2003 → 2005",
                    "value": int(trajectory["trajectory"]["2003_to_2005"]["delta_count"]),
                    "percent": float(trajectory["trajectory"]["2003_to_2005"]["delta_percent"]),
                },
                "plain_language": "Seri yang dipublikasikan mencatat 2.779 perusahaan pada 2002, 2.882 pada 2003, 2.837 pada 2004, 2.435 pada 2005, dan 2.664* pada 2006.",
                "caveat": "Penurunan angka publikasi tidak otomatis berarti jumlah usaha nyata turun dengan besaran yang sama. Seri ini tidak boleh dipakai untuk menyimpulkan dampak kebijakan atau bahwa pembaruan direktori 2005 menyebabkan perubahan tersebut.",
            },
            {
                "id": "construction-se06-2006",
                "evidence_state": "context",
                "eyebrow": "Sensus Ekonomi 2006",
                "title": "Dua publikasi BPS untuk 2006 memberi angka berbeda: 2.664 pada survei tahunan dan 4.504 pada listing Sensus Ekonomi.",
                "comparison": {
                    "annual_survey": int(same_year["annual_survey_published_count"]),
                    "se06_full_listing": int(same_year["se06_full_construction_listing"]),
                    "se06_legal": int(same_year["se06_legal_status_construction"]),
                    "se06_nonlegal": int(same_year["se06_nonlegal_status_construction"]),
                    "annual_percent_of_listing": float(same_year["annual_count_as_percent_of_full_listing"]),
                },
                "unit": "usaha/perusahaan",
                "plain_language": "Sensus Ekonomi mencatat 4.504 usaha konstruksi: 1.379 berstatus hukum dan 3.125 tanpa status hukum. Angka survei tahunan untuk tahun yang sama adalah 2.664, sehingga kedua angka itu jelas tidak boleh dianggap mengukur kelompok usaha yang persis sama.",
                "caveat": "Kita belum mengetahui secara pasti daftar usaha mana yang menjadi dasar angka survei tahunan 2.664. Rasio antara 2.664 dan 4.504 juga bukan bukti bahwa survei mengambil sampel sebesar 59,1% dari daftar sensus.",
            },
            {
                "id": "construction-qualification-bridge",
                "evidence_state": "context",
                "eyebrow": "Kelas usaha konstruksi",
                "title": "Rincian kelas usaha tersedia untuk 2003, tetapi belum tersedia dengan definisi yang sebanding untuk 2005.",
                "qualification_2003": {
                    "B": int(qualification_2003["B"]),
                    "M1": int(qualification_2003["M1"]),
                    "M2": int(qualification_2003["M2"]),
                    "K1": int(qualification_2003["K1"]),
                    "K2": int(qualification_2003["K2"]),
                    "K3": int(qualification_2003["K3"]),
                    "total": int(qualification_2003["TOTAL"]),
                },
                "arithmetic_candidate_2003": {
                    "Kecil": int(candidate_2003["Kecil"]),
                    "Menengah": int(candidate_2003["Menengah"]),
                    "Besar": int(candidate_2003["Besar"]),
                    "Jumlah": int(candidate_2003["Jumlah"]),
                },
                "total_2005": int(digital_2005["sumatera_barat_total_2005"]),
                "component_values_2005_recovered": bool(digital_2005["small_medium_large_values_retrievable_under_tested_contract"]),
                "semantic_mapping_verified": bool(digital_2005["semantic_definition_linking_2005_aggregate_labels_to_2003_six_classes_recovered"]),
                "plain_language": "Pada 2003, BPS menerbitkan enam kelas B/M1/M2/K1/K2/K3 dengan total 2.882 perusahaan. Untuk 2005 kita hanya berhasil memastikan total 2.435. Nilai Kecil/Menengah/Besar dan aturan resmi yang menghubungkannya dengan enam kelas 2003 belum ditemukan.",
                "caveat": "K1+K2+K3 = 2.732, M1+M2 = 150, dan B = 0 hanya penjumlahan aritmetika untuk data 2003. Tanpa definisi 2005 yang setara, angka itu tidak boleh dipakai untuk membuat perbandingan komposisi 2003→2005.",
            },
        ],
        "global_boundary": "Bagian sejarah ini hanya menampilkan potongan data yang bisa diperiksa. Kami tidak membuat continuity palsu, tidak merekonstruksi sampling frame (daftar unit dasar survei), tidak membuat bridge/backcast untuk mengisi tahun yang tidak sebanding, tidak menarik kesimpulan kausal, dan tidak memasukkan angka lama ini ke Panel v3 sebagai seri yang dianggap setara.",
        "authorizations": {
            "historical_context_display": True,
            "single_harmonized_series": False,
            "sampling_frame_reconstruction": False,
            "pre_post_qualification_comparison": False,
            "bridge_or_backcast": False,
            "causal_claim": False,
            "panel_v3_integration": False,
        },
    }


def write_output(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    payload = build_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bounded public historical context")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = write_output(args.output)
    print(json.dumps({"cards": len(payload["cards"]), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
