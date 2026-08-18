#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_PANEL = ROOT / "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013.csv"
POST = ROOT / "data/analysis/quasi_causal/m8-postperiod-real-grdp-2009-2013.csv"
BUK_TEXT = ROOT / "data/processed/milestone8/anomaly_crosschecks/bukittinggi-grdp-2011-2013.txt"
SOLOK_2012_TEXT = ROOT / "data/processed/milestone8/anomaly_crosschecks/solok-selatan-dalam-angka-2012.txt"
SOLOK_2013_TEXT = ROOT / "data/processed/milestone8/anomaly_crosschecks/solok-selatan-dalam-angka-2013.txt"
RESOLUTION_CSV = ROOT / "data/analysis/quasi_causal/m8-grdp-source-anomaly-resolution.csv"
RESOLVED_PANEL = ROOT / "data/analysis/quasi_causal/m8-real-grdp-panel-2005-2013-resolved.csv"
MANIFEST = ROOT / "data/manifests/milestone8_grdp_source_anomaly_resolution.json"

NUMBER = r"([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})"
EXPECTED_ANOMALY_KEYS = {
    ("idn.13.1310", 2011),
    ("idn.13.1310", 2012),
    ("idn.13.1375", 2011),
    ("idn.13.1375", 2012),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def id_number(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def page(text: str, page_no: int) -> str:
    pages = text.split("\f")
    if page_no < 1 or page_no > len(pages):
        raise RuntimeError(f"page {page_no} outside extracted text range")
    return pages[page_no - 1]


def parse_two_year_grdp(block: str, year_a: int, year_b: int, *, source_name: str) -> dict[int, float]:
    compact = " ".join(block.split())
    if "Harga Konstan 2000" not in compact and "2000 Constant Prices" not in compact:
        raise RuntimeError(f"{source_name}: constant-2000 table signal missing")
    year_pattern = re.compile(rf"{year_a}\s*[–-]\s*{year_b}")
    if not year_pattern.search(compact):
        raise RuntimeError(f"{source_name}: expected {year_a}-{year_b} period signal missing")
    match = re.search(rf"PDRB/GRDP\s+{NUMBER}\s+{NUMBER}", compact)
    if match is None:
        match = re.search(rf"Produk Domestik Regional Bruto ADH\. Pasar \(000\.000 Rp\)\s+{NUMBER}\s+{NUMBER}", compact)
    if match is None:
        raise RuntimeError(f"{source_name}: could not parse two-year total GRDP row")
    return {year_a: id_number(match.group(1)), year_b: id_number(match.group(2))}


def parse_bukittinggi() -> dict[int, float]:
    text = BUK_TEXT.read_text(encoding="utf-8", errors="replace")
    # The publication, contents and narrative are explicitly 2011-2013, while the
    # printed Table 2 header retained a stale 2010-2012 label. Do not trust that
    # stale header in isolation. We require independent in-publication narrative
    # anchors for the second and third totals before mapping the three-value row.
    if "PDRB Kota Bukittinggi   2011-2013" not in text and "PDRB Kota Bukittinggi      2011-2013" not in text:
        raise RuntimeError("Bukittinggi publication-period signal 2011-2013 missing")
    block = " ".join(page(text, 28).split())
    match = re.search(rf"PDRB\s+{NUMBER}\s+{NUMBER}\s+{NUMBER}", block)
    if match is None:
        raise RuntimeError("Bukittinggi Table 2 total row not parsed")
    values = [id_number(match.group(index)) for index in (1, 2, 3)]
    if "tahun 2012 nilai tambah yang dihasilkan sebesar 1.163.140,55 juta rupiah" not in " ".join(text.split()):
        raise RuntimeError("Bukittinggi narrative does not anchor the second value to 2012")
    if "nilai tambah yang dihasilkan pada tahun 2013 adalah sebesar 1.235.499,39 juta rupiah" not in " ".join(text.split()):
        raise RuntimeError("Bukittinggi narrative does not anchor the third value to 2013")
    # Growth sequence 6.23, 6.39, 6.22 independently supports the 2011-2013 ordering.
    if re.search(r"PDRB\s+6,23\s+6,39\s+6,22", " ".join(text.split())) is None:
        raise RuntimeError("Bukittinggi 2011-2013 growth-sequence crosscheck missing")
    return {2011: values[0], 2012: values[1], 2013: values[2]}


def central_post_values() -> dict[tuple[str, int], float]:
    output: dict[tuple[str, int], float] = {}
    for row in read_csv(POST):
        output[(row["geography_id"], int(row["year"]))] = float(row["real_grdp_constant_2000_million_rupiah"])
    return output


def pct_diff(new: float, old: float) -> float:
    return (new / old - 1.0) * 100.0


def main() -> int:
    required = [BASE_PANEL, POST, BUK_TEXT, SOLOK_2012_TEXT, SOLOK_2013_TEXT]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing anomaly-resolution inputs: {missing}")

    buk = parse_bukittinggi()
    solok_2010_2011 = parse_two_year_grdp(
        page(SOLOK_2012_TEXT.read_text(encoding="utf-8", errors="replace"), 315),
        2010,
        2011,
        source_name="Solok Selatan Dalam Angka 2012 Table 9.2",
    )
    solok_2011_2012 = parse_two_year_grdp(
        page(SOLOK_2013_TEXT.read_text(encoding="utf-8", errors="replace"), 329),
        2011,
        2012,
        source_name="Solok Selatan Dalam Angka 2013 Table 9.2",
    )
    if abs(solok_2010_2011[2011] - solok_2011_2012[2011]) > 0.005:
        raise RuntimeError(
            "Solok Selatan local-source overlap for 2011 does not reconcile: "
            f"{solok_2010_2011[2011]} vs {solok_2011_2012[2011]}"
        )

    central = central_post_values()
    decisions = [
        {
            "geography_id": "idn.13.1375",
            "geography_name": "Kota Bukittinggi",
            "year": 2011,
            "central_value": central[("idn.13.1375", 2011)],
            "local_value": buk[2011],
            "decision": "override_with_local_official_revision",
            "local_source_id": "m8_bukittinggi_grdp_crosscheck",
            "local_source_page": 28,
            "evidence_note": "local BPS 2011-2013 publication; Table 2 header has stale year labels, but publication/TOC, 2012 and 2013 narrative anchors, and growth sequence establish the 2011-2013 value ordering",
        },
        {
            "geography_id": "idn.13.1375",
            "geography_name": "Kota Bukittinggi",
            "year": 2012,
            "central_value": central[("idn.13.1375", 2012)],
            "local_value": buk[2012],
            "decision": "confirm_central_value_unchanged",
            "local_source_id": "m8_bukittinggi_grdp_crosscheck",
            "local_source_page": 28,
            "evidence_note": "central level exactly matches local official value; prior growth mismatch was induced by the erroneous 2011 denominator",
        },
        {
            "geography_id": "idn.13.1310",
            "geography_name": "Solok Selatan",
            "year": 2010,
            "central_value": central[("idn.13.1310", 2010)],
            "local_value": solok_2010_2011[2010],
            "decision": "override_with_local_official_revision",
            "local_source_id": "m8_solok_selatan_grdp_crosscheck_2012",
            "local_source_page": 315,
            "evidence_note": "local BPS Table 9.2 constant-2000 level, 2010-2011; needed to preserve the revised local level chain rather than mix revisions",
        },
        {
            "geography_id": "idn.13.1310",
            "geography_name": "Solok Selatan",
            "year": 2011,
            "central_value": central[("idn.13.1310", 2011)],
            "local_value": solok_2010_2011[2011],
            "decision": "override_with_local_official_revision",
            "local_source_id": "m8_solok_selatan_grdp_crosscheck_2012_and_2013",
            "local_source_page": "315;329",
            "evidence_note": "two independent consecutive local BPS annual publications report the same 2011 constant-2000 level",
        },
        {
            "geography_id": "idn.13.1310",
            "geography_name": "Solok Selatan",
            "year": 2012,
            "central_value": central[("idn.13.1310", 2012)],
            "local_value": solok_2011_2012[2012],
            "decision": "override_with_local_official_revision",
            "local_source_id": "m8_solok_selatan_grdp_crosscheck",
            "local_source_page": 329,
            "evidence_note": "local BPS Table 9.2 constant-2000 level, 2011-2012",
        },
    ]
    for row in decisions:
        row["difference_million_rupiah"] = float(row["local_value"]) - float(row["central_value"])
        row["relative_difference_percent_of_central"] = pct_diff(float(row["local_value"]), float(row["central_value"]))

    # The four originally flagged level-growth anomaly keys must all be directly
    # resolved or confirmed. Solok 2010 is an additional revision-chain override.
    covered_flagged = {
        (str(row["geography_id"]), int(row["year"]))
        for row in decisions
        if (str(row["geography_id"]), int(row["year"])) in EXPECTED_ANOMALY_KEYS
    }
    if covered_flagged != EXPECTED_ANOMALY_KEYS:
        raise RuntimeError(f"not all original anomaly keys are resolved: {sorted(EXPECTED_ANOMALY_KEYS - covered_flagged)}")

    RESOLUTION_CSV.parent.mkdir(parents=True, exist_ok=True)
    resolution_fields = list(decisions[0])
    with RESOLUTION_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolution_fields)
        writer.writeheader()
        writer.writerows(decisions)

    base_rows = read_csv(BASE_PANEL)
    decision_by_key = {(row["geography_id"], int(row["year"])): row for row in decisions}
    resolved_rows: list[dict[str, Any]] = []
    for base in base_rows:
        key = (base["geography_id"], int(base["year"]))
        decision = decision_by_key.get(key)
        original = float(base["real_grdp_constant_2000_million_rupiah"])
        final_value = original
        resolution_status = "not_applicable"
        resolution_source = ""
        if decision is not None:
            resolution_status = str(decision["decision"])
            resolution_source = str(decision["local_source_id"])
            if resolution_status == "override_with_local_official_revision":
                final_value = float(decision["local_value"])
            elif resolution_status == "confirm_central_value_unchanged":
                if abs(float(decision["local_value"]) - original) > 0.005:
                    raise RuntimeError(f"central/local confirmation mismatch for {key}")
            else:
                raise RuntimeError(f"unknown resolution decision {resolution_status}")
        row = dict(base)
        row["original_central_real_grdp_million_rupiah"] = original
        row["real_grdp_constant_2000_million_rupiah"] = final_value
        row["log_real_grdp"] = math.log(final_value)
        row["source_anomaly_resolution_status"] = resolution_status
        row["source_anomaly_resolution_source"] = resolution_source
        if key in EXPECTED_ANOMALY_KEYS:
            row["source_internal_consistency_status"] = "resolved_by_independent_local_bps_crosscheck"
        elif decision is not None:
            row["source_internal_consistency_status"] = "local_revision_chain_override"
        resolved_rows.append(row)

    if len(resolved_rows) != 171 or len({(r["geography_id"], r["year"]) for r in resolved_rows}) != 171:
        raise RuntimeError("resolved panel cardinality drift")
    unresolved = [row for row in resolved_rows if row["source_internal_consistency_status"] == "postperiod_level_growth_internal_mismatch_unresolved"]
    if unresolved:
        raise RuntimeError(f"unresolved source anomalies remain after local crosscheck: {[(r['geography_id'], r['year']) for r in unresolved]}")

    panel_fields = list(resolved_rows[0])
    with RESOLVED_PANEL.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=panel_fields)
        writer.writeheader()
        writer.writerows(resolved_rows)

    manifest = {
        "schema": "ranah-observatory/milestone8-grdp-source-anomaly-resolution/v1",
        "criterion": "one focused causal or quasi-causal case study",
        "original_anomaly_key_count": len(EXPECTED_ANOMALY_KEYS),
        "original_anomaly_keys": [f"{gid}:{year}" for gid, year in sorted(EXPECTED_ANOMALY_KEYS)],
        "decision_count": len(decisions),
        "override_count": sum(row["decision"] == "override_with_local_official_revision" for row in decisions),
        "confirmation_count": sum(row["decision"] == "confirm_central_value_unchanged" for row in decisions),
        "solok_selatan_2011_local_overlap_exact": True,
        "local_sources_used": [
            "m8_bukittinggi_grdp_crosscheck",
            "m8_solok_selatan_grdp_crosscheck_2012",
            "m8_solok_selatan_grdp_crosscheck",
        ],
        "no_growth_imputed_level_corrections": True,
        "original_central_values_preserved": True,
        "postperiod_source_anomalies_resolved": True,
        "resolved_panel_observation_count": len(resolved_rows),
        "resolved_panel_model_ready_on_source_consistency": True,
        "base_panel_path": str(BASE_PANEL.relative_to(ROOT)),
        "base_panel_sha256": sha256(BASE_PANEL),
        "resolution_path": str(RESOLUTION_CSV.relative_to(ROOT)),
        "resolution_sha256": sha256(RESOLUTION_CSV),
        "resolved_panel_path": str(RESOLVED_PANEL.relative_to(ROOT)),
        "resolved_panel_sha256": sha256(RESOLVED_PANEL),
        "bukittinggi_text_sha256": sha256(BUK_TEXT),
        "solok_selatan_2012_text_sha256": sha256(SOLOK_2012_TEXT),
        "solok_selatan_2013_text_sha256": sha256(SOLOK_2013_TEXT),
        "outcome_model_fit": False,
        "causal_effect_estimated": False,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
