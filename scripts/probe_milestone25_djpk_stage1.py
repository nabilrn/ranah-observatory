#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from probe_milestone25_djpk_taxonomy import (
    HTMLTableParser,
    PERIOD_SELECTOR,
    PROVINCE_SELECTOR,
    build_url as build_reference_url,
    fetch_url,
    find_postur_table,
    normalize_label,
    normalize_space,
    response_sha256,
    table_to_accounts,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
DEFAULT_CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
DEFAULT_CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
DEFAULT_COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-pilot-coverage.csv"
DEFAULT_VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-pilot-values.csv"
DEFAULT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_pilot.json"
DEFAULT_RAW_DIR = ROOT / "data/processed/djpk/stage1_pilot"
BASE_URL = "https://djpk.kemenkeu.go.id/portal/data/apbd"
PILOT_YEAR = 2024


class M25Stage1Error(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def normalize_jurisdiction(text: str) -> str:
    value = normalize_label(text)
    value = re.sub(r"\bkab\.?\b", "kabupaten", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def jurisdiction_matches(page_text: str, expected_source_name: str) -> bool:
    expected = normalize_jurisdiction(expected_source_name)
    page = normalize_jurisdiction(page_text)
    return bool(expected and expected in page)


def build_url(pemda_selector: str, year: int) -> str:
    import urllib.parse
    query = urllib.parse.urlencode(
        {
            "pemda": pemda_selector,
            "periode": PERIOD_SELECTOR,
            "provinsi": PROVINCE_SELECTOR,
            "tahun": str(year),
        }
    )
    return f"{BASE_URL}?{query}"


def parse_decimal_token(token: str) -> Decimal:
    token = token.strip().replace(" ", "")
    if not token:
        raise M25Stage1Error("empty numeric token")
    if "," in token and "." in token:
        # The right-most separator is treated as decimal; the other as grouping.
        if token.rfind(",") > token.rfind("."):
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif "," in token:
        suffix = token.rsplit(",", 1)[1]
        if 1 <= len(suffix) <= 3:
            token = token.replace(".", "").replace(",", ".")
        else:
            token = token.replace(",", "")
    elif "." in token:
        suffix = token.rsplit(".", 1)[1]
        # Portal-scaled values normally show a short decimal tail; otherwise treat as grouping.
        if len(suffix) > 3:
            token = token.replace(".", "")
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise M25Stage1Error(f"invalid numeric token {token!r}") from exc
    if not value.is_finite():
        raise M25Stage1Error("non-finite DJPK numeric token")
    return value


def parse_djpk_money_to_idr_billion(raw: str) -> Decimal:
    text = normalize_space(raw)
    if not text or text in {"-", "–", "—"}:
        raise M25Stage1Error(f"missing DJPK monetary realization: {raw!r}")
    text = text.replace("Rp", "").replace("rp", "").strip()
    match = re.fullmatch(r"([+-]?[0-9][0-9.,]*)\s*([TtMm])?", text)
    if not match:
        raise M25Stage1Error(f"unsupported DJPK monetary format: {raw!r}")
    number = parse_decimal_token(match.group(1))
    suffix = (match.group(2) or "").casefold()
    if suffix == "t":
        return number * Decimal(1000)
    if suffix == "m":
        return number
    # Unscaled portal values are interpreted as rupiah only when sufficiently large.
    if abs(number) >= Decimal(1000000):
        return number / Decimal(1000000000)
    raise M25Stage1Error(f"unscaled ambiguous DJPK amount: {raw!r}")


def load_promoted_contracts(path: Path, manifest_path: Path) -> list[dict[str, str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone25-stage1-account-contracts/v1":
        raise M25Stage1Error("unexpected M25 Stage1 contract schema")
    if manifest.get("contracts_locked") is not True:
        raise M25Stage1Error("M25 Stage1 contracts are not locked")
    if manifest.get("cross_geography_values_inspected_before_lock") is not False:
        raise M25Stage1Error("contract lock occurred after cross-geography inspection")
    rows = read_csv(path)
    promoted = [row for row in rows if row["stage1_promotion_status"] == "promoted_exact_label"]
    if len(promoted) != manifest.get("promoted_exact_label_family_count"):
        raise M25Stage1Error("promoted Stage1 contract count drift")
    if not promoted:
        raise M25Stage1Error("no promoted exact-label Stage1 contracts")
    for row in promoted:
        if row["taxonomy_contract_type"] != "exact_label":
            raise M25Stage1Error("Stage1 pilot only permits exact-label contracts")
        if not row["locked_source_label_normalized"]:
            raise M25Stage1Error("promoted contract lacks locked normalized source label")
        if row["derived_ratio_authorized"] != "False":
            raise M25Stage1Error("derived ratio unexpectedly authorized before Stage1")
    return promoted


def validate_crosswalk(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    if len(rows) != 19:
        raise M25Stage1Error("M25 Stage1 crosswalk must contain exact 19 geographies")
    if {row["djpk_pemda_selector"] for row in rows} != {f"{value:02d}" for value in range(1, 20)}:
        raise M25Stage1Error("M25 Stage1 pemda selector set drift")
    if len({row["geography_id"] for row in rows}) != 19:
        raise M25Stage1Error("M25 Stage1 geography IDs are not unique")
    if {row["mapping_status"] for row in rows} != {"qualified_explicit"}:
        raise M25Stage1Error("M25 Stage1 contains unqualified crosswalk mapping")
    return sorted(rows, key=lambda row: int(row["djpk_pemda_selector"]))


def run_probe(
    crosswalk_path: Path,
    contracts_path: Path,
    contract_manifest_path: Path,
    coverage_path: Path,
    values_path: Path,
    manifest_path: Path,
    raw_dir: Path,
    years: list[int],
) -> dict[str, Any]:
    crosswalk = validate_crosswalk(crosswalk_path)
    contracts = load_promoted_contracts(contracts_path, contract_manifest_path)
    raw_dir.mkdir(parents=True, exist_ok=True)

    coverage_rows: list[dict[str, Any]] = []
    value_rows: list[dict[str, Any]] = []
    raw_responses: list[dict[str, Any]] = []

    for geography in crosswalk:
        for year in years:
            pemda = geography["djpk_pemda_selector"]
            url = build_url(pemda, year)
            status, body, final_url = fetch_url(url)
            if status != 200:
                raise M25Stage1Error(f"DJPK HTTP {status} for {pemda}/{year}")
            raw_path = raw_dir / f"pemda-{pemda}-{year}-desember.html"
            raw_path.write_bytes(body)
            parser = HTMLTableParser()
            parser.feed(body.decode("utf-8", errors="replace"))
            header, table_rows = find_postur_table(parser.tables)
            accounts = table_to_accounts(header, table_rows)
            by_label = {row["account_label_normalized"]: row for row in accounts}

            page_text = parser.all_text
            jurisdiction_ok = jurisdiction_matches(page_text, geography["djpk_source_name"])
            year_ok = str(year) in page_text
            december_ok = bool(re.search(r"realisasi\s+apbd\s+s\.?\s*d\.?\s+desember", page_text, flags=re.IGNORECASE))
            missing_contracts: list[str] = []
            parse_failures: list[str] = []
            matched_contracts = 0
            for contract in contracts:
                label = contract["locked_source_label_normalized"]
                source_row = by_label.get(label)
                if source_row is None:
                    missing_contracts.append(contract["conceptual_family"])
                    continue
                try:
                    amount = parse_djpk_money_to_idr_billion(source_row["realization_raw"])
                except M25Stage1Error:
                    parse_failures.append(contract["conceptual_family"])
                    continue
                matched_contracts += 1
                value_rows.append(
                    {
                        "geography_id": geography["geography_id"],
                        "canonical_name": geography["canonical_name"],
                        "djpk_province_selector": geography["djpk_province_selector"],
                        "djpk_pemda_selector": pemda,
                        "djpk_source_name": geography["djpk_source_name"],
                        "year": year,
                        "period_selector": PERIOD_SELECTOR,
                        "conceptual_family": contract["conceptual_family"],
                        "source_account_label": source_row["account_label"],
                        "source_account_label_normalized": source_row["account_label_normalized"],
                        "budget_raw": source_row["budget_raw"],
                        "realization_raw": source_row["realization_raw"],
                        "realization_idr_billion": format(amount, "f"),
                        "percent_raw": source_row["percent_raw"],
                        "taxonomy_contract_type": "exact_label",
                        "claim_type": "observed_recorded_fiscal_realization",
                        "response_sha256": response_sha256(body),
                    }
                )

            page_pass = (
                jurisdiction_ok
                and year_ok
                and december_ok
                and not missing_contracts
                and not parse_failures
                and matched_contracts == len(contracts)
            )
            coverage_rows.append(
                {
                    "geography_id": geography["geography_id"],
                    "canonical_name": geography["canonical_name"],
                    "djpk_pemda_selector": pemda,
                    "year": year,
                    "requested_url": url,
                    "final_url": final_url,
                    "http_status": status,
                    "jurisdiction_match": jurisdiction_ok,
                    "fiscal_year_match": year_ok,
                    "december_realization_semantics_match": december_ok,
                    "source_account_count": len(accounts),
                    "locked_contract_count": len(contracts),
                    "matched_contract_count": matched_contracts,
                    "missing_contracts": "|".join(missing_contracts),
                    "parse_failures": "|".join(parse_failures),
                    "response_sha256": response_sha256(body),
                    "page_pass": page_pass,
                }
            )
            raw_responses.append(
                {
                    "geography_id": geography["geography_id"],
                    "year": year,
                    "path": raw_path.as_posix(),
                    "sha256": response_sha256(body),
                }
            )

    expected_pages = 19 * len(years)
    if len(coverage_rows) != expected_pages:
        raise M25Stage1Error(f"M25 Stage1 expected {expected_pages} pages, got {len(coverage_rows)}")
    all_pass = all(bool(row["page_pass"]) for row in coverage_rows)
    if not all_pass:
        failures = [f"{row['djpk_pemda_selector']}/{row['year']}" for row in coverage_rows if not row["page_pass"]]
        raise M25Stage1Error(f"M25 Stage1 page qualification failures: {failures}")
    expected_values = expected_pages * len(contracts)
    if len(value_rows) != expected_values:
        raise M25Stage1Error(f"M25 Stage1 expected {expected_values} values, got {len(value_rows)}")

    write_csv(coverage_path, list(coverage_rows[0].keys()), coverage_rows)
    write_csv(values_path, list(value_rows[0].keys()), value_rows)
    manifest = {
        "schema": "ranah-observatory/milestone25-stage1-probe/v1",
        "milestone": 25,
        "stage": 1,
        "phase": "post_phase2_fiscal_evidence_expansion",
        "years": years,
        "geography_count": 19,
        "jurisdiction_year_page_count": expected_pages,
        "promoted_exact_label_family_count": len(contracts),
        "promoted_exact_label_families": [row["conceptual_family"] for row in contracts],
        "value_row_count": len(value_rows),
        "all_pages_pass": all_pass,
        "cross_geography_probe_completed_after_contract_lock": True,
        "explicit_bridge_used": False,
        "derived_ratio_created": False,
        "imputation_performed": False,
        "statistical_model_fit": False,
        "raw_responses": raw_responses,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe locked M25 DJPK Stage1 fiscal accounts across Sumbar geographies.")
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--contract-manifest", type=Path, default=DEFAULT_CONTRACT_MANIFEST)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--values", type=Path, default=DEFAULT_VALUES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--years", type=int, nargs="+", default=[PILOT_YEAR])
    args = parser.parse_args()
    try:
        years = sorted(set(args.years))
        if any(year < 2018 or year > 2025 for year in years):
            raise M25Stage1Error("M25 Stage1 years must stay within 2018-2025")
        result = run_probe(
            args.crosswalk,
            args.contracts,
            args.contract_manifest,
            args.coverage,
            args.values,
            args.manifest,
            args.raw_dir,
            years,
        )
    except (OSError, ValueError, RuntimeError, M25Stage1Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "years": result["years"],
        "jurisdiction_year_page_count": result["jurisdiction_year_page_count"],
        "promoted_exact_label_families": result["promoted_exact_label_families"],
        "value_row_count": result["value_row_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
