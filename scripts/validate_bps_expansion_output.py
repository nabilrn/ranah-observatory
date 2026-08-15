#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

EXPECTED_SERIES_ROWS = {
    "underemployment_regency": 140,
    "inequality_gini": 8,
    "agriculture_share_adhb": 120,
    "manufacturing_share_adhb": 120,
    "rice_yield_ksa": 160,
    "export_value_port_loading": 6,
    "population_sp2020": 20,
}
EXPECTED_INDICATORS = {
    "underemployment_rate",
    "gini_ratio",
    "agriculture_share_grdp",
    "manufacturing_share_grdp",
    "rice_yield",
    "export_value",
    "population_total",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    source_csv = root / "bps-expansion-source-panel.csv"
    source_manifest_path = root / "bps-expansion-source-panel.manifest.json"
    canonical_dir = root / "canonical"
    obs_path = canonical_dir / "bps-expansion-canonical-observations.csv"
    prov_path = canonical_dir / "bps-expansion-canonical-provenance.csv"
    held_path = canonical_dir / "bps-expansion-held-source-native.csv"
    canonical_manifest_path = canonical_dir / "bps-expansion-canonical.manifest.json"
    for path in (source_csv, source_manifest_path, obs_path, prov_path, held_path, canonical_manifest_path):
        if not path.is_file():
            errors.append(f"missing expansion artifact {path.relative_to(root)}")
    if errors:
        return errors, {"source": 0, "canonical": 0, "held": 0, "provenance": 0}

    source_rows = read_csv(source_csv)
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    observations = read_csv(obs_path)
    provenance = read_csv(prov_path)
    held = read_csv(held_path)
    manifest = json.loads(canonical_manifest_path.read_text(encoding="utf-8"))

    if len(source_rows) != 726 or source_manifest.get("row_count") != 726:
        errors.append(f"source expansion must contain 726 rows, csv={len(source_rows)} manifest={source_manifest.get('row_count')}")
    if source_manifest.get("series_count") != 7:
        errors.append("source expansion must contain 7 logical series")
    if source_manifest.get("panel_csv_sha256") != sha(source_csv):
        errors.append("source expansion CSV checksum mismatch")
    source_ids = [row["expansion_row_id"] for row in source_rows]
    if len(source_ids) != len(set(source_ids)):
        errors.append("source expansion row IDs are not unique")

    if len(observations) != 574 or manifest.get("observation_count") != 574:
        errors.append(f"canonical expansion must contain 574 observations, csv={len(observations)} manifest={manifest.get('observation_count')}")
    if len(held) != 152 or manifest.get("held_source_native_count") != 152:
        errors.append(f"held expansion must contain 152 rows, csv={len(held)} manifest={manifest.get('held_source_native_count')}")
    if len(provenance) != 36 or manifest.get("provenance_count") != 36:
        errors.append(f"expansion provenance must contain 36 records, csv={len(provenance)} manifest={manifest.get('provenance_count')}")
    if manifest.get("canonical_series_count") != 7:
        errors.append("all seven logical expansion series must contribute canonical observations")
    if manifest.get("series_rows") != EXPECTED_SERIES_ROWS:
        errors.append(f"canonical expansion row counts changed: {manifest.get('series_rows')!r}")
    if manifest.get("held_series") != ["inequality_gini"]:
        errors.append("only local Gini rows may remain held in this expansion")
    if manifest.get("observations_sha256") != sha(obs_path):
        errors.append("canonical expansion observation checksum mismatch")
    if manifest.get("provenance_sha256") != sha(prov_path):
        errors.append("canonical expansion provenance checksum mismatch")
    if manifest.get("held_sha256") != sha(held_path):
        errors.append("held expansion checksum mismatch")

    obs_ids = [row["observation_id"] for row in observations]
    if len(obs_ids) != len(set(obs_ids)):
        errors.append("canonical expansion observation IDs are not unique")
    prov_ids = {row["provenance_id"] for row in provenance}
    missing_prov = sorted({row["provenance_id"] for row in observations} - prov_ids)
    if missing_prov:
        errors.append(f"canonical expansion has unresolved provenance IDs: {missing_prov[:5]}")

    indicators = {row["indicator_id"] for row in observations}
    if indicators != EXPECTED_INDICATORS:
        errors.append(f"canonical expansion indicator set changed: {sorted(indicators)}")

    by_indicator = Counter(row["indicator_id"] for row in observations)
    expected_counts = {
        "underemployment_rate": 140,
        "gini_ratio": 8,
        "agriculture_share_grdp": 120,
        "manufacturing_share_grdp": 120,
        "rice_yield": 160,
        "export_value": 6,
        "population_total": 20,
    }
    if dict(by_indicator) != expected_counts:
        errors.append(f"indicator row counts differ from reviewed contract: {dict(by_indicator)}")

    gini = [row for row in observations if row["indicator_id"] == "gini_ratio"]
    if {row["geography_id"] for row in gini} != {"idn.13"}:
        errors.append("canonical Gini observations must be province-only")
    if {row["time_start"] for row in gini} != {f"{year}-03-01" for year in range(2018, 2026)}:
        errors.append("canonical Gini must retain March reference period for 2018-2025")
    if any(row["unit"] != "index" or row["claim_type"] != "observed" for row in gini):
        errors.append("Gini canonical rows must be observed index values")

    held_gini = [row for row in held if row["expansion_series_id"] == "inequality_gini"]
    if len(held_gini) != 152:
        errors.append("held Gini layer must contain 19 local rows x 8 years")
    if any(row["canonical_geography_id"] == "idn.13" for row in held_gini):
        errors.append("province Gini must not leak into held local layer")

    underemployment = [row for row in observations if row["indicator_id"] == "underemployment_rate"]
    if any(row["unit"] != "percent" or row["claim_type"] != "observed" for row in underemployment):
        errors.append("underemployment must be observed percent")
    if any(row["time_start"][5:7] != "08" or row["comparable"] for row in underemployment):
        errors.append("underemployment must retain August reference period and unresolved cross-regime comparability")

    shares = [row for row in observations if row["indicator_id"] in {"agriculture_share_grdp", "manufacturing_share_grdp"}]
    for row in shares:
        try:
            value = float(row["value_numeric"])
        except ValueError:
            errors.append(f"{row['observation_id']}: non-numeric sector share")
            continue
        if not 0 <= value <= 100:
            errors.append(f"{row['observation_id']}: sector share outside 0-100")
        if row["unit"] != "percent" or row["claim_type"] != "derived":
            errors.append(f"{row['observation_id']}: sector share must be derived percent")
        if row["price_basis"] != "current_prices_series_2010":
            errors.append(f"{row['observation_id']}: sector share must retain current-price series-2010 basis")

    rice = [row for row in observations if row["indicator_id"] == "rice_yield"]
    if any(row["unit"] != "tonnes_per_hectare" or row["claim_type"] != "derived" for row in rice):
        errors.append("rice yield must be derived tonnes_per_hectare")
    for row in rice:
        if row["time_start"][:4] == "2025" and row["comparable"]:
            errors.append("2025 rice yield comparability must remain unresolved due source caveat")

    export = [row for row in observations if row["indicator_id"] == "export_value"]
    if len(export) != 6 or {row["geography_id"] for row in export} != {"idn.13"}:
        errors.append("export canonical family must contain six province-only annual observations")
    if any(row["unit"] != "usd" or row["claim_type"] != "observed" for row in export):
        errors.append("export canonical rows must be observed USD values")

    population = [row for row in observations if row["indicator_id"] == "population_total"]
    if len(population) != 20:
        errors.append("SP2020 population expansion must contain 20 geography observations")
    if any(row["time_start"] != "2020-09-01" or row["time_end"] != "2020-09-30" for row in population):
        errors.append("SP2020 population must retain September 2020 reference period")
    if any(row["unit"] != "persons" or row["claim_type"] != "observed" for row in population):
        errors.append("SP2020 population must be observed persons")

    for row in provenance:
        if row["source_id"] != "bps_webapi":
            errors.append(f"{row['provenance_id']}: unexpected provenance source")
        if not row["source_release"]:
            errors.append(f"{row['provenance_id']}: missing BPS last_update/source release")
        if len(row["checksum_sha256"]) != 64:
            errors.append(f"{row['provenance_id']}: invalid snapshot checksum length")
        try:
            int(row["checksum_sha256"], 16)
        except ValueError:
            errors.append(f"{row['provenance_id']}: snapshot checksum is not hexadecimal")

    return errors, {
        "source": len(source_rows),
        "canonical": len(observations),
        "held": len(held),
        "provenance": len(provenance),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated BPS structural-economic expansion artifacts.")
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        errors, counts = validate(args.root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BPS expansion output validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS expansion output validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS expansion output validation passed: "
        f"{counts['source']} source rows -> {counts['canonical']} canonical + "
        f"{counts['held']} held, {counts['provenance']} provenance records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
