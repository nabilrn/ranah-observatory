from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

SOURCE_ID = "chirps_v3"
GEOMETRY_SOURCE_ID = "big_admin_boundaries_june_2026"
INDICATOR_ID = "annual_rainfall"
SPATIAL_FRAME = "fixed_current_boundary_june_2026"
METHODOLOGY_VERSION = "chirps_v3_final_monthly_big_june_2026_fixed_boundary_v1"
EXPECTED_OBSERVATIONS = 855
EXPECTED_PROVENANCE = 45
EXPECTED_SOURCE_ITEMS = 541

OBSERVATION_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]
PROVENANCE_FIELDS = [
    "provenance_id", "source_id", "artifact_locator", "retrieved_at", "source_release",
    "checksum_sha256", "parser_revision", "transform_revision", "extraction_method", "notes",
]
SOURCE_CONTRACT_FIELDS = [
    "contract_item_id", "source_id", "role", "year", "month", "locator", "source_release",
    "transport_identity", "identity_sha256", "identity_scope", "content_length_bytes", "notes",
]
COG_RE = re.compile(r"chirps-v3\.0\.(\d{4})\.(\d{2})\.cog$")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def stable_id(prefix: str, parts: Iterable[str]) -> str:
    token = "|".join(parts)
    return prefix + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _content_length_from_range(value: str) -> str:
    if "/" not in value:
        return ""
    total = value.rsplit("/", 1)[-1].strip()
    return total if total.isdigit() else ""


def _latest_release(rows: list[dict[str, str]]) -> str:
    parsed: list[datetime] = []
    originals: dict[datetime, str] = {}
    for row in rows:
        raw = row["source_release"]
        if not raw:
            continue
        try:
            value = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            continue
        parsed.append(value)
        originals[value] = raw
    return originals[max(parsed)] if parsed else ""


def build_source_contract(production_manifest: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen_periods: set[tuple[int, int]] = set()
    for item in production_manifest["chirps_source_files"]:
        url = str(item["url"])
        match = COG_RE.search(url)
        if not match:
            raise ValueError(f"unrecognized CHIRPS COG locator {url!r}")
        year, month = int(match.group(1)), int(match.group(2))
        period = (year, month)
        if period in seen_periods:
            raise ValueError(f"duplicate CHIRPS source period {year}-{month:02d}")
        seen_periods.add(period)
        if not item.get("is_tiff") or int(item.get("http_status", 0)) not in {200, 206}:
            raise ValueError(f"unqualified CHIRPS transport identity for {year}-{month:02d}")
        rows.append({
            "contract_item_id": f"chirps_v3_final_{year:04d}_{month:02d}",
            "source_id": SOURCE_ID,
            "role": "monthly_rainfall_source_cog",
            "year": str(year),
            "month": str(month),
            "locator": url,
            "source_release": str(item.get("last_modified", "")),
            "transport_identity": str(item.get("etag", "")),
            "identity_sha256": str(item["prefix_sha256"]),
            "identity_scope": "sha256_first_16384_bytes_not_full_file_checksum",
            "content_length_bytes": _content_length_from_range(str(item.get("content_range", ""))),
            "notes": f"content_range={item.get('content_range', '')}; bytes_read={item.get('bytes_read', '')}",
        })

    expected_periods = {(year, month) for year in range(1981, 2026) for month in range(1, 13)}
    if seen_periods != expected_periods:
        missing = sorted(expected_periods - seen_periods)
        unexpected = sorted(seen_periods - expected_periods)
        raise ValueError(f"CHIRPS source contract period mismatch; missing={missing}; unexpected={unexpected}")

    big = production_manifest["big_geometry"]
    big_sha = str(big.get("sha256", ""))
    if len(big_sha) != 64:
        raise ValueError("BIG provenance lacks full response SHA-256")
    rows.append({
        "contract_item_id": "big_sumbar_kabkota_june_2026_snapshot",
        "source_id": GEOMETRY_SOURCE_ID,
        "role": "zonal_geometry_source",
        "year": "2026",
        "month": "6",
        "locator": str(big["url"]),
        "source_release": str(big["source_edition"]),
        "transport_identity": str(big.get("etag", "")),
        "identity_sha256": big_sha,
        "identity_scope": "sha256_full_geojson_query_response",
        "content_length_bytes": str(big.get("bytes", "")),
        "notes": "current boundary snapshot only; historical boundary continuity is not established",
    })
    rows.sort(key=lambda row: row["contract_item_id"])
    if len(rows) != EXPECTED_SOURCE_ITEMS:
        raise ValueError(f"expected {EXPECTED_SOURCE_ITEMS} source contract items; got {len(rows)}")
    return rows


def csv_bytes(fields: list[str], rows: list[dict[str, Any]]) -> bytes:
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_canonical(
    annual_rows: list[dict[str, str]],
    production_manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    gates = production_manifest.get("gates", {})
    if not gates or not all(bool(value) for value in gates.values()):
        raise ValueError("production manifest did not pass every dry-run gate")
    scope = production_manifest["scope"]
    if (
        int(scope["first_year"]) != 1981
        or int(scope["last_year"]) != 2025
        or int(scope["geography_count"]) != 19
        or int(scope["annual_row_count"]) != EXPECTED_OBSERVATIONS
    ):
        raise ValueError(f"unexpected production scope: {scope}")

    source_contract = build_source_contract(production_manifest)
    source_contract_sha = hashlib.sha256(csv_bytes(SOURCE_CONTRACT_FIELDS, source_contract)).hexdigest()
    big_sha = str(production_manifest["big_geometry"]["sha256"])
    retrieved_at = str(production_manifest["generated_at"])

    by_year_sources: dict[int, list[dict[str, str]]] = {}
    for year in range(1981, 2026):
        rows = [
            row for row in source_contract
            if row["source_id"] == SOURCE_ID and int(row["year"]) == year
        ]
        if len(rows) != 12:
            raise ValueError(f"expected 12 CHIRPS source items for {year}; got {len(rows)}")
        by_year_sources[year] = rows

    provenance: list[dict[str, Any]] = []
    provenance_id_by_year: dict[int, str] = {}
    for year in range(1981, 2026):
        provenance_id = stable_id(
            "chirpsprov_",
            [SOURCE_ID, str(year), source_contract_sha, big_sha, METHODOLOGY_VERSION],
        )
        provenance_id_by_year[year] = provenance_id
        provenance.append({
            "provenance_id": provenance_id,
            "source_id": SOURCE_ID,
            "artifact_locator": f"repo://data/processed/climate/rainfall/chirps-source-contract.csv#year={year}",
            "retrieved_at": retrieved_at,
            "source_release": _latest_release(by_year_sources[year]),
            "checksum_sha256": source_contract_sha,
            "parser_revision": "chirps_v3_final_monthly_cog:rasterio-1.5.0",
            "transform_revision": "build_chirps_rainfall_production:v1|materialize_chirps_rainfall:v1",
            "extraction_method": "remote_cog_range_read+geodesic_area_weighted_zonal_aggregation",
            "notes": (
                f"year_source_files=12; geometry_source={GEOMETRY_SOURCE_ID}; geometry_response_sha256={big_sha}; "
                "checksum_scope=committed_source_contract_artifact_not_full_upstream_raster_bytes; "
                "source_contract_records_prefix_sha256_etag_last_modified_and_content_length_for_each_COG"
            ),
        })

    observations: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()
    for row in annual_rows:
        gid = row["geography_id"]
        year = int(row["year"])
        key = (gid, year)
        if key in seen_keys:
            raise ValueError(f"duplicate annual rainfall candidate {key}")
        seen_keys.add(key)
        if year not in provenance_id_by_year:
            raise ValueError(f"annual rainfall candidate outside canonical period: {year}")
        if row.get("claim_type") != "model_estimate" or row.get("spatial_frame") != SPATIAL_FRAME:
            raise ValueError(f"candidate evidence contract mismatch for {key}")
        if int(row["months_complete"]) != 12:
            raise ValueError(f"incomplete candidate year for {key}")
        value = float(row["annual_rainfall_mm"])
        if not value > 0:
            raise ValueError(f"non-positive annual rainfall candidate for {key}: {value}")
        min_coverage = float(row["min_valid_area_fraction"])
        mean_coverage = float(row["mean_valid_area_fraction"])
        if min_coverage < 0.995:
            raise ValueError(f"candidate below production coverage threshold for {key}: {min_coverage}")

        observation_id = stable_id(
            "chirpsobs_",
            [SOURCE_ID, INDICATOR_ID, gid, str(year), SPATIAL_FRAME, METHODOLOGY_VERSION],
        )
        observations.append({
            "observation_id": observation_id,
            "indicator_id": INDICATOR_ID,
            "geography_id": gid,
            "time_start": f"{year:04d}-01-01",
            "time_end": f"{year:04d}-12-31",
            "frequency": "annual",
            "value_numeric": f"{value:.6f}",
            "unit": "millimetres",
            "claim_type": "model_estimate",
            "provenance_id": provenance_id_by_year[year],
            "suppressed": "false",
            "comparable": "true",
            "methodology_version": METHODOLOGY_VERSION,
            "price_basis": "",
            "notes": (
                f"spatial_frame={SPATIAL_FRAME}; historical_boundary_continuity=false; months_complete=12; "
                f"min_valid_area_fraction={min_coverage:.8f}; mean_valid_area_fraction={mean_coverage:.8f}; "
                "source_product=CHIRPS v3 Final monthly; geometry_source=BIG BATAS_KABKOTA_AR; "
                "geometry_source_edition=Juni 2026; observed_station_equivalence=false; "
                "comparability_scope=within_CHIRPS_v3_Final_fixed_current_boundary_frame; "
                "independent_station_validation=pending"
            ),
        })

    if len(observations) != EXPECTED_OBSERVATIONS or len(seen_keys) != EXPECTED_OBSERVATIONS:
        raise ValueError(f"expected {EXPECTED_OBSERVATIONS} unique observations; got {len(observations)}")
    geography_ids = {row["geography_id"] for row in observations}
    years = {int(row["time_start"][:4]) for row in observations}
    if len(geography_ids) != 19 or years != set(range(1981, 2026)):
        raise ValueError("canonical geography/year footprint is incomplete")

    observations.sort(key=lambda row: row["observation_id"])
    provenance.sort(key=lambda row: row["provenance_id"])
    manifest = {
        "schema": "ranah-observatory/chirps-annual-rainfall/v1",
        "source_id": SOURCE_ID,
        "geometry_source_id": GEOMETRY_SOURCE_ID,
        "indicator_id": INDICATOR_ID,
        "claim_type": "model_estimate",
        "spatial_frame": SPATIAL_FRAME,
        "methodology_version": METHODOLOGY_VERSION,
        "first_year": 1981,
        "last_year": 2025,
        "geography_count": 19,
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "source_contract_item_count": len(source_contract),
        "source_contract_sha256": source_contract_sha,
        "big_geometry_response_sha256": big_sha,
        "retrieved_at": retrieved_at,
        "independent_station_validation": "pending",
        "eligible_as_observed_station_data": False,
        "historical_boundary_continuity_claimed": False,
    }
    return observations, provenance, source_contract, manifest


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> str:
    payload = csv_bytes(fields, rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def write_outputs(
    observations: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    source_contract: list[dict[str, str]],
    manifest: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    obs_path = output_dir / "chirps-annual-rainfall-observations.csv"
    prov_path = output_dir / "chirps-annual-rainfall-provenance.csv"
    contract_path = output_dir / "chirps-source-contract.csv"
    obs_sha = write_csv(obs_path, OBSERVATION_FIELDS, observations)
    prov_sha = write_csv(prov_path, PROVENANCE_FIELDS, provenance)
    contract_sha = write_csv(contract_path, SOURCE_CONTRACT_FIELDS, source_contract)
    if contract_sha != manifest["source_contract_sha256"]:
        raise ValueError("source contract digest changed during write")
    final_manifest = dict(manifest)
    final_manifest.update({
        "observations_file": obs_path.name,
        "observations_sha256": obs_sha,
        "provenance_file": prov_path.name,
        "provenance_sha256": prov_sha,
        "source_contract_file": contract_path.name,
    })
    manifest_path = output_dir / "chirps-rainfall-materialization.manifest.json"
    manifest_path.write_text(json.dumps(final_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return final_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize CHIRPS annual rainfall candidates into canonical-format observations")
    parser.add_argument("annual_candidates", type=Path)
    parser.add_argument("production_manifest", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    annual_rows = read_csv(args.annual_candidates)
    production_manifest = json.loads(args.production_manifest.read_text(encoding="utf-8"))
    observations, provenance, source_contract, manifest = build_canonical(annual_rows, production_manifest)
    manifest = write_outputs(observations, provenance, source_contract, manifest, args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
