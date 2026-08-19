from __future__ import annotations

from html.parser import HTMLParser


def install_djpk_html_compat() -> None:
    """Patch the M25 DJPK table parser for source-native ``<tr/>`` row closers.

    The DJPK APBD portal currently emits body rows ending in ``<tr/>`` rather
    than valid ``</tr>``. Python's default ``HTMLParser.handle_startendtag``
    treats that token as start-then-end, which resets the active row before it
    can be committed. For this source-specific malformed token we interpret it
    only as the intended row close. No other HTML parsing behavior is changed.
    """
    import probe_milestone25_djpk_taxonomy as taxonomy

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
