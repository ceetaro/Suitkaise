"""
Suitkaise CLI - lightweight entrypoint for version and module info.
"""

from __future__ import annotations

import argparse
from typing import Iterable, Sequence

import suitkaise


def _module_names() -> list[str]:
    return ["timing", "paths", "circuits", "cerial", "processing", "sk"]


def _format_info() -> str:
    modules = ", ".join(_module_names())
    return (
        f"Suitkaise {suitkaise.__version__}\n"
        f"Modules: {modules}\n"
        f"Python: 3.11+"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="suitkaise",
        description="Suitkaise command-line utilities.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the current Suitkaise version.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "info",
        help="Print version and module information.",
    )

    subparsers.add_parser(
        "modules",
        help="List available modules.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(suitkaise.__version__)
        return 0

    if args.command == "info":
        print(_format_info())
        return 0

    if args.command == "modules":
        print("\n".join(_module_names()))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
