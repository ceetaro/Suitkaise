"""
Suitkaise CLI - lightweight entrypoint for version and module info.
"""

from __future__ import annotations

import argparse
from typing import Iterable, Sequence

import suitkaise


def _module_names() -> list[str]:
    return ["timing", "paths", "circuits", "cucumber", "processing", "sk"]


def _format_info() -> str:
    version = suitkaise.__version__
    _version = f"suitkaise {version}"
    if "b0" in version:
        _version = _version.replace("b0", " beta")
    return (
        f"\n"
        f"  {_version}\n"
        f"\n"
        f"  Website:         https://suitkaise.info\n"
        f"  Download docs:   suitkaise docs\n"
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

    subparsers.add_parser(
        "docs",
        help="Download suitkaise documentation to the project root.",
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

    if args.command == "docs":
        from . import docs

        try:
            docs.download()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error downloading docs: {e}")
            return 1
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
