from __future__ import annotations

import html as html_lib
import re
import urllib.parse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from probe_milestone25_djpk_taxonomy import normalize_label, normalize_space

EXPORT_BASE_URL = "https://djpk.kemenkeu.go.id/portal/csv_apbd"
PROVINCE_SELECTOR = "03"
PERIOD_SELECTOR = "12"
EXPORT_TYPE_SELECTOR = "apbd"
SPREADSHEET_NS = "urn:schemas-microsoft-com:office:spreadsheet"
SS_NS = "urn:schemas-microsoft-com:office:spreadsheet"
DISPLAY_ROUNDING_TOLERANCE_IDR_BILLION = Decimal("0.0051")


class M25DJPKExportError(RuntimeError):
    pass


def build_export_url(pemda_selector: str, year: int) -> str:
    if not re.fullmatch(r"\d{2}", pemda_selector):
        raise M25DJPKExportError(f"invalid DJPK pemda selector {pemda_selector!r}")
    if year < 2018 or year > 2025:
        raise M25DJPKExportError(f"M25 export year outside locked regime: {year}")
    query = urllib.parse.urlencode(
        {
            "type": EXPORT_TYPE_SELECTOR,
            "periode": PERIOD_SELECTOR,
            "tahun": str(year),
            "provinsi": PROVINCE_SELECTOR,
            "pemda": pemda_selector,
        }
    )
    return f"{EXPORT_BASE_URL}?{query}"


def _selector_tuple(url: str) -> tuple[str, str, str, str, str] | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.path.rstrip("/") != "/portal/csv_apbd":
        return None
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    required = ("type", "periode", "tahun", "provinsi", "pemda")
    values: list[str] = []
    for key in required:
        item = query.get(key)
        if item is None or len(item) != 1:
            return None
        values.append(item[0])
    return tuple(values)  # type: ignore[return-value]


def find_same_selector_export_url(html_bytes: bytes, pemda_selector: str, year: int) -> str:
    text = html_bytes.decode("utf-8", errors="replace")
    expected = _selector_tuple(build_export_url(pemda_selector, year))
    if expected is None:
        raise M25DJPKExportError("internal M25 expected export selector construction failed")

    candidates: list[str] = []
    for match in re.finditer(r"href\s*=\s*([\"'])(.*?)\1", text, flags=re.I | re.S):
        raw = html_lib.unescape(match.group(2).strip())
        absolute = urllib.parse.urljoin("https://djpk.kemenkeu.go.id", raw)
        if _selector_tuple(absolute) == expected:
            candidates.append(absolute)
    unique = sorted(set(candidates))
    if len(unique) != 1:
        raise M25DJPKExportError(
            f"expected exactly one same-selector DJPK export link for {pemda_selector}/{year}, got {len(unique)}"
        )
    return unique[0]


def parse_exact_rupiah(raw: str) -> Decimal:
    token = normalize_space(raw).replace(" ", "")
    if not token:
        raise M25DJPKExportError("empty DJPK SpreadsheetML numeric value")
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise M25DJPKExportError(f"invalid DJPK SpreadsheetML numeric value {raw!r}") from exc
    if not value.is_finite():
        raise M25DJPKExportError(f"non-finite DJPK SpreadsheetML numeric value {raw!r}")
    return value


def rupiah_to_idr_billion(value: Decimal) -> Decimal:
    return value / Decimal("1000000000")


def _data_text(cell: ET.Element) -> str:
    data = cell.find(f"{{{SPREADSHEET_NS}}}Data")
    if data is None:
        return ""
    return normalize_space("" if data.text is None else data.text)


def _resolve_duplicate_labels(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    order: list[str] = []
    for row in rows:
        label = row["account_label_normalized"]
        if label not in grouped:
            order.append(label)
        grouped[label].append(row)

    resolved: list[dict[str, str]] = []
    for label in order:
        group = grouped[label]
        if len(group) == 1:
            item = dict(group[0])
            item["duplicate_occurrence_count"] = "1"
            item["duplicate_resolution"] = "unique_label"
            resolved.append(item)
            continue

        signatures = {
            (item["budget_rupiah_raw"], item["realization_rupiah_raw"], item["percentage_raw"])
            for item in group
        }
        if len(signatures) == 1:
            item = dict(group[0])
            item["duplicate_occurrence_count"] = str(len(group))
            item["duplicate_resolution"] = "identical_exact_values_collapsed"
            resolved.append(item)
            continue

        for occurrence, item in enumerate(group, start=1):
            disambiguated = dict(item)
            disambiguated["account_label_normalized"] = f"{label} [hierarchy-conflict-{occurrence}]"
            disambiguated["duplicate_occurrence_count"] = str(len(group))
            disambiguated["duplicate_resolution"] = "nonidentical_exact_values_disambiguated"
            resolved.append(disambiguated)
    return resolved


def parse_spreadsheetml(body: bytes) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise M25DJPKExportError("DJPK export is not valid SpreadsheetML XML") from exc

    rows = root.findall(f".//{{{SPREADSHEET_NS}}}Row")
    if len(rows) < 2:
        raise M25DJPKExportError("DJPK SpreadsheetML export has no data rows")

    header = [_data_text(cell) for cell in rows[0].findall(f"{{{SPREADSHEET_NS}}}Cell")]
    normalized_header = [normalize_label(value) for value in header]
    expected = ["akun", "anggaran", "realisasi", "persentase"]
    if normalized_header[:4] != expected:
        raise M25DJPKExportError(
            f"unexpected DJPK SpreadsheetML header {normalized_header[:4]!r}; expected {expected!r}"
        )

    parsed_rows: list[dict[str, str]] = []
    for source_order, row in enumerate(rows[1:], start=1):
        cells = row.findall(f"{{{SPREADSHEET_NS}}}Cell")
        values = [_data_text(cell) for cell in cells]
        if len(values) < 4:
            continue
        label = normalize_space(values[0])
        if not label:
            continue
        budget = values[1]
        realization = values[2]
        percentage = values[3]
        # Validate exact monetary fields immediately. The percentage remains
        # source text because M25 does not derive or model realization ratios.
        parse_exact_rupiah(budget)
        parse_exact_rupiah(realization)
        parsed_rows.append(
            {
                "source_order": str(source_order),
                "account_label": label,
                "account_label_normalized": normalize_label(label),
                "budget_rupiah_raw": budget,
                "realization_rupiah_raw": realization,
                "percentage_raw": percentage,
            }
        )

    if not parsed_rows:
        raise M25DJPKExportError("DJPK SpreadsheetML export yielded no account rows")
    return _resolve_duplicate_labels(parsed_rows)


def exact_account_map(body: bytes) -> dict[str, dict[str, str]]:
    rows = parse_spreadsheetml(body)
    by_label = {row["account_label_normalized"]: row for row in rows}
    if len(by_label) != len(rows):
        raise M25DJPKExportError("DJPK SpreadsheetML duplicate-resolution keys remain ambiguous")
    return by_label


def html_display_matches_exact(
    display_idr_billion: Decimal,
    exact_rupiah: Decimal,
    *,
    tolerance: Decimal = DISPLAY_ROUNDING_TOLERANCE_IDR_BILLION,
) -> bool:
    return abs(display_idr_billion - rupiah_to_idr_billion(exact_rupiah)) <= tolerance
