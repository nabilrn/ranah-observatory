#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog/public-datasets.csv"
ENTRIES = [
    {
        "id": "bnpb-krb-sumbar-hazard-mitigation-actions-2022-2026",
        "category": "Disaster",
        "title_id": "Rekomendasi mitigasi per jenis ancaman Sumatera Barat 2022–2026",
        "title_en": "West Sumatra hazard-specific mitigation recommendations 2022–2026",
        "description_id": "Enam puluh aksi rekomendasi resmi dari Kajian Risiko Bencana BNPB untuk 11 jenis ancaman yang memiliki daftar tindakan linear. Tiga section dengan struktur rekomendasi bertingkat tidak dipaksa menjadi daftar datar. Data ini adalah rekomendasi pengurangan risiko, bukan bukti implementasi dan bukan prediksi kejadian atau kerugian.",
        "description_en": "Sixty official recommendation actions from BNPB's disaster risk assessment for 11 hazards with linear action lists. Three recommendation sections with nested structure are not forced into a flat list. These are risk-reduction recommendations, not evidence of implementation and not event or loss forecasts.",
        "source": "BNPB / InaRISK KRB Sumatera Barat 2022–2026",
        "period": "2022–2026 risk assessment",
        "geography": "Provinsi Sumatera Barat / jenis ancaman",
        "formats": "CSV",
        "status": "materialized",
        "source_path": "data/processed/bnpb/krb_sumbar_2022_2026/krb-hazard-mitigation-actions-2022-2026.csv",
    },
    {
        "id": "bnpb-krb-sumbar-recommendation-sections-2022-2026",
        "category": "Disaster",
        "title_id": "Bagian rekomendasi KRB Sumatera Barat 2022–2026",
        "title_en": "West Sumatra KRB recommendation sections 2022–2026",
        "description_id": "Empat belas bagian rekomendasi spesifik source-native dari Kajian Risiko Bencana BNPB, dipertahankan sebagai proof layer. Teks dibangun dari ekstraksi reading-order non-OCR; section epidemi, kegagalan teknologi, dan COVID-19 tetap bertingkat dan tidak di-flatten.",
        "description_en": "Fourteen source-native specific-recommendation sections from BNPB's disaster risk assessment retained as a proof layer. Text is built from non-OCR reading-order extraction; epidemic, technological-failure, and COVID-19 sections remain nested and are not flattened.",
        "source": "BNPB / InaRISK KRB Sumatera Barat 2022–2026",
        "period": "2022–2026 risk assessment",
        "geography": "Provinsi Sumatera Barat / jenis ancaman",
        "formats": "CSV",
        "status": "materialized",
        "source_path": "data/processed/bnpb/krb_sumbar_2022_2026/krb-specific-recommendation-sections.csv",
    },
]


def main() -> int:
    with CATALOG.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise RuntimeError("catalog header missing")
        rows = list(reader)
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("catalog already contains duplicate IDs")
    wanted = {entry["id"] for entry in ENTRIES}
    present = wanted & set(ids)
    if present:
        raise RuntimeError(f"M64 catalog IDs already exist: {sorted(present)}")
    for entry in ENTRIES:
        if set(entry) != set(fieldnames):
            raise RuntimeError("M64 catalog entry schema drift")
        rows.append(entry)
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print("registered 2 M64 catalog entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
