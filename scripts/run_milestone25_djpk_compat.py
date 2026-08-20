#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys

from milestone25_djpk_html_compat import install_djpk_html_compat


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_milestone25_djpk_compat.py MODULE [ARGS...]", file=sys.stderr)
        return 2
    module_name = sys.argv[1]
    forwarded = sys.argv[2:]
    install_djpk_html_compat()
    module = importlib.import_module(module_name)
    entry = getattr(module, "main", None)
    if entry is None:
        print(f"error: module {module_name!r} has no main()", file=sys.stderr)
        return 2
    sys.argv = [module_name, *forwarded]
    result = entry()
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
