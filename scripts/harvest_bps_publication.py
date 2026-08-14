from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bps_publication import PublicationAcquisitionError, download_publication, fetch_publication_page


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Acquire a public BPS publication without a WebAPI key."
    )
    parser.add_argument("url", help="Official BPS publication page URL")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Resolve the current public download link but do not download the PDF",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="PDF output path. Required unless --inspect is used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.inspect and args.output is None:
        raise SystemExit("--output is required unless --inspect is used")

    try:
        if args.inspect:
            page = fetch_publication_page(args.url)
            print(
                json.dumps(
                    {
                        "title": page.title,
                        "official_page_url": page.page_url,
                        "download_host": page.download_url.split("/", 3)[2],
                        "credential_required": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        manifest = download_publication(args.url, args.output)
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    except PublicationAcquisitionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
