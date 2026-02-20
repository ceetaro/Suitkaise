"""
One-time welcome message shown after install or upgrade.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _show_welcome(version: str) -> None:
    if not sys.stderr.isatty():
        return

    try:
        config_dir = Path.home() / ".suitkaise"
        config_dir.mkdir(exist_ok=True)
        marker = config_dir / ".welcomed_version"

        if marker.exists() and marker.read_text().strip() == version:
            return

        # get suitkaise version
        _version = f"suitkaise {version}"
        if "b0" in version:
            # get rid of "b0" and add " beta"
            _version = _version.replace("b0", " beta")

        msg = (
            f"\n"
            f"  suitkaise {_version}\n"
            f"\n"
            f"  Website:         https://suitkaise.info\n"
            f"  Download docs:   suitkaise docs\n"
            f"\n"
        )
        sys.stderr.write(msg)

        marker.write_text(version)
    except Exception:
        pass
