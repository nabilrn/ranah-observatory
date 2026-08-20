#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old in text:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"{path}: expected one {label} target, found {count}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        return
    if new in text:
        return
    raise RuntimeError(f"{path}: neither legacy nor recovered {label} state found")


def patch_transport() -> None:
    path = ROOT / "data/manifests/milestone25_transport_amendment.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("amendment_revision") != 3:
        raise RuntimeError("M25 transport amendment revision must already be 3")
    roles = list(payload.get("html_role", []))
    roles = ["annual_final_realization_semantics" if item == "december_realization_semantics" else item for item in roles]
    payload["html_role"] = roles
    if "annual_final_realization_semantics" not in roles:
        raise RuntimeError("M25 HTML annual-final semantic role missing")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_finalizer() -> None:
    path = ROOT / "scripts/finalize_milestone25_djpk_public_finance.py"
    replace_once(
        path,
        "import csv\nimport hashlib\n",
        "import csv\nimport hashlib\nfrom collections import Counter\n",
        "Counter import",
    )
    replace_once(
        path,
        'HELD = {"central_transfer_revenue"}\nREGIME_ID = "sumbar_current_kabkota_djpk_realization_2018_2025_v2"\n',
        'HELD = {"central_transfer_revenue"}\nANNUAL_FINAL_CLASSES = {\n    "calendar_year_end_december",\n    "final_accountability_audited",\n    "final_accountability_perda",\n}\nREGIME_ID = "sumbar_current_kabkota_djpk_realization_2018_2025_v2"\n',
        "annual-final constants",
    )
    replace_once(
        path,
        '    require(transport.get("html_export_selector_match_required") is True, "transport does not require same-selector export")\n    require(transport.get("html_table_value_crosscheck_required_when_parseable") is True, "transport does not require HTML crosscheck")\n',
        '    require(transport.get("html_export_selector_match_required") is True, "transport does not require same-selector export")\n    require(transport.get("amendment_revision") == 3, "transport recovery revision drift")\n    require(transport.get("annual_final_realization_semantics_required") is True, "annual-final semantics gate missing")\n    require(set(transport.get("accepted_annual_final_realization_semantics", [])) == ANNUAL_FINAL_CLASSES, "accepted annual-final semantics drift")\n    require(transport.get("intermediate_month_or_unaudited_semantics_rejected") is True, "non-final realization semantics are not rejected")\n    require(transport.get("html_table_value_crosscheck_required_when_parseable") is False, "rounded HTML display crosscheck became blocking")\n    require(transport.get("html_table_value_crosscheck_is_diagnostic") is True, "rounded HTML display diagnostic flag missing")\n',
        "transport recovery gates",
    )
    old_stage0 = '''    stage0_pages = sorted(RAW_STAGE0.glob("kota-padang-apbd-*-desember.html"))\n    require(len(stage0_pages) == 8, f"expected 8 frozen Stage 0 Padang pages, found {len(stage0_pages)}")\n    require({int(path.stem.split("-")[-2]) for path in stage0_pages} == YEARS, "Stage 0 frozen page years drift")\n    raw_by_year = {int(item["year"]): item for item in taxonomy.get("raw_responses", [])}\n    require(set(raw_by_year) == YEARS, "Stage 0 raw-response manifest years drift")\n    for path in stage0_pages:\n        year = int(path.stem.split("-")[-2])\n        require(sha256(path) == str(raw_by_year[year]["sha256"]), f"Stage 0 raw page checksum drift {year}")\n'''
    new_stage0 = '''    raw_by_year = {int(item["year"]): item for item in taxonomy.get("raw_responses", [])}\n    require(set(raw_by_year) == YEARS, "Stage 0 raw-response manifest years drift")\n    require(taxonomy.get("spreadsheetml_account_table_required") is True, "Stage 0 exact SpreadsheetML taxonomy evidence not required")\n    require(taxonomy.get("taxonomy_primary_representation") == "djpk_csv_apbd_spreadsheetml_exact_rupiah", "Stage 0 taxonomy representation drift")\n    stage0_html_pages = sorted(RAW_STAGE0.glob("kota-padang-apbd-*-desember.html"))\n    stage0_xml_pages = sorted(RAW_STAGE0.glob("kota-padang-apbd-*-desember.xml"))\n    require(len(stage0_html_pages) == 8 and len(stage0_xml_pages) == 8, "Stage 0 frozen dual-representation footprint drift")\n    for year, item in raw_by_year.items():\n        html_path = ROOT / str(item["html_path"])\n        export_path = ROOT / str(item["export_path"])\n        require(html_path.exists() and export_path.exists(), f"Stage 0 frozen source missing {year}")\n        require(sha256(html_path) == str(item["html_sha256"]), f"Stage 0 HTML checksum drift {year}")\n        require(sha256(export_path) == str(item["export_sha256"]), f"Stage 0 SpreadsheetML checksum drift {year}")\n'''
    replace_once(path, old_stage0, new_stage0, "Stage 0 dual-representation verification")
    replace_once(
        path,
        '    require(stage1.get("same_selector_export_link_required") is True, "Stage 1 same-selector export link not required")\n    require(stage1.get("spreadsheetml_is_primary_numeric_evidence") is True, "Stage 1 primary numeric representation drift")\n',
        '    require(stage1.get("same_selector_export_link_required") is True, "Stage 1 same-selector export link not required")\n    require(stage1.get("spreadsheetml_is_primary_numeric_evidence") is True, "Stage 1 primary numeric representation drift")\n    require(stage1.get("annual_final_realization_semantics_required") is True, "Stage 1 annual-final semantics gate missing")\n    manifest_semantics = stage1.get("annual_final_realization_semantics_counts", {})\n    require(set(manifest_semantics) == ANNUAL_FINAL_CLASSES, "Stage 1 annual-final semantic class drift")\n    require(sum(int(value) for value in manifest_semantics.values()) == 152, "Stage 1 annual-final semantic count drift")\n    require(stage1.get("html_table_value_crosscheck_is_diagnostic") is True, "Stage 1 HTML display crosscheck became blocking")\n',
        "Stage 1 annual-final manifest gates",
    )
    replace_once(
        path,
        '    require({row["same_selector_export_link_match"] for row in coverage} == {"True"}, "Stage 1 export-selector mismatch")\n    require({row["export_valid_spreadsheetml"] for row in coverage} == {"True"}, "Stage 1 invalid SpreadsheetML export")\n    require({row["html_value_crosscheck_failure_count"] for row in coverage} == {"0"}, "Stage 1 HTML/export crosscheck failure")\n',
        '    require({row["same_selector_export_link_match"] for row in coverage} == {"True"}, "Stage 1 export-selector mismatch")\n    require({row["export_valid_spreadsheetml"] for row in coverage} == {"True"}, "Stage 1 invalid SpreadsheetML export")\n    require({row["annual_final_realization_semantics_match"] for row in coverage} == {"True"}, "Stage 1 annual-final semantics mismatch")\n    semantic_counts = Counter(row["annual_final_realization_semantics_class"] for row in coverage)\n    require(set(semantic_counts) == ANNUAL_FINAL_CLASSES, "Stage 1 coverage annual-final class drift")\n    require(dict(semantic_counts) == {key: int(value) for key, value in manifest_semantics.items()}, "Stage 1 coverage/manifest semantic-count drift")\n    diagnostic_failure_pages = sum(int(row["html_value_crosscheck_failure_count"]) > 0 for row in coverage)\n    require(diagnostic_failure_pages == int(stage1.get("html_value_crosscheck_failure_page_count", -1)), "Stage 1 HTML diagnostic accounting drift")\n',
        "Stage 1 coverage semantic gates",
    )
    replace_once(
        path,
        '    require(panel.get("primary_numeric_evidence") == "djpk_csv_apbd_spreadsheetml_exact_rupiah", "panel numeric source drift")\n',
        '    require(panel.get("primary_numeric_evidence") == "djpk_csv_apbd_spreadsheetml_exact_rupiah", "panel numeric source drift")\n    require(panel.get("annual_final_realization_semantics_required") is True, "panel annual-final semantics gate missing")\n    require(panel.get("html_rounded_value_crosscheck_is_diagnostic") is True, "panel HTML rounded display crosscheck became blocking")\n',
        "panel semantic gates",
    )
    replace_once(
        path,
        '    require({row["reference_period"] for row in observations} == {"realisasi_s.d._desember"}, "canonical fiscal reference-period drift")\n',
        '    require({row["reference_period"] for row in observations} == {"annual_final_realization"}, "canonical fiscal reference-period drift")\n',
        "observation reference period",
    )
    replace_once(
        path,
        '    require({row["same_selector_export_link_verified"] for row in provenance} == {"True"}, "provenance export-link verification drift")\n    require({row["comparability_regime"] for row in provenance} == {REGIME_ID}, "provenance regime drift")\n',
        '    require({row["same_selector_export_link_verified"] for row in provenance} == {"True"}, "provenance export-link verification drift")\n    require({row["reference_period"] for row in provenance} == {"annual_final_realization"}, "provenance reference-period drift")\n    provenance_semantics = Counter(row["source_realization_semantics_class"] for row in provenance)\n    require(provenance_semantics == semantic_counts, "provenance annual-final semantic-count drift")\n    require({row["comparability_regime"] for row in provenance} == {REGIME_ID}, "provenance regime drift")\n',
        "provenance semantic gates",
    )
    replace_once(
        path,
        '        "criterion": "four preregistered exact-label fiscal account families with complete 19-kabupaten/kota x 2018-2025 December-realization evidence using official same-selector DJPK HTML semantics and SpreadsheetML exact values",\n',
        '        "criterion": "four preregistered exact-label fiscal account families with complete 19-kabupaten/kota x 2018-2025 annual-final realization evidence using official same-selector DJPK HTML semantics and SpreadsheetML exact values",\n',
        "completion criterion",
    )
    replace_once(
        path,
        '        "html_semantic_evidence": "identity_year_december_same_selector_export_link",\n',
        '        "html_semantic_evidence": "identity_year_annual_final_status_same_selector_export_link",\n        "annual_final_realization_semantics_counts": dict(sorted(semantic_counts.items())),\n        "annual_final_realization_semantics_required": True,\n        "html_rounded_value_crosscheck_is_diagnostic": True,\n',
        "completion semantic metadata",
    )


def patch_docs_builder() -> None:
    path = ROOT / "scripts/build_milestone25_documentation.py"
    replace_once(
        path,
        '        "All canonical values are December fiscal realizations normalized to **IDR billion** from exact rupiah values in the official same-selector `csv_apbd` SpreadsheetML export. No imputation, historical-boundary reconstruction, explicit taxonomy bridge, derived fiscal ratio, or statistical model is part of M25.",\n',
        '        "All canonical values are annual-final fiscal realizations normalized to **IDR billion** from exact rupiah values in the official same-selector `csv_apbd` SpreadsheetML export. The locked selector remains `periode=12`; source-reported final semantics across the frozen panel are **139 Desember**, **11 Perda**, and **2 Audited** records. No imputation, historical-boundary reconstruction, explicit taxonomy bridge, derived fiscal ratio, or statistical model is part of M25.",\n',
        "docs annual-final summary",
    )
    replace_once(
        path,
        '        "The DJPK APBD HTML page carries jurisdiction identity, fiscal year, December-realization semantics, and the link to the corresponding export. During qualification, the body-table markup proved structurally inconsistent across the full historical footprint. M25 therefore records a representation-only transport amendment: the scientific scope and account contracts stay unchanged, while exact numeric evidence is taken from the official SpreadsheetML export exposed by that same HTML page and selector set.",\n',
        '        "The DJPK APBD HTML page carries jurisdiction identity, fiscal year, annual-final realization semantics, and the link to the corresponding export. Historical pages requested with the locked `periode=12` selector report final status as `s.d Desember`, `s.d Audited <year>`, or `s.d Perda <year>`; intermediate-month and unaudited states remain rejected. During qualification, the body-table markup proved structurally inconsistent across the full historical footprint. M25 therefore records a representation-only transport amendment: the scientific scope and account contracts stay unchanged, while exact numeric evidence is taken from the official SpreadsheetML export exposed by that same HTML page and selector set.",\n',
        "docs representation explanation",
    )
    replace_once(
        path,
        '        "For pages where the HTML postur table is parseable, each promoted account is cross-checked against the exact export value within the rounding tolerance implied by the two-decimal HTML display. Where the body table is not parseable, the page can qualify only when jurisdiction/year/December semantics and the exact same-selector export link remain verifiable.",\n',
        '        "For pages where the HTML postur table is parseable, each promoted account receives a diagnostic rounded-display cross-check against the exact export value. That display comparison is non-blocking and cannot override exact SpreadsheetML evidence. A page qualifies only when jurisdiction, fiscal year, accepted annual-final semantics, the exact same-selector export link, valid SpreadsheetML, and all locked exact labels remain verifiable.",\n',
        "docs diagnostic crosscheck",
    )
    replace_once(
        path,
        '        "Each jurisdiction-year provenance record binds both the official HTML snapshot and its same-selector SpreadsheetML export by SHA-256. Permanent CI can work entirely offline: it verifies frozen source hashes, revalidates HTML identity/year/December/export-link semantics, re-parses exact SpreadsheetML account values, rechecks rounded HTML values when available, rebuilds the canonical panel, reruns completion/audit tests, and compares deterministic outputs byte-for-byte.",\n',
        '        "Each jurisdiction-year provenance record binds both the official HTML snapshot and its same-selector SpreadsheetML export by SHA-256. Permanent CI works from frozen evidence: it verifies both source hashes, revalidates HTML identity/year/annual-final/export-link semantics, re-parses exact SpreadsheetML account values, records rounded HTML checks only as diagnostics, rebuilds the canonical panel, reruns completion/audit tests, and compares deterministic outputs byte-for-byte.",\n',
        "docs reproducibility",
    )


def patch_audit() -> None:
    path = ROOT / "scripts/audit_milestone25_djpk_public_finance.py"
    replace_once(path, "import csv\nimport hashlib\n", "import csv\nimport hashlib\nfrom collections import Counter\n", "audit Counter import")
    replace_once(
        path,
        '        assert transport["representation_amendment_after_transport_failure"] is True\n        assert transport["scientific_design_changed"] is False\n',
        '        assert transport["representation_amendment_after_transport_failure"] is True\n        assert transport["amendment_revision"] == 3\n        assert transport["annual_final_realization_semantics_required"] is True\n        assert set(transport["accepted_annual_final_realization_semantics"]) == {"calendar_year_end_december", "final_accountability_audited", "final_accountability_perda"}\n        assert transport["intermediate_month_or_unaudited_semantics_rejected"] is True\n        assert transport["html_table_value_crosscheck_required_when_parseable"] is False\n        assert transport["html_table_value_crosscheck_is_diagnostic"] is True\n        assert transport["scientific_design_changed"] is False\n',
        "audit transport rev3",
    )
    replace_once(
        path,
        '        assert stage1["spreadsheetml_is_primary_numeric_evidence"] is True\n        assert stage1["html_table_parseable_page_count"] + stage1["html_table_unparseable_page_count"] == 152\n',
        '        assert stage1["spreadsheetml_is_primary_numeric_evidence"] is True\n        assert stage1["annual_final_realization_semantics_required"] is True\n        assert sum(stage1["annual_final_realization_semantics_counts"].values()) == 152\n        assert set(stage1["annual_final_realization_semantics_counts"]) == {"calendar_year_end_december", "final_accountability_audited", "final_accountability_perda"}\n        assert stage1["html_table_value_crosscheck_is_diagnostic"] is True\n        assert stage1["html_table_parseable_page_count"] + stage1["html_table_unparseable_page_count"] == 152\n',
        "audit Stage1 semantics",
    )
    replace_once(
        path,
        '        assert {row["same_selector_export_link_match"] for row in coverage} == {"True"}\n        assert {row["export_valid_spreadsheetml"] for row in coverage} == {"True"}\n        assert {row["html_value_crosscheck_failure_count"] for row in coverage} == {"0"}\n',
        '        assert {row["same_selector_export_link_match"] for row in coverage} == {"True"}\n        assert {row["export_valid_spreadsheetml"] for row in coverage} == {"True"}\n        assert {row["annual_final_realization_semantics_match"] for row in coverage} == {"True"}\n        semantic_counts = Counter(row["annual_final_realization_semantics_class"] for row in coverage)\n        assert dict(semantic_counts) == {key: int(value) for key, value in stage1["annual_final_realization_semantics_counts"].items()}\n        assert sum(int(row["html_value_crosscheck_failure_count"]) > 0 for row in coverage) == stage1["html_value_crosscheck_failure_page_count"]\n',
        "audit coverage semantics",
    )
    replace_once(
        path,
        '        assert panel["primary_numeric_evidence"] == "djpk_csv_apbd_spreadsheetml_exact_rupiah"\n',
        '        assert panel["primary_numeric_evidence"] == "djpk_csv_apbd_spreadsheetml_exact_rupiah"\n        assert panel["annual_final_realization_semantics_required"] is True\n        assert panel["html_rounded_value_crosscheck_is_diagnostic"] is True\n',
        "audit panel semantics",
    )
    replace_once(
        path,
        '        assert {row["reference_period"] for row in observations} == {"realisasi_s.d._desember"}\n',
        '        assert {row["reference_period"] for row in observations} == {"annual_final_realization"}\n        assert {row["reference_period"] for row in provenance} == {"annual_final_realization"}\n        assert Counter(row["source_realization_semantics_class"] for row in provenance) == semantic_counts\n',
        "audit canonical reference period",
    )


def patch_materialized_tests() -> None:
    path = ROOT / "tests/test_milestone25_djpk_materialized.py"
    replace_once(path, "import csv\nimport json\n", "import csv\nimport json\nfrom collections import Counter\n", "test Counter import")
    replace_once(
        path,
        '    assert {r["export_valid_spreadsheetml"] for r in coverage} == {"True"}\n    assert {r["missing_contracts"] for r in coverage} == {""}\n    assert {r["parse_failures"] for r in coverage} == {""}\n    assert {r["html_value_crosscheck_failure_count"] for r in coverage} == {"0"}\n',
        '    assert {r["export_valid_spreadsheetml"] for r in coverage} == {"True"}\n    assert {r["annual_final_realization_semantics_match"] for r in coverage} == {"True"}\n    semantic_counts = Counter(r["annual_final_realization_semantics_class"] for r in coverage)\n    assert dict(semantic_counts) == {key: int(value) for key, value in stage1["annual_final_realization_semantics_counts"].items()}\n    assert {r["missing_contracts"] for r in coverage} == {""}\n    assert {r["parse_failures"] for r in coverage} == {""}\n    assert sum(int(r["html_value_crosscheck_failure_count"]) > 0 for r in coverage) == stage1["html_value_crosscheck_failure_page_count"]\n',
        "materialized coverage semantics",
    )
    replace_once(
        path,
        '    assert {r["reference_period"] for r in provenance} == {"realisasi_s.d._desember"}\n',
        '    assert {r["reference_period"] for r in provenance} == {"annual_final_realization"}\n    assert Counter(r["source_realization_semantics_class"] for r in provenance) == Counter({"calendar_year_end_december": 139, "final_accountability_perda": 11, "final_accountability_audited": 2})\n',
        "materialized provenance semantics",
    )


def patch_spec() -> None:
    path = ROOT / "research/MILESTONE25_DJPK_PUBLIC_FINANCE_SPEC.md"
    replace_once(
        path,
        "- `periode=12` — realization through December;\n",
        "- `periode=12` — locked annual-final selector. Historical source pages may report final status as `s.d Desember`, `s.d Audited <year>`, or `s.d Perda <year>`; intermediate-month and unaudited states are not accepted;\n",
        "spec period selector",
    )
    replace_once(
        path,
        "- December realization semantics are present;\n",
        "- accepted annual-final realization semantics are present (`Desember`, `Audited`, or `Perda` for the same fiscal year);\n",
        "spec Stage1 semantic gate",
    )
    marker = "M25 does not assume that the DJPK selector is a BPS geography code. An explicit crosswalk is stored in `data/registries/djpk_sumbar_pemda.csv`.\n"
    addition = marker + "\nThe annual-final semantic compatibility is a representation amendment only. It does not change the locked `periode=12` selector, target years, geographies, account-family set, or statistical design. The HTML page remains blocking evidence for jurisdiction, fiscal year, accepted annual-final status, and the same-selector export link; exact numeric account values come from the official SpreadsheetML export. Rounded HTML table values are diagnostic only.\n"
    replace_once(path, marker, addition, "spec recovery note")


def write_permanent_repro() -> None:
    path = ROOT / ".github/workflows/milestone25-djpk-fiscal-repro.yml"
    content = '''name: Milestone 25 DJPK fiscal reproducibility

# Permanent read-only gate over frozen DJPK evidence. No live DJPK acquisition occurs here.
on:
  pull_request:
    paths:
      - research/MILESTONE25_DJPK_PUBLIC_FINANCE_SPEC.md
      - docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md
      - data/manifests/milestone25_design_gate.json
      - data/manifests/milestone25_transport_amendment.json
      - data/manifests/milestone25_taxonomy_discovery.json
      - data/manifests/milestone25_stage1_contracts.json
      - data/manifests/milestone25_stage1_full_export.json
      - data/manifests/milestone25_djpk_public_finance_complete.json
      - data/registries/djpk_sumbar_pemda.csv
      - data/registries/djpk_m25_stage1_account_contracts.csv
      - data/analysis/engine/djpk_finance_v1/**
      - data/processed/djpk/taxonomy_probe/**
      - data/processed/djpk/public_finance/**
      - scripts/milestone25_djpk_period_semantics.py
      - scripts/milestone25_djpk_export.py
      - scripts/lock_milestone25_stage1_contracts.py
      - scripts/materialize_milestone25_djpk_exact_panel.py
      - scripts/finalize_milestone25_djpk_public_finance.py
      - scripts/build_milestone25_documentation.py
      - scripts/audit_milestone25_djpk_public_finance.py
      - tests/test_milestone25_djpk_period_semantics.py
      - tests/test_milestone25_djpk_export.py
      - tests/test_milestone25_djpk_materializer.py
      - tests/test_milestone25_djpk_materialized.py
      - .github/workflows/milestone25-djpk-fiscal-repro.yml
  workflow_dispatch:

permissions:
  contents: read

jobs:
  reproduce:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Require complete frozen M25 evidence
        run: |
          test -f data/manifests/milestone25_djpk_public_finance_complete.json
          test -f docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md

      - name: Preserve committed deterministic M25 outputs
        run: |
          mkdir -p /tmp/m25-committed
          cp data/registries/djpk_m25_stage1_account_contracts.csv /tmp/m25-committed/
          cp data/manifests/milestone25_stage1_contracts.json /tmp/m25-committed/
          cp data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv /tmp/m25-committed/
          cp data/processed/djpk/public_finance/djpk-fiscal-provenance.csv /tmp/m25-committed/
          cp data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json /tmp/m25-committed/
          cp data/manifests/milestone25_djpk_public_finance_complete.json /tmp/m25-committed/
          cp docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md /tmp/m25-committed/

      - name: Verify Stage 0 frozen dual representation and taxonomy offline
        run: |
          python - <<'PY'
          import hashlib, json, sys
          from pathlib import Path
          sys.path.insert(0, 'scripts')
          from milestone25_djpk_export import exact_account_map
          from probe_milestone25_djpk_taxonomy import classify_conceptual_families

          manifest = json.loads(Path('data/manifests/milestone25_taxonomy_discovery.json').read_text())
          assert manifest['stage0_complete'] is True
          assert manifest['spreadsheetml_account_table_required'] is True
          assert manifest['taxonomy_primary_representation'] == 'djpk_csv_apbd_spreadsheetml_exact_rupiah'
          labels_by_year = {}
          for item in manifest['raw_responses']:
              year = int(item['year'])
              html_path = Path(item['html_path'])
              xml_path = Path(item['export_path'])
              assert hashlib.sha256(html_path.read_bytes()).hexdigest() == item['html_sha256']
              xml = xml_path.read_bytes()
              assert hashlib.sha256(xml).hexdigest() == item['export_sha256']
              labels_by_year[year] = set(exact_account_map(xml))
          assert set(labels_by_year) == set(range(2018, 2026))
          assert classify_conceptual_families(labels_by_year) == manifest['conceptual_account_family_results']
          PY

      - name: Verify all 152 Stage 1 source pairs and annual-final semantics offline
        run: |
          python - <<'PY'
          import csv, hashlib, json, sys
          from collections import Counter
          from pathlib import Path
          sys.path.insert(0, 'scripts')
          import probe_milestone25_djpk_stage1 as stage1
          from milestone25_djpk_period_semantics import classify_annual_final_realization

          manifest = json.loads(Path('data/manifests/milestone25_stage1_full_export.json').read_text())
          with Path('data/analysis/engine/djpk_finance_v1/m25-stage1-full-coverage.csv').open(newline='', encoding='utf-8') as h:
              rows = list(csv.DictReader(h))
          assert len(rows) == 152 and all(r['page_pass'] == 'True' for r in rows)
          counts = Counter()
          for row in rows:
              pemda, year = row['djpk_pemda_selector'], int(row['year'])
              html_path = Path(f'data/processed/djpk/public_finance/source/pemda-{pemda}-{year}-desember.html')
              xml_path = Path(f'data/processed/djpk/public_finance/source/pemda-{pemda}-{year}-desember.xml')
              html = html_path.read_bytes()
              xml = xml_path.read_bytes()
              assert hashlib.sha256(html).hexdigest() == row['html_response_sha256']
              assert hashlib.sha256(xml).hexdigest() == row['export_response_sha256']
              parser = stage1.HTMLTableParser(); parser.feed(html.decode('utf-8', errors='replace'))
              cls = classify_annual_final_realization(parser.all_text, year)
              assert cls == row['annual_final_realization_semantics_class']
              assert row['annual_final_realization_semantics_match'] == 'True'
              counts[cls] += 1
          assert dict(counts) == {key: int(value) for key, value in manifest['annual_final_realization_semantics_counts'].items()}
          assert sum(counts.values()) == 152
          PY

      - name: Rebuild exact-label contracts from frozen taxonomy
        run: python scripts/lock_milestone25_stage1_contracts.py

      - name: Rebuild canonical fiscal panel from frozen Stage 1 sources
        run: python scripts/materialize_milestone25_djpk_exact_panel.py

      - name: Rebuild completion manifest and documentation
        run: |
          python scripts/finalize_milestone25_djpk_public_finance.py
          python scripts/build_milestone25_documentation.py

      - name: Install focused test runner
        run: python -m pip install --disable-pip-version-check pytest

      - name: Run focused M25 tests and audit
        run: |
          python -m pytest -q \
            tests/test_milestone25_djpk_period_semantics.py \
            tests/test_milestone25_djpk_export.py \
            tests/test_milestone25_djpk_materializer.py \
            tests/test_milestone25_djpk_materialized.py
          python scripts/audit_milestone25_djpk_public_finance.py

      - name: Verify byte-identical deterministic outputs
        run: |
          cmp /tmp/m25-committed/djpk_m25_stage1_account_contracts.csv data/registries/djpk_m25_stage1_account_contracts.csv
          cmp /tmp/m25-committed/milestone25_stage1_contracts.json data/manifests/milestone25_stage1_contracts.json
          cmp /tmp/m25-committed/djpk-fiscal-canonical-observations.csv data/processed/djpk/public_finance/djpk-fiscal-canonical-observations.csv
          cmp /tmp/m25-committed/djpk-fiscal-provenance.csv data/processed/djpk/public_finance/djpk-fiscal-provenance.csv
          cmp /tmp/m25-committed/djpk-fiscal-panel.manifest.json data/processed/djpk/public_finance/djpk-fiscal-panel.manifest.json
          cmp /tmp/m25-committed/milestone25_djpk_public_finance_complete.json data/manifests/milestone25_djpk_public_finance_complete.json
          cmp /tmp/m25-committed/MILESTONE25_DJPK_PUBLIC_FINANCE.md docs/MILESTONE25_DJPK_PUBLIC_FINANCE.md
          git diff --exit-code
'''
    path.write_text(content, encoding="utf-8")


def main() -> int:
    patch_transport()
    patch_finalizer()
    patch_docs_builder()
    patch_audit()
    patch_materialized_tests()
    patch_spec()
    write_permanent_repro()
    print(json.dumps({
        "completion_recovery": "applied",
        "transport_revision": 3,
        "reference_period": "annual_final_realization",
        "permanent_repro": "offline_dual_representation",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
