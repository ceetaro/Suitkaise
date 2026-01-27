"""
Skpath Root Detection

Automatic project root detection with custom root override support.
Thread-safe with RLock for all shared state.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

from .exceptions import PathDetectionError
from .id_utils import normalize_separators

# thread-safe locks
_root_lock = threading.RLock()
_cache_lock = threading.RLock()

# module-level state
_custom_root: Path | None = None
_cached_root: Path | None = None
_cached_root_source: Path | None = None  # The path used to detect the cached root


# project root indicators

# guaranteed indicators - if found, this IS the project root
DEFINITIVE_INDICATORS = frozenset({
    "setup.sk",      # suitkaise custom marker (highest priority)
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
})

# strong indicators - likely project root
STRONG_INDICATORS = frozenset({
    ".gitignore",
    ".git",
})

# license files (case-insensitive matching)
LICENSE_PATTERNS = frozenset({
    "license",
    "license.txt",
    "license.md",
    "licence",
    "licence.txt",
    "licence.md",
})

# README files (case-insensitive matching)
README_PATTERNS = frozenset({
    "readme",
    "readme.md",
    "readme.txt",
    "readme.rst",
})

# requirements files
REQUIREMENTS_PATTERNS = frozenset({
    "requirements.txt",
    "requirements.pip",
    "requirements-dev.txt",
    "requirements-test.txt",
})


# custom root management

def set_custom_root(path: str | Path) -> None:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        paths.set_custom_root("/my/project")
        ```
    ────────────────────────────────────────────────────────\n

    Set a custom project root, overriding automatic detection.
    
    Thread-safe operation.
    
    Args:
        path: Path to use as project root
        
    Raises:
        PathDetectionError: If path doesn't exist or isn't a directory
    """
    global _custom_root
    
    if isinstance(path, str):
        path = Path(path)
    
    path = path.resolve()
    
    if not path.exists():
        raise PathDetectionError(f"Custom root path does not exist: {path}")
    
    if not path.is_dir():
        raise PathDetectionError(f"Custom root path is not a directory: {path}")
    
    with _root_lock:
        _custom_root = path


def get_custom_root() -> str | None:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        current = paths.get_custom_root()
        ```
    ────────────────────────────────────────────────────────\n

    Get the currently set custom root, if any.
    
    Returns:
        Custom root path as string with normalized separators, or None
    """
    with _root_lock:
        if _custom_root is not None:
            return normalize_separators(str(_custom_root))
        return None


def clear_custom_root() -> None:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        paths.clear_custom_root()
        ```
    ────────────────────────────────────────────────────────\n

    Clear the custom project root, reverting to automatic detection.
    
    Thread-safe operation.
    """
    global _custom_root
    
    with _root_lock:
        _custom_root = None


class CustomRoot:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        with paths.CustomRoot("/my/project"):

            # root will be an Skpath for "/my/project"
            root = paths.get_project_root()
        ```
    ────────────────────────────────────────────────────────\n

    Context manager for temporarily setting a custom project root.
    
    Thread-safe - uses RLock so can be nested from same thread.
    
    Usage:
        with CustomRoot("/path/to/project"):
            # All Skpath operations use this root
            path = Skpath("feature/file.txt")
    """
    
    def __init__(self, path: str | Path):
        self._path = path
        self._previous_root: Path | None = None
    
    def __enter__(self) -> "CustomRoot":
        global _custom_root
        
        with _root_lock:
            self._previous_root = _custom_root
        
        set_custom_root(self._path)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        global _custom_root
        
        with _root_lock:
            _custom_root = self._previous_root
        
        return None  # don't suppress exceptions


# root detection

def _has_indicator(directory: Path) -> bool:
    """Check if directory has any project root indicators."""
    try:
        contents = {item.name for item in directory.iterdir()}
        contents_lower = {item.lower() for item in contents}
    except (PermissionError, OSError):
        return False
    
    # check definitive indicators
    if contents & DEFINITIVE_INDICATORS:
        return True
    
    # check strong indicators
    if contents & STRONG_INDICATORS:
        return True
    
    # check license files (case-insensitive)
    if contents_lower & LICENSE_PATTERNS:
        return True
    
    # check README files (case-insensitive)
    if contents_lower & README_PATTERNS:
        return True
    
    # check requirements files
    if contents_lower & REQUIREMENTS_PATTERNS:
        return True
    
    return False


def _find_root_from_path(start_path: Path) -> Path | None:
    """
    Walk up from start_path to find project root.
    
    Priority:
    1. setup.sk (highest priority - Suitkaise marker)
    2. Other definitive indicators
    3. Strong indicators
    
    Args:
        start_path: Path to start searching from
        
    Returns:
        Project root Path, or None if not found
    """
    current = start_path.resolve()
    
    # if it's a file, start from its parent
    if current.is_file():
        current = current.parent
    
    # first pass: look for setup.sk specifically (highest priority)
    check_path = current
    while check_path != check_path.parent:
        setup_sk = check_path / "setup.sk"
        if setup_sk.exists():
            return check_path
        check_path = check_path.parent
    
    # second pass: look for any indicator
    check_path = current
    best_root: Path | None = None
    
    while check_path != check_path.parent:
        if _has_indicator(check_path):
            best_root = check_path
            # don't break - keep going up to find the outermost root
            # this handles nested projects correctly
        check_path = check_path.parent
    
    # check filesystem root
    if _has_indicator(check_path):
        best_root = check_path
    
    return best_root


def detect_project_root(
    from_path: str | Path | None = None,
    expected_name: str | None = None,
) -> Path:
    """
    Detect the project root directory.
    
    Priority:
    1. Custom root (if set via set_custom_root())
    2. Walk up from from_path looking for indicators
    3. Walk up from current working directory
    
    Args:
        from_path: Path to start detection from (default: cwd)
        expected_name: If provided, detected root must have this name
        
    Returns:
        Project root as Path
        
    Raises:
        PathDetectionError: If root cannot be detected or doesn't match expected_name
    """
    global _cached_root, _cached_root_source
    
    # check custom root first
    with _root_lock:
        if _custom_root is not None:
            if expected_name and _custom_root.name != expected_name:
                raise PathDetectionError(
                    f"Custom root '{_custom_root.name}' doesn't match expected name '{expected_name}'"
                )
            return _custom_root
    
    # determine start path
    if from_path is not None:
        if isinstance(from_path, str):
            start_path = Path(from_path).resolve()
        else:
            start_path = from_path.resolve()
    else:
        start_path = Path.cwd()
    
    # check cache
    with _cache_lock:
        if _cached_root is not None and _cached_root_source is not None:
            # cache hit if we're searching from within the same project
            try:
                start_path.relative_to(_cached_root)
                if expected_name is None or _cached_root.name == expected_name:
                    return _cached_root
            except ValueError:
                pass  # not relative to cached root, need to detect again

    # detect root
    root = _find_root_from_path(start_path)
    
    if root is None:
        raise PathDetectionError(
            f"Could not detect project root from path: {start_path}"
        )
    
    if expected_name and root.name != expected_name:
        raise PathDetectionError(
            f"Detected root '{root.name}' doesn't match expected name '{expected_name}'"
        )
    
    # cache the result
    with _cache_lock:
        _cached_root = root
        _cached_root_source = start_path
    
    return root


def clear_root_cache() -> None:
    """
    Clear the cached project root.
    
    Useful for testing or when project structure changes.
    """
    global _cached_root, _cached_root_source
    
    with _cache_lock:
        _cached_root = None
        _cached_root_source = None
