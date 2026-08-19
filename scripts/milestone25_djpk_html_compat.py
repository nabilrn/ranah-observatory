from __future__ import annotations

import csv
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "data/registries/djpk_sumbar_pemda.csv"


def _install_row_close_compat(taxonomy: Any) -> None:
    parser_cls = taxonomy.HTMLTableParser
    if getattr(parser_cls, "_m25_djpk_selfclosing_tr_compat", False):
        return

    def handle_startendtag(self, tag: str, attrs):  # type: ignore[no-untyped-def]
        if (
            tag.casefold() == "tr"
            and getattr(self, "_table_depth", 0) == 1
            and getattr(self, "_row", None) is not None
        ):
            self.handle_endtag("tr")
            return
        HTMLParser.handle_startendtag(self, tag, attrs)

    parser_cls.handle_startendtag = handle_startendtag
    parser_cls._m25_djpk_selfclosing_tr_compat = True


def _install_duplicate_label_compat(taxonomy: Any) -> None:
    """Make duplicate visible account labels explicit and fail-closed.

    Identical duplicate display rows can be collapsed. Non-identical duplicate
    hierarchy rows are retained only under disambiguated normalized labels, so
    their ambiguous base label cannot qualify as an exact-label contract.
    """
    if getattr(taxonomy, "_m25_djpk_duplicate_label_compat", False):
        return

    def table_to_accounts(header: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
        normalized_header = [taxonomy.normalize_label(cell) for cell in header]
        try:
            account_index = normalized_header.index("akun")
            realization_index = normalized_header.index("realisasi")
        except ValueError as exc:
            raise ValueError("DJPK postur header missing Akun/Realisasi") from exc
        budget_index = normalized_header.index("anggaran/pagu") if "anggaran/pagu" in normalized_header else None
        percent_index = normalized_header.index("%") if "%" in normalized_header else None

        parsed: list[dict[str, str]] = []
        for source_order, row in enumerate(rows, start=1):
            if len(row) <= max(account_index, realization_index):
                continue
            account = taxonomy.normalize_space(row[account_index])
            if not account:
                continue
            parsed.append(
                {
                    "source_order": str(source_order),
                    "account_label": account,
                    "account_label_normalized": taxonomy.normalize_label(account),
                    "budget_raw": taxonomy.normalize_space(row[budget_index]) if budget_index is not None and budget_index < len(row) else "",
                    "realization_raw": taxonomy.normalize_space(row[realization_index]),
                    "percent_raw": taxonomy.normalize_space(row[percent_index]) if percent_index is not None and percent_index < len(row) else "",
                    "duplicate_occurrence_count": "1",
                    "duplicate_resolution": "unique_label",
                }
            )
        if not parsed:
            raise ValueError("DJPK postur table yielded no account rows")

        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        order: list[str] = []
        for item in parsed:
            label = item["account_label_normalized"]
            if label not in grouped:
                order.append(label)
            grouped[label].append(item)

        resolved: list[dict[str, str]] = []
        for label in order:
            group = grouped[label]
            if len(group) == 1:
                resolved.append(group[0])
                continue

            value_signatures = {
                (item["budget_raw"], item["realization_raw"], item["percent_raw"])
                for item in group
            }
            if len(value_signatures) == 1:
                kept = dict(group[0])
                kept["duplicate_occurrence_count"] = str(len(group))
                kept["duplicate_resolution"] = "identical_display_values_collapsed"
                resolved.append(kept)
                continue

            for occurrence, item in enumerate(group, start=1):
                disambiguated = dict(item)
                disambiguated["account_label_normalized"] = f"{label} [hierarchy-conflict-{occurrence}]"
                disambiguated["duplicate_occurrence_count"] = str(len(group))
                disambiguated["duplicate_resolution"] = "nonidentical_hierarchy_values_disambiguated"
                resolved.append(disambiguated)

        return resolved

    taxonomy.table_to_accounts = table_to_accounts
    taxonomy._m25_djpk_duplicate_label_compat = True


def _load_explicit_identity_aliases(stage1: Any) -> dict[str, tuple[str, ...]]:
    """Return source-verified aliases keyed by the locked primary source name.

    Aliases are data, not fuzzy rules. Only non-empty aliases explicitly stored
    in the reviewed DJPK crosswalk can expand an identity match.
    """
    aliases: dict[str, tuple[str, ...]] = {}
    with CROSSWALK.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 19:
        raise ValueError(f"DJPK identity alias crosswalk must have 19 rows, got {len(rows)}")
    for row in rows:
        primary = (row.get("djpk_source_name") or "").strip()
        raw_alias = (row.get("djpk_identity_alias") or "").strip()
        if not primary:
            raise ValueError("DJPK identity alias crosswalk contains empty primary name")
        if not raw_alias:
            aliases[primary] = ()
            continue
        values = tuple(part.strip() for part in raw_alias.split("|") if part.strip())
        if not values:
            raise ValueError(f"DJPK identity alias field is malformed for {primary}")
        aliases[primary] = values
    return aliases


def _install_identity_alias_compat() -> None:
    import probe_milestone25_djpk_stage1 as stage1

    if getattr(stage1, "_m25_djpk_explicit_identity_alias_compat", False):
        return
    alias_map = _load_explicit_identity_aliases(stage1)
    original = stage1.jurisdiction_matches

    def jurisdiction_matches(page_text: str, expected_source_name: str) -> bool:
        if original(page_text, expected_source_name):
            return True
        for alias in alias_map.get(expected_source_name, ()):  # exact reviewed aliases only
            if original(page_text, alias):
                return True
        return False

    stage1.jurisdiction_matches = jurisdiction_matches
    stage1._m25_djpk_explicit_identity_alias_compat = True


def install_djpk_html_compat() -> None:
    """Install fail-closed compatibility rules for frozen DJPK APBD HTML.

    The compatibility layer handles only source-observed quirks:
    1. malformed ``<tr/>`` body-row closers;
    2. duplicate visible hierarchy labels, collapsing only identical values;
    3. explicit source-name aliases stored in the reviewed jurisdiction
       crosswalk. No fuzzy geography matching is introduced.
    """
    import probe_milestone25_djpk_taxonomy as taxonomy

    _install_row_close_compat(taxonomy)
    _install_duplicate_label_compat(taxonomy)
    _install_identity_alias_compat()
