#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERIES = ROOT / "data" / "registries" / "bps_comparative_panel_series.csv"
DEFAULT_GEOS = ROOT / "data" / "registries" / "geographies.csv"
DEFAULT_RAW = ROOT / "data" / "raw" / "bps" / "comparative"
DEFAULT_OUTPUT = ROOT / "data" / "analysis" / "comparative"
COMPARABILITY_REGIME = "bps_current_38_province_2024plus"
EXPECTED_YEARS = (2024, 2025)
EXPECTED_INDICATORS = (
    "poverty_rate",
    "gini_ratio",
    "unemployment_rate",
    "underemployment_rate",
    "real_grdp_per_capita",
    "neet_rate",
)


class ComparativePanelError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()[:24]


def semantic_result_sha(snapshot: dict[str, Any]) -> str:
    result = snapshot.get("result")
    if not isinstance(result, dict):
        raise ComparativePanelError("BPS snapshot result must be an object")
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_provinces(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    rows = read_csv(path)
    by_source: dict[str, dict[str, str]] = {}
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("geography_level") != "province" or row.get("status") != "current":
            continue
        if row.get("parent_geography_id") != "idn":
            continue
        bps_code = row.get("bps_code", "")
        if len(bps_code) != 2 or not bps_code.isdigit():
            raise ComparativePanelError(f"current province {row.get('geography_id')} lacks a two-digit BPS code")
        source_code = bps_code + "00"
        if source_code in by_source:
            raise ComparativePanelError(f"duplicate current province source code {source_code}")
        by_source[source_code] = row
        by_id[row["geography_id"]] = row
    if len(by_source) != 38:
        raise ComparativePanelError(f"expected exactly 38 current Indonesian provinces; got {len(by_source)}")
    if "1300" not in by_source or by_source["1300"].get("geography_id") != "idn.13":
        raise ComparativePanelError("current province registry does not resolve BPS 1300 to idn.13")
    return by_source, by_id


def load_series(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    ids = [row.get("indicator_id", "") for row in rows]
    if tuple(ids) != EXPECTED_INDICATORS:
        raise ComparativePanelError(
            f"comparative series registry must contain exactly {EXPECTED_INDICATORS}; got {tuple(ids)}"
        )
    for row in rows:
        if row.get("qualification_status") != "qualified_current38":
            raise ComparativePanelError(f"series {row.get('series_id')} is not qualified_current38")
        if int(row["target_start_year"]) != EXPECTED_YEARS[0] or int(row["target_end_year"]) != EXPECTED_YEARS[-1]:
            raise ComparativePanelError(f"series {row.get('series_id')} does not use the 2024-2025 current-boundary window")
    return rows


def exact_selector_match(row: dict[str, str], contract: dict[str, str]) -> bool:
    return (
        row.get("bps_turvar_id", "") == contract.get("selected_turvar_id", "")
        and row.get("bps_turvar_label", "") == contract.get("selected_turvar_label", "")
        and row.get("bps_turth_id", "") == contract.get("selected_turth_id", "")
        and row.get("bps_turth_label", "") == contract.get("selected_turth_label", "")
    )


def transform_value(raw: str, transform: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise ComparativePanelError(f"non-numeric BPS value {raw!r}") from exc
    if not math.isfinite(value):
        raise ComparativePanelError(f"non-finite BPS value {raw!r}")
    if transform == "identity":
        return value
    if transform == "divide_1000":
        return value / 1000.0
    raise ComparativePanelError(f"unsupported transform {transform!r}")


def snapshot_contract(raw_root: Path, var_id: str, year: int, contract: dict[str, str]) -> dict[str, Any]:
    series_dir = raw_root / f"var-{var_id}"
    snapshot_path = series_dir / f"var-{var_id}-{year}.json"
    checksum_path = snapshot_path.with_suffix(snapshot_path.suffix + ".sha256")
    manifest_path = series_dir / f"var-{var_id}-manifest.json"
    if not snapshot_path.exists() or not checksum_path.exists() or not manifest_path.exists():
        raise ComparativePanelError(f"missing frozen BPS source artifacts for var={var_id} year={year}")
    actual_sha = file_sha256(snapshot_path)
    checksum_text = checksum_path.read_text(encoding="utf-8").strip().split()[0]
    if checksum_text != actual_sha:
        raise ComparativePanelError(f"snapshot checksum mismatch for {snapshot_path}")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    semantic_sha = semantic_result_sha(snapshot)
    result = snapshot.get("result") or {}
    variables = result.get("var") if isinstance(result, dict) else None
    if not isinstance(variables, list) or not variables or not isinstance(variables[0], dict):
        raise ComparativePanelError(f"snapshot lacks variable metadata: {snapshot_path}")
    variable = variables[0]
    source_title = str(variable.get("label", "") or "").strip()
    source_unit = str(variable.get("unit", "") or "").strip()
    source_note = str(variable.get("note", "") or "").strip()
    expected_source_unit = contract.get("source_unit", "")
    if expected_source_unit and source_unit.casefold() != expected_source_unit.casefold():
        raise ComparativePanelError(
            f"source unit drift for {contract['series_id']}: {source_unit!r} != {expected_source_unit!r}"
        )
    retrieved_at = str(snapshot.get("retrieved_at_utc", "") or "")
    return {
        "snapshot_path": snapshot_path,
        "snapshot_sha256": actual_sha,
        "semantic_result_sha256": semantic_sha,
        "manifest_path": manifest_path,
        "retrieved_at_utc": retrieved_at,
        "source_title": source_title,
        "source_unit": source_unit,
        "source_note": source_note,
    }


def materialize(series_path: Path, geography_path: Path, raw_root: Path, output_dir: Path) -> dict[str, Any]:
    contracts = load_series(series_path)
    source_geos, canonical_geos = current_provinces(geography_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    long_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    seen_panel_keys: set[tuple[str, str, int]] = set()
    coverage: dict[tuple[str, int], set[str]] = defaultdict(set)

    for contract in contracts:
        var_id = contract["bps_var_id"]
        series_dir = raw_root / f"var-{var_id}"
        long_path = series_dir / f"var-{var_id}-long.csv"
        if not long_path.exists():
            raise ComparativePanelError(f"missing normalized BPS source series {long_path}")
        source_rows = read_csv(long_path)

        for year in EXPECTED_YEARS:
            source = snapshot_contract(raw_root, var_id, year, contract)
            selected = [
                row
                for row in source_rows
                if row.get("bps_th_label") == str(year)
                and row.get("bps_var_id") == var_id
                and exact_selector_match(row, contract)
                and row.get("bps_vervar_id") in source_geos
            ]
            by_geography: dict[str, dict[str, str]] = {}
            for row in selected:
                source_code = row["bps_vervar_id"]
                if source_code in by_geography:
                    raise ComparativePanelError(
                        f"duplicate selected source row for {contract['series_id']} year={year} geography={source_code}"
                    )
                if "provinsi" not in row.get("bps_vertical_dimension", "").casefold():
                    raise ComparativePanelError(
                        f"vertical geography drift for {contract['series_id']} year={year}: {row.get('bps_vertical_dimension')!r}"
                    )
                by_geography[source_code] = row

            if set(by_geography) != set(source_geos):
                missing = sorted(set(source_geos) - set(by_geography))
                unexpected = sorted(set(by_geography) - set(source_geos))
                raise ComparativePanelError(
                    f"current-38 footprint mismatch for {contract['series_id']} {year}; missing={missing}; unexpected={unexpected}"
                )

            provenance_id = stable_id(
                "m5prov_",
                contract["series_id"],
                year,
                source["semantic_result_sha256"],
                contract["selected_turvar_id"],
                contract["selected_turth_id"],
                contract["transform"],
            )
            provenance_rows.append(
                {
                    "panel_provenance_id": provenance_id,
                    "source_series_id": contract["series_id"],
                    "indicator_id": contract["indicator_id"],
                    "bps_var_id": var_id,
                    "year": year,
                    "source_snapshot": source["snapshot_path"].relative_to(ROOT).as_posix(),
                    "source_snapshot_sha256": source["snapshot_sha256"],
                    "semantic_result_sha256": source["semantic_result_sha256"],
                    "source_manifest": source["manifest_path"].relative_to(ROOT).as_posix(),
                    "retrieved_at_utc": source["retrieved_at_utc"],
                    "source_title": source["source_title"],
                    "source_unit": source["source_unit"],
                    "source_note": source["source_note"],
                    "selected_turvar_id": contract["selected_turvar_id"],
                    "selected_turvar_label": contract["selected_turvar_label"],
                    "selected_turth_id": contract["selected_turth_id"],
                    "selected_turth_label": contract["selected_turth_label"],
                    "transform": contract["transform"],
                    "comparability_regime": COMPARABILITY_REGIME,
                }
            )

            for source_code in sorted(by_geography):
                source_row = by_geography[source_code]
                geo = source_geos[source_code]
                geography_id = geo["geography_id"]
                key = (contract["indicator_id"], geography_id, year)
                if key in seen_panel_keys:
                    raise ComparativePanelError(f"duplicate panel key {key}")
                seen_panel_keys.add(key)
                value = transform_value(source_row["value"], contract["transform"])
                if contract["canonical_unit"] in {"percent", "index"} and not (0 <= value <= 100):
                    raise ComparativePanelError(f"out-of-range value for {key}: {value}")
                if contract["canonical_unit"] == "index" and not (0 <= value <= 1):
                    raise ComparativePanelError(f"out-of-range Gini index for {key}: {value}")
                coverage[(contract["indicator_id"], year)].add(geography_id)
                long_rows.append(
                    {
                        "panel_observation_id": stable_id("m5obs_", *key, contract["reference_period"]),
                        "indicator_id": contract["indicator_id"],
                        "geography_id": geography_id,
                        "geography_name": geo["canonical_name"],
                        "bps_province_code": geo["bps_code"],
                        "year": year,
                        "reference_period": contract["reference_period"],
                        "value_numeric": format(value, ".15g"),
                        "unit": contract["canonical_unit"],
                        "claim_type": contract["claim_type"],
                        "source_series_id": contract["series_id"],
                        "panel_provenance_id": provenance_id,
                        "comparability_regime": COMPARABILITY_REGIME,
                        "methodology_version": contract["methodology_version"],
                        "price_basis": contract["price_basis"],
                        "notes": (
                            f"BPS national domain 0000; source vertical={source_row.get('bps_vertical_dimension')}; "
                            f"source selector=turvar:{contract['selected_turvar_id']}:{contract['selected_turvar_label']}|"
                            f"turtahun:{contract['selected_turth_id']}:{contract['selected_turth_label']}; "
                            f"source universe={contract['source_universe']}; transform={contract['transform']}; "
                            f"current-boundary panel begins 2024 to avoid silent pre-DOB Papua harmonization"
                        ),
                    }
                )

    expected_row_count = len(EXPECTED_INDICATORS) * len(EXPECTED_YEARS) * len(source_geos)
    if len(long_rows) != expected_row_count:
        raise ComparativePanelError(f"expected {expected_row_count} panel observations; got {len(long_rows)}")
    if len(provenance_rows) != len(EXPECTED_INDICATORS) * len(EXPECTED_YEARS):
        raise ComparativePanelError("unexpected comparative provenance cardinality")
    for indicator_id in EXPECTED_INDICATORS:
        for year in EXPECTED_YEARS:
            if coverage[(indicator_id, year)] != set(canonical_geos):
                raise ComparativePanelError(f"coverage gate failed for {indicator_id} {year}")

    long_rows.sort(key=lambda row: (row["year"], row["geography_id"], row["indicator_id"]))
    provenance_rows.sort(key=lambda row: (row["year"], row["indicator_id"]))

    long_path = output_dir / "bps-current38-province-panel-long.csv"
    prov_path = output_dir / "bps-current38-province-panel-provenance.csv"
    wide_path = output_dir / "bps-current38-province-panel-wide.csv"
    manifest_path = output_dir / "bps-current38-province-panel.manifest.json"

    long_fields = [
        "panel_observation_id", "indicator_id", "geography_id", "geography_name", "bps_province_code",
        "year", "reference_period", "value_numeric", "unit", "claim_type", "source_series_id",
        "panel_provenance_id", "comparability_regime", "methodology_version", "price_basis", "notes",
    ]
    with long_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=long_fields)
        writer.writeheader()
        writer.writerows(long_rows)

    prov_fields = [
        "panel_provenance_id", "source_series_id", "indicator_id", "bps_var_id", "year", "source_snapshot",
        "source_snapshot_sha256", "semantic_result_sha256", "source_manifest", "retrieved_at_utc", "source_title",
        "source_unit", "source_note", "selected_turvar_id", "selected_turvar_label", "selected_turth_id",
        "selected_turth_label", "transform", "comparability_regime",
    ]
    with prov_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=prov_fields)
        writer.writeheader()
        writer.writerows(provenance_rows)

    values_by_geo_year: dict[tuple[str, int], dict[str, str]] = defaultdict(dict)
    for row in long_rows:
        values_by_geo_year[(str(row["geography_id"]), int(row["year"]))][str(row["indicator_id"])] = str(row["value_numeric"])
    wide_fields = ["geography_id", "geography_name", "bps_province_code", "year", *EXPECTED_INDICATORS]
    wide_rows: list[dict[str, Any]] = []
    for year in EXPECTED_YEARS:
        for geography_id in sorted(canonical_geos):
            geo = canonical_geos[geography_id]
            values = values_by_geo_year[(geography_id, year)]
            if set(values) != set(EXPECTED_INDICATORS):
                raise ComparativePanelError(f"wide panel is incomplete for {geography_id} {year}")
            wide_rows.append(
                {
                    "geography_id": geography_id,
                    "geography_name": geo["canonical_name"],
                    "bps_province_code": geo["bps_code"],
                    "year": year,
                    **values,
                }
            )
    with wide_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=wide_fields)
        writer.writeheader()
        writer.writerows(wide_rows)

    manifest = {
        "schema": "ranah-observatory/milestone5-comparative-panel/v1",
        "criterion": "a comparative Indonesian panel where feasible",
        "comparability_regime": COMPARABILITY_REGIME,
        "geography_level": "province",
        "geography_count": len(canonical_geos),
        "years": list(EXPECTED_YEARS),
        "indicator_ids": list(EXPECTED_INDICATORS),
        "indicator_count": len(EXPECTED_INDICATORS),
        "panel_observation_count": len(long_rows),
        "panel_provenance_count": len(provenance_rows),
        "wide_row_count": len(wide_rows),
        "west_sumatra_complete": all(
            (indicator_id, "idn.13", year) in seen_panel_keys
            for indicator_id in EXPECTED_INDICATORS
            for year in EXPECTED_YEARS
        ),
        "source_domain": "0000",
        "source_authority": "Badan Pusat Statistik (BPS-Statistics Indonesia)",
        "boundary_policy": (
            "Use the current 38-province footprint only for 2024-2025; do not silently backcast the four post-DOB "
            "Papua provinces or split pre-2024 Papua/Papua Barat observations."
        ),
        "units": {row["indicator_id"]: row["canonical_unit"] for row in contracts},
        "files": {
            "long": long_path.relative_to(ROOT).as_posix(),
            "wide": wide_path.relative_to(ROOT).as_posix(),
            "provenance": prov_path.relative_to(ROOT).as_posix(),
        },
        "milestone5_complete": True,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the Milestone 5 current-38 Indonesian province comparison panel.")
    parser.add_argument("--series-registry", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--geography-registry", type=Path, default=DEFAULT_GEOS)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        manifest = materialize(args.series_registry, args.geography_registry, args.raw_root, args.output_dir)
    except (ComparativePanelError, OSError, ValueError, json.JSONDecodeError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
