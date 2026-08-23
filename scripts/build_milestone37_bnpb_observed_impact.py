#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/bnpb/m37_observed_impact/sumatera-barat-source-rows.json"
OUT_DIR = ROOT / "data/processed/bnpb/m37_observed_impact"
OUT_CSV = OUT_DIR / "sumatera-barat-observed-impact-2024-2025.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone37_bnpb_observed_impact.json"

METRICS = {
    "deaths": {"label": "reported_deaths", "unit": "persons_reported"},
    "affected": {"label": "reported_affected_people", "unit": "persons_reported"},
    "injured": {"label": "reported_injured_or_sick_people", "unit": "persons_reported"},
    "displaced": {"label": "reported_displaced_people", "unit": "persons_reported"},
    "houses": {"label": "reported_damaged_houses", "unit": "housing_units_reported"},
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_snapshot() -> dict:
    payload = json.loads(RAW.read_text(encoding="utf-8"))
    assert payload["schema"] == "ranah-observatory/bnpb-observed-impact-source-row-snapshot/v1"
    scope = payload["scope"]
    assert scope["province_code"] == 13
    assert scope["province_name"] == "SUMATERA BARAT"
    assert scope["years"] == [2024, 2025]
    assert scope["metrics"] == list(METRICS)
    assert len(scope["hazards"]) == 9
    records = payload["records"]
    assert len(records) == 10
    assert len({(r["year"], r["metric_id"]) for r in records}) == 10
    for record in records:
        assert record["metric_id"] in METRICS
        assert len(record["workbook_sha256"]) == 64
        assert record["source_note_province_label_swap_present"] is True
        assert set(record["values"]) == set(scope["hazards"])
        for value in record["values"].values():
            assert value is None or (isinstance(value, int) and value >= 0)
    return payload


def build() -> tuple[str, str]:
    snapshot = load_snapshot()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    hazards = snapshot["scope"]["hazards"]

    rows: list[dict[str, object]] = []
    for record in sorted(snapshot["records"], key=lambda r: (r["year"], list(METRICS).index(r["metric_id"]))):
        for hazard in hazards:
            value = record["values"][hazard]
            rows.append({
                "year": record["year"],
                "metric_id": record["metric_id"],
                "hazard": hazard,
                "value": "" if value is None else value,
                "source_cell_state": "source_blank" if value is None else "reported_numeric",
                "source_resource_id": record["resource_id"],
            })

    fieldnames = ["year", "metric_id", "hazard", "value", "source_cell_state", "source_resource_id"]
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    csv_text = buf.getvalue()
    OUT_CSV.write_text(csv_text, encoding="utf-8", newline="")

    raw_bytes = RAW.read_bytes()
    blank_rows = [r for r in rows if r["source_cell_state"] == "source_blank"]
    manifest = {
        "schema": "ranah-observatory/milestone37-bnpb-observed-impact/v1",
        "milestone": 37,
        "title": "BNPB provincial observed-impact context for West Sumatra, 2024-2025",
        "source_snapshot": {
            "path": RAW.relative_to(ROOT).as_posix(),
            "sha256": sha256_bytes(raw_bytes),
            "record_count": len(snapshot["records"]),
            "full_workbooks_committed": False,
            "workbook_sha256_recorded": True,
        },
        "coverage": {
            "years": [2024, 2025],
            "metric_count": len(METRICS),
            "hazard_count": len(hazards),
            "expected_cells": len(rows),
            "numeric_cells": len(rows) - len(blank_rows),
            "source_blank_cells": len(blank_rows),
        },
        "metrics": METRICS,
        "workbook_digests": [
            {"year": r["year"], "metric_id": r["metric_id"], "resource_id": r["resource_id"], "sha256": r["workbook_sha256"]}
            for r in snapshot["records"]
        ],
        "normalized_output": {
            "path": OUT_CSV.relative_to(ROOT).as_posix(),
            "sha256": sha256_bytes(csv_text.encode("utf-8")),
            "row_count": len(rows),
        },
        "source_blank_cells": [
            {"year": r["year"], "metric_id": r["metric_id"], "hazard": r["hazard"], "interpretation": "unknown_or_not_reported_in_source_cell_not_zero"}
            for r in blank_rows
        ],
        "qualification": {
            "classification": "qualified_source_native_provincial_observed_impact_context",
            "observed_impact_context_authorized": True,
            "event_level_observed_impact_authorized": False,
            "district_city_observed_impact_authorized": False,
            "unique_person_annual_aggregation_authorized": False,
            "cross_hazard_person_sum_authorized": False,
            "cross_metric_composite_authorized": False,
            "risk_synthesis_authorized": False,
            "causal_claim_authorized": False,
            "monetary_loss_inference_authorized": False,
            "policy_ranking_authorized": False,
        },
        "interpretation": {
            "allowed": "Report source-native BNPB province-by-hazard administrative impact counts for each metric and year with blanks preserved separately from numeric zero.",
            "forbidden": "Do not treat aggregate cells as event-level records, unique people across events or hazards, a composite disaster-risk score, causal climate effects, monetary loss, or policy ranking.",
        },
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest["normalized_output"]["sha256"], sha256_bytes(OUT_MANIFEST.read_bytes())


def main() -> int:
    csv_sha, manifest_sha = build()
    print(json.dumps({"csv_sha256": csv_sha, "manifest_sha256": manifest_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
