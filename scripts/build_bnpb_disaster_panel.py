from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
DEFAULT_BNPB_GEOGRAPHY_MAP = ROOT / "data" / "registries" / "bnpb_geography_map.csv"

DISASTER_COLUMNS = (
    "BANJIR",
    "CUACA EKSTREM",
    "ERUPSI GUNUNG API",
    "GELOMBANG PASANG DAN ABRASI",
    "GEMPABUMI",
    "KEBAKARAN HUTAN DAN LAHAN",
    "KEKERINGAN",
    "TANAH LONGSOR",
    "TSUNAMI",
)
CANONICAL_EVENT_COLUMNS = {
    "BANJIR": "flood_events",
    "TANAH LONGSOR": "landslide_events",
}
GEO_NAME_FIELDS = ("Nama Kabupaten/Kota", "NAMA KABUPATEN/KOTA", "Nama Kabupaten / Kota")
GEO_CODE_FIELDS = ("Kode Wilayah Kabupaten / Kota", "Kode Wilayah Kabupaten/Kota")

SOURCE_NATIVE_FIELDS = [
    "source_row_id",
    "source_record_id",
    "metric_family",
    "canonical_geography_id",
    "source_geography_code",
    "source_geography_name",
    "year",
    "disaster_type",
    "value_numeric",
    "unit",
    "promotion_status",
    "source_snapshot_sha256",
    "notes",
]
CANONICAL_FIELDS = [
    "observation_id",
    "indicator_id",
    "geography_id",
    "time_start",
    "time_end",
    "frequency",
    "value_numeric",
    "unit",
    "claim_type",
    "provenance_id",
    "suppressed",
    "comparable",
    "methodology_version",
    "price_basis",
    "notes",
]
PROVENANCE_FIELDS = [
    "provenance_id",
    "source_id",
    "artifact_locator",
    "retrieved_at",
    "source_release",
    "checksum_sha256",
    "parser_revision",
    "transform_revision",
    "extraction_method",
    "notes",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _read_snapshot(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("snapshot_schema") != "ranah-observatory/bnpb-ckan-snapshot/v1":
        raise ValueError(f"{path}: unexpected BNPB snapshot schema")
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("records"), list):
        raise ValueError(f"{path}: snapshot does not contain DataStore records")
    return payload, digest


def _source_value(record: Mapping[str, Any], candidates: Iterable[str]) -> Any:
    for field in candidates:
        if field in record:
            return record[field]
    raise ValueError(f"missing required source field; tried {tuple(candidates)!r}")


def _clean_name(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[._,/\\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_admin_name(value: Any) -> tuple[str | None, str]:
    text = _clean_name(value)
    for prefix, level in (
        ("KABUPATEN ", "regency"),
        ("KAB ", "regency"),
        ("KOTA ", "city"),
    ):
        if text.startswith(prefix):
            return level, text[len(prefix) :].strip()
    return None, text


def _source_code_digits(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return re.sub(r"\D", "", text)
    if 0 <= number < 100:
        return str(int(round(number * 100)))
    if number.is_integer():
        return str(int(number))
    return re.sub(r"\D", "", text)


def _canonical_geographies(path: Path) -> list[dict[str, str]]:
    rows = [
        row
        for row in _read_csv(path)
        if row["parent_geography_id"] == "idn.13"
        and row["status"] == "current"
        and row["geography_level"] in {"regency", "city"}
    ]
    if len(rows) != 19:
        raise ValueError(f"expected 19 current Sumatera Barat kabupaten/kota, found {len(rows)}")
    return rows


def _explicit_geography_crosswalk(
    path: Path,
    canonical: list[dict[str, str]],
) -> dict[str, tuple[dict[str, str], str]]:
    canonical_by_id = {row["geography_id"]: row for row in canonical}
    rows = _read_csv(path)
    mapping: dict[str, tuple[dict[str, str], str]] = {}
    for row in rows:
        code = row["source_code_normalized"]
        geography_id = row["canonical_geography_id"]
        admin_type = row["source_admin_type"]
        if row["source_system"] != "Permendagri":
            raise ValueError(f"{path}: unsupported source_system {row['source_system']!r}")
        if row["mapping_status"] != "qualified_current_crosswalk":
            raise ValueError(f"{path}: unqualified mapping for source code {code!r}")
        if admin_type not in {"regency", "city"}:
            raise ValueError(f"{path}: invalid source_admin_type {admin_type!r}")
        if code in mapping:
            raise ValueError(f"{path}: duplicate source code {code!r}")
        canonical_row = canonical_by_id.get(geography_id)
        if canonical_row is None:
            raise ValueError(f"{path}: unknown canonical geography {geography_id!r}")
        if canonical_row["geography_level"] != admin_type:
            raise ValueError(
                f"{path}: admin type mismatch for {code}: "
                f"crosswalk={admin_type} canonical={canonical_row['geography_level']}"
            )
        mapping[code] = (canonical_row, admin_type)
    if len(mapping) != 19:
        raise ValueError(f"{path}: expected 19 explicit BNPB geography mappings, found {len(mapping)}")
    if {row[0]["geography_id"] for row in mapping.values()} != set(canonical_by_id):
        raise ValueError(f"{path}: crosswalk does not cover each current Sumatera Barat geography exactly once")
    return mapping


def _map_record(
    record: Mapping[str, Any],
    crosswalk: Mapping[str, tuple[dict[str, str], str]],
) -> tuple[dict[str, str], str, str]:
    source_name = str(_source_value(record, GEO_NAME_FIELDS) or "").strip()
    source_code = str(_source_value(record, GEO_CODE_FIELDS) or "").strip()
    source_digits = _source_code_digits(source_code)
    qualified = crosswalk.get(source_digits)
    if qualified is None:
        raise KeyError(source_digits)
    canonical_row, expected_admin_type = qualified
    source_admin_type, _ = _split_admin_name(source_name)
    if source_admin_type is not None and source_admin_type != expected_admin_type:
        raise ValueError(
            f"BNPB source admin type conflicts with explicit Permendagri crosswalk: "
            f"code={source_code!r} name={source_name!r} source_type={source_admin_type!r} "
            f"expected_type={expected_admin_type!r} canonical={canonical_row['geography_id']}"
        )
    return canonical_row, source_code, source_name


def _sumbar_records(
    payload: Mapping[str, Any],
    crosswalk: Mapping[str, tuple[dict[str, str], str]],
) -> list[tuple[Mapping[str, Any], dict[str, str], str, str]]:
    result: list[tuple[Mapping[str, Any], dict[str, str], str, str]] = []
    seen: set[str] = set()
    observed_sumbar_codes: set[str] = set()
    for record in payload["result"]["records"]:
        if not isinstance(record, Mapping):
            raise ValueError("BNPB DataStore record must be an object")
        source_code = str(_source_value(record, GEO_CODE_FIELDS) or "").strip()
        source_digits = _source_code_digits(source_code)
        if source_digits not in crosswalk:
            continue
        observed_sumbar_codes.add(source_digits)
        mapped, source_code, source_name = _map_record(record, crosswalk)
        geography_id = mapped["geography_id"]
        if geography_id in seen:
            raise ValueError(f"duplicate BNPB row for canonical geography {geography_id}")
        seen.add(geography_id)
        result.append((record, mapped, source_code, source_name))
    if len(result) != 19:
        expected_ids = {item[0]["geography_id"] for item in crosswalk.values()}
        missing_ids = sorted(expected_ids - seen)
        missing_codes = sorted(set(crosswalk) - observed_sumbar_codes)
        raise ValueError(
            f"expected 19 mapped Sumatera Barat rows, found {len(result)}; "
            f"missing_canonical={missing_ids}; missing_source_codes={missing_codes}"
        )
    return sorted(result, key=lambda item: item[1]["geography_id"])


def _number(value: Any, *, allow_blank: bool = False) -> float | int | None:
    if value is None or (isinstance(value, str) and value.strip() in {"", "-", "—", "NA", "N/A"}):
        if allow_blank:
            return None
        raise ValueError("required numeric source value is blank")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        if allow_blank:
            return None
        raise ValueError(f"source value is not numeric: {value!r}") from exc
    if number.is_integer():
        return int(number)
    return number


def _id(prefix: str, *parts: str) -> str:
    token = "|".join(parts)
    return prefix + hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _crosscheck_detailed(
    primary: list[tuple[Mapping[str, Any], dict[str, str], str, str]],
    crosscheck: list[tuple[Mapping[str, Any], dict[str, str], str, str]],
) -> None:
    cross_by_geo = {item[1]["geography_id"]: item[0] for item in crosscheck}
    for record, mapped, _, _ in primary:
        other = cross_by_geo[mapped["geography_id"]]
        for column in CANONICAL_EVENT_COLUMNS:
            left = _number(record.get(column))
            right = _number(other.get(column))
            if left != right:
                raise ValueError(
                    f"official BNPB 2024 cross-check mismatch for {mapped['geography_id']} {column}: "
                    f"primary={left!r} crosscheck={right!r}"
                )


def build(
    total_snapshot: Path,
    detailed_snapshot: Path,
    crosscheck_snapshot: Path,
    affected_snapshot: Path,
    *,
    geographies_path: Path = DEFAULT_GEOGRAPHIES,
    geography_map_path: Path = DEFAULT_BNPB_GEOGRAPHY_MAP,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    canonical_geos = _canonical_geographies(geographies_path)
    crosswalk = _explicit_geography_crosswalk(geography_map_path, canonical_geos)
    total_payload, total_sha = _read_snapshot(total_snapshot)
    detailed_payload, detailed_sha = _read_snapshot(detailed_snapshot)
    cross_payload, cross_sha = _read_snapshot(crosscheck_snapshot)
    affected_payload, affected_sha = _read_snapshot(affected_snapshot)

    total_rows = _sumbar_records(total_payload, crosswalk)
    detailed_rows = _sumbar_records(detailed_payload, crosswalk)
    cross_rows = _sumbar_records(cross_payload, crosswalk)
    affected_rows = _sumbar_records(affected_payload, crosswalk)
    _crosscheck_detailed(detailed_rows, cross_rows)

    source_native: list[dict[str, Any]] = []
    canonical_observations: list[dict[str, Any]] = []

    for record, mapped, source_code, source_name in total_rows:
        for year in range(2010, 2025):
            field = f"{year}.0"
            if field not in record and str(year) in record:
                field = str(year)
            value = _number(record.get(field))
            source_native.append(
                {
                    "source_row_id": _id("bnpbsrc_", "total", mapped["geography_id"], str(year)),
                    "source_record_id": "bnpb_total_events_kab_2010_2024",
                    "metric_family": "recorded_disaster_events_total",
                    "canonical_geography_id": mapped["geography_id"],
                    "source_geography_code": source_code,
                    "source_geography_name": source_name,
                    "year": year,
                    "disaster_type": "ALL_RECORDED_DISASTERS",
                    "value_numeric": value,
                    "unit": "count",
                    "promotion_status": "source_native_context",
                    "source_snapshot_sha256": total_sha,
                    "notes": "Total all-disaster event count; not disaster-type specific; geography uses explicit Permendagri crosswalk.",
                }
            )

    provenance_id = _id("bnpbprov_", detailed_sha, cross_sha)
    retrieved_at = str(detailed_payload.get("retrieved_at_utc", ""))
    provenance = [
        {
            "provenance_id": provenance_id,
            "source_id": "bnpb_satu_data",
            "artifact_locator": "bnpb-ckan://resource/a4daec53-1119-43ef-b05e-00ec3a4c42a4",
            "retrieved_at": retrieved_at,
            "source_release": "2025-03-20",
            "checksum_sha256": detailed_sha,
            "parser_revision": "bnpb_client:v1",
            "transform_revision": "build_bnpb_disaster_panel:v2",
            "extraction_method": "ckan_api",
            "notes": (
                "Primary 2024 event-by-type resource; independently cross-checked against official resource "
                f"5ff9f41f-8312-4b7c-aa18-fdbedac6ee7e snapshot_sha256={cross_sha}; "
                "geography mapped through explicit current Permendagri-to-canonical crosswalk."
            ),
        }
    ]

    for record, mapped, source_code, source_name in detailed_rows:
        for disaster_type in DISASTER_COLUMNS:
            value = _number(record.get(disaster_type), allow_blank=True)
            source_native.append(
                {
                    "source_row_id": _id("bnpbsrc_", "event", mapped["geography_id"], "2024", disaster_type),
                    "source_record_id": "bnpb_events_by_type_kab_2024_primary",
                    "metric_family": "recorded_disaster_events_by_type",
                    "canonical_geography_id": mapped["geography_id"],
                    "source_geography_code": source_code,
                    "source_geography_name": source_name,
                    "year": 2024,
                    "disaster_type": disaster_type,
                    "value_numeric": value,
                    "unit": "count",
                    "promotion_status": (
                        "canonical_ready" if disaster_type in CANONICAL_EVENT_COLUMNS else "source_native_context"
                    ),
                    "source_snapshot_sha256": detailed_sha,
                    "notes": "2024 BNPB event-by-type resource; blanks remain missing rather than zero; geography uses explicit Permendagri crosswalk.",
                }
            )
            indicator_id = CANONICAL_EVENT_COLUMNS.get(disaster_type)
            if indicator_id is None:
                continue
            if value is None:
                raise ValueError(f"canonical {indicator_id} is blank for {mapped['geography_id']}")
            canonical_observations.append(
                {
                    "observation_id": _id("bnpbobs_", indicator_id, mapped["geography_id"], "2024"),
                    "indicator_id": indicator_id,
                    "geography_id": mapped["geography_id"],
                    "time_start": "2024-01-01",
                    "time_end": "2024-12-31",
                    "frequency": "annual",
                    "value_numeric": value,
                    "unit": "count",
                    "claim_type": "observed",
                    "provenance_id": provenance_id,
                    "suppressed": "false",
                    "comparable": "",
                    "methodology_version": "BNPB/DIBI 2024 event classification",
                    "price_basis": "",
                    "notes": (
                        f"source_geography={source_code}:{source_name}; mapping=explicit_permendagri_current_crosswalk; "
                        f"source_column={disaster_type}; independent_official_crosscheck=passed; "
                        "recorded-event series may be affected by reporting intensity and classification practice."
                    ),
                }
            )

    for record, mapped, source_code, source_name in affected_rows:
        for disaster_type in DISASTER_COLUMNS:
            value = _number(record.get(disaster_type), allow_blank=True)
            source_native.append(
                {
                    "source_row_id": _id("bnpbsrc_", "affected", mapped["geography_id"], "2024", disaster_type),
                    "source_record_id": "bnpb_affected_by_type_kab_2024",
                    "metric_family": "reported_affected_people_by_type",
                    "canonical_geography_id": mapped["geography_id"],
                    "source_geography_code": source_code,
                    "source_geography_name": source_name,
                    "year": 2024,
                    "disaster_type": disaster_type,
                    "value_numeric": value,
                    "unit": "persons",
                    "promotion_status": "held_source_native",
                    "source_snapshot_sha256": affected_sha,
                    "notes": "Held: annual cross-event aggregation is not assumed to represent unique affected persons; geography uses explicit Permendagri crosswalk.",
                }
            )

    source_native.sort(key=lambda row: row["source_row_id"])
    canonical_observations.sort(key=lambda row: row["observation_id"])
    manifest = {
        "schema": "ranah-observatory/bnpb-disaster-panel/v1",
        "source_id": "bnpb_satu_data",
        "canonical_observation_count": len(canonical_observations),
        "canonical_provenance_count": len(provenance),
        "source_native_count": len(source_native),
        "mapped_geography_count": len(canonical_geos),
        "geography_mapping": "explicit_permendagri_current_crosswalk",
        "canonical_indicators": sorted({row["indicator_id"] for row in canonical_observations}),
        "source_snapshots": {
            "total_events_2010_2024": total_sha,
            "events_by_type_2024_primary": detailed_sha,
            "events_by_type_2024_crosscheck": cross_sha,
            "affected_by_type_2024": affected_sha,
        },
        "official_crosscheck": "passed",
    }
    return source_native, canonical_observations, provenance, manifest


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    output_dir: Path,
    source_native: list[dict[str, Any]],
    canonical: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / "bnpb-disaster-source-native.csv"
    canonical_path = output_dir / "bnpb-disaster-canonical-observations.csv"
    provenance_path = output_dir / "bnpb-disaster-canonical-provenance.csv"
    manifest_path = output_dir / "bnpb-disaster-panel.manifest.json"
    _write_csv(source_path, source_native, SOURCE_NATIVE_FIELDS)
    _write_csv(canonical_path, canonical, CANONICAL_FIELDS)
    _write_csv(provenance_path, provenance, PROVENANCE_FIELDS)
    payload = dict(manifest)
    payload["source_native_sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    payload["canonical_observations_sha256"] = hashlib.sha256(canonical_path.read_bytes()).hexdigest()
    payload["canonical_provenance_sha256"] = hashlib.sha256(provenance_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the first reviewed BNPB disaster panel for Sumatera Barat.")
    parser.add_argument("--total-snapshot", required=True, type=Path)
    parser.add_argument("--detailed-snapshot", required=True, type=Path)
    parser.add_argument("--crosscheck-snapshot", required=True, type=Path)
    parser.add_argument("--affected-snapshot", required=True, type=Path)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--geography-map", type=Path, default=DEFAULT_BNPB_GEOGRAPHY_MAP)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        source_native, canonical, provenance, manifest = build(
            args.total_snapshot,
            args.detailed_snapshot,
            args.crosscheck_snapshot,
            args.affected_snapshot,
            geographies_path=args.geographies,
            geography_map_path=args.geography_map,
        )
        write_outputs(args.output_dir, source_native, canonical, provenance, manifest)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
