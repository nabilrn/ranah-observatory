from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping

STATION_ID = "96163099999"
TARGET_YEARS = (1997, 1998)
SOURCE_URL_TEMPLATE = "https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/96163099999.csv"
HISTORICAL_LAT = -(53.0 / 60.0)
HISTORICAL_LON = 100.0 + 21.0 / 60.0
MAX_IDENTITY_DISTANCE_DEG = 0.04
MIN_VALID_FRACTION = 0.90
MAX_MISSING_STREAK_DAYS = 31
MISSING_SENTINEL_FLOOR_IN = 99.0
INCH_TO_MM = 25.4
USER_AGENT = "ranah-observatory-m36/1 (+https://github.com/nabilrn/ranah-observatory)"

CHIRPS_FINDING_ID = "m6_climate_1997_1998_signal"
CHIRPS_FINDING_PATH = Path("data/analysis/historical/west-sumatra-exploratory-findings.csv")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_bytes(url: str, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if int(getattr(response, "status", 200)) != 200:
                raise RuntimeError(f"unexpected HTTP status {getattr(response, 'status', None)} for {url}")
            return response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise RuntimeError(f"failed to fetch {url}: {exc}") from exc


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def normalize_name(value: Any) -> str:
    return " ".join(str(value or "").upper().replace("/", " ").replace("_", " ").split())


def historical_identity_ok(row: Mapping[str, Any]) -> bool:
    station = str(row.get("STATION") or "").strip()
    name = normalize_name(row.get("NAME"))
    lat = as_float(row.get("LATITUDE"))
    lon = as_float(row.get("LONGITUDE"))
    return (
        station == STATION_ID
        and "TABING" in name
        and lat is not None
        and lon is not None
        and abs(lat - HISTORICAL_LAT) <= MAX_IDENTITY_DISTANCE_DEG
        and abs(lon - HISTORICAL_LON) <= MAX_IDENTITY_DISTANCE_DEG
    )


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def valid_prcp_inches(value: Any) -> float | None:
    number = as_float(value)
    if number is None or number < 0 or number >= MISSING_SENTINEL_FLOOR_IN:
        return None
    return number


def max_consecutive_missing(year: int, valid_dates: set[date]) -> int:
    start = date(year, 1, 1)
    days = 366 if calendar.isleap(year) else 365
    longest = current = 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        if day in valid_dates:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def analyze_year_bytes(year: int, data: bytes) -> dict[str, Any]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{year}: source is not UTF-8 CSV") from exc

    reader = csv.DictReader(io.StringIO(text))
    required = {"STATION", "DATE", "LATITUDE", "LONGITUDE", "NAME", "PRCP"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise ValueError(f"{year}: missing required GSOD columns: {sorted(required - set(reader.fieldnames or []))}")

    rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"{year}: empty GSOD source")

    parsed_dates: list[date] = []
    duplicate_dates: set[str] = set()
    seen_dates: set[date] = set()
    wrong_year_rows = 0
    identity_fail_rows = 0
    valid_dates: set[date] = set()
    valid_values: list[float] = []
    present_missing_prcp_days = 0
    prcp_attribute_counts: Counter[str] = Counter()

    for row in rows:
        day = parse_date(row.get("DATE"))
        if day is None:
            wrong_year_rows += 1
            continue
        parsed_dates.append(day)
        if day in seen_dates:
            duplicate_dates.add(day.isoformat())
        seen_dates.add(day)
        if day.year != year:
            wrong_year_rows += 1
        if not historical_identity_ok(row):
            identity_fail_rows += 1

        attr = str(row.get("PRCP_ATTRIBUTES") or "").strip()
        if attr:
            prcp_attribute_counts[attr] += 1

        prcp = valid_prcp_inches(row.get("PRCP"))
        if day.year == year and prcp is not None:
            valid_dates.add(day)
            valid_values.append(prcp)
        elif day.year == year:
            present_missing_prcp_days += 1

    calendar_days = 366 if calendar.isleap(year) else 365
    source_dates_in_year = {d for d in seen_dates if d.year == year}
    row_absent_days = calendar_days - len(source_dates_in_year)
    minimum_valid_days = math.ceil(MIN_VALID_FRACTION * calendar_days)
    longest_missing_streak = max_consecutive_missing(year, valid_dates)
    identity_valid = identity_fail_rows == 0 and wrong_year_rows == 0 and not duplicate_dates
    completeness_pass = (
        identity_valid
        and len(valid_dates) >= minimum_valid_days
        and longest_missing_streak <= MAX_MISSING_STREAK_DAYS
    )

    total_inches = sum(valid_values) if completeness_pass else None
    total_mm = total_inches * INCH_TO_MM if total_inches is not None else None

    identity_samples = []
    for row in rows[:3]:
        identity_samples.append(
            {
                "station": str(row.get("STATION") or "").strip(),
                "date": str(row.get("DATE") or "").strip(),
                "name": str(row.get("NAME") or "").strip(),
                "latitude": as_float(row.get("LATITUDE")),
                "longitude": as_float(row.get("LONGITUDE")),
            }
        )

    return {
        "year": year,
        "source_row_count": len(rows),
        "calendar_days": calendar_days,
        "minimum_valid_prcp_days": minimum_valid_days,
        "valid_prcp_days": len(valid_dates),
        "valid_prcp_fraction": len(valid_dates) / calendar_days,
        "present_rows_missing_prcp_days": present_missing_prcp_days,
        "calendar_days_without_source_row": row_absent_days,
        "maximum_consecutive_days_without_valid_prcp": longest_missing_streak,
        "duplicate_dates": sorted(duplicate_dates),
        "wrong_year_rows": wrong_year_rows,
        "identity_fail_rows": identity_fail_rows,
        "identity_valid": identity_valid,
        "completeness_pass": completeness_pass,
        "annual_prcp_inches": total_inches,
        "annual_prcp_mm": total_mm,
        "prcp_attribute_counts": dict(sorted(prcp_attribute_counts.items())),
        "identity_sample": identity_samples,
    }


def load_chirps_finding(path: Path = CHIRPS_FINDING_PATH) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("finding_id") == CHIRPS_FINDING_ID:
                return dict(row)
    raise ValueError(f"missing frozen CHIRPS finding {CHIRPS_FINDING_ID}")


def classify(years: Mapping[int, Mapping[str, Any]]) -> tuple[str, float | None, float | None]:
    y1997 = years[1997]
    y1998 = years[1998]
    if not y1997["completeness_pass"] or not y1998["completeness_pass"]:
        return "station_overlap_incomplete_or_noncomparable", None, None
    total_1997 = float(y1997["annual_prcp_inches"])
    total_1998 = float(y1998["annual_prcp_inches"])
    delta_inches = total_1998 - total_1997
    pct_change = ((total_1998 / total_1997) - 1.0) * 100.0 if total_1997 > 0 else None
    if delta_inches > 0:
        return "station_overlap_directionally_supportive", delta_inches, pct_change
    return "station_overlap_directionally_discordant", delta_inches, pct_change


def render_summary_csv(years: Mapping[int, Mapping[str, Any]]) -> str:
    fields = [
        "year",
        "source_row_count",
        "calendar_days",
        "minimum_valid_prcp_days",
        "valid_prcp_days",
        "valid_prcp_fraction",
        "present_rows_missing_prcp_days",
        "calendar_days_without_source_row",
        "maximum_consecutive_days_without_valid_prcp",
        "identity_valid",
        "completeness_pass",
        "annual_prcp_inches",
        "annual_prcp_mm",
    ]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for year in TARGET_YEARS:
        row = years[year]
        writer.writerow({
            key: (
                f"{row[key]:.9f}" if key == "valid_prcp_fraction"
                else f"{row[key]:.6f}" if key in {"annual_prcp_inches", "annual_prcp_mm"} and row[key] is not None
                else "" if row[key] is None
                else str(row[key]).lower() if isinstance(row[key], bool)
                else row[key]
            )
            for key in fields
        })
    return out.getvalue()


def source_bytes(year: int, source_dir: Path | None) -> tuple[bytes, str, str]:
    filename = f"ncei_gsod_{STATION_ID}_{year}.csv"
    url = SOURCE_URL_TEMPLATE.format(year=year)
    if source_dir is None:
        data = fetch_bytes(url)
        mode = "live_ncei_bulk_download"
    else:
        data = (source_dir / filename).read_bytes()
        mode = "frozen_offline_source"
    return data, filename, url


def build(output_dir: Path, source_dir: Path | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_source = output_dir / "source"
    output_source.mkdir(parents=True, exist_ok=True)

    years: dict[int, dict[str, Any]] = {}
    source_records: list[dict[str, Any]] = []
    modes: set[str] = set()
    for year in TARGET_YEARS:
        data, filename, url = source_bytes(year, source_dir)
        modes.add("frozen_offline_source" if source_dir is not None else "live_ncei_bulk_download")
        (output_source / filename).write_bytes(data)
        analysis = analyze_year_bytes(year, data)
        years[year] = analysis
        source_records.append({
            "year": year,
            "url": url,
            "file": f"source/{filename}",
            "sha256": sha256_bytes(data),
            "bytes": len(data),
        })

    finding = load_chirps_finding()
    if finding.get("claim_class") != "model_estimate" or finding.get("status") != "descriptive_signal_pending_station_validation":
        raise ValueError("frozen CHIRPS finding state changed unexpectedly")
    statement = finding.get("statement") or ""
    if "all 19 kabupaten/kota are wetter in 1998 than 1997" not in statement:
        raise ValueError("frozen CHIRPS directional finding changed unexpectedly")

    classification, delta_inches, pct_change = classify(years)
    result = {
        "schema": "ranah-observatory/milestone36-station-overlap/v1",
        "station": {
            "gsod_station_identifier": STATION_ID,
            "historical_identity": "TABING, ID / BMKG PADANG/TABING",
            "historical_bmkg_coordinate": [HISTORICAL_LON, HISTORICAL_LAT],
            "stage1_representation": "ncei_gsod_96163099999",
        },
        "source_mode": sorted(modes),
        "source_files": source_records,
        "locked_rules": {
            "minimum_valid_fraction": MIN_VALID_FRACTION,
            "minimum_valid_days_each_target_year": 329,
            "maximum_missing_streak_days": MAX_MISSING_STREAK_DAYS,
            "missing_sentinel_floor_inches": MISSING_SENTINEL_FLOOR_IN,
            "missing_as_zero": False,
            "inch_to_mm": INCH_TO_MM,
            "primary_comparison": "sign(total_1998 - total_1997)",
        },
        "annual": [years[year] for year in TARGET_YEARS],
        "comparison": {
            "classification": classification,
            "delta_1998_minus_1997_inches": delta_inches,
            "delta_1998_minus_1997_mm": delta_inches * INCH_TO_MM if delta_inches is not None else None,
            "station_percent_change_1997_to_1998": pct_change,
            "chirps_finding_id": CHIRPS_FINDING_ID,
            "chirps_claim_class": finding["claim_class"],
            "chirps_status_before_m36": finding["status"],
            "chirps_statement": statement,
            "comparison_scope": "directional_independent_overlap_only",
        },
        "conclusions": {
            "both_years_completeness_pass": all(years[y]["completeness_pass"] for y in TARGET_YEARS),
            "station_overlap_classification": classification,
            "safe_to_relabel_chirps_as_observed": False,
            "safe_to_mark_global_chirps_station_validation_complete": False,
            "safe_to_merge_96163_across_station_history": False,
            "causal_claim_authorized": False,
        },
        "limitations": [
            "GSOD precipitation is derived from synoptic/hourly reports and daily totals appear only when reporting is sufficient.",
            "For this non-US station the GSOD summary day is UTC-based rather than a local-calendar climate day.",
            "A single point station is not magnitude-equivalent to 19 polygon-mean CHIRPS estimates.",
            "The station identifier 96163 has a documented historical-site/current-site discontinuity and is not concatenated across that transition.",
        ],
    }

    (output_dir / "annual-summary.csv").write_text(render_summary_csv(years), encoding="utf-8")
    (output_dir / "station-overlap.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build M36 historical Tabing station rainfall overlap")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    result = build(args.output_dir, args.source_dir)
    print(json.dumps({
        "classification": result["comparison"]["classification"],
        "both_years_completeness_pass": result["conclusions"]["both_years_completeness_pass"],
        "annual": [
            {
                "year": row["year"],
                "valid_prcp_days": row["valid_prcp_days"],
                "valid_prcp_fraction": row["valid_prcp_fraction"],
                "max_missing_streak": row["maximum_consecutive_days_without_valid_prcp"],
                "annual_prcp_mm": row["annual_prcp_mm"],
            }
            for row in result["annual"]
        ],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
