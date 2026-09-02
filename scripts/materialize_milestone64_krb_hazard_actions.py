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
FLAT_ACTION_HAZARDS = {
    "flood",
    "flash_flood",
    "extreme_weather",
    "extreme_wave_and_coastal_erosion",
    "earthquake",
    "liquefaction",
    "forest_and_land_fire",
    "drought",
    "volcanic_eruption",
    "landslide",
    "tsunami",
}
NESTED_SOURCE_ONLY_HAZARDS = {
    "epidemic_and_disease_outbreak",
    "technological_failure",
    "covid_19",
}
PAGE_HEADER_RE = re.compile(
    r"DOKUMEN\s+KAJIAN\s+RISIKO\s+BENCANA\s+NASIONAL\s+[–-]\s+PROVINSI\s+SUMATERA\s+BARAT\s+2022-2026\s+HAL\s+\d+",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(value: str) -> str:
    return " ".join(value.split())


def clean_fragment(value: str) -> str:
    value = re.sub(r"\[\[PDF_PAGE_\d+\]\]", " ", value)
    value = PAGE_HEADER_RE.sub(" ", value)
    return normalize(value)


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
    all_hazards = {hazard_id for _, hazard_id, _ in SECTIONS}
    if FLAT_ACTION_HAZARDS | NESTED_SOURCE_ONLY_HAZARDS != all_hazards:
        raise RuntimeError("M64 action-detail classification does not cover all hazards")
    if FLAT_ACTION_HAZARDS & NESTED_SOURCE_ONLY_HAZARDS:
        raise RuntimeError("M64 action-detail classification overlaps")

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
        candidates = list(re.finditer(rf"4\.2\.{number}\.\s+{re.escape(label)}", joined, re.IGNORECASE))
        if len(candidates) != 1:
            raise RuntimeError(f"M64 section heading count drift for {hazard_id}: {len(candidates)}")
        match = candidates[0]
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
    coverage: dict[str, dict[str, object]] = {}

    for idx, (_section_start, heading_end, number, hazard_id, label) in enumerate(headings):
        section_end = headings[idx + 1][0] if idx + 1 < len(headings) else chapter5.start()
        body = joined[heading_end:section_end]
        number_matches = list(re.finditer(r"(?m)^\s*(\d+)\.\s+", body))

        if hazard_id in FLAT_ACTION_HAZARDS:
            if not number_matches:
                raise RuntimeError(f"M64 no top-level action list found for {hazard_id}")
            orders = [int(m.group(1)) for m in number_matches]
            if orders != list(range(1, len(orders) + 1)):
                raise RuntimeError(f"M64 non-sequential flat action numbering for {hazard_id}: {orders}")
            intro_end = number_matches[0].start()
            detail_status = "flat_actions_materialized"
            for action_idx, match in enumerate(number_matches):
                start = heading_end + match.start()
                end = heading_end + (number_matches[action_idx + 1].start() if action_idx + 1 < len(number_matches) else len(body))
                cleaned = clean_fragment(joined[start:end])
                order = int(match.group(1))
                if len(cleaned) < 12:
                    raise RuntimeError(f"M64 suspiciously short action {hazard_id} #{order}")
                if "DOKUMEN KAJIAN RISIKO" in cleaned.upper() or "[PDF PAGE" in cleaned.upper():
                    raise RuntimeError(f"M64 page furniture leaked into action {hazard_id} #{order}")
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
            action_count = len(number_matches)
        else:
            if hazard_id not in NESTED_SOURCE_ONLY_HAZARDS:
                raise RuntimeError(f"M64 unclassified recommendation structure for {hazard_id}")
            intro_end = number_matches[0].start() if number_matches else len(body)
            detail_status = "source_section_only_nested_structure"
            action_count = 0

        intro_clean = clean_fragment(body[:intro_end])
        if len(intro_clean) < 40:
            raise RuntimeError(f"M64 recommendation context too short for {hazard_id}")
        context_rows.append({
            "krb_hazard_id": hazard_id,
            "source_hazard_label": label,
            "section_id": f"krb_4_2_{number}",
            "priority_and_scope_context_source_native": intro_clean,
            "action_detail_status": detail_status,
            "claim_type": "official_recommendation_priority_context",
            "cross_source_taxonomy_equivalence_authorized": "false",
            "prediction_claim_authorized": "false",
        })
        coverage[hazard_id] = {
            "action_detail_status": detail_status,
            "flat_action_count": action_count,
        }

    if len(context_rows) != 14 or set(coverage) != all_hazards:
        raise RuntimeError("M64 hazard recommendation coverage drift")
    if {row["krb_hazard_id"] for row in action_rows} != FLAT_ACTION_HAZARDS:
        raise RuntimeError("M64 flat action hazard footprint drift")

    ACTIONS.parent.mkdir(parents=True, exist_ok=True)
    with ACTIONS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(action_rows[0].keys()))
        writer.writeheader()
        writer.writerows(action_rows)
    with CONTEXT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(context_rows[0].keys()))
        writer.writeheader()
        writer.writerows(context_rows)

    source_native_output = final.get("output") or final.get("outputs", {}).get("source_native_sections")
    if not source_native_output:
        raise RuntimeError("M64 source-native section output metadata missing")
    final["result"]["dashboard_action_summary_ready"] = True
    final["result"]["specific_recommendation_action_count"] = len(action_rows)
    final["result"]["flat_action_hazard_count"] = len(FLAT_ACTION_HAZARDS)
    final["result"]["nested_source_only_hazard_count"] = len(NESTED_SOURCE_ONLY_HAZARDS)
    final["result"]["priority_context_row_count"] = len(context_rows)
    final["result"]["observed_implementation_claimed"] = False
    final["result"]["nested_numbering_flattened"] = False
    final["result"]["page_furniture_removed_from_action_text"] = True
    final["action_coverage_by_hazard"] = coverage
    final["outputs"] = {
        "source_native_sections": source_native_output,
        "hazard_actions": {"path": ACTIONS.relative_to(ROOT).as_posix(), "sha256": sha256(ACTIONS)},
        "priority_context": {"path": CONTEXT.relative_to(ROOT).as_posix(), "sha256": sha256(CONTEXT)},
    }
    final.pop("output", None)
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "actions": len(action_rows),
        "flat_hazards": len(FLAT_ACTION_HAZARDS),
        "nested_source_only_hazards": sorted(NESTED_SOURCE_ONLY_HAZARDS),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
