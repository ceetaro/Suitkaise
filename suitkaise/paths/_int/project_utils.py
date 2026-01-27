"""
Skpath Project Utilities

Utilities for working with project-wide paths:
- get_project_paths: List all paths in project
- get_project_structure: Hierarchical dict representation
- get_formatted_project_tree: Visual tree string
"""

from __future__ import annotations

import fnmatch
import os
import threading
from pathlib import Path
from typing import Any

from .exceptions import PathDetectionError
from .id_utils import normalize_separators
from .root_detection import detect_project_root
from .skpath import Skpath

# thread-safe lock
_project_lock = threading.RLock()


def _parse_ignore_file(ignore_path: Path) -> list[str]:
    """
    Parse an ignore file (like .gitignore) and return patterns.
    
    Args:
        ignore_path: Path to the ignore file
        
    Returns:
        List of ignore patterns
    """
    patterns: list[str] = []
    
    try:
        with open(ignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
    except (IOError, OSError, UnicodeDecodeError):
        pass
    
    return patterns


def _collect_ignore_patterns(root: Path) -> list[str]:
    """
    Collect all ignore patterns from .*ignore files in root.
    
    Looks for: .gitignore, .cursorignore, .dockerignore, etc.
    
    Args:
        root: Project root directory
        
    Returns:
        Combined list of all ignore patterns
    """
    all_patterns: list[str] = []
    
    try:
        for item in root.iterdir():
            if item.is_file() and item.name.endswith("ignore"):
                patterns = _parse_ignore_file(item)
                all_patterns.extend(patterns)
    except (PermissionError, OSError):
        pass
    
    return all_patterns


def _matches_any_pattern(path_str: str, patterns: list[str]) -> bool:
    """
    Check if a path matches any of the ignore patterns.
    
    Args:
        path_str: Path string (relative to root)
        patterns: List of ignore patterns
        
    Returns:
        True if path should be ignored
    """
    # normalize to forward slashes for matching
    path_str = normalize_separators(path_str)
    parts = path_str.split("/")
    
    for pattern in patterns:
        # handle negation patterns (starting with !)
        if pattern.startswith("!"):
            continue  # skip negation for now (would need more complex logic)
        
        # handle directory patterns (ending with /)
        is_dir_pattern = pattern.endswith("/")
        if is_dir_pattern:
            pattern = pattern[:-1]
        
        # handle patterns with /
        if "/" in pattern:
            # pattern is relative to root
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(path_str, pattern + "/*"):
                return True
        else:
            # pattern matches any path component
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
            # also try matching the full path
            if fnmatch.fnmatch(path_str, pattern):
                return True
            if fnmatch.fnmatch(path_str, "*/" + pattern):
                return True
            if fnmatch.fnmatch(path_str, "*/" + pattern + "/*"):
                return True
    
    return False


def get_project_paths(
    root: str | Path | Skpath | None = None,
    exclude: str | Path | Skpath | list[str | Path | Skpath] | None = None,
    as_strings: bool = False,
    use_ignore_files: bool = True,
) -> list[Skpath] | list[str]:
    """
    Get all paths in the project.
    
    Args:
        root: Custom root directory (defaults to detected project root)
        exclude: Paths to exclude (single path or list of paths)
        as_strings: Return string paths instead of Skpath objects
        use_ignore_files: Respect .*ignore files (default True)
        
    Returns:
        List of paths (Skpath or str based on as_strings)
        
    Raises:
        PathDetectionError: If project root cannot be detected
    """
    # resolve root
    if root is None:
        root_path = detect_project_root()
    elif isinstance(root, Skpath):
        root_path = Path(root.ap)
    elif isinstance(root, str):
        root_path = Path(root).resolve()
    else:
        root_path = root.resolve()
    
    if not root_path.exists():
        raise PathDetectionError(f"Root path does not exist: {root_path}")
    
    if not root_path.is_dir():
        raise PathDetectionError(f"Root path is not a directory: {root_path}")
    
    # build exclude set
    exclude_set: set[str] = set()
    if exclude is not None:
        if not isinstance(exclude, list):
            exclude = [exclude]
        for ex in exclude:
            if isinstance(ex, Skpath):
                exclude_set.add(normalize_separators(ex.ap))
            elif isinstance(ex, Path):
                exclude_set.add(normalize_separators(str(ex.resolve())))
            else:
                exclude_set.add(normalize_separators(str(Path(ex).resolve())))
    
    # get ignore patterns
    ignore_patterns: list[str] = []
    if use_ignore_files:
        ignore_patterns = _collect_ignore_patterns(root_path)
    
    # collect paths
    result_paths: list[Any] = []

    def add_result(path: Path) -> None:
        abs_path = normalize_separators(str(path))
        if as_strings:
            result_paths.append(abs_path)
        else:
            result_paths.append(Skpath._from_path(path, root=root_path))

    def should_skip_dir(dir_path: Path) -> bool:
        if not use_ignore_files:
            return False
        try:
            rel_dir = normalize_separators(str(dir_path.relative_to(root_path)))
        except ValueError:
            return False
        if not rel_dir:
            return False
        return _matches_any_pattern(rel_dir, ignore_patterns)

    def should_skip_entry(path: Path) -> bool:
        abs_path = normalize_separators(str(path))
        if abs_path in exclude_set:
            return True
        if not use_ignore_files:
            return False
        try:
            rel_path = normalize_separators(str(path.relative_to(root_path)))
        except ValueError:
            return False
        return _matches_any_pattern(rel_path, ignore_patterns)

    for dirpath, dirnames, filenames in os.walk(root_path):
        dir_path = Path(dirpath)
        if should_skip_dir(dir_path):
            dirnames.clear()
            continue
        if use_ignore_files:
            dirnames[:] = [
                d for d in dirnames
                if not should_skip_entry(dir_path / d)
            ]
        for filename in filenames:
            file_path = dir_path / filename
            if should_skip_entry(file_path):
                continue
            add_result(file_path)
        for dirname in dirnames:
            subdir_path = dir_path / dirname
            if should_skip_entry(subdir_path):
                continue
            add_result(subdir_path)

    return result_paths


def get_project_structure(
    root: str | Path | Skpath | None = None,
    exclude: str | Path | Skpath | list[str | Path | Skpath] | None = None,
    use_ignore_files: bool = True,
) -> dict[str, Any]:
    """
    Get hierarchical dict representation of project structure.
    
    Args:
        root: Custom root directory (defaults to detected project root)
        exclude: Paths to exclude
        use_ignore_files: Respect .*ignore files (default True)
        
    Returns:
        Nested dictionary representing the project structure
        
    Raises:
        PathDetectionError: If project root cannot be detected
    """
    # resolve root
    if root is None:
        root_path = detect_project_root()
    elif isinstance(root, Skpath):
        root_path = Path(root.ap)
    elif isinstance(root, str):
        root_path = Path(root).resolve()
    else:
        root_path = root.resolve()
    
    # get all paths
    paths = get_project_paths(
        root=root_path,
        exclude=exclude,
        as_strings=True,
        use_ignore_files=use_ignore_files,
    )
    
    # build structure
    structure: dict[str, Any] = {}
    root_name = root_path.name
    structure[root_name] = {}
    
    for path_str in paths:
        path = Path(path_str)
        try:
            rel_path = path.relative_to(root_path)
        except ValueError:
            continue
        
        parts = rel_path.parts
        current = structure[root_name]
        
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    
    return structure


def get_formatted_project_tree(
    root: str | Path | Skpath | None = None,
    exclude: str | Path | Skpath | list[str | Path | Skpath] | None = None,
    use_ignore_files: bool = True,
    depth: int | None = None,
    include_files: bool = True,
) -> str:
    """
    Get a formatted tree string for the project structure.
    
    Uses │, ├─, and └─ characters to create a visual hierarchy.
    
    Args:
        root: Custom root directory (defaults to detected project root)
        exclude: Paths to exclude
        use_ignore_files: Respect .*ignore files (default True)
        depth: Maximum depth to display (default None) (None = no limit)
        include_files: Include files in the tree (default True)
        
    Returns:
        Formatted tree string
        
    Raises:
        PathDetectionError: If project root cannot be detected
    """
    # resolve root
    if root is None:
        root_path = detect_project_root()
    elif isinstance(root, Skpath):
        root_path = Path(root.ap)
    elif isinstance(root, str):
        root_path = Path(root).resolve()
    else:
        root_path = root.resolve()
    
    # build exclude set
    exclude_set: set[str] = set()
    if exclude is not None:
        if not isinstance(exclude, list):
            exclude = [exclude]
        for ex in exclude:
            if isinstance(ex, Skpath):
                exclude_set.add(normalize_separators(ex.ap))
            elif isinstance(ex, Path):
                exclude_set.add(normalize_separators(str(ex.resolve())))
            else:
                exclude_set.add(normalize_separators(str(Path(ex).resolve())))
    
    # get ignore patterns
    ignore_patterns: list[str] = []
    if use_ignore_files:
        ignore_patterns = _collect_ignore_patterns(root_path)
    
    # build tree
    lines: list[str] = [f"{root_path.name}/"]

    def should_skip_entry(path: Path) -> bool:
        abs_path = normalize_separators(str(path))
        if abs_path in exclude_set:
            return True
        if not use_ignore_files:
            return False
        try:
            rel_path = normalize_separators(str(path.relative_to(root_path)))
        except ValueError:
            return False
        return _matches_any_pattern(rel_path, ignore_patterns)

    def list_filtered(dir_path: Path) -> list[Path]:
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except (PermissionError, OSError):
            return []
        filtered_items: list[Path] = []
        for item in items:
            if should_skip_entry(item):
                continue
            if not include_files and item.is_file():
                continue
            filtered_items.append(item)
        return filtered_items

    def _format_tree(
        dir_path: Path,
        prefix: str,
        current_depth: int,
    ) -> None:
        if depth is not None and current_depth > depth:
            return
        items = list_filtered(dir_path)
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                _format_tree(item, new_prefix, current_depth + 1)
            else:
                lines.append(f"{prefix}{connector}{item.name}")
    
    _format_tree(root_path, "", 1)
    
    return "\n".join(lines)
