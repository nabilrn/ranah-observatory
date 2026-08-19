from __future__ import annotations

from collections import defaultdict
from html.parser import HTMLParser
from typing import Any


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

    The DJPK portal can repeat the same visible label at two hierarchy levels.
    Reference-year diagnostics established that ``Belanja Modal`` and
    ``Belanja Pegawai`` use two levels with byte-equivalent displayed values in
    every 2018-2025 Kota Padang reference page. Such duplicates are safe to
    collapse because either occurrence represents the exact same displayed
    quantity.

    Non-identical duplicates are *never* collapsed. Their normalized labels are
    disambiguated so the unsuffixed label disappears from the qualification
    universe. This prevents an ambiguous hierarchy row from becoming an exact
    label contract accidentally. The raw HTML remains frozen as provenance.
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

            # Conflicting hierarchy rows remain separately represented, but the
            # ambiguous base label is deliberately unavailable for exact-label
            # qualification or Stage 1 lookup.
            for occurrence, item in enumerate(group, start=1):
                disambiguated = dict(item)
                disambiguated["account_label_normalized"] = f"{label} [hierarchy-conflict-{occurrence}]"
                disambiguated["duplicate_occurrence_count"] = str(len(group))
                disambiguated["duplicate_resolution"] = "nonidentical_hierarchy_values_disambiguated"
                resolved.append(disambiguated)

        return resolved

    taxonomy.table_to_accounts = table_to_accounts
    taxonomy._m25_djpk_duplicate_label_compat = True


def install_djpk_html_compat() -> None:
    """Install source-specific compatibility rules for frozen DJPK APBD HTML.

    Two source quirks are handled conservatively:
    1. malformed ``<tr/>`` body-row closers are interpreted as row closes;
    2. duplicate visible labels collapse only when all displayed values are
       identical, while non-identical duplicates are disambiguated and cannot
       qualify under their base label.
    """
    import probe_milestone25_djpk_taxonomy as taxonomy

    _install_row_close_compat(taxonomy)
    _install_duplicate_label_compat(taxonomy)
