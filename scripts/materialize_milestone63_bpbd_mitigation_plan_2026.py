#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACQ = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_acquisition.json"
EXCERPT = ROOT / "data/processed/bpbd/mitigation_plan_2026/renja-bpbd-2026-pages-51-64.txt"
TARGETS = ROOT / "data/processed/bpbd/mitigation_plan_2026/bpbd-mitigation-targets-2026.csv"
GAPS = ROOT / "data/processed/bpbd/mitigation_plan_2026/bpbd-mitigation-gaps-2026.csv"
FINAL = ROOT / "data/manifests/milestone63_bpbd_mitigation_plan_2026_final.json"
SOURCE_DOCUMENT = "Rencana Kerja BPBD Provinsi Sumatera Barat Tahun 2026"
SOURCE_PAGES = "PDF physical pages 51-64"

TARGET_SPECS = [
    ("preparedness_program_percent", "Program Penanggulangan Bencana", "Persentase kesiapsiagaan menghadapi bencana", "72", "percent", "72%"),
    ("hazard_information_dissemination_percent", "Pelayanan Informasi Rawan Bencana Provinsi", "Persentase informasi rawan bencana provinsi yang disebarluaskan", "56", "percent", "56%"),
    ("legalized_risk_assessment_documents", "Penyusunan Kajian Risiko Bencana Provinsi", "Jumlah Dokumen Kajian Risiko Bencana yang Dilegalisasi", "1", "document", "1 dokumen"),
    ("hazard_kie_recipients", "Sosialisasi, Komunikasi, Informasi dan Edukasi (KIE) Rawan Bencana Provinsi (Per Jenis Bencana)", "Jumlah warga negara termasuk kelompok rentan dan aparatur di kawasan risiko tinggi bencana lintas Kabupaten/Kota yang memperoleh KIE", "425", "people", "425 orang"),
    ("trained_population_percent", "Pelayanan Pencegahan dan Kesiapsiagaan Terhadap Bencana", "Persentase masyarakat yang terlatih dalam mencegah dan menghadapi bencana", "56", "percent", "56%"),
    ("preparedness_mechanism_areas", "Penguatan Kapasitas Kawasan untuk Pencegahan dan Kesiapsiagaan Bencana", "Jumlah kawasan rawan bencana yang ditargetkan dalam penguatan kapasitas", "3", "areas", "3 kawasan"),
    ("preparedness_drill_participants", "Gladi Kesiapsiagaan Terhadap Bencana", "Jumlah warga negara dan aparatur di kawasan risiko tinggi bencana lintas Kabupaten/Kota yang terlibat gladi kesiapsiagaan", "300", "people", "300 orang"),
    ("priority_hazard_contingency_plan_documents", "Penyusunan Rencana Kontinjensi", "Jumlah dokumen rencana kontinjensi per jenis ancaman bencana prioritas", "1", "document", "1 dokumen"),
    ("risk_root_cause_actions", "Pengelolaan Risiko Bencana", "Jumlah akar masalah risiko bencana lintas Kabupaten/Kota yang tertangani", "1", "activity", "1 kegiatan"),
    ("certified_provincial_trc_personnel", "Pengembangan Kapasitas Tim Reaksi Cepat (TRC) Bencana", "Jumlah personil TRC tingkat Provinsi yang memiliki sertifikasi kompetensi untuk penanganan awal darurat bencana", "60", "people", "60 orang"),
    ("high_risk_families_equipped", "Penyediaan Peralatan Perlindungan dan Kesiapsiagaan Bencana", "Jumlah keluarga di kawasan risiko tinggi bencana lintas Kabupaten/Kota yang memperoleh peralatan perlindungan dan kesiapsiagaan", "750", "families", "750 keluarga"),
    ("skpdb_documents", "Pengendalian Operasi dan Penyediaan Sarana Prasarana Kesiapsiagaan terhadap Bencana", "Dokumen Sistem Komando Penanganan Darurat Bencana (SKPDB) dengan proses bisnis dan prosedur tetap yang dilegalkan", "1", "document", "1 dokumen"),
    ("prevention_mitigation_training_participants", "Pelatihan Pencegahan dan Mitigasi Bencana", "Jumlah warga negara termasuk kelompok rentan dan aparatur di kawasan risiko tinggi bencana lintas Kabupaten/Kota yang mengikuti pelatihan", "120", "people", "120 orang"),
]

GAP_SPECS = [
    ("planning_documents", "planning", "Dokumen perencanaan penanggulangan bencana di kabupaten/kota belum lengkap", "Belum lengkapnya dokumen perencanaan penanggulangan bencana"),
    ("dibi_access_accuracy", "data_information", "Akses dan keakuratan Data Informasi Bencana Indonesia (DIBI) masih kurang", "Masih kurangnya akses dan"),
    ("dissemination_socialization", "public_information", "Diseminasi dan sosialisasi kebencanaan belum maksimal", "Belum maksimalnya diseminasi dan sosialisasi kebencanaan"),
    ("trc_formation_training", "response_capacity", "Masih ada pemerintah daerah yang belum membentuk dan membina TRC PB", "belum membentuk"),
    ("forum_prb", "risk_reduction_governance", "Masih ada pemerintah daerah yang belum membentuk Forum PRB", "Forum PRB"),
    ("nagari_tangguh", "community_resilience", "Masih ada kabupaten/kota yang belum membentuk dan membina nagari tangguh", "membina nagari tangguh"),
    ("volunteer_development", "community_resilience", "Pembinaan relawan kebencanaan di kabupaten/kota belum maksimal", "pembinaan relawan kebencanaan"),
    ("pusdalops_operations", "operations", "Operasional PUSDALOPS PB belum memadai", "operasional pusat pengedalian oparesional"),
    ("simulation_training", "preparedness", "Simulasi dan pelatihan kebencanaan bagi aparatur dan masyarakat belum maksimal", "simulasi dan pelatihan kebencanaan"),
    ("tes_evacuation_routes", "evacuation_infrastructure", "Tempat evakuasi sementara (TES) dan jalur evakuasi di wilayah rawan bencana belum memadai", "tempat evakuasi sementara"),
    ("preparedness_ews_equipment", "early_warning", "Peralatan kesiapsiagaan dan sistem peringatan dini bencana belum memadai", "sistem peringatan dini bencana"),
    ("field_equipment_logistics", "logistics", "Peralatan lapangan dan logistik kebencanaan belum memadai", "peralatan lapangan dan"),
    ("rehab_reconstruction_support_equipment", "recovery_capacity", "Peralatan penunjang pelaksanaan rehabilitasi dan rekonstruksi belum memadai", "peralatan penunjang"),
    ("emergency_coordination", "emergency_response", "Koordinasi siaga darurat dan penanganan tanggap darurat di wilayah bencana belum maksimal", "koordinasi siaga darurat"),
    ("contingency_based_operations", "emergency_response", "Operasi siaga darurat dan penanganan darurat sesuai rencana kontingensi per jenis bencana belum maksimal", "sesuai rencana"),
    ("emergency_monitoring_evaluation", "emergency_response", "Monitoring dan evaluasi penanganan siaga darurat dan tanggap darurat belum maksimal", "monitoring dan evaluasi penanganan"),
    ("jitu_pasna", "post_disaster_assessment", "Masih ada kabupaten/kota yang belum menyusun JITU PASNA pada wilayah dengan status bencana", "JITU PASNA"),
    ("rehab_reconstruction_coordination", "recovery_capacity", "Koordinasi serta monitoring dan evaluasi rehabilitasi dan rekonstruksi belum maksimal", "rehabilitasi dan rekonstruksi"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(value: str) -> str:
    return " ".join(value.lower().split())


def main() -> int:
    acq = json.loads(ACQ.read_text(encoding="utf-8"))
    if sha256(EXCERPT) != acq["text_excerpt"]["sha256"]:
        raise RuntimeError("M63 excerpt checksum drift")
    text = norm(EXCERPT.read_text(encoding="utf-8", errors="replace"))

    target_rows = []
    for record_id, activity, indicator, value, unit, value_needle in TARGET_SPECS:
        if norm(activity) not in text or norm(value_needle) not in text:
            raise RuntimeError(f"M63 target evidence missing: {record_id}")
        target_rows.append({
            "plan_year": 2026,
            "record_id": record_id,
            "program_or_activity": activity,
            "indicator": indicator,
            "target_value": value,
            "target_unit": unit,
            "geographic_scope": "Provinsi Sumatera Barat / lintas Kabupaten/Kota as stated",
            "claim_type": "official_planning_target",
            "source_document": SOURCE_DOCUMENT,
            "source_excerpt_pages": SOURCE_PAGES,
            "actual_achievement_claimed": "false",
        })

    gap_rows = []
    for gap_id, theme, label, needle in GAP_SPECS:
        if norm(needle) not in text:
            raise RuntimeError(f"M63 gap evidence missing: {gap_id}")
        gap_rows.append({
            "plan_year": 2026,
            "gap_id": gap_id,
            "theme": theme,
            "gap_label": label,
            "geographic_scope": "Provinsi Sumatera Barat / kabupaten-kota aggregate diagnostic",
            "claim_type": "official_planning_diagnostic",
            "quantified": "false",
            "source_document": SOURCE_DOCUMENT,
            "source_excerpt_pages": SOURCE_PAGES,
            "municipality_identified": "false",
        })

    TARGETS.parent.mkdir(parents=True, exist_ok=True)
    with TARGETS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(target_rows[0].keys()))
        writer.writeheader()
        writer.writerows(target_rows)
    with GAPS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(gap_rows[0].keys()))
        writer.writeheader()
        writer.writerows(gap_rows)

    final = {
        "schema": "ranah-observatory/milestone63-bpbd-mitigation-plan-2026-final/v1",
        "milestone": 63,
        "depends_on": [62],
        "source_manifest": {"path": ACQ.relative_to(ROOT).as_posix(), "sha256": sha256(ACQ)},
        "result": {
            "planning_target_count": len(target_rows),
            "qualitative_gap_count": len(gap_rows),
            "plan_year": 2026,
            "dashboard_planning_context_ready": True,
            "actual_capacity_score_materialized": False,
            "planning_targets_treated_as_actuals": False,
            "municipality_gap_attribution_authorized": False,
            "prediction_claim_authorized": False,
            "budget_comparison_materialized": False,
        },
        "interpretation_boundary": {
            "targets_are_forward_planning_commitments": True,
            "gaps_are_official_qualitative_diagnostics": True,
            "gaps_are_not_numeric_capacity_scores": True,
            "targets_do_not_establish_achievement": True,
            "no_unmitigated_probability_inference": True,
        },
        "outputs": {
            "targets": {"path": TARGETS.relative_to(ROOT).as_posix(), "sha256": sha256(TARGETS)},
            "gaps": {"path": GAPS.relative_to(ROOT).as_posix(), "sha256": sha256(GAPS)},
        },
    }
    FINAL.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(final["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
