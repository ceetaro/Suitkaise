"""
SKPath API - Smart Path Operations for Suitkaise

This module provides enhanced path functionality with automatic project root
detection, cross-platform path normalization, and powerful path utilities.

Key Features:
- SKPath class: Enhanced Path with ap (absolute), np (normalized), and id properties
- @autopath decorator: Automatic type conversion for path parameters
- Project root detection: Automatic detection with custom root override
- Path utilities: Project-wide path listing, structure, and tree visualization

Philosophy: Make path operations intuitive while providing cross-platform compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Import internal implementations
try:
    from ._int import (
        # Core class
        SKPath,
        
        # Types
        AnyPath,
        
        # Decorator
        autopath,
        
        # Exceptions
        PathDetectionError,
        
        # Root management
        CustomRoot,
        set_custom_root,
        get_custom_root,
        clear_custom_root,
        clear_root_cache,
        detect_project_root,
        
        # Caller utilities
        detect_caller_path,
        detect_current_dir,
        get_cwd_path,
        get_module_file_path,
        
        # Project utilities
        get_project_paths as _get_project_paths,
        get_project_structure as _get_project_structure,
        get_formatted_project_tree as _get_formatted_project_tree,
        
        # ID utilities
        encode_path_id,
        decode_path_id,
        normalize_separators,
    )
except ImportError as e:
    raise ImportError(
        "Internal skpath module could not be imported. "
        f"Ensure that the internal module is available. Error: {e}"
    )


# ============================================================================
# Core Class (re-exported)
# ============================================================================

# SKPath is imported directly from _int


# ============================================================================
# Decorator (re-exported)
# ============================================================================

# autopath is imported directly from _int


# ============================================================================
# Project Root Functions
# ============================================================================

def get_project_root(expected_name: str | None = None) -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        root = skpath.get_project_root()
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.skpath import SKPath
        
        root = SKPath().root
        ```
    ────────────────────────────────────────────────────────\n

    Get the project root directory.
    
    Detection priority:
    1. Custom root (if set via set_custom_root())
    2. setup.sk file (Suitkaise marker)
    3. Standard project indicators (setup.py, pyproject.toml, etc.)
    
    Args:
        expected_name: If provided, detected root must have this name
        
    Returns:
        SKPath object pointing to the project root
        
    Raises:
        PathDetectionError: If project root detection fails or doesn't match expected_name
    """
    root_path = detect_project_root(expected_name=expected_name)
    return SKPath(root_path)


# ============================================================================
# Caller Path Functions
# ============================================================================

def get_caller_path() -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        caller = skpath.get_caller_path()
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.skpath import SKPath
        
        caller = SKPath()
        ```
    ────────────────────────────────────────────────────────\n

    Get the file path of the caller.
    
    Returns:
        SKPath object pointing to the caller's file
        
    Raises:
        PathDetectionError: If caller detection fails
    """
    caller = detect_caller_path(skip_frames=1)
    return SKPath(caller)


def get_current_dir() -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        current_dir = skpath.get_current_dir()
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.skpath import SKPath
        
        current_dir = SKPath().parent
        ```
    ────────────────────────────────────────────────────────\n

    Get the directory containing the caller's file.
    
    Returns:
        SKPath object pointing to the caller's directory
    """
    caller = detect_caller_path(skip_frames=1)
    return SKPath(caller.parent)


def get_cwd() -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        cwd = skpath.get_cwd()
        ```
    ────────────────────────────────────────────────────────\n

    Get the current working directory.
    
    Returns:
        SKPath object pointing to the current working directory
    """
    return SKPath(get_cwd_path())


def get_module_path(obj: Any) -> SKPath | None:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        path = skpath.get_module_path(SomeClass)
        ```
    ────────────────────────────────────────────────────────\n

    Get the file path of the module where an object is defined.
    
    Args:
        obj: Object to inspect. Can be:
            - A module object
            - A module name string
            - Any object with __module__ attribute
            
    Returns:
        SKPath object pointing to the module file, or None if not found
        
    Raises:
        ImportError: If obj is a module name string that cannot be imported
    """
    path = get_module_file_path(obj)
    if path is None:
        return None
    return SKPath(path)


# ============================================================================
# ID Functions
# ============================================================================

def get_id(
    path: str | Path | "SKPath",
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        path_id = skpath.get_id("myproject/feature/file.txt")
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.skpath import SKPath
        
        path_id = SKPath("myproject/feature/file.txt").id
        ```
    ────────────────────────────────────────────────────────\n

    Get the reversible encoded ID for a path.
    
    The ID can be used to reconstruct the path: SKPath(path_id)
    
    Args:
        path: Path to generate ID for
        
    Returns:
        Base64url encoded ID string (reversible)
    """
    if isinstance(path, SKPath):
        return path.id
    return SKPath(path).id


# ============================================================================
# Project Path Functions
# ============================================================================

def get_project_paths(
    root: str | Path | "SKPath" | None = None,
    exclude: str | Path | "SKPath" | list[str | Path | "SKPath"] | None = None,
    as_strings: bool = False,
    use_ignore_files: bool = True,
) -> list["SKPath"] | list[str]:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        # Get all paths in project
        paths = skpath.get_project_paths()
        
        # Get paths as strings for memory efficiency
        paths = skpath.get_project_paths(as_strings=True)
        
        # Exclude specific paths
        paths = skpath.get_project_paths(exclude=["build", "dist"])
        
        # Use custom root
        paths = skpath.get_project_paths(root="src")
        ```
    ────────────────────────────────────────────────────────\n

    Get all paths in the project.
    
    Automatically respects .*ignore files (.gitignore, .cursorignore, etc.).
    
    Args:
        root: Custom root directory (defaults to detected project root)
        exclude: Paths to exclude (single path or list)
        as_strings: Return string paths instead of SKPath objects
        use_ignore_files: Respect .*ignore files (default True)
        
    Returns:
        List of paths (SKPath or str based on as_strings)
        
    Raises:
        PathDetectionError: If project root cannot be detected
    """
    return _get_project_paths(
        root=root,
        exclude=exclude,
        as_strings=as_strings,
        use_ignore_files=use_ignore_files,
    )


def get_project_structure(
    root: str | Path | "SKPath" | None = None,
    exclude: str | Path | "SKPath" | list[str | Path | "SKPath"] | None = None,
    use_ignore_files: bool = True,
) -> dict:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        structure = skpath.get_project_structure()
        # Returns:
        # {
        #     "myproject": {
        #         "src": {
        #             "main.py": {},
        #             "utils.py": {}
        #         },
        #         "tests": {...}
        #     }
        # }
        ```
    ────────────────────────────────────────────────────────\n

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
    return _get_project_structure(
        root=root,
        exclude=exclude,
        use_ignore_files=use_ignore_files,
    )


def get_formatted_project_tree(
    root: str | Path | "SKPath" | None = None,
    exclude: str | Path | "SKPath" | list[str | Path | "SKPath"] | None = None,
    use_ignore_files: bool = True,
    depth: int = 3,
    include_files: bool = True,
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        tree = skpath.get_formatted_project_tree()
        print(tree)
        
        # Output:
        # myproject/
        # ├── src/
        # │   ├── main.py
        # │   └── utils/
        # └── tests/
        #     └── test_main.py
        ```
    ────────────────────────────────────────────────────────\n

    Get a formatted tree string for the project structure.
    
    Uses │, ├─, and └─ characters to create a visual hierarchy.
    
    Args:
        root: Custom root directory (defaults to detected project root)
        exclude: Paths to exclude
        use_ignore_files: Respect .*ignore files (default True)
        depth: Maximum depth to display (default 3)
        include_files: Include files in the tree (default True)
        
    Returns:
        Formatted tree string
        
    Raises:
        PathDetectionError: If project root cannot be detected
    """
    return _get_formatted_project_tree(
        root=root,
        exclude=exclude,
        use_ignore_files=use_ignore_files,
        depth=depth,
        include_files=include_files,
    )


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Core class
    "SKPath",
    
    # Types
    "AnyPath",
    
    # Decorator
    "autopath",
    
    # Exceptions
    "PathDetectionError",
    
    # Root management
    "CustomRoot",
    "set_custom_root",
    "get_custom_root",
    "clear_custom_root",
    "get_project_root",
    
    # Path functions
    "get_caller_path",
    "get_current_dir",
    "get_cwd",
    "get_module_path",
    "get_id",
    
    # Project functions
    "get_project_paths",
    "get_project_structure",
    "get_formatted_project_tree",
]
