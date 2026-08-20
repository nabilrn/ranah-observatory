from __future__ import annotations

import re


class M25DJPKPeriodSemanticsError(RuntimeError):
    pass


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def classify_annual_final_realization(page_text: str, year: int) -> str | None:
    """Classify source-reported annual/final DJPK realization semantics.

    M25 keeps the locked SIKD selector `periode=12` and requires the HTML
    source to explicitly identify a final annual realization representation.
    Historical SIKD pages do not use one literal consistently: current pages
    can say `s.d Desember`, while archived final-accountability records can say
    `s.d Audited <year>` or `s.d Perda <year>`.

    This helper deliberately rejects intermediate month/status labels.  It is
    a semantic compatibility rule, not a fallback for missing period evidence.
    """
    if year < 2018 or year > 2025:
        raise M25DJPKPeriodSemanticsError(f"year outside locked M25 regime: {year}")

    text = _normalized(page_text)
    if re.search(r"realisasi\s+apbd\s+s\.?\s*d\.?\s+desember\b", text, flags=re.IGNORECASE):
        return "calendar_year_end_december"

    year_token = re.escape(str(year))
    if re.search(
        rf"realisasi\s+apbd\s+s\.?\s*d\.?\s+audited\s+{year_token}\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "final_accountability_audited"

    if re.search(
        rf"realisasi\s+apbd\s+s\.?\s*d\.?\s+perda\s+{year_token}\b",
        text,
        flags=re.IGNORECASE,
    ):
        return "final_accountability_perda"

    return None


def annual_final_realization_matches(page_text: str, year: int) -> bool:
    return classify_annual_final_realization(page_text, year) is not None
