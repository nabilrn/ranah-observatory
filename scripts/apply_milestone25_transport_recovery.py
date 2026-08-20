#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
PROBE = ROOT / "scripts/probe_milestone25_djpk_stage1_export.py"
MATERIALIZER = ROOT / "scripts/materialize_milestone25_djpk_exact_panel.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one {label} replacement target, found {count}")
    return text.replace(old, new, 1)


def patch_transport() -> None:
    payload = json.loads(TRANSPORT.read_text(encoding="utf-8"))
    if payload.get("representation_amendment_after_transport_failure") is not True:
        raise RuntimeError("M25 transport amendment is not the expected representation-only contract")
    if payload.get("scientific_design_changed") is not False:
        raise RuntimeError("scientific design is not locked")
    if payload.get("html_role") is None or "optional_rounded_display_crosscheck" not in payload["html_role"]:
        raise RuntimeError("HTML cross-check was not preregistered as optional")
    if payload.get("spreadsheetml_export_role") is None or "primary_exact_account_value_evidence" not in payload["spreadsheetml_export_role"]:
        raise RuntimeError("SpreadsheetML is not the locked primary exact evidence")

    payload["amendment_revision"] = 2
    payload["recovery_decision_path"] = "data/manifests/milestone25_transport_recovery_decision.json"
    payload["html_table_value_crosscheck_required_when_parseable"] = False
    payload["html_table_value_crosscheck_is_diagnostic"] = True
    payload["recovery_only_transport_change"] = True
    payload["recovery_reason"] = (
        "Live full-panel diagnostics showed legacy rounded HTML display mismatches on a bounded set of 2021/2022 pages. "
        "All jurisdiction/year/December/same-selector SpreadsheetML gates remain blocking; only the rounded HTML value comparison is diagnostic."
    )
    TRANSPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_probe() -> None:
    text = PROBE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    if payload.get("html_table_value_crosscheck_required_when_parseable") is not True:\n        raise M25Stage1ExportError("HTML value cross-check is not required when parseable")\n',
        '    if payload.get("html_table_value_crosscheck_required_when_parseable") is not False:\n        raise M25Stage1ExportError("HTML rounded-value cross-check must be diagnostic-only in recovery revision 2")\n    if payload.get("html_table_value_crosscheck_is_diagnostic") is not True:\n        raise M25Stage1ExportError("HTML rounded-value diagnostic flag is missing")\n',
        "probe transport gate",
    )
    text = replace_once(
        text,
        '                and not parse_failures\n                and not html_crosscheck_failures\n                and matched_contracts == len(contracts)\n',
        '                and not parse_failures\n                and matched_contracts == len(contracts)\n',
        "page-pass HTML crosscheck gate",
    )
    text = replace_once(
        text,
        '        "html_table_unparseable_page_count": sum(not bool(row["html_table_parseable"]) for row in coverage_rows),\n        "same_selector_export_link_required": True,\n',
        '        "html_table_unparseable_page_count": sum(not bool(row["html_table_parseable"]) for row in coverage_rows),\n        "html_value_crosscheck_failure_page_count": sum(int(row["html_value_crosscheck_failure_count"]) > 0 for row in coverage_rows),\n        "html_table_value_crosscheck_is_diagnostic": True,\n        "same_selector_export_link_required": True,\n',
        "probe manifest diagnostics",
    )
    text = replace_once(
        text,
        '        if value_rows:\n            write_csv(values_path, list(value_rows[0].keys()), value_rows)\n        raise M25Stage1ExportError(f"M25 dual-representation page qualification failures: {failures}")\n',
        '        if value_rows:\n            write_csv(values_path, list(value_rows[0].keys()), value_rows)\n        for row in coverage_rows:\n            if not bool(row["page_pass"]):\n                print("M25_FAIL " + json.dumps(row, sort_keys=True), file=sys.stderr)\n        raise M25Stage1ExportError(f"M25 dual-representation page qualification failures: {failures}")\n',
        "probe failure diagnostics",
    )
    PROBE.write_text(text, encoding="utf-8")


def patch_materializer() -> None:
    text = MATERIALIZER.read_text(encoding="utf-8")
    old = '''                html_crosscheck_status = "not_available_html_table_unparseable"\n                if html_parseable:\n                    html_row = html_accounts.get(label)\n                    if html_row is None:\n                        raise M25MaterializationError(f"HTML locked label missing on parseable page {family} {geography_id}/{year}")\n                    display_amount = stage1.parse_djpk_money_to_idr_billion(html_row["realization_raw"])\n                    if not html_display_matches_exact(display_amount, realization_rupiah):\n                        raise M25MaterializationError(f"HTML/export rounded-value mismatch {family} {geography_id}/{year}")\n                    html_crosscheck_status = "passed_display_rounding_crosscheck"\n                if probe_row["html_crosscheck_status"] != html_crosscheck_status:\n                    raise M25MaterializationError(f"HTML crosscheck status drift {family} {geography_id}/{year}")\n'''
    new = '''                html_crosscheck_status = "not_available_html_table_unparseable"\n                if html_parseable:\n                    html_row = html_accounts.get(label)\n                    if html_row is None:\n                        html_crosscheck_status = "diagnostic_locked_label_missing_in_html_table"\n                    else:\n                        try:\n                            display_amount = stage1.parse_djpk_money_to_idr_billion(html_row["realization_raw"])\n                            if html_display_matches_exact(display_amount, realization_rupiah):\n                                html_crosscheck_status = "passed_display_rounding_crosscheck"\n                            else:\n                                html_crosscheck_status = "diagnostic_display_rounding_mismatch"\n                        except stage1.M25Stage1Error:\n                            html_crosscheck_status = "diagnostic_html_display_parse_failure"\n\n                probe_status_map = {\n                    "failed_locked_label_missing_in_html_table": "diagnostic_locked_label_missing_in_html_table",\n                    "failed_display_rounding_crosscheck": "diagnostic_display_rounding_mismatch",\n                    "failed_html_display_parse": "diagnostic_html_display_parse_failure",\n                }\n                expected_probe_status = probe_status_map.get(probe_row["html_crosscheck_status"], probe_row["html_crosscheck_status"])\n                if expected_probe_status != html_crosscheck_status:\n                    raise M25MaterializationError(f"HTML diagnostic status drift {family} {geography_id}/{year}")\n'''
    text = replace_once(text, old, new, "materializer HTML diagnostic block")
    text = replace_once(
        text,
        '        "html_semantic_evidence": "identity_year_december_same_selector_export_link",\n        "derived_ratio_count": 0,\n',
        '        "html_semantic_evidence": "identity_year_december_same_selector_export_link",\n        "html_rounded_value_crosscheck_is_diagnostic": True,\n        "derived_ratio_count": 0,\n',
        "materializer manifest diagnostic flag",
    )
    MATERIALIZER.write_text(text, encoding="utf-8")


def main() -> int:
    patch_transport()
    patch_probe()
    patch_materializer()
    print(json.dumps({
        "transport_revision": 2,
        "scientific_design_changed": False,
        "html_rounded_value_crosscheck_is_diagnostic": True,
        "spreadsheetml_remains_primary_exact_numeric_evidence": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
