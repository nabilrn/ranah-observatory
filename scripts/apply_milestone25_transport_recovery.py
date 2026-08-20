#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / "data/manifests/milestone25_transport_amendment.json"
PROBE = ROOT / "scripts/probe_milestone25_djpk_stage1_export.py"
MATERIALIZER = ROOT / "scripts/materialize_milestone25_djpk_exact_panel.py"


def replace_or_validate(text: str, old: str, new: str, label: str) -> str:
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == 1 and new_count == 0:
        return text.replace(old, new, 1)
    if old_count == 0 and new_count == 1:
        return text
    raise RuntimeError(
        f"unexpected {label} state: old_count={old_count}, new_count={new_count}"
    )


def replace_exact_count(text: str, old: str, new: str, count: int, label: str) -> str:
    old_count = text.count(old)
    new_count = text.count(new)
    if old_count == count and new_count == 0:
        return text.replace(old, new)
    if old_count == 0 and new_count == count:
        return text
    raise RuntimeError(
        f"unexpected {label} state: old_count={old_count}, new_count={new_count}, expected={count}"
    )


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

    payload["amendment_revision"] = 3
    payload["recovery_decision_path"] = "data/manifests/milestone25_transport_recovery_decision.json"
    payload["html_table_value_crosscheck_required_when_parseable"] = False
    payload["html_table_value_crosscheck_is_diagnostic"] = True
    payload["annual_final_realization_semantics_required"] = True
    payload["requested_period_selector"] = "12"
    payload["accepted_annual_final_realization_semantics"] = [
        "calendar_year_end_december",
        "final_accountability_audited",
        "final_accountability_perda",
    ]
    payload["intermediate_month_or_unaudited_semantics_rejected"] = True
    payload["annual_final_semantic_compatibility_is_source_reported"] = True
    payload["annual_final_semantic_compatibility_basis"] = [
        "DJPK SIKD distinguishes annual APBD/LRA-Akhir-Tahun reporting from monthly LRA reporting",
        "DJPK historical accountability records use LKPD Audited/Perda final-status representations",
        "live historical SIKD pages requested with periode=12 report realization status as Desember, Audited <year>, or Perda <year>",
    ]
    payload["recovery_only_transport_change"] = True
    payload["recovery_reason"] = (
        "Live full-panel diagnostics established two representation differences without changing the locked scientific target. "
        "First, legacy rounded HTML display values can diverge from exact same-selector SpreadsheetML and are therefore diagnostic only. "
        "Second, historical SIKD pages requested with the locked annual selector periode=12 encode final annual realization semantics as "
        "s.d Desember, s.d Audited <year>, or s.d Perda <year>. The recovery accepts only those explicit final annual classes and "
        "continues to reject intermediate-month or unaudited semantics. Jurisdiction, fiscal year, annual-final semantics, exact "
        "same-selector export link, valid SpreadsheetML, and all locked exact-label contracts remain blocking gates."
    )
    TRANSPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_probe() -> None:
    text = PROBE.read_text(encoding="utf-8")

    text = replace_or_validate(
        text,
        'import probe_milestone25_djpk_stage1 as stage1\nfrom milestone25_djpk_export import (\n',
        'import probe_milestone25_djpk_stage1 as stage1\nfrom milestone25_djpk_period_semantics import classify_annual_final_realization\nfrom milestone25_djpk_export import (\n',
        "probe annual-final semantics import",
    )
    text = replace_or_validate(
        text,
        '            december_ok = bool(\n                re.search(r"realisasi\\s+apbd\\s+s\\.?\\s*d\\.?\\s+desember", page_text, flags=re.IGNORECASE)\n            )\n',
        '            annual_semantics_class = classify_annual_final_realization(page_text, year)\n            annual_semantics_ok = annual_semantics_class is not None\n',
        "probe annual-final semantics classification",
    )
    text = replace_or_validate(
        text,
        '                and december_ok\n                and export_link_ok\n',
        '                and annual_semantics_ok\n                and export_link_ok\n',
        "probe annual-final page gate",
    )
    text = replace_or_validate(
        text,
        '                    "december_realization_semantics_match": december_ok,\n                    "same_selector_export_link_match": export_link_ok,\n',
        '                    "annual_final_realization_semantics_match": annual_semantics_ok,\n                    "annual_final_realization_semantics_class": annual_semantics_class or "unqualified",\n                    "same_selector_export_link_match": export_link_ok,\n',
        "probe annual-final coverage fields",
    )
    text = replace_or_validate(
        text,
        '    if payload.get("html_table_value_crosscheck_required_when_parseable") is not True:\n        raise M25Stage1ExportError("HTML value cross-check is not required when parseable")\n',
        '    if payload.get("html_table_value_crosscheck_required_when_parseable") is not False:\n        raise M25Stage1ExportError("HTML rounded-value cross-check must be diagnostic-only in recovery revision 3")\n    if payload.get("html_table_value_crosscheck_is_diagnostic") is not True:\n        raise M25Stage1ExportError("HTML rounded-value diagnostic flag is missing")\n    if payload.get("annual_final_realization_semantics_required") is not True:\n        raise M25Stage1ExportError("annual-final realization semantics gate is missing")\n    if payload.get("requested_period_selector") != "12":\n        raise M25Stage1ExportError("locked annual period selector drift")\n    if payload.get("intermediate_month_or_unaudited_semantics_rejected") is not True:\n        raise M25Stage1ExportError("non-final period semantics are not fail-closed")\n',
        "probe transport gate",
    )
    text = replace_or_validate(
        text,
        '                and not parse_failures\n                and not html_crosscheck_failures\n                and matched_contracts == len(contracts)\n',
        '                and not parse_failures\n                and matched_contracts == len(contracts)\n',
        "page-pass HTML crosscheck gate",
    )
    text = replace_or_validate(
        text,
        '        "html_table_unparseable_page_count": sum(not bool(row["html_table_parseable"]) for row in coverage_rows),\n        "same_selector_export_link_required": True,\n',
        '        "html_table_unparseable_page_count": sum(not bool(row["html_table_parseable"]) for row in coverage_rows),\n        "html_value_crosscheck_failure_page_count": sum(int(row["html_value_crosscheck_failure_count"]) > 0 for row in coverage_rows),\n        "html_table_value_crosscheck_is_diagnostic": True,\n        "annual_final_realization_semantics_required": True,\n        "annual_final_realization_semantics_counts": {\n            semantic_class: sum(row["annual_final_realization_semantics_class"] == semantic_class for row in coverage_rows)\n            for semantic_class in (\n                "calendar_year_end_december",\n                "final_accountability_audited",\n                "final_accountability_perda",\n            )\n        },\n        "same_selector_export_link_required": True,\n',
        "probe manifest recovery diagnostics",
    )
    text = replace_or_validate(
        text,
        '        if value_rows:\n            write_csv(values_path, list(value_rows[0].keys()), value_rows)\n        raise M25Stage1ExportError(f"M25 dual-representation page qualification failures: {failures}")\n',
        '        if value_rows:\n            write_csv(values_path, list(value_rows[0].keys()), value_rows)\n        for row in coverage_rows:\n            if not bool(row["page_pass"]):\n                print("M25_FAIL " + json.dumps(row, sort_keys=True), file=sys.stderr)\n        raise M25Stage1ExportError(f"M25 dual-representation page qualification failures: {failures}")\n',
        "probe failure diagnostics",
    )
    PROBE.write_text(text, encoding="utf-8")


def patch_materializer() -> None:
    text = MATERIALIZER.read_text(encoding="utf-8")

    text = replace_or_validate(
        text,
        'import probe_milestone25_djpk_stage1 as stage1\nfrom milestone25_djpk_export import (\n',
        'import probe_milestone25_djpk_stage1 as stage1\nfrom milestone25_djpk_period_semantics import classify_annual_final_realization\nfrom milestone25_djpk_export import (\n',
        "materializer annual-final semantics import",
    )
    text = replace_or_validate(
        text,
        ') -> tuple[str, bool, dict[str, dict[str, str]]]:\n',
        ') -> tuple[str, str, bool, dict[str, dict[str, str]]]:\n',
        "materializer semantic return annotation",
    )
    text = replace_or_validate(
        text,
        '    if not re.search(r"realisasi\\s+apbd\\s+s\\.?\\s*d\\.?\\s+desember", page_text, flags=re.IGNORECASE):\n        raise M25MaterializationError(f"frozen HTML December semantics failed {pemda}/{year}")\n',
        '    annual_semantics_class = classify_annual_final_realization(page_text, year)\n    if annual_semantics_class is None:\n        raise M25MaterializationError(f"frozen HTML annual-final semantics failed {pemda}/{year}")\n',
        "materializer annual-final semantics gate",
    )
    text = replace_or_validate(
        text,
        '    return linked_export, parseable, html_accounts\n',
        '    return linked_export, annual_semantics_class, parseable, html_accounts\n',
        "materializer semantic return value",
    )
    text = replace_or_validate(
        text,
        '            linked_export, html_parseable, html_accounts = verify_html_semantics(\n',
        '            linked_export, annual_semantics_class, html_parseable, html_accounts = verify_html_semantics(\n',
        "materializer semantic caller",
    )
    text = replace_exact_count(
        text,
        '"reference_period": "realisasi_s.d._desember",',
        '"reference_period": "annual_final_realization",',
        2,
        "materializer reference-period labels",
    )
    text = replace_or_validate(
        text,
        '                    "period_selector": "12",\n                    "reference_period": "annual_final_realization",\n                    "html_snapshot": html_path.relative_to(ROOT).as_posix(),\n',
        '                    "period_selector": "12",\n                    "reference_period": "annual_final_realization",\n                    "source_realization_semantics_class": annual_semantics_class,\n                    "html_snapshot": html_path.relative_to(ROOT).as_posix(),\n',
        "materializer provenance semantics class",
    )

    old_crosscheck = '''                html_crosscheck_status = "not_available_html_table_unparseable"\n                if html_parseable:\n                    html_row = html_accounts.get(label)\n                    if html_row is None:\n                        raise M25MaterializationError(f"HTML locked label missing on parseable page {family} {geography_id}/{year}")\n                    display_amount = stage1.parse_djpk_money_to_idr_billion(html_row["realization_raw"])\n                    if not html_display_matches_exact(display_amount, realization_rupiah):\n                        raise M25MaterializationError(f"HTML/export rounded-value mismatch {family} {geography_id}/{year}")\n                    html_crosscheck_status = "passed_display_rounding_crosscheck"\n                if probe_row["html_crosscheck_status"] != html_crosscheck_status:\n                    raise M25MaterializationError(f"HTML crosscheck status drift {family} {geography_id}/{year}")\n'''
    new_crosscheck = '''                html_crosscheck_status = "not_available_html_table_unparseable"\n                if html_parseable:\n                    html_row = html_accounts.get(label)\n                    if html_row is None:\n                        html_crosscheck_status = "diagnostic_locked_label_missing_in_html_table"\n                    else:\n                        try:\n                            display_amount = stage1.parse_djpk_money_to_idr_billion(html_row["realization_raw"])\n                            if html_display_matches_exact(display_amount, realization_rupiah):\n                                html_crosscheck_status = "passed_display_rounding_crosscheck"\n                            else:\n                                html_crosscheck_status = "diagnostic_display_rounding_mismatch"\n                        except stage1.M25Stage1Error:\n                            html_crosscheck_status = "diagnostic_html_display_parse_failure"\n\n                probe_status_map = {\n                    "failed_locked_label_missing_in_html_table": "diagnostic_locked_label_missing_in_html_table",\n                    "failed_display_rounding_crosscheck": "diagnostic_display_rounding_mismatch",\n                    "failed_html_display_parse": "diagnostic_html_display_parse_failure",\n                }\n                expected_probe_status = probe_status_map.get(probe_row["html_crosscheck_status"], probe_row["html_crosscheck_status"])\n                if expected_probe_status != html_crosscheck_status:\n                    raise M25MaterializationError(f"HTML diagnostic status drift {family} {geography_id}/{year}")\n'''
    text = replace_or_validate(text, old_crosscheck, new_crosscheck, "materializer HTML diagnostic block")

    text = replace_or_validate(
        text,
        '        "html_semantic_evidence": "identity_year_december_same_selector_export_link",\n        "derived_ratio_count": 0,\n',
        '        "html_semantic_evidence": "identity_year_annual_final_status_same_selector_export_link",\n        "annual_final_realization_semantics_required": True,\n        "html_rounded_value_crosscheck_is_diagnostic": True,\n        "derived_ratio_count": 0,\n',
        "materializer manifest recovery flags",
    )
    MATERIALIZER.write_text(text, encoding="utf-8")


def main() -> int:
    patch_transport()
    patch_probe()
    patch_materializer()
    print(json.dumps({
        "transport_revision": 3,
        "scientific_design_changed": False,
        "annual_final_realization_semantics_required": True,
        "accepted_annual_final_realization_semantics": [
            "calendar_year_end_december",
            "final_accountability_audited",
            "final_accountability_perda",
        ],
        "intermediate_month_or_unaudited_semantics_rejected": True,
        "html_rounded_value_crosscheck_is_diagnostic": True,
        "spreadsheetml_remains_primary_exact_numeric_evidence": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
