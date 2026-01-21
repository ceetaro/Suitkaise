"""PokerML entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Bootstrap suitkaise import path first
_this_file = Path(__file__).resolve()
_project_root = _this_file.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from suitkaise.paths import Skpath


def _bootstrap_paths() -> None:
    # Now use Skpath for the rest of path setup
    poker_dir = Skpath(_this_file).parent / "poker_ml"
    project_root = poker_dir.parent.parent.parent
    poker_path = poker_dir.parent.platform
    root_path = project_root.platform

    if poker_path not in sys.path:
        sys.path.insert(0, poker_path)
    if root_path not in sys.path:
        sys.path.insert(0, root_path)

    current = os.environ.get("PYTHONPATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if poker_path not in parts:
        parts.insert(0, poker_path)
    if root_path not in parts:
        parts.insert(0, root_path)
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)


_bootstrap_paths()

from poker_ml.main import main


if __name__ == "__main__":
    main()
