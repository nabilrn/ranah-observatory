#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

from normalize_bps_dynamic import BPSDynamicNormalizationError, normalize_dynamic_payload

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshots" / "bps" / "var-484-1971.json"
CHECKSUM = ROOT / "data" / "snapshots" / "bps" / "var-484-1971.json.sha256"
SOURCE_NATIVE = ROOT / "data" / "processed" / "bps" / "historical_population_source_native.csv"
GEOGRAPHIES = ROOT / "data" / "registries" / "geographies.csv"
ANOMALIES = ROOT / "data" / "registries" / "historical_source_anomalies.csv"
EXPECTED_SHA256 = "b0d808a6b59b018c7a28f5d47b882f17248eb9ae2d0b05a6acb62366ca2813e1"
SPLIT_OR_LATER_CODES = {"1301", "1310", "1311", "1312", "1377"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    raw = SNAPSHOT.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        errors.append(f"snapshot SHA-256 mismatch: {digest}")

    checksum_line = CHECKSUM.read_text(encoding="utf-8").strip()
    expected_line = f"{EXPECTED_SHA256}  {SNAPSHOT.name}"
    if checksum_line != expected_line:
        errors.append("checksum sidecar does not match the frozen snapshot")

    snapshot = json.loads(raw.decode("utf-8"))
    result = snapshot.get("result")
    if not isinstance(result, dict):
        errors.append("snapshot result is missing")
        return errors, {"source_rows": 0, "local_rows": 0}

    try:
        normalized, diagnostics = normalize_dynamic_payload(result)
    except BPSDynamicNormalizationError as exc:
        errors.append(f"dynamic normalization failed: {exc}")
        return errors, {"source_rows": 0, "local_rows": 0}

    selected = [
        row
        for row in normalized
        if str(row["bps_var_id"]) == "484"
        and str(row["bps_turvar_id"]) == "34"
        and str(row["bps_th_label"]) == "1971"
        and str(row["bps_turth_id"]) == "0"
    ]
    if len(selected) != 15:
        errors.append(f"expected 15 observed total-population rows for 1971, found {len(selected)}")

    variable_note = str(result.get("var", [{}])[0].get("note", ""))
    if "1971" not in variable_note or "Sensus Penduduk" not in variable_note:
        errors.append("BPS variable metadata does not explicitly identify 1971 as a census year")

    processed = read_csv(SOURCE_NATIVE)
    if len(processed) != len(selected):
        errors.append(f"processed source-native row count {len(processed)} does not match normalized count {len(selected)}")

    normalized_by_code = {str(row["bps_vervar_id"]): row for row in selected}
    processed_by_code = {row["bps_vervar_id"]: row for row in processed}
    if set(normalized_by_code) != set(processed_by_code):
        errors.append("processed source-native geography codes do not exactly match observed snapshot values")

    for code, row in processed_by_code.items():
        source = normalized_by_code.get(code)
        if source is None:
            continue
        if row["bps_vervar_label"] != str(source["bps_vervar_label"]):
            errors.append(f"{code}: source geography label differs from snapshot")
        try:
            processed_value = int(row["value"])
            source_value = int(source["value"])
        except ValueError:
            errors.append(f"{code}: population value must be integer-compatible")
            continue
        if processed_value != source_value:
            errors.append(f"{code}: processed value {processed_value} != snapshot value {source_value}")
        if row["snapshot_sha256"] != EXPECTED_SHA256:
            errors.append(f"{code}: processed row does not retain snapshot checksum")
        if row["canonical_indicator_id"] != "historical_population":
            errors.append(f"{code}: wrong canonical indicator mapping")
        if row["reconstruction_state"] != "observed_source_era":
            errors.append(f"{code}: source observation was incorrectly promoted to reconstruction")

    for code in SPLIT_OR_LATER_CODES:
        if code in processed_by_code:
            errors.append(f"later/split geography {code} was synthesized into the 1971 source-native table")

    province = processed_by_code.get("1300")
    if province is None:
        errors.append("province aggregate 1300 is missing")
        province_value = 0
    else:
        province_value = int(province["value"])
        if province_value != 2789822:
            errors.append(f"unexpected 1971 province population {province_value}")
        if province["canonical_geography_id"] != "idn.13.h1958":
            errors.append("1971 province row must map to source-era geography idn.13.h1958")
        if province["mapping_status"] != "qualified_source_era":
            errors.append("1971 province row is not qualified as source-era")

    locals_total = sum(int(row["value"]) for code, row in processed_by_code.items() if code != "1300")
    if locals_total != province_value:
        errors.append(f"1971 local rows sum to {locals_total}, not province total {province_value}")

    for code, row in processed_by_code.items():
        if code == "1300":
            continue
        if row["canonical_geography_id"]:
            errors.append(f"{code}: historical local row must not map directly to a modern canonical geography")
        if row["mapping_status"] != "historical_geography_pending":
            errors.append(f"{code}: expected historical_geography_pending")

    geographies = {row["geography_id"]: row for row in read_csv(GEOGRAPHIES)}
    historical_province = geographies.get("idn.13.h1958")
    if not historical_province:
        errors.append("source-era Sumatera Barat geography idn.13.h1958 is missing")
    else:
        if historical_province["status"] != "historical":
            errors.append("idn.13.h1958 must be historical")
        if historical_province["valid_from"] != "1958-07-31":
            errors.append("idn.13.h1958 must retain the qualified UU 61/1958 anchor date")
        if historical_province["source_id"] != "bpk_legal_database":
            errors.append("idn.13.h1958 must cite the qualified legal source")

    anomalies = {row["anomaly_id"]: row for row in read_csv(ANOMALIES)}
    conflict = anomalies.get("bukittinggi_population_1971_official_conflict")
    if not conflict:
        errors.append("Bukittinggi 1971 official-source conflict is not registered")
    else:
        if "63356" not in conflict["claim_a"] or "63132" not in conflict["claim_b"]:
            errors.append("Bukittinggi conflict register does not retain both competing values")
        if conflict["status"] != "unresolved":
            errors.append("Bukittinggi conflict must remain unresolved")

    if diagnostics["unexpected_datacontent_keys"]:
        errors.append("snapshot normalizer reported unexpected data keys")

    return errors, {"source_rows": len(processed), "local_rows": max(0, len(processed) - 1)}


def main() -> int:
    try:
        errors, counts = validate()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BPS historical anchor validation FAILED: {exc}", file=sys.stderr)
        return 1
    if errors:
        print("BPS historical anchor validation FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        "BPS historical anchor validation passed: "
        f"{counts['source_rows']} source-native rows, {counts['local_rows']} local rows, province total reconciled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
