#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "data/manifests/milestone27_design_gate.json"
RAW_ROOT = ROOT / "data/processed/bkpm/m27_resource_inventory"
INVENTORY = ROOT / "data/analysis/engine/investment_realization_v1/m27-bkpm-resource-inventory.csv"
MANIFEST = ROOT / "data/manifests/milestone27_bkpm_resource_inventory.json"

QUARTER_ORDER = {"I": 1, "II": 2, "III": 3, "IV": 4}
USER_AGENT = "ranah-observatory/1.0 (+https://github.com/nabilrn/ranah-observatory)"


class InventoryError(RuntimeError):
    pass


class SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.hrefs: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
        attrs_map = {k: (v or "") for k, v in attrs}
        href = attrs_map.get("href", "").strip()
        if href:
            self.hrefs.append(html.unescape(href))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            value = re.sub(r"\s+", " ", html.unescape(data)).strip()
            if value:
                self.text.append(value)

    @property
    def normalized_text(self) -> str:
        return " | ".join(self.text)


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(payload))


def request_bytes(url: str, *, attempts: int = 3) -> tuple[str, str, bytes]:
    error: Exception | None = None
    for attempt in range(attempts):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as response:
                final_url = response.geturl()
                content_type = response.headers.get("Content-Type", "")
                body = response.read()
                if not body:
                    raise InventoryError(f"empty response: {url}")
                return final_url, content_type, body
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, InventoryError) as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise InventoryError(f"request failed after {attempts} attempts: {url}: {error}")


def parse_surface(body: bytes) -> SurfaceParser:
    parser = SurfaceParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    return parser


def parse_label(text: str, label: str) -> str:
    # The official detail page renders metadata as label/value rows. The value is
    # captured only up to the next known metadata label separator.
    labels = [
        "Nama Konten", "Jenis Konten", "Deskripsi Konten", "Kategori Konten", "Sifat Konten",
        "Pengguna", "Bentuk Penyajian", "Pemilik Data", "Frekuensi Update Konten",
        "Dimensi Dalam Dataset", "Matrik Dalam Dataset", "Cara Mendapatkan Data",
        "Frekuensi Pengumpulan", "Alat Dan Metode Pengumpulan", "Publisher", "Modified",
        "Release Date", "Identifier", "Public Access Level", "Kategori",
    ]
    next_labels = "|".join(re.escape(item) for item in labels if item != label)
    match = re.search(
        rf"(?:^|\|\s*){re.escape(label)}\s*\|?\s*(.*?)(?=\s*\|\s*(?:{next_labels})\b|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip(" |")


def transport_locators(base_url: str, raw_text: str, hrefs: list[str]) -> list[str]:
    candidates: set[str] = set()
    for href in hrefs:
        absolute = urllib.parse.urljoin(base_url, href)
        lower = absolute.lower()
        if any(token in lower for token in (".csv", "/download/", "download?", "/storage/", "/uploads/")):
            candidates.add(absolute)

    # Some BKPM resource buttons keep the file locator in data/script text rather
    # than an anchor href. Record such locators without requesting them.
    for match in re.finditer(r"https?://[^\s\"'<>]+", raw_text):
        value = html.unescape(match.group(0)).rstrip("),.;")
        lower = value.lower()
        if any(token in lower for token in (".csv", "/download/", "/storage/", "/uploads/")):
            candidates.add(value)
    return sorted(candidates)


def candidate_from_url(url: str, pattern: re.Pattern[str], start_year: int, end_year: int) -> tuple[int, str] | None:
    slug = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1].lower()
    match = pattern.search(slug)
    if not match:
        return None
    quarter = match.group(1).upper()
    year = int(match.group(2))
    if quarter not in QUARTER_ORDER or not (start_year <= year <= end_year):
        return None
    return year, quarter


def extract_resource_name(text: str) -> tuple[str, str]:
    # Resource headings on the current official surface are rendered as
    # "<resource name> (CSV)". Metadata-only extraction stops here.
    match = re.search(r"([^|]{3,250})\s*\((CSV|JSON|XLSX|XLS|PDF)\)", text, flags=re.IGNORECASE)
    if not match:
        return "", ""
    name = re.sub(r"\s+", " ", match.group(1)).strip(" |")
    # Avoid accidentally swallowing preceding page prose when text is flattened.
    if "Sumber data" in name:
        name = name.split("Sumber data", 1)[-1].strip(" |")
    return name, match.group(2).upper()


def load_gate() -> dict[str, Any]:
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    if gate.get("schema") != "ranah-observatory/milestone27-design-gate/v1":
        raise InventoryError("unexpected M27 design-gate schema")
    if gate.get("contract_locked_before_live_inventory") is not True:
        raise InventoryError("M27 contract is not locked before live inventory")
    forbidden = (
        "target_investment_values_inspection_authorized",
        "investment_value_aggregation_authorized",
        "annual_sum_authorized",
        "pma_pmdn_combination_authorized",
        "external_currency_conversion_authorized",
        "missing_row_as_zero_authorized",
        "value_based_deduplication_authorized",
        "geography_fuzzy_mapping_authorized",
        "historical_boundary_reconstruction_authorized",
        "per_capita_normalization_authorized",
        "ranking_authorized",
        "statistical_model_fit_authorized",
        "causal_claim_authorized",
        "monetary_wasted_potential_estimate_authorized",
    )
    for key in forbidden:
        if gate.get(key) is not False:
            raise InventoryError(f"forbidden M27 authorization enabled: {key}")
    return gate


def inventory_live() -> dict[str, Any]:
    gate = load_gate()
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    discovery = gate["discovery_transport"]
    target = gate["target_period"]
    start_year = int(target["start_year"])
    end_year = int(target["end_year"])
    pattern = re.compile(discovery["candidate_slug_regex"], flags=re.IGNORECASE)

    listing_evidence: list[dict[str, Any]] = []
    candidates: dict[str, dict[str, Any]] = {}
    seen_page_signatures: set[str] = set()
    empty_listing_seen = False

    for page in range(int(discovery["first_page"]), int(discovery["max_page"]) + 1):
        requested_url = discovery["listing_url_template"].format(page=page)
        final_url, content_type, body = request_bytes(requested_url)
        if urllib.parse.urlparse(final_url).hostname != discovery["official_domain_required"]:
            raise InventoryError(f"listing escaped official domain: {final_url}")
        parser = parse_surface(body)
        detail_links = sorted({
            urllib.parse.urljoin(final_url, href)
            for href in parser.hrefs
            if discovery["candidate_href_fragment"] in href
        })
        page_signature = hashlib.sha256("\n".join(detail_links).encode("utf-8")).hexdigest()
        raw_path = RAW_ROOT / "listing" / f"page-{page:02d}.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)
        listing_evidence.append({
            "page": page,
            "requested_url": requested_url,
            "final_url": final_url,
            "content_type": content_type,
            "raw_path": rel(raw_path),
            "raw_sha256": sha256_bytes(body),
            "raw_bytes": len(body),
            "detail_link_count": len(detail_links),
        })

        if not detail_links:
            empty_listing_seen = True
            break
        if page_signature in seen_page_signatures:
            # A repeated link set means the portal has clamped an out-of-range
            # page request. Keep the frozen response but stop discovery.
            break
        seen_page_signatures.add(page_signature)

        for url in detail_links:
            parsed = candidate_from_url(url, pattern, start_year, end_year)
            if parsed is None:
                continue
            year, quarter = parsed
            candidates.setdefault(url, {
                "year": year,
                "quarter": quarter,
                "listing_pages": [],
            })["listing_pages"].append(page)

    rows: list[dict[str, Any]] = []
    detail_evidence: list[dict[str, Any]] = []
    expected_names = [str(x) for x in gate["expected_declared_schema_family"]]

    for index, (url, candidate) in enumerate(
        sorted(candidates.items(), key=lambda item: (item[1]["year"], QUARTER_ORDER[item[1]["quarter"]], item[0]))
    ):
        year = int(candidate["year"])
        quarter = str(candidate["quarter"])
        final_url, content_type, body = request_bytes(url)
        if urllib.parse.urlparse(final_url).hostname != discovery["official_domain_required"]:
            raise InventoryError(f"detail escaped official domain: {final_url}")
        parser = parse_surface(body)
        text = parser.normalized_text
        title_match = re.search(
            rf"Data Realisasi Investasi Triwulan\s+{re.escape(quarter)}\s+Tahun\s+{year}",
            text,
            flags=re.IGNORECASE,
        )
        if not title_match:
            raise InventoryError(f"detail title does not confirm candidate period: {url}")
        title = title_match.group(0)
        identifier = parse_label(text, "Identifier")
        modified = parse_label(text, "Modified")
        release = parse_label(text, "Release Date")
        access = parse_label(text, "Public Access Level")
        update_frequency = parse_label(text, "Frekuensi Update Konten")
        collection_frequency = parse_label(text, "Frekuensi Pengumpulan")
        collection_method = parse_label(text, "Alat Dan Metode Pengumpulan")
        resource_name, resource_format = extract_resource_name(text)
        locators = transport_locators(final_url, body.decode("utf-8", errors="replace"), parser.hrefs)
        declared_present = [name for name in expected_names if re.search(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE)]

        raw_path = RAW_ROOT / "detail" / str(year) / f"q{QUARTER_ORDER[quarter]}-{index:03d}.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(body)
        sidecar_path = raw_path.with_suffix(".request.json")
        sidecar = {
            "schema": "ranah-observatory/milestone27-bkpm-detail-request/v1",
            "year": year,
            "quarter": quarter,
            "requested_url": url,
            "final_url": final_url,
            "content_type": content_type,
            "response_path": rel(raw_path),
            "response_sha256": sha256_bytes(body),
            "response_bytes": len(body),
            "resource_file_requested": False,
            "target_investment_values_inspected": False,
        }
        write_json(sidecar_path, sidecar)
        detail_evidence.append({
            "year": year,
            "quarter": quarter,
            "detail_url": final_url,
            "raw_path": rel(raw_path),
            "raw_sha256": sha256_bytes(body),
            "request_sidecar_path": rel(sidecar_path),
            "request_sidecar_sha256": sha256_path(sidecar_path),
        })

        if locators:
            promotion_state = "metadata_and_transport_qualified_schema_pending"
        else:
            promotion_state = "metadata_qualified_resource_transport_pending"
        rows.append({
            "year": year,
            "quarter": quarter,
            "quarter_number": QUARTER_ORDER[quarter],
            "dataset_title": title,
            "dataset_identifier": identifier,
            "dataset_detail_url": final_url,
            "listing_pages": ";".join(str(x) for x in sorted(set(candidate["listing_pages"]))),
            "release_date": release,
            "modified_date": modified,
            "public_access_level": access,
            "update_frequency": update_frequency,
            "collection_frequency": collection_frequency,
            "collection_method": collection_method,
            "resource_name": resource_name,
            "resource_format": resource_format,
            "resource_transport_locator_count": len(locators),
            "resource_transport_locators": ";".join(locators),
            "declared_expected_variable_count": len(declared_present),
            "declared_expected_variables": ";".join(declared_present),
            "declared_expected_schema_complete": str(set(declared_present) == set(expected_names)).lower(),
            "promotion_state": promotion_state,
            "resource_file_downloaded": "false",
            "target_investment_values_inspected": "false",
            "investment_value_aggregation_performed": "false",
        })

    by_period: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_period[(int(row["year"]), str(row["quarter"]))].append(row)

    expected_periods = [(year, quarter) for year in range(start_year, end_year + 1) for quarter in QUARTER_ORDER]
    missing_periods = [f"{year}-Q{QUARTER_ORDER[quarter]}" for year, quarter in expected_periods if not by_period[(year, quarter)]]
    duplicate_periods = {
        f"{year}-Q{QUARTER_ORDER[quarter]}": len(items)
        for (year, quarter), items in sorted(by_period.items())
        if len(items) > 1
    }

    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "year", "quarter", "quarter_number", "dataset_title", "dataset_identifier",
        "dataset_detail_url", "listing_pages", "release_date", "modified_date",
        "public_access_level", "update_frequency", "collection_frequency", "collection_method",
        "resource_name", "resource_format", "resource_transport_locator_count",
        "resource_transport_locators", "declared_expected_variable_count", "declared_expected_variables",
        "declared_expected_schema_complete", "promotion_state", "resource_file_downloaded",
        "target_investment_values_inspected", "investment_value_aggregation_performed",
    ]
    with INVENTORY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "schema": "ranah-observatory/milestone27-bkpm-resource-inventory/v1",
        "milestone": 27,
        "stage": "stage0_value_blind_resource_inventory",
        "source_candidate_id": gate["source_candidate_id"],
        "official_surface": gate["official_surface"],
        "target_period": target,
        "listing_pages_fetched": len(listing_evidence),
        "listing_empty_page_seen": empty_listing_seen,
        "listing_evidence": listing_evidence,
        "candidate_detail_count": len(rows),
        "distinct_period_count": len(by_period),
        "possible_period_count": len(expected_periods),
        "missing_period_count": len(missing_periods),
        "missing_periods": missing_periods,
        "duplicate_period_count": len(duplicate_periods),
        "duplicate_periods": duplicate_periods,
        "period_coverage_inferred_from_adjacent_periods": False,
        "detail_evidence": detail_evidence,
        "direct_resource_transport_period_count": sum(1 for row in rows if int(row["resource_transport_locator_count"]) > 0),
        "declared_expected_schema_complete_period_count": sum(1 for row in rows if row["declared_expected_schema_complete"] == "true"),
        "design_gate": {"path": rel(GATE), "sha256": sha256_path(GATE)},
        "outputs": {"inventory": rel(INVENTORY), "inventory_sha256": sha256_path(INVENTORY)},
        "resource_file_download_performed": False,
        "resource_header_retrieval_performed": False,
        "target_investment_values_inspected": False,
        "source_selection_uses_target_investment_values": False,
        "investment_value_aggregation_performed": False,
        "annual_sum_performed": False,
        "pma_pmdn_combination_performed": False,
        "external_currency_conversion_performed": False,
        "missing_row_interpreted_as_zero": False,
        "value_based_deduplication_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "per_capita_normalization_performed": False,
        "ranking_performed": False,
        "statistical_model_fit": False,
        "causal_claim_created": False,
        "monetary_wasted_potential_estimated": False,
        "stage0_complete": False,
    }
    write_json(MANIFEST, manifest)
    return manifest


def inventory_offline() -> dict[str, Any]:
    # Stage 0 live inventory freezes all official listing/detail HTML. Offline
    # reproducibility is enabled only after the live inventory itself is reviewed
    # and a deterministic parser contract is promoted in a later commit.
    raise InventoryError("offline mode not authorized until live Stage 0 inventory evidence is reviewed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe BKPM quarterly investment-realization history without reading target values")
    parser.add_argument("--mode", choices=("live", "offline"), default="live")
    args = parser.parse_args()
    try:
        manifest = inventory_live() if args.mode == "live" else inventory_offline()
    except (OSError, ValueError, json.JSONDecodeError, InventoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "candidate_detail_count": manifest["candidate_detail_count"],
        "distinct_period_count": manifest["distinct_period_count"],
        "missing_period_count": manifest["missing_period_count"],
        "duplicate_period_count": manifest["duplicate_period_count"],
        "direct_resource_transport_period_count": manifest["direct_resource_transport_period_count"],
        "target_investment_values_inspected": manifest["target_investment_values_inspected"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
