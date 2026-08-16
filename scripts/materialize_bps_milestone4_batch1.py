#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SERIES = ROOT / "data" / "registries" / "bps_milestone4_batch1_series.csv"
DEFAULT_GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
DEFAULT_INDICATORS = ROOT / "data" / "registries" / "indicators.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "processed" / "bps" / "milestone4"

EXPECTED_CODES = {
    "1301", "1302", "1303", "1304", "1305", "1306", "1307", "1308", "1309",
    "1310", "1311", "1312", "1371", "1372", "1373", "1374", "1375", "1376", "1377",
}
EXPECTED_BATCH_INDICATORS = 22
EXPECTED_BATCH_OBSERVATIONS = 415
EXPECTED_BATCH_PROVENANCE = 19

# These timestamps and BPS metadata versions come from the successful bounded
# qualification probe (GitHub Actions run 31946726813). Re-harvests must match
# the locked semantic result hashes before these qualified provenance identities
# may be reused.
QUALIFIED_SOURCE_META: dict[str, tuple[str, str]] = {
    "512": ("2026-08-16T12:19:10+00:00", "2021-04-16 02:44:07"),
    "883": ("2026-08-16T12:19:15+00:00", "2026-05-12 02:24:40"),
    "877": ("2026-08-16T12:19:18+00:00", "2026-05-12 02:00:30"),
    "320": ("2026-08-16T12:19:23+00:00", "2026-02-28 02:00:54"),
    "555": ("2026-08-16T12:19:30+00:00", "2025-03-27 01:08:53"),
    "774": ("2026-08-16T12:19:34+00:00", "2026-05-04 10:44:27"),
    "319": ("2026-08-16T12:19:38+00:00", "2026-02-28 01:58:42"),
    "289": ("2026-08-16T12:19:44+00:00", "2025-05-06 09:05:36"),
    "875": ("2026-08-16T12:19:48+00:00", "2026-05-12 11:54:57"),
    "876": ("2026-08-16T12:19:51+00:00", "2026-05-12 12:01:54"),
    "878": ("2026-08-16T12:19:55+00:00", "2026-05-12 02:01:05"),
    "879": ("2026-08-16T12:19:58+00:00", "2026-05-12 02:01:48"),
    "884": ("2026-08-16T12:20:01+00:00", "2026-05-12 02:35:55"),
    "727": ("2026-08-16T12:20:05+00:00", "2025-05-22 09:02:51"),
    "729": ("2026-08-16T12:20:08+00:00", "2025-05-22 09:16:54"),
    "492": ("2026-08-16T12:20:13+00:00", "2025-02-13 03:39:59"),
    "760": ("2026-08-16T12:20:17+00:00", "2025-02-13 03:42:38"),
    "473": ("2026-08-16T12:20:22+00:00", "2026-01-26 02:23:41"),
    "773": ("2026-08-16T12:20:37+00:00", "2025-12-23 10:55:02"),
}

OBS_FIELDS = [
    "observation_id", "indicator_id", "geography_id", "time_start", "time_end", "frequency",
    "value_numeric", "unit", "claim_type", "provenance_id", "suppressed", "comparable",
    "methodology_version", "price_basis", "notes",
]
PROV_FIELDS = [
    "provenance_id", "source_id", "artifact_locator", "retrieved_at", "source_release",
    "checksum_sha256", "parser_revision", "transform_revision", "extraction_method", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def stable_id(prefix: str, *parts: str) -> str:
    return prefix + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def semantic_result_sha256(snapshot_path: Path) -> str:
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if "result" not in payload:
        raise ValueError(f"{snapshot_path}: missing BPS result payload")
    canonical = json.dumps(
        payload["result"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def geography_map(path: Path) -> dict[str, str]:
    result = {
        row["bps_code"]: row["geography_id"]
        for row in read_csv(path)
        if row.get("parent_geography_id") == "idn.13"
        and row.get("status") == "current"
        and row.get("geography_level") in {"regency", "city"}
    }
    if set(result) != EXPECTED_CODES:
        raise ValueError(f"current Sumbar geography footprint drifted: {sorted(result)}")
    return result


def validate_indicator_registry(path: Path, configs: list[dict[str, str]]) -> None:
    indicators = {row["indicator_id"]: row for row in read_csv(path)}
    for config in configs:
        iid = config["indicator_id"]
        row = indicators.get(iid)
        if row is None:
            raise ValueError(f"batch indicator is not registered: {iid}")
        allowed = set(filter(None, row["allowed_claim_types"].split("|")))
        if config["claim_type"] not in allowed:
            raise ValueError(f"claim type {config['claim_type']} not allowed for {iid}: {sorted(allowed)}")
        if config["canonical_unit"] != row["unit"]:
            raise ValueError(f"canonical unit mismatch for {iid}: {config['canonical_unit']} != {row['unit']}")


def parse_decimal(value: str, context: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{context}: non-numeric source value {value!r}") from exc
    if not number.is_finite():
        raise ValueError(f"{context}: non-finite source value")
    return number


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def transformed_value(config: dict[str, str], rows_by_turvar: dict[str, dict[str, str]]) -> tuple[Decimal | None, str]:
    transform = config["transform"]
    selected = config["selected_turvar_id"]
    denominator_ids = [item for item in config["denominator_turvar_ids"].split("|") if item]

    def get(turvar_id: str) -> Decimal:
        row = rows_by_turvar.get(turvar_id)
        if row is None:
            raise ValueError(f"{config['series_id']}: missing required turvar {turvar_id}")
        return parse_decimal(row["value"], f"{config['series_id']} turvar={turvar_id}")

    if transform == "identity":
        value = get(selected)
        detail = f"source_value={decimal_text(value)}; selected_turvar={selected}"
    elif transform == "multiply_10":
        source = get(selected)
        value = source * Decimal("10")
        detail = f"source_value_per_100={decimal_text(source)}; selected_turvar={selected}; multiplier=10"
    elif transform == "sum_turvar_ids":
        if not denominator_ids:
            raise ValueError(f"{config['series_id']}: sum transform has no turvar ids")
        parts = [(tid, get(tid)) for tid in denominator_ids]
        value = sum((part for _, part in parts), Decimal("0"))
        detail = "source_components=" + "|".join(f"{tid}:{decimal_text(part)}" for tid, part in parts)
    elif transform == "share_selected_over_sum_turvar_ids":
        if selected not in denominator_ids:
            raise ValueError(f"{config['series_id']}: numerator must be part of denominator categories")
        numerator = get(selected)
        parts = [(tid, get(tid)) for tid in denominator_ids]
        denominator = sum((part for _, part in parts), Decimal("0"))
        detail = (
            f"numerator={selected}:{decimal_text(numerator)}; denominator_components="
            + "|".join(f"{tid}:{decimal_text(part)}" for tid, part in parts)
        )
        if denominator < 0:
            raise ValueError(f"{config['series_id']}: negative road-length denominator")
        if denominator == 0:
            return None, detail + "; undefined_zero_denominator=true"
        value = (numerator / denominator * Decimal("100")).quantize(Decimal("0.000001"))
    else:
        raise ValueError(f"{config['series_id']}: unsupported transform {transform!r}")
    return value, detail


def existing_collisions(output_dir: Path) -> tuple[set[str], set[tuple[str, str, str, str]]]:
    ids: set[str] = set()
    keys: set[tuple[str, str, str, str]] = set()
    for path in (ROOT / "data" / "processed").rglob("*.csv"):
        if output_dir in path.parents:
            continue
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = set(reader.fieldnames or [])
                if not {"observation_id", "indicator_id", "geography_id", "time_start"}.issubset(fields):
                    continue
                for row in reader:
                    oid = (row.get("observation_id") or "").strip()
                    if oid:
                        ids.add(oid)
                    key = (
                        (row.get("indicator_id") or "").strip(),
                        (row.get("geography_id") or "").strip(),
                        (row.get("time_start") or "").strip(),
                        (row.get("time_end") or "").strip(),
                    )
                    if all(key[:3]):
                        keys.add(key)
        except (OSError, UnicodeDecodeError, csv.Error):
            continue
    return ids, keys


def load_source(input_root: Path, config: dict[str, str]) -> tuple[list[dict[str, str]], Path]:
    var_id = config["bps_var_id"]
    period = config["period_label"]
    source_dir = input_root / f"var-{var_id}"
    long_path = source_dir / f"var-{var_id}-long.csv"
    snapshot_path = source_dir / f"var-{var_id}-{period}.json"
    if not long_path.is_file() or not snapshot_path.is_file():
        raise ValueError(f"missing harvested source for var={var_id} period={period}")
    rows = [row for row in read_csv(long_path) if row["bps_th_label"] == period]
    if not rows:
        raise ValueError(f"no normalized rows for var={var_id} period={period}")
    if {row["bps_th_id"] for row in rows} != {config["period_id"]}:
        raise ValueError(f"BPS period id drifted for var={var_id} period={period}")
    actual_semantic_sha = semantic_result_sha256(snapshot_path)
    if actual_semantic_sha != config["semantic_result_sha256"]:
        raise ValueError(
            f"semantic source drift for var={var_id} period={period}: "
            f"{actual_semantic_sha} != {config['semantic_result_sha256']}"
        )
    return rows, snapshot_path


def build(
    input_root: Path,
    series_path: Path,
    geography_path: Path,
    indicator_path: Path,
    output_dir: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    configs = read_csv(series_path)
    if len(configs) != EXPECTED_BATCH_INDICATORS or len({row["indicator_id"] for row in configs}) != EXPECTED_BATCH_INDICATORS:
        raise ValueError("Milestone 4 closure registry must contain exactly 22 unique indicator series")
    geo = geography_map(geography_path)
    validate_indicator_registry(indicator_path, configs)
    existing_ids, existing_keys = existing_collisions(output_dir)

    source_cache: dict[tuple[str, str], tuple[list[dict[str, str]], Path]] = {}
    provenance_by_source: dict[tuple[str, str], dict[str, str]] = {}
    observations: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_keys: set[tuple[str, str, str, str]] = set()
    series_summary: list[dict[str, Any]] = []

    for config in configs:
        source_key = (config["bps_var_id"], config["period_label"])
        if source_key not in source_cache:
            source_cache[source_key] = load_source(input_root, config)
        rows, _snapshot_path = source_cache[source_key]
        var_id, period = source_key
        meta = QUALIFIED_SOURCE_META.get(var_id)
        if meta is None:
            raise ValueError(f"qualified source metadata missing for var={var_id}")
        retrieved_at, source_release = meta
        provenance_id = stable_id("bpsm4prov_", var_id, period, config["semantic_result_sha256"])
        if source_key not in provenance_by_source:
            first = rows[0]
            provenance_by_source[source_key] = {
                "provenance_id": provenance_id,
                "source_id": "bps_webapi",
                "artifact_locator": f"bps-webapi://domain/1300/var/{var_id}/th/{config['period_id']}",
                "retrieved_at": retrieved_at,
                "source_release": source_release,
                "checksum_sha256": config["semantic_result_sha256"],
                "parser_revision": "normalize_bps_dynamic:v2",
                "transform_revision": "materialize_bps_milestone4_batch1:v1",
                "extraction_method": "api",
                "notes": (
                    f"var={var_id} {first['bps_var_label']}; period={period}; "
                    "checksum_scope=sha256_of_canonicalized_BPS_result_payload_excluding_local_retrieval_wrapper; "
                    "the source was re-harvested and required to match this semantic checksum before materialization"
                ),
            }
        elif provenance_by_source[source_key]["provenance_id"] != provenance_id:
            raise ValueError(f"inconsistent semantic hash configuration for var={var_id} period={period}")

        grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
        source_labels: dict[str, str] = {}
        for row in rows:
            code = row["bps_vervar_id"]
            if code not in EXPECTED_CODES:
                continue
            turvar_id = row["bps_turvar_id"]
            if turvar_id in grouped[code]:
                raise ValueError(f"duplicate source cell var={var_id} period={period} geography={code} turvar={turvar_id}")
            grouped[code][turvar_id] = row
            source_labels[code] = row["bps_vervar_label"]

        expected_count = int(config["expected_geography_count"])
        actual_codes = set(grouped)
        if expected_count == 19:
            if actual_codes != EXPECTED_CODES:
                raise ValueError(f"{config['series_id']}: expected all 19 current geographies; got {sorted(actual_codes)}")
        elif expected_count == 18:
            expected = EXPECTED_CODES - {"1301"}
            if actual_codes != expected:
                raise ValueError(f"{config['series_id']}: expected 18 geographies excluding Mentawai; got {sorted(actual_codes)}")
        else:
            raise ValueError(f"{config['series_id']}: unsupported expected geography count {expected_count}")

        produced = 0
        undefined_codes: list[str] = []
        for code in sorted(actual_codes):
            geography_id = geo[code]
            value, transform_detail = transformed_value(config, grouped[code])
            if value is None:
                undefined_codes.append(code)
                continue
            observation_id = stable_id(
                "bpsm4obs_", config["indicator_id"], geography_id, config["time_start"], config["time_end"], provenance_id
            )
            semantic_key = (config["indicator_id"], geography_id, config["time_start"], config["time_end"])
            if observation_id in seen_ids or semantic_key in seen_keys:
                raise ValueError(f"duplicate batch observation for {semantic_key}")
            if observation_id in existing_ids or semantic_key in existing_keys:
                raise ValueError(f"collision with existing canonical observation for {semantic_key}")
            seen_ids.add(observation_id)
            seen_keys.add(semantic_key)
            missing_note = ""
            if expected_count == 18:
                missing_note = " source_geography_1301_Kepulauan_Mentawai_absent_not_zero_imputed;"
            observations.append({
                "observation_id": observation_id,
                "indicator_id": config["indicator_id"],
                "geography_id": geography_id,
                "time_start": config["time_start"],
                "time_end": config["time_end"],
                "frequency": config["frequency"],
                "value_numeric": decimal_text(value),
                "unit": config["canonical_unit"],
                "claim_type": config["claim_type"],
                "provenance_id": provenance_id,
                "suppressed": "false",
                "comparable": "true",
                "methodology_version": config["methodology_version"],
                "price_basis": config["price_basis"],
                "notes": (
                    f"series_id={config['series_id']}; source_var={var_id}; source_period={period}; "
                    f"source_geography={code}:{source_labels[code]}; transform={config['transform']}; "
                    f"{transform_detail}; source_universe={config['source_universe']}; "
                    f"qualification={config['qualification_notes']};{missing_note}"
                ),
            })
            produced += 1
        expected_produced = expected_count
        if config["series_id"] == "m4_road_good_2024":
            expected_undefined = {"1374", "1375"}
            if set(undefined_codes) != expected_undefined:
                raise ValueError(
                    f"{config['series_id']}: undefined geography set drifted: {sorted(undefined_codes)}"
                )
            expected_produced = 17
        elif undefined_codes:
            raise ValueError(
                f"{config['series_id']}: unexpected undefined geography values: {sorted(undefined_codes)}"
            )
        if produced != expected_produced:
            raise ValueError(
                f"{config['series_id']}: produced {produced} rows instead of {expected_produced}"
            )
        series_summary.append({
            "series_id": config["series_id"],
            "indicator_id": config["indicator_id"],
            "bps_var_id": int(var_id),
            "period_label": period,
            "row_count": produced,
            "claim_type": config["claim_type"],
            "transform": config["transform"],
            "missing_current_geographies": sorted(EXPECTED_CODES - actual_codes),
            "undefined_current_geographies": sorted(undefined_codes),
        })

    provenance = sorted(provenance_by_source.values(), key=lambda row: row["provenance_id"])
    observations.sort(key=lambda row: row["observation_id"])
    if len(observations) != EXPECTED_BATCH_OBSERVATIONS:
        raise ValueError(f"expected {EXPECTED_BATCH_OBSERVATIONS} batch observations; got {len(observations)}")
    if len(provenance) != EXPECTED_BATCH_PROVENANCE:
        raise ValueError(f"expected {EXPECTED_BATCH_PROVENANCE} provenance rows; got {len(provenance)}")
    if {row["provenance_id"] for row in observations} - {row["provenance_id"] for row in provenance}:
        raise ValueError("batch contains unresolved provenance ids")

    return observations, provenance, {
        "schema": "ranah-observatory/bps-milestone4-closure-batch/v1",
        "source_id": "bps_webapi",
        "indicator_count": len({row["indicator_id"] for row in observations}),
        "observation_count": len(observations),
        "provenance_count": len(provenance),
        "source_snapshot_count": len(source_cache),
        "semantic_source_locks_enforced": True,
        "canonical_promotion_performed": True,
        "series": series_summary,
        "held_candidates": [
            {"bps_var_id": 427, "reason": "BPS Dynamic Data datacontent is not an object in the qualified probe"},
            {"bps_var_id": 797, "reason": "electricity customer count is not household electricity access"},
            {"bps_var_id": 759, "reason": "industry category ids 1 2 3 are not semantically qualified from current artifact"},
            {"bps_var_id": 855, "reason": "formal informal classification rule requires separate qualification"},
            {"bps_var_id": 303, "reason": "source dimension is industry class rather than a regency city geography panel"},
        ],
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_outputs(observations: list[dict[str, str]], provenance: list[dict[str, str]], manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    obs_path = output_dir / "bps-milestone4-batch1-observations.csv"
    prov_path = output_dir / "bps-milestone4-batch1-provenance.csv"
    manifest_path = output_dir / "bps-milestone4-batch1.manifest.json"
    obs_sha = write_csv(obs_path, OBS_FIELDS, observations)
    prov_sha = write_csv(prov_path, PROV_FIELDS, provenance)
    final = dict(manifest)
    final.update({
        "observations_file": obs_path.name,
        "observations_sha256": obs_sha,
        "provenance_file": prov_path.name,
        "provenance_sha256": prov_sha,
    })
    manifest_path.write_text(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return final


def validate_output(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "bps-milestone4-batch1.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    obs_path = output_dir / manifest["observations_file"]
    prov_path = output_dir / manifest["provenance_file"]
    observations = read_csv(obs_path)
    provenance = read_csv(prov_path)
    if len({row["indicator_id"] for row in observations}) != EXPECTED_BATCH_INDICATORS:
        raise ValueError("frozen batch indicator count drifted")
    if len(observations) != EXPECTED_BATCH_OBSERVATIONS or len(provenance) != EXPECTED_BATCH_PROVENANCE:
        raise ValueError("frozen batch cardinality drifted")
    if hashlib.sha256(obs_path.read_bytes()).hexdigest() != manifest["observations_sha256"]:
        raise ValueError("frozen batch observations checksum mismatch")
    if hashlib.sha256(prov_path.read_bytes()).hexdigest() != manifest["provenance_sha256"]:
        raise ValueError("frozen batch provenance checksum mismatch")
    prov_ids = {row["provenance_id"] for row in provenance}
    if any(row["provenance_id"] not in prov_ids for row in observations):
        raise ValueError("frozen batch contains unresolved provenance")
    if len({row["observation_id"] for row in observations}) != len(observations):
        raise ValueError("frozen batch contains duplicate observation ids")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the BPS Milestone 4 closure batch.")
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--series", type=Path, default=DEFAULT_SERIES)
    parser.add_argument("--geographies", type=Path, default=DEFAULT_GEOGRAPHIES)
    parser.add_argument("--indicators", type=Path, default=DEFAULT_INDICATORS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_only:
            manifest = validate_output(args.output_dir)
        else:
            if args.input_root is None:
                raise ValueError("--input-root is required unless --validate-only is used")
            observations, provenance, manifest = build(
                args.input_root, args.series, args.geographies, args.indicators, args.output_dir
            )
            manifest = write_outputs(observations, provenance, manifest, args.output_dir)
            validate_output(args.output_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
