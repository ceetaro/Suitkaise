"""PokerML entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# bootstrap suitkaise import path first (this will just work for you, don't worry)
_this_file = Path(__file__).resolve()
_project_root = _this_file.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from suitkaise import paths


def _bootstrap_paths() -> None:
    # use Skpath for path setup
    file_path = paths.Skpath(__file__)
    project_root = file_path.root
    
    # get platform-native path strings for sys.path
    root_path = project_root.platform
    poker_path = (project_root / "suitkaise-examples" / "pokerML" / "poker_ml").platform

    # add to sys.path for this process
    if poker_path not in sys.path:
        sys.path.insert(0, poker_path)
    if root_path not in sys.path:
        sys.path.insert(0, root_path)

    # update PYTHONPATH for subprocesses
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
