"""
Skpath Type Definitions

Type aliases for path operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .skpath import Skpath

# AnyPath accepts str, Path, or Skpath
# Note: Does NOT include None - use AnyPath | None when None is acceptable
# Using Union for forward reference compatibility at runtime
AnyPath = Union[str, Path, "Skpath"]
