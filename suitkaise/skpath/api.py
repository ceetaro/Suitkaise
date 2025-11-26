"""
`skpath` API - Smart Path Operations

This module provides the user-facing API for intelligent path handling with dual-path
architecture, automatic project root detection, and magical caller detection.

Key Features:
- `SKPath` objects with absolute and normalized paths
- Zero-configuration initialization with automatic caller detection
- Project root detection with sophisticated indicators
- AutoPath decorator for automatic path conversion
- Complete project structure analysis
- Path utilities with cross-module compatibility
- Smart ambiguous path resolution with helpful error messages

Best Practices for Path Organization:
1. Use relative paths for clarity: `SKPath('feature1/api.py')` vs `SKPath('feature2/api.py')`
2. Use unique filenames when possible: `SKPath('feature1_api.py')` vs `SKPath('feature2_api.py')`
3. Organize files in descriptive directory structures
4. Avoid bare filenames (like `'config.py'`) when multiple files with the same name exist

Exception Handling:
- `MultiplePathsError`: Raised when ambiguous filenames are encountered
- Provides specific recommendations for resolving path ambiguity
"""

import os
import inspect
import fnmatch
from pathlib import Path
from typing import Dict, List, Set, Optional, Union, Tuple, Any, Callable, Sequence, Type
from functools import wraps


# Import internal path operations with fallback
try:
    from ._int.path_ops import (
        _get_non_sk_caller_file_path,
        _get_project_root,
        _get_cwd,
        _get_current_dir,
        _get_module_file_path,
        _equal_paths,
        _path_id,
        _get_all_project_paths,
        _get_project_structure,
        _get_formatted_project_tree,
        _force_project_root,
        _clear_forced_project_root,
        _get_forced_project_root,
        DetectionError,
        MultiplePathsError
    )
except ImportError:
    raise ImportError(
        "Internal path operations could not be imported. "
        "Ensure that the internal path operations module is available."
    )

class SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.skpath import SKPath
        
        # no args automatically gets caller file path
        path = SKPath()

        # arg creates SKPath from string (Path objects work too)
        path = SKPath("a/path/goes/here")
        ```
    ────────────────────────────────────────────────────────\n

    A smart path object that maintains both an absolute path and 
    a path normalized (relative) to the project root.
    
    `SKPath` is a class with properties that expose two path views:
    
    - `ap`: Absolute filesystem path (string), with separators normalized (all `/`)
    - `np`: Normalized path including your project root name (string). If the file is
      outside any detected project root, `np` is the empty string `''`.
    
    Key Behavioral Notes:
    - Each `SKPath` instance captures its project root at creation time
    - Calling `force_project_root()` affects only NEW instances
    - The `np` property returns the project-root-prefixed path (e.g., `MyProj/src/app.py`)
      when inside the project; it returns `''` (empty string) when outside
    - All path operations remain consistent with the instance's original root
    
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.skpath import SKPath
        
        # no args automatically gets caller file path
        path = SKPath()
        
        abspath = path.ap
        normpath = path.np
        
        # or...
        abspath = SKPath().ap
        normpath = SKPath().np
        
        # example ap: /Users/johndoe/Documents/MyProj/src/main.py
        # example np: MyProj/src/main.py (auto-detected MyProj as root)
        # example np: '' (empty string) if the path is outside the project root
        ```
    ────────────────────────────────────────────────────────\n

        ```python
        # Available Properties and Methods:
        from suitkaise.skpath import SKPath
        
        path = SKPath("a/path/goes/here")
        
        # get the absolute path
        abs_path = path.ap
        
        # get the normalized path
        norm_path = path.np
        
        # get the root
        root = path.root
        
        # get the final component of the path
        file_name = path.name
        
        # get the parent directory of the final component
        parent_dir = path.parent
        
        # get the final component without the suffix
        file_stem = path.stem
        
        # get the suffix
        file_suffix = path.suffix
        
        # get all suffixes
        file_suffixes = path.suffixes
        
        # get the path parts as a tuple
        path_parts = path.parts
        
        # check if the path exists
        path_exists = path.exists
        
        # check if the path is a file
        is_file = path.is_file
        
        # check if the path is a directory
        is_dir = path.is_dir
        
        # check if the path is absolute
        is_absolute = path.is_absolute
        
        # check if the path is a symlink
        is_symlink = path.is_symlink
        
        # get the stat information for the path
        stat = path.stat
        
        # get the lstat information for the path
        lstat = path.lstat
        
        # iterate over the directory contents
        for item in path.iterdir:
            print(item)
        
        # get the dict view of the path
        path_dict = path.as_dict
        
        # get the path ID (md5 hash of the path) (32 chars)
        path_id = path.id
        
        # get the short path ID (8 chars)
        path_id_short = path.id_short
        
        # find all paths matching a pattern
        matching_paths = path.glob("*.txt")
        
        # recursively find all paths matching a pattern
        matching_paths = path.rglob("*.txt")
        
        # get the relative path to another path
        relative_path = path.relative_to(other_path)
        
        # get the path with a different name
        new_path = path.with_new_name("new_name.txt")
        
        # get the path with only a different stem
        new_path = path.with_new_stem("new_stem")
        
        # get the path with only a different suffix
        new_path = path.with_new_suffix(".txt")
        
        # get the path as a string (uses absolute path for standard library compatibility)
        path_str = str(path)
        
        # get the path as a repr string
        path_repr = repr(path)
        
        # check if the path is equal to another path (can also use `equalpaths`)
        # works with any combination of strings, Path objects, and SKPath objects
        is_equal = path == other_path
        
        # get a hash of the path
        path_hash = hash(path)
        
        # supports truediv for path joining (SKPath / "other/path")
        
        # supports os.fspath() for things like `with open(SKPath) as f:`
        ```
    ────────────────────────────────────────────────────────
    """
    
    def __init__(self, path: Optional[Union[str, Path, 'SKPath']] = None, 
                 project_root: Optional[Union[str, Path, 'SKPath']] = None):
        """
        Initialize an `SKPath` object with automatic caller detection.
        
        Args:
            `path`: The path to wrap (if `None`, auto-detects caller's file)
            `project_root`: Project root path (auto-detected if `None`)
            
        Raises:
            `DetectionError`: If `path` is `None` and caller detection fails
            `FileNotFoundError`: If provided `path` doesn't exist under project root
            `MultiplePathsError`: If ambiguous filename matches multiple files
        """
        # Handle zero-argument magic initialization
        if path is None:
            try:
                caller_file = _get_non_sk_caller_file_path()
                if caller_file is None:
                    raise DetectionError("caller file path", "SKPath initialization")
            except RuntimeError:
                raise DetectionError("caller file path", "SKPath initialization")
            self._absolute_path = caller_file
            self._original_path_input = None
        else:
            # Store original path input for reference and debugging
            self._original_path_input = path

            if isinstance(path, SKPath):
                path = str(path)
            
            # Handle path resolution with project root awareness
            path_obj = Path(path)
            if not path_obj.is_absolute():
                # For relative paths, we need to handle them intelligently
                # First, get project root to resolve relative to it
                temp_resolved = path_obj.resolve()  # Temporary resolution from CWD
                temp_project_root = project_root
                if temp_project_root is None:
                    temp_project_root = _get_project_root(temp_resolved.parent if temp_resolved.is_file() else temp_resolved)
                else:
                    temp_project_root = Path(temp_project_root).resolve()
                
                # Try to resolve relative path within project root
                if temp_project_root:
                    self._absolute_path = self._resolve_relative_path(path_obj, temp_project_root)
                else:
                    # Fallback to current directory resolution if no project root found
                    self._absolute_path = path_obj.resolve()
            else:
                self._absolute_path = path_obj.resolve()
        
        # Auto-detect or use provided project root
        if project_root is None:
            self._project_root = _get_project_root(self._absolute_path.parent if self._absolute_path.is_file() else self._absolute_path)
        else:
            self._project_root = Path(project_root).resolve()
        
        # Calculate normalized path
        self._normalized_path = self._calculate_normalized_path()

    def _resolve_relative_path(self, path_obj: Path, project_root: Path) -> Path:
        """
        Resolve a relative path intelligently within the project root.
        
        This method handles ambiguous relative paths by:
        1. First trying direct resolution from project root
        2. If that fails, searching for the file under project root
        3. Raising clear errors for ambiguous cases
        
        Args:
            `path_obj`: The relative `Path` object to resolve
            `project_root`: The project root to resolve relative to
            
        Returns:
            Absolute `Path` object
            
        Raises:
            `FileNotFoundError`: If `path` doesn't exist under project root
            `ValueError`: If multiple matches found (ambiguous path)
        """
        # Strategy 1: Try direct resolution from project root
        direct_path = project_root / path_obj
        if direct_path.exists():
            return direct_path.resolve()
        
        # Strategy 2: If direct resolution fails, search under project root
        # This handles cases like SKPath("data.txt") when data.txt could be in multiple subdirs
        filename = path_obj.name
        
        # Only search if it's just a filename (no directory components)
        if len(path_obj.parts) == 1:
            matches = []
            try:
                # Search for file under project root
                for match in project_root.rglob(filename):
                    # Only include files, not directories
                    if match.is_file():
                        matches.append(match)
                
                if len(matches) == 0:
                    # No matches found - file doesn't exist under project root
                    raise FileNotFoundError(
                        f"Path '{path_obj}' not found under project root '{project_root}'. "
                        f"Make sure the file exists or provide a more specific path."
                    )
                elif len(matches) == 1:
                    # Exactly one match - perfect!
                    return matches[0].resolve()
                else:
                    # Multiple matches - ambiguous!
                    raise MultiplePathsError(filename, matches, project_root)
            except (OSError, PermissionError):
                # Fall back to original behavior if we can't search
                return path_obj.resolve()
        
        # For paths with directory components, fall back to original behavior
        return path_obj.resolve()

    def _calculate_normalized_path(self) -> Optional[str]:
        """
        Calculate the normalized path relative to project root.
        
        Returns:
            `str`: Relative path from project root, or `None` if path is outside project root
        """
        if self._project_root is None:
            # If we can't find project root, no normalized path available
            return ''
        
        try:
            # Build root-prefixed normalized path
            root_name = self._project_root.name
            try:
                relative_path = self._absolute_path.relative_to(self._project_root)
                rel_str = str(relative_path).replace('\\', '/')
                if rel_str == '.':
                    return root_name
                return f"{root_name}/{rel_str}"
            except ValueError:
                # Path is not under project root - return empty string
                return ''
        except Exception:
            # Be conservative on unexpected errors
            return ''
        
    @property
    def ap(self) -> str:
        """Absolute path - the full system path."""
        # Normalize separators to forward slashes for cross-OS consistency
        return str(self._absolute_path).replace('\\', '/')
    
    @property
    def np(self) -> Optional[str]:
        """
        Normalized path - path relative to project root.
        
        Returns:
            `str`: Project-root-prefixed path (e.g., `'MyProj/src/main.py'`)
            `''`: Empty string if path is outside the project root or root unknown
        """
        return self._normalized_path
    
    @property
    def root(self) -> Optional['SKPath']:
        """
        ────────────────────────────────────────────────────────
            ```python
            skpath1 = SKPath("file.txt")  # Uses current project root

            force_project_root("/new/root")

            skpath2 = SKPath("file.txt")  # Uses new project root

            skpath1.root != skpath2.root  # True - different roots
            ```
        ────────────────────────────────────────────────────────\n

        The project root directory for this `SKPath` instance.
        
        Important: Each `SKPath` instance captures the project root at creation time.
        If `force_project_root()` is called after creating an `SKPath`, 
        existing instances will continue to use their original project root.

        Returns:
            `SKPath`: The project root directory, or `None` if no root detected
        """
        if self._project_root is None:
            return None
        return SKPath(self._project_root)
    
    @property
    def path_object(self) -> Path:
        """Get the underlying Path object for advanced operations."""
        return self._absolute_path
    
    @property
    def original_str(self) -> Optional[str]:
        """Get the original path input that was provided to `SKPath` constructor."""
        return None if self._original_path_input is None else str(self._original_path_input)

    @property
    def original_repr(self) -> Optional[str]:
        """Get the representation of the original path input that was provided to `SKPath` constructor."""
        return repr(self._original_path_input) if self._original_path_input is not None else None
    
    @property
    def name(self) -> str:
        """The final component of the path."""
        return self._absolute_path.name
    
    @property
    def stem(self) -> str:
        """The final component without suffix."""
        return self._absolute_path.stem
    
    @property
    def suffix(self) -> str:
        """The file extension. If multiple, only the last one."""
        return self._absolute_path.suffix
    
    @property
    def suffixes(self) -> List[str]:
        """
        ────────────────────────────────────────────────────────
            ```python
            path = SKPath("archive.tar.gz")

            path.suffixes # result: ['.tar', '.gz']

            path.suffix  # Only the last one: '.gz'
            ```
        ────────────────────────────────────────────────────────\n

        All suffixes of the path as a list.
        
        Useful for files with multiple extensions like `'file.tar.gz'`.
        
        Returns:
            List of all suffixes in order (e.g., [`'.tar'`, `'.gz'`])
        """
        return self._absolute_path.suffixes
    
    @property
    def parent(self) -> 'SKPath':
        """The parent directory as an `SKPath`."""
        return SKPath(self._absolute_path.parent, self._project_root)
    
    @property
    def parents(self) -> List['SKPath']:
        """All parent directories as `SKPath` objects."""
        return [SKPath(parent, self._project_root) for parent in self._absolute_path.parents]
    
    @property
    def parts(self) -> Tuple[str, ...]:
        """The path components as a tuple."""
        return self._absolute_path.parts
    
    @property
    def exists(self) -> bool:
        """Check if the path exists."""
        return self._absolute_path.exists()
    
    @property
    def is_file(self) -> bool:
        """Check if the path is a file."""
        return self._absolute_path.is_file()
    
    @property
    def is_dir(self) -> bool:
        """Check if the path is a directory."""
        return self._absolute_path.is_dir()
    
    @property
    def is_absolute(self) -> bool:
        """Check if the path is absolute."""
        return self._absolute_path.is_absolute()
    
    @property
    def is_symlink(self) -> bool:
        """Check if the path is a symbolic link."""
        return self._absolute_path.is_symlink()
    
    @property
    def stat(self):
        """Get stat information for the path."""
        return self._absolute_path.stat()
    
    @property
    def lstat(self):
        """Get lstat information for the path."""
        return self._absolute_path.lstat()
    
    @property
    def iterdir(self) -> List['SKPath']:
        """Iterate over directory contents as `SKPath` objects."""
        if not self.is_dir:
            raise NotADirectoryError(f"{self} is not a directory")
        return [SKPath(item, self._project_root) for item in self._absolute_path.iterdir()]

    @property
    def as_dict(self) -> Dict[str, Optional[str]]:
        """Return the dual-path structure as a dictionary."""
        return {
            "ap": self.ap,
            "np": self.np
        }

    @property
    def id(self) -> str:
        """
        Return the path ID based on absolute path.
        
        Each unique absolute path gets a unique ID, ensuring that multiple
        `SKPath` objects pointing to the same file will have the same ID,
        regardless of how they were created (relative vs absolute input).
        
        Returns:
            32-character MD5-based path identifier
        """
        return path_id(self)

    @property
    def id_short(self) -> str:
        """
        Return the short path ID based on absolute path.
        
        Shortened version of the full path ID for display purposes.
        
        Returns:
            8-character shortened path identifier
        """
        return path_id_short(self)
    
    def glob(self, pattern: str) -> List['SKPath']:
        """Find all paths matching the pattern."""
        return [SKPath(match, self._project_root) for match in self._absolute_path.glob(pattern)]
    
    def rglob(self, pattern: str) -> List['SKPath']:
        """Recursively find all paths matching the pattern."""
        return [SKPath(match, self._project_root) for match in self._absolute_path.rglob(pattern)]
    
    def relative_to(self, other: Union[str, Path, 'SKPath']) -> 'SKPath':
        """Return relative path to another path."""
        other_sp = SKPath(other)
        try:
            rel = self._absolute_path.relative_to(Path(other_sp))
        except Exception as e:
            raise ValueError(f"Path {self._absolute_path} is not relative to {Path(other_sp)}: {e}")
        return SKPath(rel, self._project_root)
    
    def with_new_name(self, name: str) -> 'SKPath':
        """Return a new `SKPath` with different name."""
        return SKPath(self._absolute_path.with_name(name), self._project_root)
    
    def with_new_stem(self, stem: str) -> 'SKPath':
        """Return a new `SKPath` with different stem."""
        return SKPath(self._absolute_path.with_stem(stem), self._project_root)
    
    def with_new_suffix(self, suffix: str) -> 'SKPath':
        """Return a new `SKPath` with different suffix."""
        return SKPath(self._absolute_path.with_suffix(suffix), self._project_root)
    
    def __str__(self) -> str:
        """String conversion returns absolute path for compatibility."""
        return self.ap

    def __repr__(self) -> str:
        """Detailed representation showing both paths and original input."""
        if self._original_path_input:
            return f"SKPath(input='{str(self._original_path_input)}', ap='{self.ap}', np='{self.np}')"
        else:
            return f"SKPath(ap='{self.ap}', np='{self.np}')"
    
    def __eq__(self, other) -> bool:
        """Compare `SKPath` objects based on their absolute paths."""
        return equalpaths(self, other)
    
    def __hash__(self) -> int:
        """Hash based on absolute path for use in `sets`/`dicts`."""
        return hash(self._absolute_path)
    
    def __truediv__(self, other) -> 'SKPath':
        """Support path joining with `/` operator."""
        return SKPath(self._absolute_path / other, self._project_root)
    
    def __fspath__(self) -> str:
        """Support for `os.fspath()`."""
        return str(self._absolute_path)
    

# Type alias for valid path objects (which are strings, Path objects, or SKPath objects)
AnyPath = Union[str, Path, SKPath]

# ============================================================================
# Convenience Functions - Direct access to path operations
# ============================================================================

def get_project_root(expected_name: Optional[str] = None) -> Optional[SKPath]:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        # get the project root (expects python project necessities)
        root = skpath.get_project_root()
        ```
    ────────────────────────────────────────────────────────\n
    Automatic project root detection with sophisticated indicator-based algorithm.
    
    Uses sophisticated indicator-based detection requiring necessary files
    (`LICENSE`, `README`, `requirements`) and scoring based on project structure.
    Developers who set up a project correctly should find that this automatically
    detects their project root without any hassle.
    
    Args:
        `expected_name`: Expected project name (returns `None` if name doesn't match)
        
    Returns:
        `SKPath` object pointing to project root, or `None` if not found
        
    Raises:
        `DetectionError`: If project root detection fails completely

    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        # get the project root (expects python project necessities)
        root = skpath.get_project_root()
        
        # optionally, add intended name of project root you'd like to find
        # doing this will return None unless a valid root WITH this name is found
        root = skpath.get_project_root("Suitkaise")
        
        # or get root like this
        root = skpath.SKPath().root
        ```
    ────────────────────────────────────────────────────────\n

    Required Project Files:\n

        For detection to work correctly, *at least one of each of these is required*
        - License file: `LICENSE`, `LICENSE.txt`, `license`, etc.
        - README file: `README`, `README.md`, `readme.txt`, etc.
        - Requirements file: `requirements.txt`, `requirements.pip`, etc.
    
    Strong Project Indicators:\n

        These files significantly increase confidence:
        - Python setup files: `setup.py`, `setup.cfg`, `pyproject.toml`
        - Configuration files: `tox.ini`, `.gitignore`, `.dockerignore`
        - Environment files: `.env`, `.env.local`, etc.
        - Package initializer: `__init__.py`
    """
    result = _get_project_root(expected_name=expected_name)
    if result is None:
        if expected_name is None:
            raise DetectionError("project root", "get_project_root function call")
        return None
    return SKPath(result)

def get_caller_path() -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        caller = skpath.get_caller_path()

        # equivalent to caller = SKPath()
        ```
    ────────────────────────────────────────────────────────\n

    Know where you were called from with automatic caller detection.
    
    Uses caller detection to find the user's file, ignoring any
    internal `suitkaise` library calls in the process. Provides error handling,
    project context, and extended functionality for the resulting path object.
    
    Returns:
        `SKPath` object for the calling file
        
    Raises:
        `DetectionError`: If caller detection fails

    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Error logging that shows where problems occur

        def log_error(message):

            caller = skpath.get_caller_path()

            # log the error with the caller's file name
            error_log = caller.root / "logs" / f"error_{caller.stem}.log"
            with open(error_log, "a") as f:
                f.write(f"{caller.np}: {message}\\n")
        ```
    ────────────────────────────────────────────────────────
    """
    try:
        caller_file = _get_non_sk_caller_file_path()
        if caller_file is None:
            raise DetectionError("caller file path", "get_caller_path function call")
    except RuntimeError:
        raise DetectionError("caller file path", "get_caller_path function call")
    return SKPath(caller_file)

def get_module_path(obj: Any) -> Optional[SKPath]:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        source_path = skpath.get_module_path(MyClass)
        ```
    ────────────────────────────────────────────────────────\n

    Get a module file path as an `SKPath`.
    
    This function can handle:
    - Objects (finds the module where the object is defined)
    - Module names as strings (e.g., `'__main__'`, `'sys'`, `'pathlib'`)
    - Module objects directly
    
    Useful for introspection, debugging, or finding where objects are defined.

    Args:
        `obj`: The object to inspect, module name string, or module object

    Returns:
        `SKPath` object for the module file, or `None` if not found

    Raises:
        `ImportError`: If `obj` is a module name string that cannot be imported

    ────────────────────────────────────────────────────────
        ```python
        # Object Tracing Example:

        # in one file, "/path/to/my/file.py"
        
        class MyClass:
            def __init__(self):
                self.name = "MyClass"
                self.favorite_number = 92
                self.a_cool_dict = {"a": 1, "b": 2, "c": 3}
                self.fail = False
        
                rint = random.randint(1, 10)
                if rint == 10:
                    self.fail = True
        
        # ...

        # later, in a different file...
        my_class = MyClass()
        
        if my_class.fail:
            print(f"Error caused by {my_class.__class__.__name__}")
            
            # will return "/path/to/my/file.py" where MyClass is defined
            print(f"Path to class: {skpath.get_module_path(my_class.__class__)}")
        ```
    ────────────────────────────────────────────────────────\n

        ```python
        # Real use case: Dynamic plugin loading with source tracking

        def load_plugins():

            plugins = []

            for plugin_class in discover_plugins():
                plugin_source = skpath.get_module_path(plugin_class)
                plugins.append({
                    'class': plugin_class,
                    'source': plugin_source.np if plugin_source else 'built-in',
                    'last_modified': plugin_source.stat().st_mtime if plugin_source else None
                })

            return plugins
        ```
    ────────────────────────────────────────────────────────
    """
    # Special handling for module name strings - should raise ImportError if not found
    if isinstance(obj, str):
        try:
            import importlib
            module = importlib.import_module(obj)
            if hasattr(module, '__file__') and module.__file__:
                return SKPath(module.__file__)
            else:
                # Module exists but has no file (built-in module)
                return None
        except (ImportError, ModuleNotFoundError) as e:
            raise ImportError(f"No module named '{obj}'") from e
    
    # For all other objects, use the internal function and return None if not found
    module_file = _get_module_file_path(obj)
    if module_file is None:
        return None
    return SKPath(module_file)

def get_current_dir() -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        current_dir = skpath.get_current_dir()
        ```
    ────────────────────────────────────────────────────────\n

    Get the directory of the current calling file.
    
    Returns:
        `SKPath` object for the calling file's directory
        
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Loading config files next to your script

        config_file = skpath.get_current_dir() / "config.json"
        ```
    ────────────────────────────────────────────────────────
    """
    return SKPath(_get_current_dir())


def get_cwd() -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        cwd = skpath.get_cwd()
        print(f"Working from: {cwd.np}")  # Shows "MyProj/scripts" instead of full path
        ```
    ────────────────────────────────────────────────────────\n

    Current working directory with project context and error handling.
    
    Provides the working directory as an `SKPath` with both absolute and 
    project-relative views, plus extended functionality for path operations.
    
    Returns:
        `SKPath` object for current working directory
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Saving relative output files

        output_file = skpath.get_cwd() / "output.txt"

        print(f"Saving to: {output_file.np}")  # User sees "MyProj/scripts/output.txt"
        ```
    ────────────────────────────────────────────────────────
    """
    return SKPath(_get_cwd())

def equalpaths(path1: Union[str, Path, SKPath], path2: Union[str, Path, SKPath]) -> bool:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        path1 = "/home/user/project/data/file.txt"
        path2 = Path("data/file.txt")  # note: pathlib import isn't needed for equalpaths to work
        
        paths_equal = skpath.equalpaths(path1, path2)
        ```
    ────────────────────────────────────────────────────────\n

    Intelligent path comparison with project-aware semantics.
    
    Compares normalized project-relative paths first (`SKPath.np`) for
    cross-OS stability, then falls back to absolute path comparison.
    
    This function handles strings, Path objects, and `SKPath` objects
    automatically, providing consistent comparison results with project
    context through normalized paths. No need to manually resolve paths.
    
    Args:
        `path1`: First path to compare
        `path2`: Second path to compare

    Returns:
        `True` if the paths are considered equal
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Checking if uploaded file conflicts with existing files

        def check_file_conflict(uploaded_path, existing_files):

            for existing in existing_files:
                if skpath.equalpaths(uploaded_path, existing):
                    return f"File already exists at {existing.np}"

            return None
        ```
    ────────────────────────────────────────────────────────\n

    Note:
        `equalpaths()` converts both paths to `SKPath` objects before comparing them,
        compares `np` paths first and falls back to `ap` comparison when needed.
    """
    # Normalized-first comparison
    if isinstance(path1, SKPath):
        np1 = path1.np
        abs1 = str(path1)
    else:
        sp1 = SKPath(path1)
        np1 = sp1.np
        abs1 = sp1.ap

    if isinstance(path2, SKPath):
        np2 = path2.np
        abs2 = str(path2)
    else:
        sp2 = SKPath(path2)
        np2 = sp2.np
        abs2 = sp2.ap

    # Compare only when both np are non-empty and non-None
    if np1 and np2 and np1 == np2:
        return True

    elif abs1 == abs2:
        return True
    
    else:
        return False


def path_id(path: Union[str, Path, SKPath], short: bool = False) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        short_id = skpath.path_id_short(filepath)
        ```
    ────────────────────────────────────────────────────────\n

    Reproducible path fingerprint with consistent hashing (full md5 hex hash - 32 characters).
    
    Provides error handling, consistent ID always using absolute paths,
    and automatic hashing and hexdigest generation. Same path will always
    generate the same ID across runs and platforms.
    
    Args:
        `path`: Path to generate ID for
        `short`: If `True`, return a shortened version of the ID
        
    Returns:
        Reproducible string ID for the path

    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Creating unique cache keys for processed files
        
        # auto converts to SKPath object
        @skpath.autopath()
        def process_image(image_path: skpath.AnyPath):

            cache_key = image_path.id_short
            cache_file = image_path.root / "cache" / f"processed_{cache_key}.jpg"
            
            if cache_file.exists():
                return cache_file  # Already processed
            
            # Process image and save to cache...
        ```
    ────────────────────────────────────────────────────────
    """
    path_str = str(path) if isinstance(path, SKPath) else str(path)
    return _path_id(path_str, short=short)

def path_id_short(path: Union[str, Path, SKPath]) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        short_id = skpath.path_id_short(filepath)
        ```
    ────────────────────────────────────────────────────────\n

    Short reproducible path fingerprint (8 characters from md5 hash).
    
    Provides error handling, consistent ID always using absolute paths,
    and automatic hashing. Same path will always generate the same ID
    across runs and platforms. Convenient for cache keys and short identifiers.
    
    Args:
        `path`: Path to generate ID for
        
    Returns:
        Short reproducible string ID for the path

    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Creating cache keys for processed files
        
        # auto converts to SKPath object
        @skpath.autopath()
        def process_thumbnails(image_path: skpath.AnyPath):

            cache_key = image_path.id_short  # 8 character ID
            cache_file = image_path.root / "cache" / f"thumb_{cache_key}.jpg"
            
            if cache_file.exists():
                return cache_file  # Already processed
            
            # Generate thumbnail and save to cache...
        ```
    ────────────────────────────────────────────────────────\n
    
    Note:
        This is equivalent to `path_id(path, short=True)`. Same path will always
        generate the same ID across runs and platforms.
    """
    return path_id(path, short=True)

def get_project_paths(
    custom_root: Optional[Union[str, Path]] = None,
    except_paths: Optional[Union[str, List[str]]] = None,
    as_str: bool = False,
    ignore: bool = True) -> Sequence[Union[SKPath, str]]:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        proj_paths = skpath.get_project_paths()
        ```
    ────────────────────────────────────────────────────────\n

    Smart file discovery with intelligent filtering and automatic ignore file support.
    
    Automatically respects .gitignore, .dockerignore, and other .*ignore files
    unless overridden. Provides memory-efficient options and customizable filtering.
    
    Args:
        `custom_root`: Custom root directory (defaults to detected project root)
        `except_paths`: Paths to exclude from results
        `as_str`: Return string paths instead of `SKPath` objects (memory efficiency)
        `ignore`: Respect .*ignore files (default True)
        
    Returns:
        List of paths in the project (`SKPath`s or strings based on `as_str`)

    ────────────────────────────────────────────────────────
        ```python
        # get all project paths, except paths starting with this/one/path/i/dont/want
        
        # - custom_root allows you to start from subdirectories (default is auto-detected project root)
        # - ignore=False will include all paths, including .gitignore, .dockerignore, and .skignore paths (default is True)
        # - as_str=True will return a list of strings instead of SKPath objects (default is False)
        # - except_paths is a list of paths to exclude from the results (default is None)
        
        proj_path_list = skpath.get_project_paths(except_paths="this/one/path/i/dont/want")
        
        # as abspath strings instead of skpaths
        proj_path_list = skpath.get_project_paths(except_paths="this/one/path/i/dont/want", as_str=True)
        
        # including all .gitignore, .dockerignore, and .skignore paths
        proj_path_list = skpath.get_project_paths(except_paths="this/one/path/i/dont/want", ignore=False)
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Code analysis tools
        def analyze_code_complexity():
            python_files = skpath.get_project_paths()
            complexity_report = {}
            
            for file_path in python_files:
                if file_path.suffix == '.py':
                    # Analyze file...
                    complexity_report[file_path.np] = calculate_complexity(file_path)
            
            return complexity_report
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Memory efficient version with strings
        def find_large_files():
            all_paths = skpath.get_project_paths(as_str=True)
            large_files = []
            
            for path_str in all_paths:
                if os.path.getsize(path_str) > 1024 * 1024:  # > 1MB
                    large_files.append(path_str)
            
            return large_files
        ```
    ────────────────────────────────────────────────────────\n
    
    Note:
        Includes smart optimizations:
        - Automatic `.*ignore` parsing - No manual ignore logic needed
        - Selective exclusion - `except_paths` parameter for custom filtering  
        - Memory efficiency - `as_str=True` option to avoid creating `SKPath` objects when not needed
        - Customizable root - `custom_root` parameter to use a set root instead of auto-detecting
    """
    # Get raw paths from internal function
    if custom_root is not None:
        custom_root = Path(custom_root).resolve()
    raw = _get_all_project_paths(
        except_paths=except_paths,
        as_str=True,  # Always get strings first
        ignore=ignore,
        force_root=custom_root if custom_root is not None else None
    )
    raw_paths: List[str] = [str(p) for p in raw]
    
    if as_str:
        return raw_paths
    else:
        if custom_root is not None:
            return [SKPath(path, custom_root) for path in raw_paths]
        else:
            return [SKPath(path) for path in raw_paths]
    

def get_project_structure(
    custom_root: Optional[Union[str, Path]] = None,
    except_paths: Optional[Union[str, List[str]]] = None,
    ignore: bool = True) -> Dict:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        proj_structure = skpath.get_project_structure()
        ```
    ────────────────────────────────────────────────────────\n

    Hierarchical project data as a nested dictionary structure.
    
    Automatically respects .gitignore, .dockerignore, and other .*ignore files
    unless overridden. Builds a complete nested dictionary representation for
    UI components, data analysis, or programmatic project exploration.
    
    Args:
        `custom_root`: Custom root directory (defaults to detected project root)
        `except_paths`: Paths to exclude from results
        `ignore`: Respect .*ignore files (default True)
        
    Returns:
        Nested dictionary representing directory structure

    ────────────────────────────────────────────────────────
        ```python
        # get a nested dictionary representing your project structure
        
        # - custom_root allows you to start from subdirectories (default is auto-detected project root)
        # - ignore=False will include all paths, including .gitignore, .dockerignore, and .skignore paths (default is True)
        # - except_paths is a list of paths to exclude from the results (default is None)
        
        proj_structure = skpath.get_project_structure()
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Interactive file explorer UI
        def create_file_tree_widget(structure, parent_widget=None):
            \"\"\"Create a GUI tree widget from project structure.\"\"\"

            for name, content in structure.items():

                if isinstance(content, dict):
                    # It's a directory
                    folder_widget = FolderWidget(name, parent_widget)
                    create_file_tree_widget(content, folder_widget)  # Recursive
                else:
                    # It's a file
                    FileWidget(name, parent_widget)
        ```
    ────────────────────────────────────────────────────────
        ```python
        # example result
        {
            "root": {
                "subdir1": {
                    "file1.txt": {},
                    "file2.py": {}
                },
                "subdir2": {
                    "file3.md": {}
                }
            }
        }
        ```
    ────────────────────────────────────────────────────────\n
    
    Note:
        Includes smart optimizations shared with other project analysis functions:
        - Automatic `.*ignore` parsing - No manual ignore logic needed
        - Selective exclusion - `except_paths` parameter for custom filtering  
        - Customizable root - `custom_root` parameter to use a set root instead of auto-detecting
    """
    return _get_project_structure(
        custom_root if custom_root is not None else None,
        except_paths, ignore
    )


def get_formatted_project_tree(
    custom_root: Optional[Union[str, Path]] = None,
    max_depth: int = 3,
    show_files: bool = True,
    except_paths: Optional[Union[str, List[str]]] = None,
    ignore: bool = True) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        tree_str = skpath.get_formatted_project_tree()
        print(tree_str)
        ```
    ────────────────────────────────────────────────────────\n

    Pretty terminal output with tree-like visual hierarchy.

    Uses tree-like characters (│, ├─, └─) to create a beautiful visual hierarchy.
    Automatically respects `.gitignore`, `.dockerignore`, and other `.*ignore` files
    unless overridden. Perfect for documentation, debugging, or terminal display.
    
    Args:
        `custom_root`: Custom root directory (defaults to detected project root)
        `max_depth`: Maximum depth to display (prevents huge output)
        `show_files`: Whether to show files or just directories
        `except_paths`: Paths to exclude from results
        `ignore`: Respect `.*ignore` files (default `True`)

    Returns:
        Formatted string representing directory structure

    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Project documentation generation

        def generate_project_structure_overview():
            \"\"\"Generate markdown documentation with project structure.\"\"\"

            tree = skpath.get_formatted_project_tree(
                show_files=False,  # Just directories for overview
                max_depth=3
            )
            
            tree_section = f"Project Structure:\n{tree}"
        ```
    ────────────────────────────────────────────────────────\n
    Sample formatted tree (first 15 lines):

    Note: the output in the docstring does not display correctly due to 
    docstring formatting limitations, but the actual output will.

        tmplyff3mg7/\n
        ├── __pycache__/\n
        │   └── main.cpython-39.pyc\n
        ├── docs/\n
        │   └── api.md\n
        ├── src/\n
        │   ├── config.json\n
        │   ├── main.py\n
        │   └── utils.py\n
        ├── tests/\n
        ... and more\n
    
    Note:
        Includes smart optimizations shared with other project analysis functions:
        - Automatic `.*ignore` parsing - No manual ignore logic needed
        - Selective exclusion - `except_paths` parameter for custom filtering  
        - Customizable root - `custom_root` parameter to use a set root instead of auto-detecting
        - Depth limiting with `max_depth` to prevent huge output
    """
    return _get_formatted_project_tree(
        custom_root if custom_root is not None else None, 
        max_depth, show_files, except_paths, ignore
    )

def force_project_root(root: Union[str, Path, SKPath]) -> None:
    """
    ────────────────────────────────────────────────────────
        ```python
        skpath1 = SKPath("file.txt")  # Uses auto-detected root
        
        force_project_root("/new/project/root")
        skpath2 = SKPath("file.txt")  # Uses forced root
        
        # if skpath1 and skpath2 have different project roots
        are_the_same = skpath1.np == skpath2.np # will be False
        ```
    ────────────────────────────────────────────────────────\n

    RECOMMENDED: use `force_project_root()` before creating any `SKPath` objects if
    you want to force a specific project root for the duration of that script. If using 
    mid-script, use in isolation, ensuring that `clear_forced_project_root()` is called
    after that isolated section finishes or use the `ForceRoot` context manager.

    ────────────────────────────────────────────────────────\n   

    Override project root for special cases like testing with temporary directories.
    
    Useful for uninitialized projects, testing scenarios, or when auto-detection
    fails. Provides complete control over project root behavior.
    
    Important: This affects only NEW `SKPath` instances created after the call.
    Existing `SKPath` objects retain their original project root and continue
    to function with their original root for consistency.
    
    Args:
        `path`: Path to use as project root
        
    Raises:
        `FileNotFoundError`: If path doesn't exist
        `NotADirectoryError`: If path is not a directory
        
    ────────────────────────────────────────────────────────
        ```python
        # Use case: Testing with temporary directories
        import tempfile
        
        def test_file_operations():

            with tempfile.TemporaryDirectory() as temp_dir:

                # Set up test project structure
                test_project = Path(temp_dir) / "test_project"
                test_project.mkdir()
                (test_project / "LICENSE").touch()
                (test_project / "README.md").touch()
                (test_project / "requirements.txt").touch()
                
                # Force SKPath to use our test directory
                skpath.force_project_root(test_project)
                
                # Now all SKPath operations use the test directory
                test_file = skpath.get_project_root() / "test_data.json"
                # ... run tests
                
                # Clean up
                skpath.clear_forced_project_root()
        ```
    ────────────────────────────────────────────────────────
    """
    path_str = str(SKPath(root))
    _force_project_root(path_str)


def clear_forced_project_root() -> None:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath

        if skpath.get_forced_project_root():
            skpath.clear_forced_project_root()

        # Now project root will be auto-detected again
        ```
    ────────────────────────────────────────────────────────\n

    Clear any forced project root, returning to auto-detection.
    
    """
    _clear_forced_project_root()


def get_forced_project_root() -> Optional[SKPath]:
    """
    ────────────────────────────────────────────────────────
        ```python
        forced_root = get_forced_project_root()

        if forced_root:
            print(f"Forced project root: {forced_root}")
            clear_forced_project_root()  # Clear it if needed
        else:
            print("No forced project root set")
        ```
    ────────────────────────────────────────────────────────\n

    Get the currently forced project root, if any.
    
    Returns:
        `SKPath` object of the forced project root, or `None` if no forced root is set
    """
    forced = _get_forced_project_root()
    return None if forced is None else SKPath(forced)


class ForceRoot:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        with skpath.ForceRoot("/new/project/root"):
            # All SKPath operations in this block use the new root

            # sp1 will use the new root
            sp1 = SKPath("file.txt")

        # sp2 will use the root from before the context manager block
        sp2 = SKPath("file.txt")

        # if root from ForceRoot was different from the original root
        are_the_same = sp1.np == sp2.np # will be False
        ```
    ────────────────────────────────────────────────────────\n

    Context manager for temporarily forcing a project root.
    
    Uses `force_project_root()` in isolation, ensuring that `clear_forced_project_root()` is called
    after that section finishes.
    """
    def __init__(self, root: Union[str, Path, SKPath]):
        self.path = str(SKPath(root))
        self.original_root = get_forced_project_root()

    def __enter__(self):
        force_project_root(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        clear_forced_project_root()
        if self.original_root:
            force_project_root(self.original_root)

    def __str__(self):
        return f"ForceRoot(root={self.path})"

    def __repr__(self):
        return f"ForceRoot(root={self.path})"

# ============================================================================
# AutoPath Decorator - Automatic Path Conversion Magic
# ============================================================================

def autopath(autofill: bool = False, 
             defaultpath: Optional[Union[str, Path, SKPath]] = None):
    """
    ────────────────────────────────────────────────────────
        ```python
        # standard autopath functionality

        @autopath()
        def process_file(path: skpath.AnyPath = None):
            if not path:
                raise ValueError("No path provided")
        
            # we can use path.np without checking type because autopath turns everything into SKPaths
            print(f"Processing {path.np}...")
            # do some processing of the file...
        
        # later...
        
        # relative path will convert to an SKPath automatically before being used
        process_file("my/relative/path")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # standard autopath functionality, but function doesn't accept SKPath type!

        @autopath()
        def process_file(path: str = None): # only accepts strings!
            print(f"Processing {path}...")
            # do some processing of the file...
        
        # later...
        
        # relative path will convert only to an absolute path string instead!
        process_file("my/relative/path")
        ```
    ────────────────────────────────────────────────────────\n
    Decorator that automatically converts path parameters to appropriate types.
    
    This decorator provides super easy path handling by:
    1. Converting valid path strings to `SKPath` objects (if function accepts them)
    2. Converting `SKPath` objects to strings (if function only accepts strings)
    3. Auto-filling missing paths with caller location or default
    4. Handling type compatibility automatically
    
    Args:
        `autofill`: If `True`, use caller file path when path parameter is `None`
        `defaultpath`: Default path to use when path parameter is `None`
        
    Returns:
        Decorated function with automatic path conversion
        
    ────────────────────────────────────────────────────────
        ```python
        # using defaultpath to set a default path

        @autopath(defaultpath="my/default/path")
        def save_to_file(data: Any = None, path: skpath.AnyPath = None) -> bool:
            # save data to file with given path...
        
        # later...
        
        # user forgets to add path, or just wants to save all data to same file
        saved_to_file = save_to_file(data, path=None) # -> still saves to my/default/path!
        ```
    ────────────────────────────────────────────────────────\n

        ```python
        # automatically fill with caller file path

        @autopath(autofill=True)
        def process_file(path: skpath.AnyPath = None):
            print(f"Processing {path.np}...")
            # do some processing of the file...
        
        # later...
        
        # relative path will convert to an SKPath automatically before being used
        process_file() # uses caller file path because we are autofilling
        
        # NOTE: autofill WILL be ignored if defaultpath is used and has a valid path value!
        
        # autofill WILL be ignored below!
        @autopath(autofill=True, defaultpath="a/valid/path/or/skpath_dict")
        ```
    ────────────────────────────────────────────────────────
    """
    def decorator(func: Callable) -> Callable:
        # Get function signature for parameter inspection
        sig = inspect.signature(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Bind arguments to get parameter names and values
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Find parameters with 'path' in the name
            path_params = [name for name in bound_args.arguments.keys() if 'path' in name.lower()]
            
            for param_name in path_params:
                param_value = bound_args.arguments[param_name]
                param_annotation = sig.parameters[param_name].annotation
                
                # Handle None values with autofill/defaultpath
                if param_value is None:
                    if defaultpath is not None:
                        # Use default path (overrides autofill)
                        param_value = defaultpath
                    elif autofill:
                        # Use caller's file location
                        try:
                            caller_file = _get_non_sk_caller_file_path()
                            if caller_file:
                                param_value = caller_file
                        except:
                            pass  # Leave as None if auto-detection fails
                
                # Skip if still None
                if param_value is None:
                    continue
                
                # Determine priority type for conversion based on annotation
                # Priority: SKPath > Path > str (SKPath default for no annotation)
                def get_annotation_types(annotation):
                    """Extract types from annotation, handling Union types"""
                    if annotation == inspect.Parameter.empty:
                        return []
                    elif hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
                        # Union type like str | SKPath or Union[str, Path]
                        return list(annotation.__args__)
                    else:
                        # Single type
                        return [annotation]
                
                annotation_types = get_annotation_types(param_annotation)
                
                # Determine target type based on priority: SKPath > Path > str
                if not annotation_types:
                    # No annotation - default to SKPath
                    target_type = SKPath
                elif SKPath in annotation_types:
                    # SKPath is available - use it
                    target_type = SKPath
                elif Path in annotation_types:
                    # Path is available - use it
                    target_type = Path
                elif str in annotation_types:
                    # Only str is available - use it
                    target_type = str
                else:
                    # No compatible types, skip conversion
                    continue
                
                # Convert based on current type and target type
                if isinstance(param_value, (str, Path, SKPath)):
                    # Validate it looks like a path
                    path_str = str(param_value)
                    looks_like_path = (
                        '/' in path_str or '\\' in path_str or  # Has path separators
                        '.' in path_str or                      # Has extension or relative reference
                        path_str in ['.', '..'] or              # Special path references
                        (isinstance(param_value, Path) and param_value.is_absolute()) or  # Absolute Path
                        (isinstance(param_value, SKPath) and param_value.is_absolute)  # Absolute SKPath
                    )
                    
                    if looks_like_path:
                        try:
                            # Convert to target type
                            if target_type == SKPath:
                                if not isinstance(param_value, SKPath):
                                    bound_args.arguments[param_name] = SKPath(param_value)
                            elif target_type == Path:
                                if not isinstance(param_value, Path):
                                    bound_args.arguments[param_name] = Path(param_value).resolve()
                            elif target_type == str:
                                if not isinstance(param_value, str):
                                    bound_args.arguments[param_name] = str(Path(param_value).resolve())
                        except (OSError, ValueError):
                            # Not a valid path, leave as-is
                            pass
            
            # Call function with converted arguments
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator

# ============================================================================
# Factory Functions
# ============================================================================

def create(
    path: Optional[Union[str, Path]] = None,
    custom_root: Optional[Union[str, Path]] = None,
) -> SKPath:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        # Create SKPath from a specific path
        my_path = skpath.create("/path/to/my/file.txt")
        
        # Create SKPath using caller's file location
        my_caller_path = skpath.create()
        
        # Create SKPath with custom project root
        my_custom_path = skpath.create("/path/to/my/file.txt", custom_root="/path/to/project")
        ```
    ────────────────────────────────────────────────────────\n

    Create an `SKPath` object from a given path.
    
    Factory function for creating `SKPath` objects with optional project root override.
    
    Args:
        `path`: The path to convert to `SKPath` (auto-detects caller if `None`)
        `custom_root`: Project root path (auto-detected if `None`)
        
    Returns:
        `SKPath` object
    """
    return SKPath(path, Path(custom_root).resolve() if custom_root is not None else None)

# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main class
    'SKPath',

    # Special types
    'AnyPath',
    
    # Convenience functions
    'get_project_root',
    'get_caller_path', 
    'get_current_dir',
    'get_cwd',
    'equalpaths',
    'path_id',
    'path_id_short',
    'get_project_paths',
    'get_project_structure',
    'get_formatted_project_tree',
    
    # Project root management
    'force_project_root',
    'clear_forced_project_root', 
    'get_forced_project_root',

    # Forcing project root
    'ForceRoot',
    
    # Decorators
    'autopath',
    
    # Factory functions
    'create',
]