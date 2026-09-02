#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone64_krb_recommendations_acquisition.json"
EXCERPT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-recommendation-search-excerpt.txt"
OUT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-specific-recommendation-sections.csv"
FINAL = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"

SECTIONS = [
    (1, "flood", "BANJIR"),
    (2, "flash_flood", "BANJIR BANDANG"),
    (3, "extreme_weather", "CUACA EKSTRIM"),
    (4, "extreme_wave_and_coastal_erosion", "GELOMBANG EKSTRIM DAN ABRASI"),
    (5, "earthquake", "GEMPABUMI"),
    (6, "liquefaction", "LIKUEFAKSI"),
    (7, "forest_and_land_fire", "KEBAKARAN HUTAN DAN LAHAN"),
    (8, "drought", "KEKERINGAN"),
    (9, "volcanic_eruption", "LETUSAN GUNUNGAPI"),
    (10, "landslide", "TANAH LONGSOR"),
    (11, "tsunami", "TSUNAMI"),
    (12, "epidemic_and_disease_outbreak", "EPIDEMI DAN WABAH PENYAKIT"),
    (13, "technological_failure", "KEGAGALAN TEKNOLOGI"),
    (14, "covid_19", "COVID-19"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value: str) -> str:
    return " ".join(value.split())


def split_pages(text: str) -> list[tuple[int, str]]:
    pattern = re.compile(r"^===== PDF PAGE (\d+) =====$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    pages: list[tuple[int, str]] = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        pages.append((int(match.group(1)), text[start:end]))
    return pages


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    if acq["schema"] != "ranah-observatory/milestone64-krb-recommendations-acquisition/v1":
        raise RuntimeError("unsupported M64 acquisition manifest")
    if sha256(EXCERPT) != acq["text_extraction"]["excerpt_sha256"]:
        raise RuntimeError("M64 excerpt checksum drift")

    pages = [(page, body) for page, body in split_pages(EXCERPT.read_text(encoding="utf-8", errors="replace")) if 100 <= page <= 106]
    if [page for page, _ in pages] != list(range(100, 107)):
        raise RuntimeError(f"M64 expected recommendation pages 100-106, got {[p for p, _ in pages]}")

    joined_parts: list[str] = []
    offset_page: list[tuple[int, int]] = []
    offset = 0
    for page, body in pages:
        marker = f"\n[[PDF_PAGE_{page}]]\n"
        part = marker + body
        joined_parts.append(part)
        offset_page.append((offset, page))
        offset += len(part)
    joined = "".join(joined_parts)

    heading_matches: list[tuple[int, int, str, str]] = []
    for number, hazard_id, label in SECTIONS:
        pattern = re.compile(rf"4\.2\.{number}\.\s+{re.escape(label)}", re.IGNORECASE)
        candidates = list(pattern.finditer(joined))
        if len(candidates) != 1:
            raise RuntimeError(f"M64 section heading count drift for {number} {label}: {len(candidates)}")
        heading_matches.append((candidates[0].start(), number, hazard_id, label))
    heading_matches.sort()

    def page_for_position(position: int) -> int:
        current = pages[0][0]
        for start, page in offset_page:
            if start <= position:
                current = page
            else:
                break
        return current

    rows: list[dict[str, object]] = []
    for idx, (start, number, hazard_id, label) in enumerate(heading_matches):
        end = heading_matches[idx + 1][0] if idx + 1 < len(heading_matches) else len(joined)
        section = joined[start:end]
        start_page = page_for_position(start)
        end_page = page_for_position(max(start, end - 1))
        cleaned = re.sub(r"\[\[PDF_PAGE_(\d+)\]\]", r" [PDF page \1] ", section)
        cleaned = normalize(cleaned)
        if len(cleaned) < 120:
            raise RuntimeError(f"M64 suspiciously short section {hazard_id}: {len(cleaned)} chars")
        rows.append({
            "section_id": f"krb_4_2_{number}",
            "krb_hazard_id": hazard_id,
            "source_hazard_label": label,
            "start_pdf_page": start_page,
            "end_pdf_page": end_page,
            "claim_type": "official_risk_reduction_recommendation_section",
            "recommendation_text_source_native": cleaned,
            "prediction_claim_authorized": "false",
            "unmitigated_loss_forecast_authorized": "false",
        })

    if len(rows) != 14 or len({r["krb_hazard_id"] for r in rows}) != 14:
        raise RuntimeError("M64 section coverage drift")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    final = {
        "schema": "ranah-observatory/milestone64-krb-recommendations-final/v1",
        "milestone": 64,
        "depends_on": [63],
        "source_manifest": {"path": ACQ.relative_to(ROOT).as_posix(), "sha256": sha256(ACQ)},
        "result": {
            "specific_recommendation_section_count": 14,
            "hazard_count": 14,
            "source_page_span": [100, 106],
            "source_native_sections_materialized": True,
            "dashboard_action_summary_ready": False,
            "recommendations_treated_as_observed_outcomes": False,
            "causal_prediction_authorized": False,
            "unmitigated_loss_forecast_authorized": False,
        },
        "taxonomy_boundary": {
            "identifier_namespace": "krb_hazard_id",
            "source_labels_preserved": True,
            "cross_source_taxonomy_equivalence_authorized": False,
        },
        "output": {"path": OUT.relative_to(ROOT).as_posix(), "sha256": sha256(OUT)},
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
