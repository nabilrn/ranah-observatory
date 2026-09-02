#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web/static/data/disaster-summary.json"
M63 = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_final.json"
PACKAGE = ROOT / "web/package.json"
PAGE_TS = ROOT / "web/src/routes/[lang]/explore/disaster/+page.ts"
PAGE_SVELTE = ROOT / "web/src/routes/[lang]/explore/disaster/+page.svelte"
PANEL = ROOT / "web/src/lib/components/MitigationPlanPanel.svelte"
PUBLIC_TYPES = ROOT / "web/src/lib/public-data.ts"
EXPECTED_SCHEMA = "ranah-observatory/public-disaster-summary/v5"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    require(PUBLIC.exists(), "M67 public artifact missing; run web build chain first")
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    require(public.get("schema") == EXPECTED_SCHEMA, f"M67 public schema drift: {public.get('schema')!r}")
    require(public["risk_mitigation_2024"]["risk"]["row_count"] == 124, "M67 dropped M66 risk layer")
    require(public["risk_mitigation_2024"]["recommendations"]["action_count"] == 49, "M67 dropped M66 recommendation layer")

    m63 = json.loads(M63.read_text(encoding="utf-8"))
    require(m63["result"]["planning_target_count"] == 13, "M67 upstream M63 target count drift")
    require(m63["result"]["qualitative_gap_count"] == 18, "M67 upstream M63 gap count drift")
    require(m63["result"]["planning_targets_treated_as_actuals"] is False, "M67 upstream target boundary drift")
    require(m63["result"]["municipality_gap_attribution_authorized"] is False, "M67 upstream municipality boundary drift")
    require(m63["result"]["prediction_claim_authorized"] is False, "M67 upstream prediction boundary drift")

    target_meta = m63["outputs"]["targets"]
    gap_meta = m63["outputs"]["gaps"]
    target_path = ROOT / target_meta["path"]
    gap_path = ROOT / gap_meta["path"]
    require(sha256(target_path) == target_meta["sha256"], "M67 target source checksum drift")
    require(sha256(gap_path) == gap_meta["sha256"], "M67 gap source checksum drift")

    plan = public.get("mitigation_plan_2026")
    require(isinstance(plan, dict), "M67 mitigation_plan_2026 payload missing")
    source = plan["source"]
    require(source["manifest_path"] == M63.relative_to(ROOT).as_posix(), "M67 manifest path drift")
    require(source["manifest_sha256"] == sha256(M63), "M67 manifest checksum drift")
    require(source["targets_path"] == target_path.relative_to(ROOT).as_posix(), "M67 target path drift")
    require(source["targets_sha256"] == sha256(target_path), "M67 target checksum drift")
    require(source["gaps_path"] == gap_path.relative_to(ROOT).as_posix(), "M67 gap path drift")
    require(source["gaps_sha256"] == sha256(gap_path), "M67 gap checksum drift")
    require(plan["plan_year"] == 2026, "M67 plan year drift")

    source_targets = {row["record_id"]: row for row in read_csv(target_path)}
    public_targets = {row["record_id"]: row for row in plan["targets"]["rows"]}
    require(len(source_targets) == len(public_targets) == plan["targets"]["count"] == 13, "M67 target footprint drift")
    require(set(source_targets) == set(public_targets), "M67 target IDs differ from M63")
    for record_id, row in public_targets.items():
        src = source_targets[record_id]
        require(row["program_or_activity"] == src["program_or_activity"], f"M67 program text drift: {record_id}")
        require(row["indicator"] == src["indicator"], f"M67 indicator text drift: {record_id}")
        require(row["target_value"] == int(src["target_value"]), f"M67 target value drift: {record_id}")
        require(row["target_unit"] == src["target_unit"], f"M67 target unit drift: {record_id}")
        require(row["geographic_scope"] == src["geographic_scope"], f"M67 target scope drift: {record_id}")
        require(row["source_excerpt_pages"] == src["source_excerpt_pages"], f"M67 target provenance drift: {record_id}")
        require(src["claim_type"] == "official_planning_target" and src["actual_achievement_claimed"] == "false", f"M67 unsafe target source row: {record_id}")

    source_gaps = {row["gap_id"]: row for row in read_csv(gap_path)}
    public_gaps = {row["gap_id"]: row for row in plan["gaps"]["rows"]}
    require(len(source_gaps) == len(public_gaps) == plan["gaps"]["count"] == 18, "M67 gap footprint drift")
    require(set(source_gaps) == set(public_gaps), "M67 gap IDs differ from M63")
    themes: Counter[str] = Counter()
    for gap_id, row in public_gaps.items():
        src = source_gaps[gap_id]
        require(row["theme"] == src["theme"], f"M67 gap theme drift: {gap_id}")
        require(row["gap_label"] == src["gap_label"], f"M67 gap text drift: {gap_id}")
        require(row["geographic_scope"] == src["geographic_scope"], f"M67 gap scope drift: {gap_id}")
        require(row["source_excerpt_pages"] == src["source_excerpt_pages"], f"M67 gap provenance drift: {gap_id}")
        require(src["claim_type"] == "official_planning_diagnostic", f"M67 unsafe gap claim type: {gap_id}")
        require(src["quantified"] == "false" and src["municipality_identified"] == "false", f"M67 unsafe gap source row: {gap_id}")
        themes[row["theme"]] += 1
    require(dict(sorted(themes.items())) == plan["gaps"]["theme_counts"], "M67 gap theme summary drift")

    boundaries = plan["boundaries"]
    require(boundaries["targets_are_forward_planning_commitments"] is True, "M67 planning-target boundary disabled")
    require(boundaries["gaps_are_official_qualitative_diagnostics"] is True, "M67 gap diagnostic boundary disabled")
    for key in (
        "targets_are_actual_achievements",
        "gaps_are_numeric_capacity_scores",
        "municipality_gap_attribution_authorized",
        "prediction_claim_authorized",
        "unmitigated_probability_inference_authorized",
    ):
        require(boundaries[key] is False, f"M67 unsafe boundary enabled: {key}")

    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    require(package["scripts"]["data"].endswith("python3 ../scripts/promote_public_disaster_mitigation_plan.py"), "M67 promoter missing from web chain")
    require(EXPECTED_SCHEMA in PAGE_TS.read_text(encoding="utf-8"), "M67 page loader does not require v5")
    require("mitigation_plan_2026: PublicMitigationPlan2026" in PUBLIC_TYPES.read_text(encoding="utf-8"), "M67 TypeScript contract missing")
    page_text = PAGE_SVELTE.read_text(encoding="utf-8")
    require("MitigationPlanPanel" in page_text and "summary.mitigation_plan_2026" in page_text, "M67 disaster page does not mount mitigation plan panel")
    panel_text = PANEL.read_text(encoding="utf-8")
    for phrase in (
        "target 2026 — bukan capaian aktual",
        "tidak dijadikan skor kapasitas",
        "tidak menunjuk wilayah tertentu",
        "Jangan baca bagian ini sebagai skor kinerja daerah atau ramalan bencana",
    ):
        require(phrase in panel_text, f"M67 public boundary copy missing: {phrase}")

    print(json.dumps({"status": "ok", "schema": EXPECTED_SCHEMA, "targets": 13, "gaps": 18, "themes": len(themes)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
