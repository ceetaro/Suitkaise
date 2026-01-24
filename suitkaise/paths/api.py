"""
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# import internals
try:
    from ._int import (
        # core class
        Skpath,
        
        # types
        AnyPath,
        
        # decorator
        autopath,
        
        # exceptions
        PathDetectionError,
        NotAFileError,
        
        # root management
        CustomRoot,
        set_custom_root,
        get_custom_root,
        clear_custom_root,
        clear_root_cache,
        detect_project_root,
        
        # caller utilities
        detect_caller_path,
        detect_current_dir,
        get_cwd_path,
        get_module_file_path,
        
        # project utilities
        get_project_paths as _get_project_paths,
        get_project_structure as _get_project_structure,
        get_formatted_project_tree as _get_formatted_project_tree,
        
        # id utils
        encode_path_id,
        decode_path_id,
        normalize_separators,
    )
except ImportError as e:
    raise ImportError(
        "Internal skpath module could not be imported. "
        f"Ensure that the internal module is available. Error: {e}"
    )


# project root functions

def get_project_root(expected_name: str | None = None) -> Skpath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        root = paths.get_project_root()
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import Skpath
        
        root = Skpath().root
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
        Skpath object pointing to the project root
        
    Raises:
        PathDetectionError: If project root detection fails or doesn't match expected_name
    """
    root_path = detect_project_root(expected_name=expected_name)
    return Skpath(root_path)



# caller path functions

def get_caller_path() -> Skpath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        caller = paths.get_caller_path()
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import Skpath
        
        caller = Skpath()
        ```
    ────────────────────────────────────────────────────────\n

    Get the file path of the caller.
    
    Returns:
        Skpath object pointing to the caller's file
        
    Raises:
        PathDetectionError: If caller detection fails
    """
    caller = detect_caller_path(skip_frames=1)
    return Skpath(caller)


def get_current_dir() -> Skpath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        current_dir = paths.get_current_dir()
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import Skpath
        
        current_dir = Skpath().parent
        ```
    ────────────────────────────────────────────────────────\n

    Get the directory containing the caller's file.
    
    Returns:
        Skpath object pointing to the caller's directory
    """
    caller = detect_caller_path(skip_frames=1)
    return Skpath(caller.parent)


def get_cwd() -> Skpath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        cwd = paths.get_cwd()
        ```
    ────────────────────────────────────────────────────────\n

    Get the current working directory.
    
    Returns:
        Skpath object pointing to the current working directory
    """
    return Skpath(get_cwd_path())


def get_module_path(obj: Any) -> Skpath | None:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        path = paths.get_module_path(SomeClass)
        ```
    ────────────────────────────────────────────────────────\n

    Get the file path of the module where an object is defined.
    
    Args:
        obj: Object to inspect. Can be:
            - A module object
            - A module name string
            - Any object with __module__ attribute
            
    Returns:
        Skpath object pointing to the module file, or None if not found
        
    Raises:
        ImportError: If obj is a module name string that cannot be imported
    """
    path = get_module_file_path(obj)
    if path is None:
        return None
    return Skpath(path)



# id functions

def get_id(
    path: str | Path | "Skpath",
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        path_id = paths.get_id("myproject/feature/file.txt")
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import Skpath
        
        path_id = Skpath("myproject/feature/file.txt").id
        ```
    ────────────────────────────────────────────────────────\n

    Get the reversible encoded ID for a path.
    
    The ID can be used to reconstruct the path: Skpath(path_id)
    
    Args:
        path: Path to generate ID for
        
    Returns:
        Base64url encoded ID string (reversible)
    """
    if isinstance(path, Skpath):
        return path.id
    return Skpath(path).id



# project path functions

def get_project_paths(
    root: str | Path | "Skpath" | None = None,
    exclude: str | Path | "Skpath" | list[str | Path | "Skpath"] | None = None,
    as_strings: bool = False,
    use_ignore_files: bool = True,
) -> list["Skpath"] | list[str]:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        # Get all paths in project
        paths = paths.get_project_paths()
        
        # Get paths as strings for memory efficiency
        paths = paths.get_project_paths(as_strings=True)
        
        # Exclude specific paths
        paths = paths.get_project_paths(exclude=["build", "dist"])
        
        # Use custom root
        paths = paths.get_project_paths(root="src")
        ```
    ────────────────────────────────────────────────────────\n

    Get all paths in the project.
    
    Automatically respects .*ignore files (.gitignore, .cursorignore, etc.).
    
    Args:
        root: Custom root directory (defaults to detected project root)
        exclude: Paths to exclude (single path or list)
        as_strings: Return string paths instead of Skpath objects
        use_ignore_files: Respect .*ignore files (default True)
        
    Returns:
        List of paths (Skpath or str based on as_strings)
        
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
    root: str | Path | "Skpath" | None = None,
    exclude: str | Path | "Skpath" | list[str | Path | "Skpath"] | None = None,
    use_ignore_files: bool = True,
) -> dict:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        structure = paths.get_project_structure()
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

    Get a hierarchical dict representation of the project structure.
    
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
    root: str | Path | "Skpath" | None = None,
    exclude: str | Path | "Skpath" | list[str | Path | "Skpath"] | None = None,
    use_ignore_files: bool = True,
    depth: int = 3,
    include_files: bool = True,
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths
        
        tree = paths.get_formatted_project_tree()
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


# path validation utilities

# chars that are invalid in filenames across common operating systems
_INVALID_FILENAME_CHARS = set('<>:"/\\|?*\0')
# additional chars that are problematic
_PROBLEMATIC_CHARS = set('\t\n\r')
# reserved names on Windows
_WINDOWS_RESERVED = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


def is_valid_filename(filename: str) -> bool:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import is_valid_filename
        
        is_valid_filename("my_file.txt")     # True
        is_valid_filename("file<name>.txt")  # False (contains <, >)
        is_valid_filename("CON")             # False (Windows reserved)
        is_valid_filename("")                # False (empty)
        ```
    ────────────────────────────────────────────────────────\n

    Check if a filename is valid across common operating systems.
    
    Checks for:
    - Empty or whitespace-only names
    - Invalid characters (<>:"/\\|?*\\0)
    - Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    - Names ending with space or period (problematic on Windows)
    
    Args:
        filename: The filename to validate (not a full path)
        
    Returns:
        True if the filename is valid, False otherwise
    """
    if not filename or not filename.strip():
        return False
    
    # check for invalid characters
    if any(char in _INVALID_FILENAME_CHARS for char in filename):
        return False
    
    # check for problematic characters
    if any(char in _PROBLEMATIC_CHARS for char in filename):
        return False
    
    # check Windows reserved names (case-insensitive)
    name_upper = filename.upper()
    base_name = name_upper.split('.')[0]  # CON.txt -> CON
    if base_name in _WINDOWS_RESERVED:
        return False
    
    # names ending with space or period are problematic on Windows
    if filename.endswith(' ') or filename.endswith('.'):
        return False
    
    return True


def streamline_path(
    path: str,
    max_length: int | None = None,
    replacement_char: str = "_",
    lowercase: bool = False,
    strip_whitespace: bool = True,
    allow_unicode: bool = True,
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import streamline_path
        
        # Basic cleanup
        streamline_path("My File<1>.txt")
        # "My File_1_.txt"
        
        # Lowercase and limit length
        streamline_path("My Long Filename.txt", max_length=10, lowercase=True)
        # "my long fi"
        
        # Replace invalid chars with custom character
        streamline_path("file:name.txt", replacement_char="-")
        # "file-name.txt"
        
        # ASCII only (no unicode)
        streamline_path("файл.txt", allow_unicode=False)
        # "____.txt"
        ```
    ────────────────────────────────────────────────────────\n

    Sanitize a path or filename by removing/replacing invalid characters.
    
    Args:
        path: The path or filename to sanitize
        max_length: Maximum length to truncate to (None = no limit)
        replacement_char: Character to replace invalid chars with (default "_")
        lowercase: Convert to lowercase (default False)
        strip_whitespace: Strip leading/trailing whitespace (default True)
        allow_unicode: Allow unicode characters (default True)
        
    Returns:
        Sanitized path string
    """
    result = path
    
    # strip whitespace first
    if strip_whitespace:
        result = result.strip()
    
    # replace invalid characters
    for char in _INVALID_FILENAME_CHARS:
        result = result.replace(char, replacement_char)
    
    # replace problematic characters
    for char in _PROBLEMATIC_CHARS:
        result = result.replace(char, replacement_char)
    
    # handle unicode if not allowed
    if not allow_unicode:
        # replace non-ASCII characters
        result = ''.join(
            char if ord(char) < 128 else replacement_char
            for char in result
        )
    
    # lowercase
    if lowercase:
        result = result.lower()
    
    # truncate to max length
    if max_length is not None and len(result) > max_length:
        result = result[:max_length]
    
    # clean up trailing spaces/periods that may have been introduced
    result = result.rstrip(' .')
    
    return result


# module exports

__all__ = [
    # core class
    "Skpath",
    
    # types
    "AnyPath",
    
    # decorator
    "autopath",
    
    # exceptions
    "PathDetectionError",
    "NotAFileError",
    
    # root management
    "CustomRoot",
    "set_custom_root",
    "get_custom_root",
    "clear_custom_root",
    "get_project_root",
    
    # path functions
    "get_caller_path",
    "get_current_dir",
    "get_cwd",
    "get_module_path",
    "get_id",
    
    # project functions
    "get_project_paths",
    "get_project_structure",
    "get_formatted_project_tree",
    
    # path utilities
    "is_valid_filename",
    "streamline_path",
]
