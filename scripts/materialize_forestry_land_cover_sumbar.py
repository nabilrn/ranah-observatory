#!/usr/bin/env python3
"""Materialize official Sumatera Barat land-cover tables for 2022 and 2023.

Source: Kementerian Kehutanan SIGAP official publications. The published
Sumatera Barat tables are province-level and report areas in thousand hectares
for forest-estate functions and APL. They do NOT provide district rows inside
these PDFs, so this materializer must not be represented as kabupaten/kota data.

The source table explicitly excludes water bodies from its calculation and does
not present the Cloud class. Missing / excluded classes are never zero-filled.
Raw PDF bytes are kept below data/raw (gitignored); tracked outputs are a
source-faithful CSV plus a validation/provenance manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data/raw/forestry/land_cover"
OUT_DIR = ROOT / "data/processed/forestry/land_cover"
OUTPUT_CSV = OUT_DIR / "sumbar-land-cover-2022-2023.csv"
MANIFEST = ROOT / "data/manifests/sumbar_forestry_land_cover_2022_2023.json"
DICTIONARY_URL = "https://sigap.kehutanan.go.id/tema-kamus/575"
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"
MAX_PDF_BYTES = 120 * 1024 * 1024

PUBLICATIONS = {
    2022: "https://sigap.kehutanan.go.id/sigap-admin-2026/files/download/rekal-pl-2022.pdf",
    2023: "https://sigap.kehutanan.go.id/sigap-admin-2026/files/download/buku-rekalkulasi-pl-indonesia-tahun-2023.pdf",
}

# Numbering follows the published province tables. Codes and standardized names
# are qualified against the official SIGAP land-cover data dictionary.
CLASSES: dict[int, dict[str, Any]] = {
    1: {"code": "2001", "name": "Hutan Lahan Kering Primer", "group": "forest", "aliases": ["Hutan Lahan Kering Primer"]},
    2: {"code": "2002", "name": "Hutan Lahan Kering Sekunder", "group": "forest", "aliases": ["Hutan Lahan Kering Sekunder"]},
    3: {"code": "2005", "name": "Hutan Rawa Primer", "group": "forest", "aliases": ["Hutan Rawa Primer"]},
    4: {"code": "20051", "name": "Hutan Rawa Sekunder", "group": "forest", "aliases": ["Hutan Rawa Sekunder"]},
    5: {"code": "2004", "name": "Hutan Mangrove Primer", "group": "forest", "aliases": ["Hutan Mangrove Primer"]},
    6: {"code": "20041", "name": "Hutan Mangrove Sekunder", "group": "forest", "aliases": ["Hutan Mangrove Sekunder"]},
    7: {"code": "2006", "name": "Hutan Tanaman", "group": "forest", "aliases": ["Hutan Tanaman*", "Hutan Tanaman"]},
    8: {"code": "2007", "name": "Semak Belukar", "group": "non_forest", "aliases": ["Semak/Belukar", "Semak Belukar"]},
    9: {"code": "20071", "name": "Semak Belukar Rawa", "group": "non_forest", "aliases": ["Semak Belukar Rawa"]},
    10: {"code": "3000", "name": "Savana/ Padang Rumput", "group": "non_forest", "aliases": ["Savana/Rumput", "Savana/Padang Rumput", "Savana/ Padang Rumput"]},
    11: {"code": "2010", "name": "Perkebunan", "group": "non_forest", "aliases": ["Perkebunan"]},
    12: {"code": "20091", "name": "Pertanian Lahan Kering", "group": "non_forest", "aliases": ["Pertanian Lahan Kering"]},
    13: {"code": "20092", "name": "Pertanian Lahan Kering Campur", "group": "non_forest", "aliases": ["Pertanian Lahan Kering Campur"]},
    14: {"code": "20122", "name": "Permukiman Transmigrasi", "group": "non_forest", "aliases": ["Transmigrasi", "Permukiman Transmigrasi"]},
    15: {"code": "20093", "name": "Sawah", "group": "non_forest", "aliases": ["Sawah"]},
    16: {"code": "20094", "name": "Tambak", "group": "non_forest", "aliases": ["Tambak"]},
    17: {"code": "2014", "name": "Lahan Terbuka", "group": "non_forest", "aliases": ["Tanah Terbuka", "Lahan Terbuka"]},
    18: {"code": "20141", "name": "Pertambangan", "group": "non_forest", "aliases": ["Pertambangan"]},
    19: {"code": "2012", "name": "Permukiman", "group": "non_forest", "aliases": ["Permukiman"]},
    20: {"code": "50011", "name": "Rawa", "group": "non_forest", "aliases": ["Rawa"]},
    21: {"code": "20121", "name": "Bandara/ Pelabuhan", "group": "non_forest", "aliases": ["Pelabuhan Udara/Laut", "Bandara/Pelabuhan", "Bandara/ Pelabuhan"]},
}

METRICS = [
    "hk_thousand_ha",
    "hl_thousand_ha",
    "hpt_thousand_ha",
    "hp_thousand_ha",
    "hutan_tetap_thousand_ha",
    "hpk_thousand_ha",
    "kawasan_hutan_thousand_ha",
    "apl_thousand_ha",
    "total_thousand_ha",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_bytes(url: str, *, max_bytes: int) -> tuple[bytes, dict[str, str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise RuntimeError(f"response exceeded {max_bytes} bytes: {url}")
        headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
        return raw, headers, response.geturl()


def qualify_dictionary() -> dict[str, Any]:
    raw, headers, final_url = request_bytes(DICTIONARY_URL, max_bytes=4 * 1024 * 1024)
    text = raw.decode("utf-8", errors="replace")
    folded = re.sub(r"\s+", " ", text).casefold()
    missing = []
    for item in CLASSES.values():
        if item["code"] not in text or item["name"].casefold() not in folded:
            missing.append({"code": item["code"], "name": item["name"]})
    # Two official domain classes are intentionally absent from the province
    # calculation table. Confirm the dictionary still publishes both.
    for code, name in (("5001", "Tubuh Air"), ("2500", "Awan")):
        if code not in text or name.casefold() not in folded:
            missing.append({"code": code, "name": name})
    if missing:
        raise RuntimeError(f"official SIGAP class dictionary contract changed: {missing}")
    return {
        "url": DICTIONARY_URL,
        "resolved_url": final_url,
        "content_type": headers.get("content-type"),
        "sha256": sha256_bytes(raw),
        "qualified_class_count": 23,
    }


def download_publication(year: int, url: str) -> tuple[Path, dict[str, Any]]:
    raw, headers, final_url = request_bytes(url, max_bytes=MAX_PDF_BYTES)
    if not raw.startswith(b"%PDF-"):
        raise RuntimeError(f"official {year} publication is not PDF: {raw[:40]!r}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"rekalkulasi-penutupan-lahan-{year}.pdf"
    path.write_bytes(raw)
    return path, {
        "year": year,
        "url": url,
        "resolved_url": final_url,
        "content_type": headers.get("content-type"),
        "raw_path": path.relative_to(ROOT).as_posix(),
        "raw_committed": False,
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def extract_sumbar_page(pdf_path: Path, year: int) -> tuple[int, str, int]:
    reader = PdfReader(str(pdf_path), strict=False)
    candidates: list[tuple[int, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except Exception:
            text = page.extract_text() or ""
        folded = re.sub(r"\s+", " ", text).casefold()
        if "luas penutupan lahan provinsi sumatera barat" in folded and f"tahun {year}" in folded:
            candidates.append((index, text))
    if len(candidates) != 1:
        raise RuntimeError(f"expected one Sumatera Barat table page for {year}, got {[item[0] for item in candidates]}")
    index, text = candidates[0]
    if "tubuh air" not in text.casefold() or "tidak termasuk dalam penghitungan" not in text.casefold():
        raise RuntimeError(f"{year} Sumbar table no longer carries the water-exclusion footnote")
    return index, text, len(reader.pages)


def parse_source_number(token: str) -> Decimal | None:
    token = token.strip()
    if token == "-":
        return None
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+|\d+", token):
        raise RuntimeError(f"unexpected source numeric token: {token!r}")
    return Decimal(token.replace(".", "").replace(",", "."))


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(value, "f")


def parse_metric_tokens(raw: str, *, context: str) -> list[Decimal | None]:
    tokens = raw.split()
    if len(tokens) != len(METRICS):
        raise RuntimeError(f"{context}: expected {len(METRICS)} metric tokens, got {len(tokens)}: {tokens}")
    return [parse_source_number(token) for token in tokens]


def parse_class_rows(text: str, year: int) -> list[dict[str, Any]]:
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for line in lines:
        match = re.match(r"^\s*(\d{1,2})\s+(.*)$", line)
        if not match:
            continue
        class_number = int(match.group(1))
        if class_number not in CLASSES or class_number in seen:
            continue
        remainder = match.group(2).strip()
        spec = CLASSES[class_number]
        source_label = None
        for alias in sorted(spec["aliases"], key=len, reverse=True):
            if remainder.casefold().startswith(alias.casefold()):
                source_label = remainder[: len(alias)]
                numeric_part = remainder[len(alias):].strip()
                break
        if source_label is None:
            continue
        metrics = parse_metric_tokens(numeric_part, context=f"{year} class {class_number} {source_label}")
        row: dict[str, Any] = {
            "year": year,
            "geography_id": "idn.13",
            "geography_name": "Sumatera Barat",
            "class_number": class_number,
            "class_code": spec["code"],
            "class_name": spec["name"],
            "source_class_label": source_label.rstrip("*"),
            "forest_group": spec["group"],
        }
        row.update(dict(zip(METRICS, metrics, strict=True)))
        rows.append(row)
        seen.add(class_number)
    if seen != set(CLASSES):
        raise RuntimeError(f"{year} class coverage mismatch; missing={sorted(set(CLASSES) - seen)} seen={sorted(seen)}")
    rows.sort(key=lambda item: item["class_number"])
    return rows


def parse_summary_row(text: str, label: str, year: int) -> list[Decimal | None]:
    candidates = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.casefold().startswith(label.casefold()):
            numeric_part = stripped[len(label):].strip()
            try:
                values = parse_metric_tokens(numeric_part, context=f"{year} {label}")
            except RuntimeError:
                continue
            candidates.append(values)
    if len(candidates) != 1:
        raise RuntimeError(f"{year}: expected one parseable {label!r} row, got {len(candidates)}")
    return candidates[0]


def sum_metric(rows: list[dict[str, Any]], metric: str) -> Decimal:
    return sum((row[metric] for row in rows if row[metric] is not None), Decimal("0"))


def validate_rows(rows: list[dict[str, Any]], text: str, year: int) -> dict[str, Any]:
    forest_rows = [row for row in rows if row["forest_group"] == "forest"]
    non_forest_rows = [row for row in rows if row["forest_group"] == "non_forest"]
    reported_forest = parse_summary_row(text, "Jumlah Hutan", year)
    reported_non_forest = parse_summary_row(text, "Jumlah Non Hutan", year)
    reported_total = parse_summary_row(text, "Total", year)
    tolerance = Decimal("0.2")  # table is rounded to 0.1 thousand ha
    checks = []
    for index, metric in enumerate(METRICS):
        calculated_forest = sum_metric(forest_rows, metric)
        calculated_non_forest = sum_metric(non_forest_rows, metric)
        forest_target = reported_forest[index]
        non_forest_target = reported_non_forest[index]
        total_target = reported_total[index]
        if forest_target is None or non_forest_target is None or total_target is None:
            raise RuntimeError(f"{year} summary unexpectedly missing numeric {metric}")
        forest_delta = abs(calculated_forest - forest_target)
        non_forest_delta = abs(calculated_non_forest - non_forest_target)
        total_delta = abs((forest_target + non_forest_target) - total_target)
        if max(forest_delta, non_forest_delta, total_delta) > tolerance:
            raise RuntimeError(
                f"{year} reconciliation failed for {metric}: "
                f"forest_delta={forest_delta}, non_forest_delta={non_forest_delta}, total_delta={total_delta}"
            )
        checks.append(
            {
                "metric": metric,
                "reported_forest": format_decimal(forest_target),
                "reported_non_forest": format_decimal(non_forest_target),
                "reported_total": format_decimal(total_target),
                "forest_class_sum_delta": format_decimal(forest_delta),
                "non_forest_class_sum_delta": format_decimal(non_forest_delta),
                "reported_total_delta": format_decimal(total_delta),
            }
        )
    return {
        "class_count": len(rows),
        "forest_class_count": len(forest_rows),
        "non_forest_class_count": len(non_forest_rows),
        "rounding_tolerance_thousand_ha": format_decimal(tolerance),
        "metric_checks": checks,
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "year", "geography_id", "geography_name", "class_number", "class_code",
        "class_name", "source_class_label", "forest_group", *METRICS,
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            serialized = dict(row)
            for metric in METRICS:
                serialized[metric] = format_decimal(row[metric])
            writer.writerow(serialized)


def main() -> None:
    dictionary = qualify_dictionary()
    all_rows: list[dict[str, Any]] = []
    sources = []
    validations: dict[str, Any] = {}

    for year, url in PUBLICATIONS.items():
        pdf_path, source = download_publication(year, url)
        page_index, text, page_count = extract_sumbar_page(pdf_path, year)
        rows = parse_class_rows(text, year)
        validation = validate_rows(rows, text, year)
        source.update({"pdf_page_count": page_count, "sumbar_table_pdf_page_index": page_index})
        sources.append(source)
        validations[str(year)] = validation
        all_rows.extend(rows)

    if len(all_rows) != 42:
        raise RuntimeError(f"expected 42 source table rows, got {len(all_rows)}")
    write_csv(all_rows)

    forest_totals = {
        str(year): format_decimal(sum_metric([row for row in all_rows if row["year"] == year and row["forest_group"] == "forest"], "total_thousand_ha"))
        for year in PUBLICATIONS
    }
    manifest = {
        "schema": "ranah-observatory/forestry-land-cover-sumbar/v1",
        "provider": "Kementerian Kehutanan Republik Indonesia",
        "producer": "Direktorat Inventarisasi dan Pemantauan Sumber Daya Hutan",
        "geography": {"id": "idn.13", "name": "Sumatera Barat", "level": "province"},
        "source_unit": "thousand_hectares",
        "source_precision": "0.1 thousand ha (approximately 100 ha)",
        "class_dictionary": dictionary,
        "publication_sources": sources,
        "table_contract": {
            "published_class_rows_per_year": 21,
            "official_domain_class_count": 23,
            "omitted_from_published_sumbar_table": [
                {
                    "class_code": "5001",
                    "class_name": "Tubuh Air",
                    "status": "explicitly_excluded_from_calculation_by_source_footnote",
                },
                {
                    "class_code": "2500",
                    "class_name": "Awan",
                    "status": "not_presented_in_source_table; no zero inferred",
                },
            ],
            "district_rows_present_in_publication_tables": False,
            "district_values_inferred": False,
            "change_interpretation": "2022 and 2023 source tables are comparable province-level land-cover snapshots; class deltas are land-cover change context, not automatically deforestation.",
        },
        "validation": validations,
        "derived_summary": {
            "forest_total_thousand_ha_from_class_rows": forest_totals,
            "forest_change_2022_to_2023_thousand_ha": format_decimal(Decimal(forest_totals["2023"]) - Decimal(forest_totals["2022"])),
        },
        "output": {
            "path": OUTPUT_CSV.relative_to(ROOT).as_posix(),
            "sha256": sha256_path(OUTPUT_CSV),
            "row_count": len(all_rows),
        },
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "rows": len(all_rows),
                "years": sorted(PUBLICATIONS),
                "forest_total_thousand_ha": forest_totals,
                "forest_change_2022_to_2023_thousand_ha": manifest["derived_summary"]["forest_change_2022_to_2023_thousand_ha"],
                "output": OUTPUT_CSV.relative_to(ROOT).as_posix(),
                "manifest": MANIFEST.relative_to(ROOT).as_posix(),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
