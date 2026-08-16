from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "processed" / "climate" / "rainfall"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
REPO_LOCATOR_RE = re.compile(
    r"^repo://data/processed/climate/rainfall/chirps-source-contract\.csv#year=(19[89][0-9]|20[0-2][0-9])$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def expected_geographies() -> set[str]:
    return {
        row["geography_id"]
        for row in read_csv(GEOGRAPHIES)
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    }


def validate(directory: Path = DEFAULT_DIR) -> dict:
    observations_path = directory / "chirps-annual-rainfall-observations.csv"
    provenance_path = directory / "chirps-annual-rainfall-provenance.csv"
    contract_path = directory / "chirps-source-contract.csv"
    manifest_path = directory / "chirps-rainfall-materialization.manifest.json"
    for path in (observations_path, provenance_path, contract_path, manifest_path):
        if not path.is_file():
            raise ValueError(f"missing frozen CHIRPS file: {path}")

    observations = read_csv(observations_path)
    provenance = read_csv(provenance_path)
    contract = read_csv(contract_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_geo = expected_geographies()
    if len(expected_geo) != 19:
        raise ValueError(f"canonical Sumatera Barat registry must contain 19 current regency/city geographies; got {len(expected_geo)}")

    indicator_rows = [row for row in read_csv(INDICATORS) if row["indicator_id"] == "annual_rainfall"]
    if len(indicator_rows) != 1:
        raise ValueError("annual_rainfall indicator registry row missing or duplicated")
    indicator = indicator_rows[0]
    if indicator["unit"] != "millimetres" or "model_estimate" not in indicator["allowed_claim_types"].split("|"):
        raise ValueError("annual_rainfall indicator registry does not allow expected model-estimate millimetre semantics")

    if len(observations) != 855 or len({row["observation_id"] for row in observations}) != 855:
        raise ValueError("frozen observation footprint must contain exactly 855 unique IDs")
    keys: set[tuple[str, int]] = set()
    provenance_ids = {row["provenance_id"] for row in provenance}
    if len(provenance) != 45 or len(provenance_ids) != 45:
        raise ValueError("frozen provenance footprint must contain exactly 45 unique IDs")

    for row in observations:
        if row["indicator_id"] != "annual_rainfall" or row["claim_type"] != "model_estimate":
            raise ValueError(f"invalid observation evidence semantics: {row['observation_id']}")
        if row["frequency"] != "annual" or row["unit"] != "millimetres":
            raise ValueError(f"invalid annual rainfall frequency/unit: {row['observation_id']}")
        if row["geography_id"] not in expected_geo:
            raise ValueError(f"unexpected canonical geography: {row['geography_id']}")
        year = int(row["time_start"][:4])
        if year < 1981 or year > 2025:
            raise ValueError(f"observation year outside frozen period: {year}")
        if row["time_start"] != f"{year:04d}-01-01" or row["time_end"] != f"{year:04d}-12-31":
            raise ValueError(f"invalid annual period bounds: {row['observation_id']}")
        key = (row["geography_id"], year)
        if key in keys:
            raise ValueError(f"duplicate geography-year observation: {key}")
        keys.add(key)
        value = float(row["value_numeric"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid frozen rainfall value: {row['observation_id']}")
        if row["provenance_id"] not in provenance_ids:
            raise ValueError(f"observation references missing provenance: {row['observation_id']}")
        if row["suppressed"] != "false" or row["comparable"] != "true":
            raise ValueError(f"unexpected suppression/comparability status: {row['observation_id']}")
        required_notes = (
            "spatial_frame=fixed_current_boundary_june_2026",
            "historical_boundary_continuity=false",
            "observed_station_equivalence=false",
            "independent_station_validation=pending",
        )
        if not all(token in row["notes"] for token in required_notes):
            raise ValueError(f"observation notes lost evidence limitations: {row['observation_id']}")

    expected_keys = {(gid, year) for gid in expected_geo for year in range(1981, 2026)}
    if keys != expected_keys:
        raise ValueError("frozen geography-year footprint is incomplete")

    contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    if manifest.get("source_contract_sha256") != contract_sha:
        raise ValueError("frozen source-contract checksum does not match manifest")
    for row in provenance:
        if row["source_id"] != "chirps_v3":
            raise ValueError(f"unexpected provenance source_id: {row['source_id']}")
        if not REPO_LOCATOR_RE.fullmatch(row["artifact_locator"]):
            raise ValueError(f"provenance locator is not repository-scoped: {row['artifact_locator']}")
        year = int(row["artifact_locator"].rsplit("=", 1)[-1])
        if not 1981 <= year <= 2025:
            raise ValueError(f"provenance locator year outside frozen period: {year}")
        if row["checksum_sha256"] != contract_sha:
            raise ValueError(f"provenance checksum does not bind frozen source contract: {row['provenance_id']}")
        if "committed_source_contract_artifact_not_full_upstream_raster_bytes" not in row["notes"]:
            raise ValueError(f"provenance lost checksum-scope disclosure: {row['provenance_id']}")
        if "artifact://" in row["artifact_locator"]:
            raise ValueError(f"artifact-only locator survived repository freeze: {row['provenance_id']}")

    chirps_contract = [row for row in contract if row["source_id"] == "chirps_v3"]
    big_contract = [row for row in contract if row["source_id"] == "big_admin_boundaries_june_2026"]
    if len(contract) != 541 or len(chirps_contract) != 540 or len(big_contract) != 1:
        raise ValueError("frozen source contract must contain 540 CHIRPS COG identities and one BIG geometry identity")
    if len({(row["year"], row["month"]) for row in chirps_contract}) != 540:
        raise ValueError("frozen CHIRPS source periods are duplicated or incomplete")
    for row in chirps_contract:
        if row["identity_scope"] != "sha256_first_16384_bytes_not_full_file_checksum":
            raise ValueError(f"CHIRPS digest scope drift: {row['contract_item_id']}")
        if not SHA256_RE.fullmatch(row["identity_sha256"]):
            raise ValueError(f"invalid CHIRPS prefix SHA-256: {row['contract_item_id']}")
        if "bytes 0-16383/" not in row["notes"] or "bytes_read=16384" not in row["notes"]:
            raise ValueError(f"CHIRPS range-read evidence missing: {row['contract_item_id']}")
    if big_contract[0]["identity_scope"] != "sha256_full_geojson_query_response":
        raise ValueError("BIG geometry digest is not labelled as a full response checksum")
    if not SHA256_RE.fullmatch(big_contract[0]["identity_sha256"]):
        raise ValueError("BIG full-response SHA-256 is invalid")

    observations_sha = hashlib.sha256(observations_path.read_bytes()).hexdigest()
    provenance_sha = hashlib.sha256(provenance_path.read_bytes()).hexdigest()
    if manifest.get("observations_sha256") != observations_sha:
        raise ValueError("frozen observation checksum does not match manifest")
    if manifest.get("provenance_sha256") != provenance_sha:
        raise ValueError("frozen provenance checksum does not match manifest")
    if manifest.get("freeze_status") != "repository_baseline":
        raise ValueError("freeze manifest is not marked repository_baseline")
    if manifest.get("canonical_repository_path") != "data/processed/climate/rainfall":
        raise ValueError("freeze manifest repository path is incorrect")
    if manifest.get("independent_station_validation") != "pending":
        raise ValueError("freeze incorrectly advances station validation status")
    if manifest.get("eligible_as_observed_station_data") is not False:
        raise ValueError("freeze incorrectly qualifies CHIRPS as observed station data")
    if manifest.get("historical_boundary_continuity_claimed") is not False:
        raise ValueError("freeze incorrectly claims historical boundary continuity")

    return {
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "source_contract_item_count": len(contract),
        "geography_count": len(expected_geo),
        "first_year": 1981,
        "last_year": 2025,
        "observations_sha256": observations_sha,
        "provenance_sha256": provenance_sha,
        "source_contract_sha256": contract_sha,
        "status": "valid_repository_baseline",
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
