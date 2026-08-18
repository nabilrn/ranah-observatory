#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / "data/analysis/quasi_causal/m8-preperiod-real-grdp-2005-2009.csv"
POST = ROOT / "data/analysis/quasi_causal/m8-postperiod-real-grdp-2009-2013.csv"
OUTPUT = ROOT / "data/analysis/quasi_causal/m8-grdp-2009-overlap.csv"
MANIFEST = ROOT / "data/manifests/milestone8_grdp_overlap.json"

EXPECTED_GEOGRAPHIES = {
    "idn.13.1301", "idn.13.1302", "idn.13.1303", "idn.13.1304", "idn.13.1305",
    "idn.13.1306", "idn.13.1307", "idn.13.1308", "idn.13.1309", "idn.13.1310",
    "idn.13.1311", "idn.13.1312", "idn.13.1371", "idn.13.1372", "idn.13.1373",
    "idn.13.1374", "idn.13.1375", "idn.13.1376", "idn.13.1377",
}
MATERIALITY_THRESHOLD_PERCENT = 0.5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def overlap_rows(path: Path) -> dict[str, dict[str, str]]:
    rows = [row for row in read_csv(path) if row.get("year") == "2009"]
    ids = [row.get("geography_id", "") for row in rows]
    if len(rows) != 19 or len(set(ids)) != 19 or set(ids) != EXPECTED_GEOGRAPHIES:
        raise RuntimeError(f"{path.name}: 2009 overlap footprint is not exact 19 geographies")
    return {row["geography_id"]: row for row in rows}


def main() -> int:
    pre = overlap_rows(PRE)
    post = overlap_rows(POST)

    output: list[dict[str, Any]] = []
    for gid in sorted(EXPECTED_GEOGRAPHIES):
        left = pre[gid]
        right = post[gid]
        if left["geography_name"] != right["geography_name"]:
            raise RuntimeError(f"geography-name mismatch for {gid}: {left['geography_name']!r} vs {right['geography_name']!r}")
        pre_value = float(left["real_grdp_constant_2000_million_rupiah"])
        post_value = float(right["real_grdp_constant_2000_million_rupiah"])
        if pre_value <= 0 or post_value <= 0:
            raise RuntimeError(f"non-positive 2009 GRDP for {gid}")
        absolute_difference = post_value - pre_value
        relative_difference_percent = absolute_difference / pre_value * 100.0
        output.append(
            {
                "geography_id": gid,
                "geography_name": left["geography_name"],
                "pre_source_2009_million_rupiah": pre_value,
                "pre_source_revision_status": left["revision_status"],
                "post_source_2009_million_rupiah": post_value,
                "post_source_revision_status": right["revision_status"],
                "absolute_difference_million_rupiah": absolute_difference,
                "relative_difference_percent_of_pre": relative_difference_percent,
                "absolute_relative_difference_percent": abs(relative_difference_percent),
                "within_0_5_percent_materiality_gate": abs(relative_difference_percent) <= MATERIALITY_THRESHOLD_PERCENT,
                "bridge_value_selected_million_rupiah": post_value,
                "bridge_source": "later_postperiod_source_table_13_1_2",
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output[0])
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)

    failures = [row for row in output if row["within_0_5_percent_materiality_gate"] is not True]
    max_row = max(output, key=lambda row: float(row["absolute_relative_difference_percent"]))
    exact_matches = sum(float(row["absolute_difference_million_rupiah"]) == 0.0 for row in output)
    reconciled = len(failures) == 0
    manifest = {
        "schema": "ranah-observatory/milestone8-grdp-overlap/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "overlap_year": 2009,
        "geography_count": len(output),
        "price_basis": "constant_2000",
        "unit": "million_rupiah",
        "pre_source": "m8_grdp_pre Table 22",
        "pre_source_2009_revision_status": "preliminary",
        "post_source": "m8_grdp_post Table 13.1.2",
        "materiality_threshold_percent": MATERIALITY_THRESHOLD_PERCENT,
        "materiality_rule_locked_before_model_fit": True,
        "bridge_rule": "if every 2009 absolute relative difference <=0.5%, retain pre source for 2005-2008 and use the later post-period source for 2009-2013; preserve all overlap differences",
        "bridge_source_for_2009": "later_postperiod_source_table_13_1_2" if reconciled else None,
        "exact_match_count": exact_matches,
        "max_absolute_relative_difference_percent": float(max_row["absolute_relative_difference_percent"]),
        "max_difference_geography_id": max_row["geography_id"],
        "max_difference_geography_name": max_row["geography_name"],
        "failure_count": len(failures),
        "failures": failures,
        "overlap_2009_reconciled": reconciled,
        "pre_input_path": str(PRE.relative_to(ROOT)),
        "pre_input_sha256": sha256(PRE),
        "post_input_path": str(POST.relative_to(ROOT)),
        "post_input_sha256": sha256(POST),
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "outcome_panel_combined": False,
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if reconciled else 1


if __name__ == "__main__":
    raise SystemExit(main())
