#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data/raw/bnpb/m37_observed_impact"
RAW_ARCHIVE = RAW_DIR / "official-workbooks.zip"
OUT_DIR = ROOT / "data/processed/bnpb/m37_observed_impact"
OUT_CSV = OUT_DIR / "sumatera-barat-observed-impact-2024-2025.csv"
OUT_MANIFEST = ROOT / "data/manifests/milestone37_bnpb_observed_impact.json"

PROVINCE_CODE = 13
PROVINCE_NAME = "SUMATERA BARAT"

HAZARDS = (
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

METRICS = {
    "deaths": {"label": "reported_deaths", "unit": "persons_reported"},
    "affected": {"label": "reported_affected_people", "unit": "persons_reported"},
    "injured": {"label": "reported_injured_or_sick_people", "unit": "persons_reported"},
    "displaced": {"label": "reported_displaced_people", "unit": "persons_reported"},
    "houses": {"label": "reported_damaged_houses", "unit": "housing_units_reported"},
}

SOURCES = {
    2024: {
        "package_id": "f61d78e5-04c6-4ce8-9acf-e425dadc1f4d",
        "dataset_title": "Kompilasi Data Kejadian dan Dampak Bencana",
        "release_role": "master_compilation_detailed_2024",
        "resources": {
            "deaths": "69605ad2-73ea-4967-b2d5-639ad9291833",
            "affected": "5b9f7853-e69b-4d3a-917c-3fa3e473ed60",
            "injured": "b1e58b39-8dc4-4b9b-abc6-50139acd2fda",
            "displaced": "d1fd9f08-26e1-453a-9be0-422538f01b5e",
            "houses": "471f71cb-27a4-4460-836f-416c0c35b4dc",
        },
    },
    2025: {
        "package_id": "58878b43-41b5-4ffb-b851-c6d8c8c4d438",
        "dataset_title": "Kompilasi Data Kejadian dan Dampak Bencana 2025",
        "release_role": "separate_2026_published_release",
        "resources": {
            "deaths": "aefe8331-5962-4610-8b0c-2de637a336cd",
            "affected": "8d8db1c8-d79b-4fb1-b735-d8b9c1e0517a",
            "injured": "50b99a45-d8ff-496e-a64f-9e689754371c",
            "displaced": "eefa5746-5c65-4156-ac74-2eff2bfac767",
            "houses": "43b83e79-c8b6-4b9a-b2f0-d1cbd9cfa636",
        },
    },
}

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def col_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        raise ValueError(f"invalid cell reference: {cell_ref}")
    value = 0
    for ch in match.group(1):
        value = value * 26 + (ord(ch) - 64)
    return value - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        xml = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(xml)
    return ["".join(t.text or "" for t in si.iter(f"{{{NS_MAIN}}}t")) for si in root.findall(f"{{{NS_MAIN}}}si")]


def _sheet_paths(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall(f"{{{NS_PKG_REL}}}Relationship")}
    out: list[tuple[str, str]] = []
    sheets = workbook.find(f"{{{NS_MAIN}}}sheets")
    assert sheets is not None
    for sheet in sheets.findall(f"{{{NS_MAIN}}}sheet"):
        name = sheet.attrib["name"]
        rid = sheet.attrib[f"{{{NS_REL}}}id"]
        target = rel_map[rid].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        out.append((name, target))
    return out


def _sheet_rows(zf: zipfile.ZipFile, path: str, shared: list[str]) -> list[list[object | None]]:
    root = ET.fromstring(zf.read(path))
    rows: list[list[object | None]] = []
    for row in root.findall(f".//{{{NS_MAIN}}}row"):
        cells: dict[int, object | None] = {}
        max_index = -1
        for cell in row.findall(f"{{{NS_MAIN}}}c"):
            idx = col_index(cell.attrib.get("r", ""))
            max_index = max(max_index, idx)
            cell_type = cell.attrib.get("t")
            value_el = cell.find(f"{{{NS_MAIN}}}v")
            value: object | None
            if cell_type == "inlineStr":
                inline = cell.find(f"{{{NS_MAIN}}}is")
                value = "" if inline is None else "".join(t.text or "" for t in inline.iter(f"{{{NS_MAIN}}}t"))
            elif value_el is None or value_el.text is None:
                value = None
            elif cell_type == "s":
                value = shared[int(value_el.text)]
            elif cell_type in {"str", "e"}:
                value = value_el.text
            else:
                raw = value_el.text
                try:
                    num = float(raw)
                    value = int(num) if num.is_integer() else num
                except ValueError:
                    value = raw
            cells[idx] = value
        rows.append([cells.get(i) for i in range(max_index + 1)] if max_index >= 0 else [])
    return rows


def read_workbook_bytes(data: bytes) -> dict[str, list[list[object | None]]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        shared = _shared_strings(zf)
        return {name: _sheet_rows(zf, target, shared) for name, target in _sheet_paths(zf)}


def raw_member_bytes(year: int, metric_id: str) -> bytes:
    member = f"{year}/{metric_id}.xlsx"
    with zipfile.ZipFile(RAW_ARCHIVE) as archive:
        return archive.read(member)


def find_data_sheet(workbook: dict[str, list[list[object | None]]]) -> tuple[str, list[list[object | None]]]:
    for name, rows in workbook.items():
        for row in rows[:8]:
            strings = {str(v).strip() for v in row if v is not None}
            if {"Kode Wilayah Provinsi", "Provinsi", "BANJIR", "TSUNAMI"}.issubset(strings):
                return name, rows
    raise AssertionError("no provincial impact data sheet found")


def extract_sumbar_bytes(data: bytes, source_label: str = "<bytes>") -> tuple[str, dict[str, object | None], dict[str, object]]:
    workbook = read_workbook_bytes(data)
    sheet_name, rows = find_data_sheet(workbook)
    header_index = next(i for i, row in enumerate(rows) if "Kode Wilayah Provinsi" in row and "Provinsi" in row)
    header = rows[header_index]
    index = {str(v).strip(): i for i, v in enumerate(header) if v is not None}
    assert all(h in index for h in HAZARDS)
    target = None
    for row in rows[header_index + 1:]:
        if len(row) <= index["Kode Wilayah Provinsi"]:
            continue
        code = row[index["Kode Wilayah Provinsi"]]
        if code in (PROVINCE_CODE, float(PROVINCE_CODE), str(PROVINCE_CODE)):
            target = row
            break
    assert target is not None, f"province code {PROVINCE_CODE} absent in {source_label}"
    assert str(target[index["Provinsi"]]).strip().upper() == PROVINCE_NAME
    values = {hazard: target[index[hazard]] if index[hazard] < len(target) else None for hazard in HAZARDS}
    for hazard, value in values.items():
        assert value is None or (isinstance(value, (int, float)) and value >= 0), (hazard, value)
    notes_rows = workbook.get("Keterangan", [])
    notes_text = "\n".join(" | ".join(str(v).strip() for v in row if v is not None and str(v).strip()) for row in notes_rows)
    method_ref = (
        "Peraturan BNPB No. 7 Tahun 2023"
        if "Peraturan BNPB No. 7 Tahun 2023" in notes_text
        else "Juklak BNPB No. 7 Tahun 2023"
        if "Juklak BNPB No. 7 Tahun 2023" in notes_text
        else None
    )
    assert method_ref is not None
    diagnostics = {
        "sheet_name": sheet_name,
        "header_count": len([v for v in header if v is not None]),
        "methodology_reference_text": method_ref,
        "source_note_province_label_swap_present": (
            "Provinsi | : | Nama Kabupaten yang Mengalami Bencana" in notes_text
            and "Kabupaten | : | Nama Provinsi yang Mengalami Bencana" in notes_text
        ),
    }
    return sheet_name, values, diagnostics


def build() -> tuple[str, str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "year", "metric_id", "metric_label", "unit", "province_code", "province_name", "hazard", "value",
        "source_cell_state", "source_package_id", "source_resource_id", "source_file_sha256",
    ]
    rows: list[dict[str, object]] = []
    source_manifest: list[dict[str, object]] = []
    assert RAW_ARCHIVE.exists(), RAW_ARCHIVE
    archive_sha256 = sha256_file(RAW_ARCHIVE)
    for year in (2024, 2025):
        source = SOURCES[year]
        for metric_id in METRICS:
            member = f"{year}/{metric_id}.xlsx"
            raw_bytes = raw_member_bytes(year, metric_id)
            _, values, diagnostics = extract_sumbar_bytes(raw_bytes, member)
            digest = sha256_bytes(raw_bytes)
            resource_id = source["resources"][metric_id]
            source_manifest.append({
                "year": year,
                "metric_id": metric_id,
                "package_id": source["package_id"],
                "resource_id": resource_id,
                "dataset_title": source["dataset_title"],
                "release_role": source["release_role"],
                "raw_archive_path": RAW_ARCHIVE.relative_to(ROOT).as_posix(),
                "raw_archive_sha256": archive_sha256,
                "raw_member": member,
                "raw_member_sha256": digest,
                **diagnostics,
            })
            meta = METRICS[metric_id]
            for hazard in HAZARDS:
                value = values[hazard]
                rows.append({
                    "year": year,
                    "metric_id": metric_id,
                    "metric_label": meta["label"],
                    "unit": meta["unit"],
                    "province_code": PROVINCE_CODE,
                    "province_name": PROVINCE_NAME,
                    "hazard": hazard,
                    "value": "" if value is None else value,
                    "source_cell_state": "source_blank" if value is None else "reported_numeric",
                    "source_package_id": source["package_id"],
                    "source_resource_id": resource_id,
                    "source_file_sha256": digest,
                })
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    csv_text = buf.getvalue()
    OUT_CSV.write_text(csv_text, encoding="utf-8", newline="")
    blank_rows = [r for r in rows if r["source_cell_state"] == "source_blank"]
    numeric_rows = [r for r in rows if r["source_cell_state"] == "reported_numeric"]
    manifest = {
        "schema": "ranah-observatory/milestone37-bnpb-observed-impact/v1",
        "milestone": 37,
        "title": "BNPB provincial observed-impact context for West Sumatra, 2024-2025",
        "geography": {"level": "province", "code": PROVINCE_CODE, "name": PROVINCE_NAME},
        "coverage": {
            "years": [2024, 2025],
            "metric_count": len(METRICS),
            "hazard_count": len(HAZARDS),
            "expected_cells": 2 * len(METRICS) * len(HAZARDS),
            "numeric_cells": len(numeric_rows),
            "source_blank_cells": len(blank_rows),
        },
        "metrics": METRICS,
        "hazards": list(HAZARDS),
        "raw_archive": {"path": RAW_ARCHIVE.relative_to(ROOT).as_posix(), "sha256": archive_sha256, "member_count": 10},
        "sources": source_manifest,
        "normalized_output": {
            "path": OUT_CSV.relative_to(ROOT).as_posix(),
            "sha256": sha256_bytes(csv_text.encode()),
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
    return manifest["normalized_output"]["sha256"], sha256_file(OUT_MANIFEST)


def main() -> int:
    csv_sha, manifest_sha = build()
    print(json.dumps({"csv_sha256": csv_sha, "manifest_sha256": manifest_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
