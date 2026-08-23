#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / "publication" / "v0.1"
SOURCE = PUB / "submission" / "manuscript-with-assets.md"
OUT = PUB / "preprint"
BIB = PUB / "references.bib"
MAP = PUB / "reference-map.csv"
AUTHORSHIP = PUB / "AUTHORSHIP.md"
METADATA = PUB / "submission" / "metadata.json"

AUTHOR = "Nabil Rizki Navisa"
AFFILIATION = "Independent Researcher"
LICENSE = "CC BY 4.0"
RELEASE_DATE = "2026-08-23"

REFERENCES = {
    "CHIRPS3_DATA_2025": "Climate Hazards Center. (2025). Climate Hazards Center Infrared Precipitation with Stations version 3 (CHIRPS3) Data Repository. https://doi.org/10.15780/G2JQ0P",
    "FUNK_ET_AL_2026_CHIRPS3": "Funk, C., Peterson, P., Harrison, L., et al. (2026). The Climate Hazards Center Infrared Precipitation with Stations, Version 3. Scientific Data, 13, 718. https://doi.org/10.1038/s41597-026-07096-4",
    "BPS_WEBAPI": "Badan Pusat Statistik. WebAPI BPS Developer Documentation. https://webapi.bps.go.id/developer (accessed 2026-08-23).",
    "BIG_BOUNDARIES": "Badan Informasi Geospasial. Area Batas Wilayah Administrasi Kabupaten/Kota Map Service. https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_KABKOTA_AR/MapServer/0 (accessed 2026-08-23).",
    "DJPK_SIKD_APBD": "Direktorat Jenderal Perimbangan Keuangan. Portal Data SIKD: APBD. https://djpk.kemenkeu.go.id/portal/data/apbd (accessed 2026-08-23).",
    "BKPM_REALIZATION_REPORTS": "Kementerian Investasi dan Hilirisasi/BKPM. Laporan Realisasi Investasi. https://www.bkpm.go.id/id/info/realisasi-investasi (accessed 2026-08-23).",
    "BKPM_SATUDATA": "Kementerian Investasi dan Hilirisasi/BKPM. Satu Data Kementerian Investasi dan Hilirisasi/BKPM. https://data.bkpm.go.id/ (accessed 2026-08-23).",
    "BNPB_INARISK_METHOD": "Badan Nasional Penanggulangan Bencana. InaRISK: Metodologi. https://inarisk.bnpb.go.id/metodologi (accessed 2026-08-23; framework documentation only).",
    "BNPB_DIBI_2012": "Badan Nasional Penanggulangan Bencana. (2012). Peraturan Kepala BNPB Nomor 07 Tahun 2012 tentang Pedoman Pengelolaan Data dan Informasi Bencana Indonesia.",
    "USGS_PADANG_2009": "U.S. Geological Survey. (2009). M 7.6 - 30 km WSW of Pariaman, Indonesia (event usp000h237). https://earthquake.usgs.gov/earthquakes/eventpage/usp000h237",
    "MANN1945": "Mann, H. B. (1945). Nonparametric Tests Against Trend. Econometrica, 13(3), 245–259. https://doi.org/10.2307/1907187",
    "THEIL1950": "Theil, H. (1950). A Rank-Invariant Method of Linear and Polynomial Regression Analysis. Proceedings of the Royal Netherlands Academy of Sciences, 53, 386–392, 521–525, 1397–1412.",
    "SEN1968": "Sen, P. K. (1968). Estimates of the Regression Coefficient Based on Kendall's Tau. Journal of the American Statistical Association, 63(324), 1379–1389. https://doi.org/10.1080/01621459.1968.10480934",
    "HAMED_RAO1998": "Hamed, K. H., & Rao, A. R. (1998). A Modified Mann-Kendall Trend Test for Autocorrelated Data. Journal of Hydrology, 204(1–4), 182–196. https://doi.org/10.1016/S0022-1694(97)00125-X",
    "HOLM1979": "Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics, 6(2), 65–70. https://www.jstor.org/stable/4615733",
    "PETTITT1979": "Pettitt, A. N. (1979). A Non-Parametric Approach to the Change-Point Problem. Journal of the Royal Statistical Society: Series C (Applied Statistics), 28(2), 126–135. https://doi.org/10.2307/2346729",
}

SECTION_CITATIONS = {
    "### 2.1 Primary modern kabupaten/kota regime": ["BPS_WEBAPI", "BIG_BOUNDARIES"],
    "### 2.2 Historical climate regime": ["CHIRPS3_DATA_2025", "FUNK_ET_AL_2026_CHIRPS3"],
    "### 2.4 Public finance, disaster components, investment, and broader outcomes": [
        "DJPK_SIKD_APBD", "BKPM_REALIZATION_REPORTS", "BKPM_SATUDATA", "BNPB_INARISK_METHOD", "BNPB_DIBI_2012"
    ],
    "### 3.3 Association and identification": ["USGS_PADANG_2009"],
    "### 3.5 Locked negative-result designs": ["MANN1945", "THEIL1950", "SEN1968", "HAMED_RAO1998", "HOLM1979", "PETTITT1979"],
}

BLOCKED_IDS = {
    "B01_MONETARY_WASTED_POTENTIAL",
    "B02_THEORETICAL_MAXIMUM",
    "B03_CAUSAL_RESIDUAL",
    "B04_GUARANTEED_POLICY_GAIN",
    "B05_CAUSAL_RAINFALL_UNEMPLOYMENT",
    "B06_EVENT_COUNTS_AS_IMPACT",
    "B07_COMPOSITE_DISASTER_RISK",
    "B08_SENSITIVITY_AS_POLICY_EFFECT",
    "B09_POLICY_RANKING",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_map() -> list[dict[str, str]]:
    with MAP.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def bib_ids() -> set[str]:
    text = BIB.read_text(encoding="utf-8")
    return set(re.findall(r"@[A-Za-z]+\{([^,\s]+),", text))


def insert_after_heading(text: str, heading: str, block: str) -> str:
    marker = heading + "\n"
    assert marker in text, heading
    return text.replace(marker, marker + "\n" + block.rstrip() + "\n", 1)


def build_preprint(source: str) -> str:
    lines = source.splitlines()
    assert lines and lines[0].startswith("# Ranah Observatory:")
    author_block = [
        "",
        f"**{AUTHOR}**  ",
        f"{AFFILIATION}  ",
        f"Technical report / preprint v0.1 · {RELEASE_DATE} · {LICENSE}",
        "",
        "> **Citation-layer boundary:** bracketed `REF:` citations below document source families and methods already used by the frozen research package. They do not alter claim IDs, analytical results, or inference status.",
    ]
    text = "\n".join([lines[0], *author_block, *lines[1:]]) + "\n"

    for heading, ids in SECTION_CITATIONS.items():
        refs = " ".join(f"`[REF:{ref_id}]`" for ref_id in ids)
        text = insert_after_heading(text, heading, f"> **Source/method documentation:** {refs}")

    text = text.rstrip() + "\n\n## References and source documentation\n\n"
    text += "These references document source families and statistical methods already present in the frozen evidence base. They are editorial documentation and do not upgrade any claim state.\n\n"
    for ref_id, formatted in REFERENCES.items():
        text += f"- **[{ref_id}]** {formatted}\n"
    return text


def main() -> None:
    rows = read_map()
    map_ids = [row["reference_id"] for row in rows]
    assert len(rows) == 16
    assert len(set(map_ids)) == 16
    assert set(map_ids) == set(REFERENCES)
    assert bib_ids() == set(REFERENCES)

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    assert metadata["authors"] == [{"affiliation": AFFILIATION, "name": AUTHOR, "role": "author"}]
    assert metadata["publication_license"] == "CC-BY-4.0"
    assert metadata["claim_upgrade_performed"] is False

    source = SOURCE.read_text(encoding="utf-8")
    assert all(blocked in source for blocked in BLOCKED_IDS)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    preprint = build_preprint(source)
    assert all(blocked in preprint for blocked in BLOCKED_IDS)
    assert all(f"REF:{ref_id}" in preprint or f"[{ref_id}]" in preprint for ref_id in REFERENCES)
    (OUT / "preprint.md").write_text(preprint, encoding="utf-8")

    refs_md = "# References and source documentation\n\n"
    refs_md += "Editorial bibliography for Ranah Observatory v0.1. Reference acquisition does not modify the frozen analytical evidence base.\n\n"
    refs_md += "\n".join(f"- **[{ref_id}]** {formatted}" for ref_id, formatted in REFERENCES.items()) + "\n"
    (OUT / "references.md").write_text(refs_md, encoding="utf-8")

    shutil.copyfile(MAP, OUT / "reference-map.csv")

    readme = f"""# Ranah Observatory v0.1 citation-ready preprint layer

Author: **{AUTHOR}**  
Affiliation: **{AFFILIATION}**  
Release: **v0.1**  
License: **{LICENSE}**

This directory is generated from the certified M31 manuscript-with-assets and the M33 reference registry. `preprint.md` adds authorship, bounded source/method citation callouts, and a bibliography without editing the frozen scientific manuscript or claim ledger.

The authoritative scientific claim source remains `publication/v0.1/manuscript.md`. The authoritative submission metadata remains `publication/v0.1/submission/metadata.json`.

M33 acquires editorial source/method documentation only. It does not acquire new analytical observations, refit models, impute data, qualify forecasts, upgrade causal claims, monetize gaps, construct composite risk, or rank policies.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    source_paths = [
        "CITATION.cff",
        "publication/v0.1/AUTHORSHIP.md",
        "publication/v0.1/claim-ledger.csv",
        "publication/v0.1/references.bib",
        "publication/v0.1/reference-map.csv",
        "publication/v0.1/submission/manuscript-with-assets.md",
        "publication/v0.1/submission/metadata.json",
    ]
    output_paths = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != "preprint-manifest.json")
    manifest = {
        "schema": "ranah-observatory/publication-v0.1-preprint-manifest/v1",
        "release": "v0.1",
        "builder": "publication/v0.1/tools/build_preprint.py",
        "author": AUTHOR,
        "affiliation": AFFILIATION,
        "publication_license": "CC-BY-4.0",
        "reference_count": 16,
        "editorial_reference_acquisition": True,
        "new_analytical_source_acquisition": False,
        "new_statistical_or_ml_model_fit": False,
        "claim_upgrade_performed": False,
        "blocked_claims_retained": sorted(BLOCKED_IDS),
        "source_sha256": {rel: sha256(ROOT / rel) for rel in source_paths},
        "output_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in output_paths},
    }
    (OUT / "preprint-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print({"preprint_outputs": 5, "references": 16, "author": AUTHOR, "claim_upgrade": False})


if __name__ == "__main__":
    main()
