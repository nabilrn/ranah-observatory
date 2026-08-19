#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "data/manifests/milestone25_design_gate.json"
DEFAULT_CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
DEFAULT_DISCOVERY = ROOT / "data/analysis/engine/djpk_finance_v1/m25-taxonomy-discovery.csv"
DEFAULT_PRESENCE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-account-presence.csv"
DEFAULT_MANIFEST = ROOT / "data/manifests/milestone25_taxonomy_discovery.json"
DEFAULT_RAW_DIR = ROOT / "data/processed/djpk/taxonomy_probe"

BASE_URL = "https://djpk.kemenkeu.go.id/portal/data/apbd"
YEARS = list(range(2018, 2026))
PROVINCE_SELECTOR = "03"
PEMDA_SELECTOR = "12"
PERIOD_SELECTOR = "12"
EXPECTED_JURISDICTION = "Kota Padang"


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_label(text: str) -> str:
    value = normalize_space(text).casefold()
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


class HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._table_rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._in_cell = False
        self._cell_parts: list[str] = []
        self.all_text_parts: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag == "title":
            self._in_title = True
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table_rows = []
        elif tag == "tr" and self._table_depth == 1:
            self._row = []
        elif tag in {"td", "th"} and self._table_depth == 1 and self._row is not None:
            self._in_cell = True
            self._cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "title":
            self._in_title = False
        elif tag in {"td", "th"} and self._in_cell:
            assert self._row is not None
            self._row.append(normalize_space(" ".join(self._cell_parts)))
            self._in_cell = False
            self._cell_parts = []
        elif tag == "tr" and self._table_depth == 1:
            if self._row and any(cell for cell in self._row):
                assert self._table_rows is not None
                self._table_rows.append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            if self._table_depth == 1 and self._table_rows is not None:
                self.tables.append(self._table_rows)
                self._table_rows = None
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        text = normalize_space(data)
        if not text:
            return
        self.all_text_parts.append(text)
        if self._in_title:
            self.title_parts.append(text)
        if self._in_cell:
            self._cell_parts.append(text)

    @property
    def all_text(self) -> str:
        return normalize_space(" ".join(self.all_text_parts))

    @property
    def title(self) -> str:
        return normalize_space(" ".join(self.title_parts))


def find_postur_table(tables: list[list[list[str]]]) -> tuple[list[str], list[list[str]]]:
    for table in tables:
        for index, row in enumerate(table):
            normalized = [normalize_label(cell) for cell in row]
            if "akun" in normalized and "realisasi" in normalized:
                return row, table[index + 1 :]
    raise ValueError("DJPK APBD postur table with Akun/Realisasi header not found")


def table_to_accounts(header: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    normalized_header = [normalize_label(cell) for cell in header]
    try:
        account_index = normalized_header.index("akun")
        realization_index = normalized_header.index("realisasi")
    except ValueError as exc:
        raise ValueError("DJPK postur header missing Akun/Realisasi") from exc
    budget_index = normalized_header.index("anggaran/pagu") if "anggaran/pagu" in normalized_header else None
    percent_index = normalized_header.index("%") if "%" in normalized_header else None

    accounts: list[dict[str, str]] = []
    for source_order, row in enumerate(rows, start=1):
        if len(row) <= max(account_index, realization_index):
            continue
        account = normalize_space(row[account_index])
        if not account:
            continue
        accounts.append(
            {
                "source_order": str(source_order),
                "account_label": account,
                "account_label_normalized": normalize_label(account),
                "budget_raw": normalize_space(row[budget_index]) if budget_index is not None and budget_index < len(row) else "",
                "realization_raw": normalize_space(row[realization_index]),
                "percent_raw": normalize_space(row[percent_index]) if percent_index is not None and percent_index < len(row) else "",
            }
        )
    if not accounts:
        raise ValueError("DJPK postur table yielded no account rows")
    normalized = [item["account_label_normalized"] for item in accounts]
    duplicates = sorted({label for label in normalized if normalized.count(label) > 1})
    if duplicates:
        raise ValueError(f"duplicate normalized DJPK account labels in one page: {duplicates}")
    return accounts


def response_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_url(year: int) -> str:
    query = urllib.parse.urlencode(
        {
            "pemda": PEMDA_SELECTOR,
            "periode": PERIOD_SELECTOR,
            "provinsi": PROVINCE_SELECTOR,
            "tahun": str(year),
        }
    )
    return f"{BASE_URL}?{query}"


def fetch_url(url: str, timeout: float = 35.0, retries: int = 3) -> tuple[int, bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RanahObservatory/1.0; research source qualification)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "id,en;q=0.8",
    }
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = int(getattr(response, "status", 200))
                final_url = str(response.geturl())
                return status, body, final_url
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(float(attempt))
    raise RuntimeError(f"DJPK retrieval failed after {retries} attempts: {last_error}")


def extract_note(text: str, year: int) -> str:
    marker = text.casefold().find("keterangan:")
    if marker < 0:
        return ""
    tail = text[marker : marker + 700]
    # Stop before the table header when present.
    cut = tail.casefold().find(" akun ")
    if cut > 0:
        tail = tail[:cut]
    return normalize_space(tail)


def classify_conceptual_families(labels_by_year: dict[int, set[str]]) -> list[dict[str, Any]]:
    def years_for(label: str) -> list[int]:
        normalized = normalize_label(label)
        return [year for year in YEARS if normalized in labels_by_year[year]]

    pad_years = years_for("PAD")
    capex_years = years_for("Belanja Modal")
    expenditure_exact_candidates = ["Belanja", "Belanja Daerah"]
    revenue_candidates = ["Pendapatan", "Pendapatan Daerah"]
    transfer_candidates = ["Dana Perimbangan", "TKDD", "Pendapatan Transfer Pemerintah Pusat"]

    result: list[dict[str, Any]] = []

    result.append(
        {
            "conceptual_family": "own_source_revenue_pad",
            "status": "exact_label_qualified" if pad_years == YEARS else "held_taxonomy_incomplete",
            "source_labels": "PAD",
            "years_covered": "|".join(str(year) for year in pad_years),
            "bridge_review_required": False,
        }
    )
    result.append(
        {
            "conceptual_family": "capital_expenditure",
            "status": "exact_label_qualified" if capex_years == YEARS else "held_taxonomy_incomplete",
            "source_labels": "Belanja Modal",
            "years_covered": "|".join(str(year) for year in capex_years),
            "bridge_review_required": False,
        }
    )

    for family, candidates in (
        ("total_revenue", revenue_candidates),
        ("total_expenditure", expenditure_exact_candidates),
    ):
        candidate_years = {label: years_for(label) for label in candidates}
        exact = next((label for label, years in candidate_years.items() if years == YEARS), None)
        union = sorted({year for years in candidate_years.values() for year in years})
        if exact:
            status = "exact_label_qualified"
            bridge = False
            labels = exact
        elif union == YEARS and all(candidate_years[label] for label in candidates):
            status = "explicit_bridge_candidate"
            bridge = True
            labels = "|".join(label for label in candidates if candidate_years[label])
        else:
            status = "held_taxonomy_incomplete"
            bridge = True
            labels = "|".join(label for label in candidates if candidate_years[label])
        result.append(
            {
                "conceptual_family": family,
                "status": status,
                "source_labels": labels,
                "years_covered": "|".join(str(year) for year in union),
                "bridge_review_required": bridge,
            }
        )

    transfer_years = {label: years_for(label) for label in transfer_candidates}
    transfer_union = sorted({year for years in transfer_years.values() for year in years})
    result.append(
        {
            "conceptual_family": "central_transfer_revenue",
            "status": "held_semantic_bridge_review",
            "source_labels": "|".join(label for label in transfer_candidates if transfer_years[label]),
            "years_covered": "|".join(str(year) for year in transfer_union),
            "bridge_review_required": True,
        }
    )
    return sorted(result, key=lambda item: item["conceptual_family"])


def validate_gate(path: Path) -> dict[str, Any]:
    gate = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": "ranah-observatory/milestone25-design-gate/v1",
        "design_locked_before_taxonomy_probe": True,
        "source_id": "djpk_sikd_apbd_portal",
        "source_base_url": BASE_URL,
        "djpk_province_selector": PROVINCE_SELECTOR,
        "annual_realization_period_selector": PERIOD_SELECTOR,
        "target_start_year": 2018,
        "target_end_year": 2025,
        "target_year_count": 8,
        "taxonomy_reference_geography_id": "idn.13.1371",
        "taxonomy_reference_pemda_selector": PEMDA_SELECTOR,
        "current_sumbar_geography_count": 19,
        "stage0_page_count": 8,
        "stage1_jurisdiction_year_count": 152,
        "conceptual_account_family_count": 5,
        "cross_geography_values_inspected_before_taxonomy_lock": False,
        "realization_not_budget_appropriation": True,
        "imputation_authorized": False,
        "historical_boundary_reconstruction_authorized": False,
        "posthoc_account_family_search_authorized": False,
        "derived_ratio_creation_authorized_before_component_qualification": False,
        "statistical_model_fit_authorized": False,
    }
    for key, value in expected.items():
        if gate.get(key) != value:
            raise ValueError(f"M25 design gate drift: {key}={gate.get(key)!r} expected={value!r}")
    return gate


def validate_crosswalk(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    if len(rows) != 19:
        raise ValueError(f"M25 DJPK crosswalk must have 19 rows, got {len(rows)}")
    if {row["djpk_province_selector"] for row in rows} != {PROVINCE_SELECTOR}:
        raise ValueError("M25 DJPK province selector drift")
    if {row["djpk_pemda_selector"] for row in rows} != {f"{value:02d}" for value in range(1, 20)}:
        raise ValueError("M25 DJPK pemda selectors must be exact 01..19")
    if len({row["geography_id"] for row in rows}) != 19:
        raise ValueError("M25 DJPK crosswalk geography IDs are not unique")
    padang = next((row for row in rows if row["geography_id"] == "idn.13.1371"), None)
    if not padang or padang["djpk_pemda_selector"] != PEMDA_SELECTOR or padang["djpk_source_name"] != EXPECTED_JURISDICTION:
        raise ValueError("M25 Kota Padang reference crosswalk drift")
    if {row["mapping_status"] for row in rows} != {"qualified_explicit"}:
        raise ValueError("M25 DJPK crosswalk contains unqualified mapping")
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_probe(
    gate_path: Path,
    crosswalk_path: Path,
    discovery_path: Path,
    presence_path: Path,
    manifest_path: Path,
    raw_dir: Path,
) -> dict[str, Any]:
    gate = validate_gate(gate_path)
    validate_crosswalk(crosswalk_path)
    raw_dir.mkdir(parents=True, exist_ok=True)

    discovery_rows: list[dict[str, Any]] = []
    labels_by_year: dict[int, set[str]] = {}
    account_details_by_year: dict[int, list[dict[str, str]]] = {}
    response_files: list[dict[str, Any]] = []

    for year in YEARS:
        url = build_url(year)
        status, body, final_url = fetch_url(url)
        if status != 200:
            raise RuntimeError(f"DJPK returned HTTP {status} for year {year}")
        raw_path = raw_dir / f"kota-padang-apbd-{year}-desember.html"
        raw_path.write_bytes(body)
        parser = HTMLTableParser()
        parser.feed(body.decode("utf-8", errors="replace"))
        header, table_rows = find_postur_table(parser.tables)
        accounts = table_to_accounts(header, table_rows)
        normalized_labels = {item["account_label_normalized"] for item in accounts}
        labels_by_year[year] = normalized_labels
        account_details_by_year[year] = accounts

        text = parser.all_text
        jurisdiction_ok = normalize_label(EXPECTED_JURISDICTION) in normalize_label(text)
        year_ok = str(year) in text
        december_ok = bool(re.search(r"realisasi\s+apbd\s+s\.?\s*d\.?\s+desember", text, flags=re.IGNORECASE))
        note = extract_note(text, year)
        page_pass = jurisdiction_ok and year_ok and december_ok and bool(accounts)
        if not page_pass:
            raise RuntimeError(
                f"DJPK Stage0 identity/period failure year={year}: jurisdiction={jurisdiction_ok} year={year_ok} december={december_ok} accounts={len(accounts)}"
            )
        digest = response_sha256(body)
        discovery_rows.append(
            {
                "year": year,
                "requested_url": url,
                "final_url": final_url,
                "http_status": status,
                "page_title": parser.title,
                "jurisdiction_expected": EXPECTED_JURISDICTION,
                "jurisdiction_match": jurisdiction_ok,
                "fiscal_year_match": year_ok,
                "december_realization_semantics_match": december_ok,
                "account_count": len(accounts),
                "source_note": note,
                "response_sha256": digest,
                "raw_snapshot": raw_path.relative_to(ROOT).as_posix() if raw_path.is_relative_to(ROOT) else raw_path.as_posix(),
                "page_pass": page_pass,
            }
        )
        response_files.append({"year": year, "path": raw_path.as_posix(), "sha256": digest})

    all_labels = sorted({label for labels in labels_by_year.values() for label in labels})
    presence_rows: list[dict[str, Any]] = []
    for label in all_labels:
        years_present = [year for year in YEARS if label in labels_by_year[year]]
        source_labels = sorted(
            {
                item["account_label"]
                for year in years_present
                for item in account_details_by_year[year]
                if item["account_label_normalized"] == label
            }
        )
        presence_rows.append(
            {
                "account_label_normalized": label,
                "source_labels": "|".join(source_labels),
                "year_count": len(years_present),
                "years_present": "|".join(str(year) for year in years_present),
                "present_all_2018_2025": years_present == YEARS,
                **{f"present_{year}": year in years_present for year in YEARS},
            }
        )

    conceptual = classify_conceptual_families(labels_by_year)
    write_csv(discovery_path, list(discovery_rows[0].keys()), discovery_rows)
    write_csv(presence_path, list(presence_rows[0].keys()), presence_rows)

    manifest = {
        "schema": "ranah-observatory/milestone25-taxonomy-discovery/v1",
        "milestone": 25,
        "stage": 0,
        "phase": "post_phase2_fiscal_evidence_expansion",
        "criterion": "eight-year reference-jurisdiction APBD taxonomy discovery before cross-geography fiscal extraction",
        "stage0_complete": True,
        "source_id": "djpk_sikd_apbd_portal",
        "reference_geography_id": "idn.13.1371",
        "reference_name": "Padang",
        "reference_djpk_province_selector": PROVINCE_SELECTOR,
        "reference_djpk_pemda_selector": PEMDA_SELECTOR,
        "period_selector": PERIOD_SELECTOR,
        "years": YEARS,
        "page_count": len(discovery_rows),
        "all_pages_pass": all(bool(row["page_pass"]) for row in discovery_rows),
        "unique_normalized_account_label_count": len(all_labels),
        "conceptual_account_family_results": conceptual,
        "cross_geography_values_inspected_before_taxonomy_lock": False,
        "statistical_model_fit": False,
        "derived_ratio_created": False,
        "imputation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "posthoc_account_family_search_performed": False,
        "inputs": {
            "design_gate": {"path": gate_path.relative_to(ROOT).as_posix(), "sha256": sha256(gate_path)},
            "crosswalk": {"path": crosswalk_path.relative_to(ROOT).as_posix(), "sha256": sha256(crosswalk_path)},
        },
        "outputs": {
            "taxonomy_discovery": {"path": discovery_path.relative_to(ROOT).as_posix() if discovery_path.is_relative_to(ROOT) else discovery_path.as_posix(), "sha256": sha256(discovery_path)},
            "account_presence": {"path": presence_path.relative_to(ROOT).as_posix() if presence_path.is_relative_to(ROOT) else presence_path.as_posix(), "sha256": sha256(presence_path)},
        },
        "raw_responses": response_files,
        "design_gate_schema": gate["schema"],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe DJPK Kota Padang APBD taxonomy for M25 Stage 0.")
    parser.add_argument("--design-gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--discovery", type=Path, default=DEFAULT_DISCOVERY)
    parser.add_argument("--presence", type=Path, default=DEFAULT_PRESENCE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    args = parser.parse_args()
    try:
        result = run_probe(args.design_gate, args.crosswalk, args.discovery, args.presence, args.manifest, args.raw_dir)
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "stage0_complete": result["stage0_complete"],
        "page_count": result["page_count"],
        "conceptual_account_family_results": result["conceptual_account_family_results"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
