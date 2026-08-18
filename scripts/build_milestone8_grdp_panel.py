#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "data/analysis/quasi_causal/m8-preperiod-real-grdp-2005-2009.csv"
POST = ROOT / "data/analysis/quasi_causal/m8-postperiod-real-grdp-2009-2013.csv"
OVERLAP = ROOT / "data/manifests/milestone8_grdp_overlap.json"
POST_MANIFEST = ROOT / "data/manifests/milestone8_postperiod_grdp.json"
OUTPUT = ROOT / "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013.csv"
MANIFEST = ROOT / "data/manifests/milestone8_grdp_panel.json"

YEARS = list(range(2005, 2014))
EXPECTED_GEOGRAPHIES = {
    "idn.13.1301", "idn.13.1302", "idn.13.1303", "idn.13.1304", "idn.13.1305",
    "idn.13.1306", "idn.13.1307", "idn.13.1308", "idn.13.1309", "idn.13.1310",
    "idn.13.1311", "idn.13.1312", "idn.13.1371", "idn.13.1372", "idn.13.1373",
    "idn.13.1374", "idn.13.1375", "idn.13.1376", "idn.13.1377",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def main() -> int:
    overlap = json.loads(OVERLAP.read_text(encoding="utf-8"))
    if overlap.get("overlap_2009_reconciled") is not True:
        raise RuntimeError("2009 overlap is not reconciled")
    if overlap.get("bridge_source_for_2009") != "later_postperiod_source_table_13_1_2":
        raise RuntimeError("unexpected 2009 bridge source")
    if float(overlap.get("materiality_threshold_percent")) != 0.5:
        raise RuntimeError("2009 materiality gate drift")

    pre_rows = read_csv(PRE)
    post_rows = read_csv(POST)
    pre_selected = [row for row in pre_rows if int(row["year"]) <= 2008]
    post_selected = [row for row in post_rows if int(row["year"]) >= 2009]
    if len(pre_selected) != 76:
        raise RuntimeError(f"expected 76 pre-bridge observations, got {len(pre_selected)}")
    if len(post_selected) != 95:
        raise RuntimeError(f"expected 95 post-bridge observations, got {len(post_selected)}")

    post_manifest = json.loads(POST_MANIFEST.read_text(encoding="utf-8"))
    growth = post_manifest.get("growth_crosscheck") or {}
    failed_keys = {
        (str(row["geography_id"]), int(row["year"]))
        for row in growth.get("failures", [])
        if row.get("geography_id") and row.get("year") is not None
    }

    combined: list[dict[str, Any]] = []
    for row in pre_selected + post_selected:
        year = int(row["year"])
        value = float(row["real_grdp_constant_2000_million_rupiah"])
        if not math.isfinite(value) or value <= 0:
            raise RuntimeError(f"invalid GRDP value for {row['geography_id']} {year}")
        key = (row["geography_id"], year)
        source_block = "preperiod_table22" if year <= 2008 else "postperiod_table13_1_2"
        if year <= 2008:
            consistency = "preperiod_level_source_qualified"
        elif key in failed_keys:
            consistency = "postperiod_level_growth_internal_mismatch_unresolved"
        elif year == 2009:
            consistency = "overlap_reconciled_growth_crosscheck_not_applied"
        else:
            consistency = "postperiod_level_growth_crosscheck_passed"
        combined.append(
            {
                "geography_id": row["geography_id"],
                "geography_name": row["geography_name"],
                "year": year,
                "event_time": year - 2009,
                "real_grdp_constant_2000_million_rupiah": value,
                "log_real_grdp": math.log(value),
                "price_basis": "constant_2000",
                "unit": "million_rupiah",
                "source_block": source_block,
                "source_table": row["source_table"],
                "source_pdf_page": row["source_pdf_page"],
                "revision_status": row["revision_status"],
                "source_internal_consistency_status": consistency,
            }
        )

    combined.sort(key=lambda row: (row["geography_id"], int(row["year"])))
    keys = {(row["geography_id"], int(row["year"])) for row in combined}
    if len(combined) != 171 or len(keys) != 171:
        raise RuntimeError(f"expected exact 171 unique panel observations, got rows={len(combined)} keys={len(keys)}")
    if {row["geography_id"] for row in combined} != EXPECTED_GEOGRAPHIES:
        raise RuntimeError("combined panel geography footprint drift")
    for gid in EXPECTED_GEOGRAPHIES:
        observed_years = {int(row["year"]) for row in combined if row["geography_id"] == gid}
        if observed_years != set(YEARS):
            raise RuntimeError(f"incomplete 2005-2013 footprint for {gid}: {sorted(observed_years)}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(combined[0])
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined)

    anomaly_rows = [
        row for row in combined
        if row["source_internal_consistency_status"] == "postperiod_level_growth_internal_mismatch_unresolved"
    ]
    anomaly_geographies = sorted({row["geography_id"] for row in anomaly_rows})
    model_ready = len(anomaly_rows) == 0
    manifest = {
        "schema": "ranah-observatory/milestone8-grdp-panel/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "geography_count": 19,
        "years": YEARS,
        "observation_count": len(combined),
        "price_basis": "constant_2000",
        "unit": "million_rupiah",
        "bridge_rule": overlap.get("bridge_rule"),
        "preperiod_years_from_table22": [2005, 2006, 2007, 2008],
        "postperiod_years_from_table13_1_2": [2009, 2010, 2011, 2012, 2013],
        "overlap_2009_reconciled": True,
        "anomaly_row_count": len(anomaly_rows),
        "anomaly_geography_count": len(anomaly_geographies),
        "anomaly_geography_ids": anomaly_geographies,
        "anomaly_rows": [
            {"geography_id": row["geography_id"], "geography_name": row["geography_name"], "year": row["year"]}
            for row in anomaly_rows
        ],
        "postperiod_source_anomalies_resolved": len(anomaly_rows) == 0,
        "model_ready": model_ready,
        "pre_input_path": str(PRE.relative_to(ROOT)),
        "pre_input_sha256": sha256(PRE),
        "post_input_path": str(POST.relative_to(ROOT)),
        "post_input_sha256": sha256(POST),
        "overlap_manifest_path": str(OVERLAP.relative_to(ROOT)),
        "overlap_manifest_sha256": sha256(OVERLAP),
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "outcome_panel_combined": True,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
