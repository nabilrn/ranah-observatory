#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/milestone8/source_text/appendix-candidates/sumbar-source-pages-096-098.txt"
OUTPUT = ROOT / "data/analysis/quasi_causal/m8-preperiod-real-grdp-2005-2009.csv"
MANIFEST = ROOT / "data/manifests/milestone8_preperiod_grdp.json"

ROWS = [
    ("idn.13.1301", "Kepulauan Mentawai", "1. Kepulauan Mentawai"),
    ("idn.13.1302", "Pesisir Selatan", "2. Pesisir Selatan"),
    ("idn.13.1303", "Solok", "3. Solok"),
    ("idn.13.1304", "Sijunjung", "4. Sijunjung"),
    ("idn.13.1305", "Tanah Datar", "5. Tanah Datar"),
    ("idn.13.1306", "Padang Pariaman", "6. Padang Pariaman"),
    ("idn.13.1307", "Agam", "7. Agam"),
    ("idn.13.1308", "Lima Puluh Kota", "8. 50 Kota"),
    ("idn.13.1309", "Pasaman", "9. Pasaman"),
    ("idn.13.1310", "Solok Selatan", "10. Solok Selatan"),
    ("idn.13.1311", "Dharmasraya", "11. Dharmasraya"),
    ("idn.13.1312", "Pasaman Barat", "12. Pasaman Barat"),
    ("idn.13.1371", "Kota Padang", "71. Padang"),
    ("idn.13.1372", "Kota Solok", "72. Solok"),
    ("idn.13.1373", "Kota Sawahlunto", "73. Sawahlunto"),
    ("idn.13.1374", "Kota Padang Panjang", "74. Padang Panjang"),
    ("idn.13.1375", "Kota Bukittinggi", "75. Bukittinggi"),
    ("idn.13.1376", "Kota Payakumbuh", "76. Payakumbuh"),
    ("idn.13.1377", "Kota Pariaman", "77. Pariaman"),
]
YEARS = [2005, 2006, 2007, 2008, 2009]
NUMBER = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_id_number(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def extract_page(text: str, page_no: int) -> str:
    marker = f"===== PDF PAGE {page_no} ====="
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"missing page marker {page_no}")
    next_marker = text.find("===== PDF PAGE ", start + len(marker))
    return text[start : next_marker if next_marker >= 0 else len(text)]


def parse_rows(block: str) -> list[dict[str, Any]]:
    if "Tabel/Table 22" not in block:
        raise RuntimeError("pre-period page lost Table 22 identifier")
    if "PDRB Atas Dasar Harga Konstan 2000 Menurut Kabupaten/Kota, 2005 - 2009" not in block:
        raise RuntimeError("pre-period page lost constant-2000 table title")
    if "(Jutaan/Million Rupiahs)" not in block:
        raise RuntimeError("pre-period page lost million-rupiah unit contract")

    positions: list[tuple[int, tuple[str, str, str]]] = []
    cursor = 0
    for row in ROWS:
        label = row[2]
        pos = block.find(label, cursor)
        if pos < 0:
            raise RuntimeError(f"missing expected Table 22 row label {label!r}")
        positions.append((pos, row))
        cursor = pos + len(label)
    end = block.find("Jumlah/Total", positions[-1][0])
    if end < 0:
        raise RuntimeError("missing Table 22 total-row boundary")

    observations: list[dict[str, Any]] = []
    for idx, (pos, (geography_id, geography_name, source_label)) in enumerate(positions):
        stop = positions[idx + 1][0] if idx + 1 < len(positions) else end
        region = block[pos:stop]
        values = NUMBER.findall(region)
        if len(values) != 5:
            raise RuntimeError(f"{source_label}: expected five Table 22 values, got {values}")
        for year, source_value in zip(YEARS, values, strict=True):
            observations.append(
                {
                    "geography_id": geography_id,
                    "geography_name": geography_name,
                    "year": year,
                    "real_grdp_constant_2000_million_rupiah": parse_id_number(source_value),
                    "source_value": source_value,
                    "source_table": "22",
                    "source_pdf_page": 97,
                    "revision_status": "revised" if year == 2008 else "preliminary" if year == 2009 else "unspecified",
                }
            )
    return observations


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "geography_id",
        "geography_name",
        "year",
        "real_grdp_constant_2000_million_rupiah",
        "source_value",
        "source_table",
        "source_pdf_page",
        "revision_status",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    rows = parse_rows(extract_page(text, 97))
    if len(rows) != 95:
        raise RuntimeError(f"expected 95 pre-period observations, got {len(rows)}")
    keys = {(row["geography_id"], row["year"]) for row in rows}
    if len(keys) != 95:
        raise RuntimeError("duplicate pre-period geography-year keys")
    if any(float(row["real_grdp_constant_2000_million_rupiah"]) <= 0 for row in rows):
        raise RuntimeError("pre-period table contains non-positive GRDP")

    write_csv(rows)
    manifest = {
        "schema": "ranah-observatory/milestone8-preperiod-grdp/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "source_plan_id": "m8_grdp_pre",
        "source_text_path": str(SOURCE.relative_to(ROOT)),
        "source_text_sha256": sha256(SOURCE),
        "source_table": "22",
        "source_pdf_page": 97,
        "price_basis": "constant_2000",
        "unit": "million_rupiah",
        "years": YEARS,
        "geography_count": 19,
        "observation_count": len(rows),
        "revision_status": {"2008": "revised", "2009": "preliminary"},
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "national_scanned_source_required_for_primary_panel": False,
        "ocr_performed": False,
        "overlap_2009_reconciled": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
