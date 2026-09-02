#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone64_krb_recommendations_acquisition.json"
SECTIONS_MANIFEST = ROOT / "data/manifests/milestone64_krb_recommendations_final.json"
EXCERPT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-recommendation-reading-order-pages-98-109.txt"
ACTIONS = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-mitigation-actions-2022-2026.csv"
CONTEXT = ROOT / "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-recommendation-context-2022-2026.csv"
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
    pages = []
    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        pages.append((int(match.group(1)), text[start:end]))
    return pages


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    final = json.loads(SECTIONS_MANIFEST.read_text(encoding="utf-8"))
    reading = acq["text_extraction"]["reading_order_excerpt"]
    if sha256(EXCERPT) != reading["sha256"]:
        raise RuntimeError("M64 action input checksum drift")
    if final["result"]["source_native_sections_materialized"] is not True:
        raise RuntimeError("M64 source-native sections are not qualified")
    if final["result"]["reading_order_extraction_used"] is not True:
        raise RuntimeError("M64 action materialization requires reading-order evidence")

    pages = split_pages(EXCERPT.read_text(encoding="utf-8", errors="replace"))
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

    headings: list[tuple[int, int, int, str, str]] = []
    for number, hazard_id, label in SECTIONS:
        match = re.search(rf"4\.2\.{number}\.\s+{re.escape(label)}", joined, re.IGNORECASE)
        if not match:
            raise RuntimeError(f"M64 missing section heading for {hazard_id}")
        headings.append((match.start(), match.end(), number, hazard_id, label))
    headings.sort()
    chapter5 = re.search(r"BAB\s+5\s+PENUTUP", joined, re.IGNORECASE)
    if not chapter5:
        raise RuntimeError("M64 Chapter 5 boundary missing")

    def page_for_position(position: int) -> int:
        current = pages[0][0]
        for start, page in offset_page:
            if start <= position:
                current = page
            else:
                break
        return current

    action_rows: list[dict[str, object]] = []
    context_rows: list[dict[str, object]] = []
    counts: dict[str, int] = {}

    for idx, (section_start, heading_end, number, hazard_id, label) in enumerate(headings):
        section_end = headings[idx + 1][0] if idx + 1 < len(headings) else chapter5.start()
        body = joined[heading_end:section_end]
        action_matches = list(re.finditer(r"(?m)^\s*(\d+)\.\s+", body))
        if not action_matches:
            raise RuntimeError(f"M64 no top-level action list found for {hazard_id}")
        orders = [int(m.group(1)) for m in action_matches]
        if orders != list(range(1, len(orders) + 1)):
            raise RuntimeError(f"M64 non-sequential action numbering for {hazard_id}: {orders}")

        intro = body[:action_matches[0].start()]
        intro_clean = normalize(re.sub(r"\[\[PDF_PAGE_(\d+)\]\]", r" [PDF page \1] ", intro))
        if len(intro_clean) < 40:
            raise RuntimeError(f"M64 recommendation context too short for {hazard_id}")
        context_rows.append({
            "krb_hazard_id": hazard_id,
            "source_hazard_label": label,
            "section_id": f"krb_4_2_{number}",
            "priority_and_scope_context_source_native": intro_clean,
            "claim_type": "official_recommendation_priority_context",
            "cross_source_taxonomy_equivalence_authorized": "false",
            "prediction_claim_authorized": "false",
        })

        for action_idx, match in enumerate(action_matches):
            start = heading_end + match.start()
            end = heading_end + (action_matches[action_idx + 1].start() if action_idx + 1 < len(action_matches) else len(body))
            raw = joined[start:end]
            cleaned = normalize(re.sub(r"\[\[PDF_PAGE_(\d+)\]\]", r" [PDF page \1] ", raw))
            order = int(match.group(1))
            if len(cleaned) < 12:
                raise RuntimeError(f"M64 suspiciously short action {hazard_id} #{order}")
            action_rows.append({
                "krb_hazard_id": hazard_id,
                "source_hazard_label": label,
                "section_id": f"krb_4_2_{number}",
                "action_order": order,
                "action_text_source_native": cleaned,
                "start_pdf_page": page_for_position(start),
                "end_pdf_page": page_for_position(max(start, end - 1)),
                "claim_type": "official_risk_reduction_recommendation",
                "observed_implementation_claimed": "false",
                "prediction_claim_authorized": "false",
                "unmitigated_loss_forecast_authorized": "false",
            })
        counts[hazard_id] = len(action_matches)

    if len(context_rows) != 14 or set(counts) != {hazard_id for _, hazard_id, _ in SECTIONS}:
        raise RuntimeError("M64 hazard action coverage drift")

    ACTIONS.parent.mkdir(parents=True, exist_ok=True)
    with ACTIONS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(action_rows[0].keys()))
        writer.writeheader()
        writer.writerows(action_rows)
    with CONTEXT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(context_rows[0].keys()))
        writer.writeheader()
        writer.writerows(context_rows)

    final["result"]["dashboard_action_summary_ready"] = True
    final["result"]["specific_recommendation_action_count"] = len(action_rows)
    final["result"]["priority_context_row_count"] = len(context_rows)
    final["result"]["observed_implementation_claimed"] = False
    final["action_coverage_by_hazard"] = counts
    final["outputs"] = {
        "source_native_sections": final.pop("output"),
        "hazard_actions": {"path": ACTIONS.relative_to(ROOT).as_posix(), "sha256": sha256(ACTIONS)},
        "priority_context": {"path": CONTEXT.relative_to(ROOT).as_posix(), "sha256": sha256(CONTEXT)},
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"actions": len(action_rows), "hazards": len(counts), "counts": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
