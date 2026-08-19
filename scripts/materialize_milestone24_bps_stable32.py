#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE = ROOT / "data/manifests/milestone24_bps_stable32_probe.json"
DEFAULT_SERIES = ROOT / "data/registries/bps_comparative_panel_series.csv"
DEFAULT_GEOS = ROOT / "data/registries/geographies.csv"
DEFAULT_RAW = ROOT / "data/processed/bps/comparative_stable32/source"
DEFAULT_OUTPUT = ROOT / "data/processed/bps/comparative_stable32"
YEARS = list(range(2018, 2026))
EXCLUDED_CODES = {"91", "92", "94", "95", "96", "97"}
REGIME_ID = "bps_stable32_province_2018_2025_v1"


class M24MaterializationError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
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


def transform_value(raw: str, transform: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise M24MaterializationError(f"non-numeric BPS value {raw!r}") from exc
    if not math.isfinite(value):
        raise M24MaterializationError(f"non-finite BPS value {raw!r}")
    if transform == "identity":
        return value
    if transform == "divide_1000":
        return value / 1000.0
    raise M24MaterializationError(f"unsupported transform {transform!r}")


def current_stable32(path: Path) -> dict[str, dict[str, str]]:
    stable: dict[str, dict[str, str]] = {}
    excluded = 0
    for row in read_csv(path):
        if row.get("geography_level") != "province" or row.get("status") != "current" or row.get("parent_geography_id") != "idn":
            continue
        code = row.get("bps_code", "")
        if len(code) != 2 or not code.isdigit():
            raise M24MaterializationError(f"invalid province BPS code {code!r}")
        if code in EXCLUDED_CODES:
            excluded += 1
            continue
        source_code = code + "00"
        if source_code in stable:
            raise M24MaterializationError(f"duplicate stable32 source code {source_code}")
        stable[source_code] = row
    if len(stable) != 32 or excluded != 6:
        raise M24MaterializationError(f"stable32 geography contract drift: stable={len(stable)} excluded={excluded}")
    if stable.get("1300", {}).get("geography_id") != "idn.13":
        raise M24MaterializationError("West Sumatra missing from stable32")
    return dict(sorted(stable.items()))


def exact_selector(row: dict[str, str], contract: dict[str, str]) -> bool:
    return (
        row.get("bps_turvar_id", "") == contract["selected_turvar_id"]
        and row.get("bps_turvar_label", "") == contract["selected_turvar_label"]
        and row.get("bps_turth_id", "") == contract["selected_turth_id"]
        and row.get("bps_turth_label", "") == contract["selected_turth_label"]
    )


def qualified_contracts(probe_path: Path, series_path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    if probe.get("schema") != "ranah-observatory/milestone24-bps-stable32-probe/v1":
        raise M24MaterializationError("unexpected M24 probe schema")
    if probe.get("candidate_year_probe_count") != 48 or probe.get("stable_geography_count") != 32:
        raise M24MaterializationError("M24 probe footprint drift")
    if probe.get("selector_search_after_probe_performed") is not False:
        raise M24MaterializationError("M24 probe indicates selector search")
    qualified_ids = list(probe.get("qualified_series_ids", []))
    by_id = {row["series_id"]: row for row in read_csv(series_path)}
    missing = [series_id for series_id in qualified_ids if series_id not in by_id]
    if missing:
        raise M24MaterializationError(f"qualified M24 series missing registry contracts: {missing}")
    contracts = [by_id[series_id] for series_id in qualified_ids]
    return probe, contracts


def snapshot_contract(raw_root: Path, var_id: str, year: int) -> dict[str, Any]:
    series_dir = raw_root / f"var-{var_id}"
    snapshot_path = series_dir / f"var-{var_id}-{year}.json"
    checksum_path = snapshot_path.with_suffix(snapshot_path.suffix + ".sha256")
    manifest_path = series_dir / f"var-{var_id}-manifest.json"
    long_path = series_dir / f"var-{var_id}-long.csv"
    for path in (snapshot_path, checksum_path, manifest_path, long_path):
        if not path.exists():
            raise M24MaterializationError(f"missing frozen M24 source artifact {path}")
    actual_sha = sha256(snapshot_path)
    checksum_sha = checksum_path.read_text(encoding="utf-8").strip().split()[0]
    if checksum_sha != actual_sha:
        raise M24MaterializationError(f"snapshot checksum mismatch: {snapshot_path}")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    result = snapshot.get("result")
    if not isinstance(result, dict):
        raise M24MaterializationError("snapshot result must be an object")
    semantic_sha = hashlib.sha256(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "snapshot_path": snapshot_path,
        "snapshot_sha256": actual_sha,
        "semantic_result_sha256": semantic_sha,
        "manifest_path": manifest_path,
        "long_path": long_path,
        "retrieved_at_utc": str(snapshot.get("retrieved_at_utc", "")),
    }


def materialize(probe_path: Path, series_path: Path, geos_path: Path, raw_root: Path, output_dir: Path) -> dict[str, Any]:
    probe, contracts = qualified_contracts(probe_path, series_path)
    stable = current_stable32(geos_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    observations: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    seen_obs: set[tuple[str, str, int]] = set()

    for contract in contracts:
        var_id = contract["bps_var_id"]
        source_rows = read_csv(raw_root / f"var-{var_id}" / f"var-{var_id}-long.csv")
        for year in YEARS:
            source = snapshot_contract(raw_root, var_id, year)
            selected = [
                row for row in source_rows
                if row.get("bps_var_id") == var_id
                and row.get("bps_th_label") == str(year)
                and exact_selector(row, contract)
                and row.get("bps_vervar_id") in stable
            ]
            by_code: dict[str, dict[str, str]] = {}
            for row in selected:
                code = row["bps_vervar_id"]
                if code in by_code:
                    raise M24MaterializationError(f"duplicate stable32 source row {contract['series_id']} {year} {code}")
                if "provinsi" not in row.get("bps_vertical_dimension", "").casefold():
                    raise M24MaterializationError(f"vertical geography drift {contract['series_id']} {year}")
                by_code[code] = row
            if set(by_code) != set(stable):
                missing = sorted(set(stable) - set(by_code))
                unexpected = sorted(set(by_code) - set(stable))
                raise M24MaterializationError(
                    f"stable32 footprint mismatch {contract['series_id']} {year}: missing={missing} unexpected={unexpected}"
                )

            prov_id = stable_id(
                "m24prov_", contract["series_id"], year, source["semantic_result_sha256"],
                contract["selected_turvar_id"], contract["selected_turth_id"], contract["transform"]
            )
            provenance.append({
                "panel_provenance_id": prov_id,
                "source_series_id": contract["series_id"],
                "indicator_id": contract["indicator_id"],
                "bps_var_id": var_id,
                "year": year,
                "source_snapshot": source["snapshot_path"].relative_to(ROOT).as_posix(),
                "source_snapshot_sha256": source["snapshot_sha256"],
                "semantic_result_sha256": source["semantic_result_sha256"],
                "source_manifest": source["manifest_path"].relative_to(ROOT).as_posix(),
                "retrieved_at_utc": source["retrieved_at_utc"],
                "selected_turvar_id": contract["selected_turvar_id"],
                "selected_turvar_label": contract["selected_turvar_label"],
                "selected_turth_id": contract["selected_turth_id"],
                "selected_turth_label": contract["selected_turth_label"],
                "transform": contract["transform"],
                "reference_period": contract["reference_period"],
                "methodology_version": contract["methodology_version"],
                "comparability_regime": REGIME_ID,
            })

            for source_code, geo in stable.items():
                source_row = by_code[source_code]
                value = transform_value(source_row["value"], contract["transform"])
                key = (contract["indicator_id"], geo["geography_id"], year)
                if key in seen_obs:
                    raise M24MaterializationError(f"duplicate canonical observation {key}")
                seen_obs.add(key)
                observations.append({
                    "observation_id": stable_id("m24obs_", *key, contract["reference_period"]),
                    "indicator_id": contract["indicator_id"],
                    "geography_id": geo["geography_id"],
                    "geography_name": geo["canonical_name"],
                    "bps_province_code": geo["bps_code"],
                    "year": year,
                    "reference_period": contract["reference_period"],
                    "value_numeric": format(value, ".15g"),
                    "unit": contract["canonical_unit"],
                    "claim_type": contract["claim_type"],
                    "source_series_id": contract["series_id"],
                    "panel_provenance_id": prov_id,
                    "comparability_regime": REGIME_ID,
                    "methodology_version": contract["methodology_version"],
                    "price_basis": contract["price_basis"],
                    "geographic_backcasting_performed": False,
                    "imputation_performed": False,
                })

    observations.sort(key=lambda row: (row["indicator_id"], row["geography_id"], row["year"]))
    provenance.sort(key=lambda row: (row["indicator_id"], row["year"]))

    obs_path = output_dir / "bps-stable32-canonical-observations.csv"
    prov_path = output_dir / "bps-stable32-provenance.csv"
    manifest_path = output_dir / "bps-stable32.manifest.json"

    if observations:
        write_csv(obs_path, list(observations[0].keys()), observations)
    else:
        write_csv(obs_path, [
            "observation_id", "indicator_id", "geography_id", "geography_name", "bps_province_code", "year",
            "reference_period", "value_numeric", "unit", "claim_type", "source_series_id", "panel_provenance_id",
            "comparability_regime", "methodology_version", "price_basis", "geographic_backcasting_performed", "imputation_performed"
        ], [])
    if provenance:
        write_csv(prov_path, list(provenance[0].keys()), provenance)
    else:
        write_csv(prov_path, [
            "panel_provenance_id", "source_series_id", "indicator_id", "bps_var_id", "year", "source_snapshot",
            "source_snapshot_sha256", "semantic_result_sha256", "source_manifest", "retrieved_at_utc",
            "selected_turvar_id", "selected_turvar_label", "selected_turth_id", "selected_turth_label", "transform",
            "reference_period", "methodology_version", "comparability_regime"
        ], [])

    expected_count = len(contracts) * 32 * 8
    if len(observations) != expected_count:
        raise M24MaterializationError(f"expected {expected_count} stable32 observations, got {len(observations)}")
    if len(provenance) != len(contracts) * 8:
        raise M24MaterializationError("unexpected M24 provenance cardinality")

    manifest = {
        "schema": "ranah-observatory/bps-stable32-comparator/v1",
        "milestone": 24,
        "source_id": "bps_webapi",
        "domain": "0000",
        "comparability_regime": REGIME_ID,
        "start_year": 2018,
        "end_year": 2025,
        "year_count": 8,
        "geography_level": "province",
        "geography_count": 32,
        "excluded_current_papua_bps_codes": sorted(EXCLUDED_CODES),
        "qualified_series_count": len(contracts),
        "qualified_series_ids": [contract["series_id"] for contract in contracts],
        "indicator_ids": [contract["indicator_id"] for contract in contracts],
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "probe_qualified_candidate_count": probe["qualified_candidate_count"],
        "imputation_performed": False,
        "geographic_backcasting_performed": False,
        "province_district_model_pooling_performed": False,
        "credential_persisted": False,
        "inputs": {
            "probe": {"path": probe_path.relative_to(ROOT).as_posix(), "sha256": sha256(probe_path)},
            "series_registry": {"path": series_path.relative_to(ROOT).as_posix(), "sha256": sha256(series_path)},
            "geography_registry": {"path": geos_path.relative_to(ROOT).as_posix(), "sha256": sha256(geos_path)},
        },
        "outputs": {
            "canonical_observations": {"path": obs_path.relative_to(ROOT).as_posix(), "sha256": sha256(obs_path)},
            "provenance": {"path": prov_path.relative_to(ROOT).as_posix(), "sha256": sha256(prov_path)},
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize probe-qualified M24 BPS stable32 comparator series.")
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--series", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOS)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        manifest = materialize(args.probe, args.series, args.geographies, args.raw_root, args.output_dir)
    except (OSError, json.JSONDecodeError, M24MaterializationError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({
        "qualified_series_count": manifest["qualified_series_count"],
        "observation_count": manifest["observation_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
