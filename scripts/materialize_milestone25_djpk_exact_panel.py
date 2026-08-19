#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from probe_milestone25_djpk_stage1 import (
    HTMLTableParser,
    M25Stage1Error,
    find_postur_table,
    normalize_label,
    parse_djpk_money_to_idr_billion,
    table_to_accounts,
)

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"
CONTRACTS = ROOT / "data/registries/djpk_m25_stage1_account_contracts.csv"
CONTRACT_MANIFEST = ROOT / "data/manifests/milestone25_stage1_contracts.json"
COVERAGE = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv"
PROBE_VALUES = ROOT / "data/analysis/engine/djpk_finance_v1/m25-stage1-full-values.csv"
RAW_ROOT = ROOT / "data/processed/djpk/public_finance/source"
OUT_DIR = ROOT / "data/processed/djpk/public_finance"
OBS_OUT = OUT_DIR / "djpk-fiscal-canonical-observations.csv"
PROV_OUT = OUT_DIR / "djpk-fiscal-provenance.csv"
MANIFEST_OUT = OUT_DIR / "djpk-fiscal-panel.manifest.json"

YEARS = list(range(2018, 2026))
REGIME_ID = "sumbar_current_kabkota_djpk_realization_2018_2025_v1"


class M25MaterializationError(RuntimeError):
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()[:24]


def load_contracts() -> list[dict[str, str]]:
    manifest = json.loads(CONTRACT_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ranah-observatory/milestone25-stage1-account-contracts/v1":
        raise M25MaterializationError("unexpected Stage1 contract manifest")
    if manifest.get("contracts_locked") is not True:
        raise M25MaterializationError("Stage1 contracts not locked")
    if manifest.get("cross_geography_values_inspected_before_lock") is not False:
        raise M25MaterializationError("contracts were not locked before cross-geography extraction")
    rows = read_csv(CONTRACTS)
    promoted = [row for row in rows if row["stage1_promotion_status"] == "promoted_exact_label"]
    if not promoted:
        raise M25MaterializationError("no exact-label contracts promoted")
    if len(promoted) != manifest.get("promoted_exact_label_family_count"):
        raise M25MaterializationError("promoted contract cardinality drift")
    for row in promoted:
        if row["taxonomy_contract_type"] != "exact_label" or not row["locked_source_label_normalized"]:
            raise M25MaterializationError("non-exact contract reached exact-panel materializer")
    return promoted


def validate_crosswalk() -> list[dict[str, str]]:
    rows = read_csv(CROSSWALK)
    if len(rows) != 19 or len({row["geography_id"] for row in rows}) != 19:
        raise M25MaterializationError("DJPK crosswalk footprint drift")
    if {row["djpk_pemda_selector"] for row in rows} != {f"{value:02d}" for value in range(1, 20)}:
        raise M25MaterializationError("DJPK selector set drift")
    return sorted(rows, key=lambda row: int(row["djpk_pemda_selector"]))


def materialize() -> dict[str, Any]:
    contracts = load_contracts()
    crosswalk = validate_crosswalk()
    coverage = read_csv(COVERAGE)
    probe_values = read_csv(PROBE_VALUES)

    if len(coverage) != 19 * 8:
        raise M25MaterializationError(f"expected 152 full-probe pages, got {len(coverage)}")
    if any(row["page_pass"] != "True" for row in coverage):
        raise M25MaterializationError("full probe contains a failed jurisdiction-year")
    coverage_by_key = {(row["geography_id"], int(row["year"])): row for row in coverage}
    if len(coverage_by_key) != 152:
        raise M25MaterializationError("duplicate full-probe coverage keys")

    expected_probe_values = 152 * len(contracts)
    if len(probe_values) != expected_probe_values:
        raise M25MaterializationError(
            f"probe value count drift: expected {expected_probe_values}, got {len(probe_values)}"
        )
    probe_value_by_key = {
        (row["geography_id"], int(row["year"]), row["conceptual_family"]): row
        for row in probe_values
    }
    if len(probe_value_by_key) != expected_probe_values:
        raise M25MaterializationError("duplicate Stage1 probe value keys")

    observations: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []

    for geography in crosswalk:
        geography_id = geography["geography_id"]
        pemda = geography["djpk_pemda_selector"]
        for year in YEARS:
            coverage_row = coverage_by_key.get((geography_id, year))
            if coverage_row is None:
                raise M25MaterializationError(f"missing coverage {geography_id}/{year}")
            raw_path = RAW_ROOT / f"pemda-{pemda}-{year}-desember.html"
            if not raw_path.exists():
                raise M25MaterializationError(f"missing frozen DJPK page {raw_path}")
            actual_sha = sha256(raw_path)
            if actual_sha != coverage_row["response_sha256"]:
                raise M25MaterializationError(f"DJPK page hash drift {geography_id}/{year}")

            body = raw_path.read_bytes()
            parser = HTMLTableParser()
            parser.feed(body.decode("utf-8", errors="replace"))
            header, source_rows = find_postur_table(parser.tables)
            accounts = table_to_accounts(header, source_rows)
            by_label = {row["account_label_normalized"]: row for row in accounts}

            provenance_id = stable_id("m25prov_", geography_id, year, actual_sha)
            provenance.append(
                {
                    "fiscal_provenance_id": provenance_id,
                    "geography_id": geography_id,
                    "canonical_name": geography["canonical_name"],
                    "djpk_province_selector": geography["djpk_province_selector"],
                    "djpk_pemda_selector": pemda,
                    "year": year,
                    "period_selector": "12",
                    "reference_period": "realisasi_s.d._desember",
                    "source_snapshot": raw_path.relative_to(ROOT).as_posix(),
                    "source_snapshot_sha256": actual_sha,
                    "source_url": coverage_row["final_url"],
                    "claim_type": "observed_recorded_fiscal_realization",
                    "comparability_regime": REGIME_ID,
                }
            )

            for contract in contracts:
                family = contract["conceptual_family"]
                label = contract["locked_source_label_normalized"]
                source = by_label.get(label)
                if source is None:
                    raise M25MaterializationError(f"locked source label missing {family} {geography_id}/{year}")
                amount = parse_djpk_money_to_idr_billion(source["realization_raw"])
                probe_row = probe_value_by_key.get((geography_id, year, family))
                if probe_row is None:
                    raise M25MaterializationError(f"probe value missing {family} {geography_id}/{year}")
                probe_amount = Decimal(probe_row["realization_idr_billion"])
                if amount != probe_amount:
                    raise M25MaterializationError(
                        f"raw/probe realization mismatch {family} {geography_id}/{year}: {amount} != {probe_amount}"
                    )
                if normalize_label(source["account_label"]) != label:
                    raise M25MaterializationError("source-label normalization drift")
                observations.append(
                    {
                        "observation_id": stable_id("m25obs_", family, geography_id, year),
                        "fiscal_account_id": family,
                        "geography_id": geography_id,
                        "geography_name": geography["canonical_name"],
                        "djpk_province_selector": geography["djpk_province_selector"],
                        "djpk_pemda_selector": pemda,
                        "year": year,
                        "reference_period": "realisasi_s.d._desember",
                        "source_account_label": source["account_label"],
                        "realization_idr_billion": format(amount, "f"),
                        "unit": "IDR_billion",
                        "claim_type": "observed_recorded_fiscal_realization",
                        "taxonomy_contract_type": "exact_label",
                        "taxonomy_contract_status": contract["stage1_promotion_status"],
                        "fiscal_provenance_id": provenance_id,
                        "comparability_regime": REGIME_ID,
                        "imputation_performed": False,
                        "historical_boundary_reconstruction_performed": False,
                    }
                )

    observations.sort(key=lambda row: (row["fiscal_account_id"], row["geography_id"], row["year"]))
    provenance.sort(key=lambda row: (row["geography_id"], row["year"]))
    expected_observations = 152 * len(contracts)
    if len(observations) != expected_observations:
        raise M25MaterializationError("canonical fiscal observation count drift")
    if len(provenance) != 152:
        raise M25MaterializationError("fiscal provenance count drift")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OBS_OUT, list(observations[0].keys()), observations)
    write_csv(PROV_OUT, list(provenance[0].keys()), provenance)

    held_rows = [row for row in read_csv(CONTRACTS) if row["stage1_promotion_status"] != "promoted_exact_label"]
    manifest = {
        "schema": "ranah-observatory/djpk-fiscal-panel/v1",
        "milestone": 25,
        "source_id": "djpk_sikd_apbd_portal",
        "comparability_regime": REGIME_ID,
        "geography_level": "kabupaten_kota",
        "geography_count": 19,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "jurisdiction_year_count": 152,
        "promoted_exact_label_family_count": len(contracts),
        "promoted_exact_label_families": [row["conceptual_family"] for row in contracts],
        "held_family_count": len(held_rows),
        "held_families": [row["conceptual_family"] for row in held_rows],
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "derived_ratio_count": 0,
        "explicit_bridge_used": False,
        "imputation_performed": False,
        "historical_boundary_reconstruction_performed": False,
        "statistical_model_fit": False,
        "inputs": {
            "crosswalk": {"path": CROSSWALK.relative_to(ROOT).as_posix(), "sha256": sha256(CROSSWALK)},
            "account_contracts": {"path": CONTRACTS.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACTS)},
            "account_contract_manifest": {"path": CONTRACT_MANIFEST.relative_to(ROOT).as_posix(), "sha256": sha256(CONTRACT_MANIFEST)},
            "full_probe_coverage": {"path": COVERAGE.relative_to(ROOT).as_posix(), "sha256": sha256(COVERAGE)},
            "full_probe_values": {"path": PROBE_VALUES.relative_to(ROOT).as_posix(), "sha256": sha256(PROBE_VALUES)},
        },
        "outputs": {
            "canonical_observations": {"path": OBS_OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OBS_OUT)},
            "provenance": {"path": PROV_OUT.relative_to(ROOT).as_posix(), "sha256": sha256(PROV_OUT)},
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    try:
        manifest = materialize()
    except (OSError, json.JSONDecodeError, ValueError, M25MaterializationError, M25Stage1Error) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({
        "promoted_exact_label_families": manifest["promoted_exact_label_families"],
        "observation_count": manifest["observation_count"],
        "held_families": manifest["held_families"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
