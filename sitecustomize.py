"""
Ensure PokerML package is importable in subprocesses.

Python automatically imports sitecustomize if it is on sys.path.
This keeps Pool worker deserialization stable for poker_ml modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parent
poker_dir = root / "suitkaise-examples" / "pokerML"

if poker_dir.exists():
    poker_path = str(poker_dir)
    if poker_path not in sys.path:
        sys.path.insert(0, poker_path)
