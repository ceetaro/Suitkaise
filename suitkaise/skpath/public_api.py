"""
SKPath API - Smart Path Operations for Suitkaise

This module provides the user-facing API for intelligent path handling with dual-path
architecture, automatic project root detection, and magical caller detection.

Key Features:
- SKPath objects with absolute and normalized paths
- Zero-configuration initialization with automatic caller detection
- Project root detection with sophisticated indicators
- AutoPath decorator for automatic path conversion
- Complete project structure analysis
- Path utilities with cross-module compatibility
"""

import os
import inspect
import fnmatch
from pathlib import Path
from typing import Dict, List, Set, Optional, Union, Tuple, Any, Callable
from functools import wraps

# Import internal path operations with fallback
try:
    from .._int.path.path_ops import (
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
        _get_forced_project_root
    )
except ImportError:
    raise ImportError(
        "Internal path operations could not be imported. "
        "Ensure that the internal path operations module is available."
    )

class SKPath:
    """
    A smart path object that maintains both absolute and normalized paths.
    
    SKPath provides easy access to both the full system path and the path
    relative to the project root, with intelligent string conversion for
    compatibility with standard path operations.

    The "magic" comes from automatic caller detection and project root discovery,
    making path operations work seamlessly without configuration.
    """
    
    def __init__(self, path: Optional[Union[str, Path]] = None, 
                 project_root: Optional[Path] = None):
        """
        Initialize an SKPath object with magical caller detection.
        
        Args:
            path: The path to wrap (if None, auto-detects caller's file)
            project_root: Project root path (auto-detected if None)
            
        Raises:
            RuntimeError: If path is None and caller detection fails
            FileNotFoundError: If provided path doesn't exist
        """
        # Handle zero-argument magic initialization
        if path is None:
            caller_file = _get_non_sk_caller_file_path()
            if caller_file is None:
                raise RuntimeError("Could not auto-detect caller file path. Please provide a path explicitly.")
            self._absolute_path = caller_file
        else:
            # Convert provided path to absolute
            path_obj = Path(path)
            if not path_obj.is_absolute():
                # For relative paths, resolve from current directory
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

    def _calculate_normalized_path(self) -> str:
        """Calculate the normalized path relative to project root."""
        if self._project_root is None:
            # If we can't find project root, normalized path is just the filename
            return self._absolute_path.name
        
        try:
            # Get path relative to project root
            relative_path = self._absolute_path.relative_to(self._project_root)
            return str(relative_path).replace('\\', '/')  # Normalize separators
        except ValueError:
            # Path is not under project root, use absolute path
            return str(self._absolute_path)
        
    @property
    def ap(self) -> str:
        """Absolute path - the full system path."""
        return str(self._absolute_path)
    
    @property
    def np(self) -> str:
        """Normalized path - path relative to project root."""
        return self._normalized_path
    
    @property
    def project_root(self) -> Optional[Path]:
        """The detected project root directory."""
        return self._project_root
    
    @property
    def path_object(self) -> Path:
        """Get the underlying Path object for advanced operations."""
        return self._absolute_path
    
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
        """The file extension."""
        return self._absolute_path.suffix
    
    @property
    def suffixes(self) -> List[str]:
        """All suffixes of the path."""
        return self._absolute_path.suffixes
    
    @property
    def parent(self) -> 'SKPath':
        """The parent directory as an SKPath."""
        return SKPath(self._absolute_path.parent, self._project_root)
    
    @property
    def parents(self) -> List['SKPath']:
        """All parent directories as SKPaths."""
        return [SKPath(parent, self._project_root) for parent in self._absolute_path.parents]
    
    @property
    def parts(self) -> Tuple[str, ...]:
        """The path components as a tuple."""
        return self._absolute_path.parts
    
    def exists(self) -> bool:
        """Check if the path exists."""
        return self._absolute_path.exists()
    
    def is_file(self) -> bool:
        """Check if the path is a file."""
        return self._absolute_path.is_file()
    
    def is_dir(self) -> bool:
        """Check if the path is a directory."""
        return self._absolute_path.is_dir()
    
    def is_absolute(self) -> bool:
        """Check if the path is absolute."""
        return self._absolute_path.is_absolute()
    
    def is_symlink(self) -> bool:
        """Check if the path is a symbolic link."""
        return self._absolute_path.is_symlink()
    
    def stat(self):
        """Get stat information for the path."""
        return self._absolute_path.stat()
    
    def lstat(self):
        """Get lstat information for the path."""
        return self._absolute_path.lstat()
    
    def iterdir(self) -> List['SKPath']:
        """Iterate over directory contents as SKPaths."""
        if not self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory")
        return [SKPath(item, self._project_root) for item in self._absolute_path.iterdir()]
    
    def glob(self, pattern: str) -> List['SKPath']:
        """Find all paths matching the pattern."""
        return [SKPath(match, self._project_root) for match in self._absolute_path.glob(pattern)]
    
    def rglob(self, pattern: str) -> List['SKPath']:
        """Recursively find all paths matching the pattern."""
        return [SKPath(match, self._project_root) for match in self._absolute_path.rglob(pattern)]
    
    def relative_to(self, other: Union[str, Path, 'SKPath']) -> Path:
        """Return relative path to another path."""
        if isinstance(other, SKPath):
            return self._absolute_path.relative_to(other._absolute_path)
        return self._absolute_path.relative_to(Path(other))
    
    def with_name(self, name: str) -> 'SKPath':
        """Return a new SKPath with different name."""
        return SKPath(self._absolute_path.with_name(name), self._project_root)
    
    def with_stem(self, stem: str) -> 'SKPath':
        """Return a new SKPath with different stem."""
        return SKPath(self._absolute_path.with_stem(stem), self._project_root)
    
    def with_suffix(self, suffix: str) -> 'SKPath':
        """Return a new SKPath with different suffix."""
        return SKPath(self._absolute_path.with_suffix(suffix), self._project_root)
    
    def resolve(self) -> 'SKPath':
        """Return absolute version of the path."""
        return SKPath(self._absolute_path.resolve(), self._project_root)
    
    def as_dict(self) -> Dict[str, str]:
        """Return the dual-path structure as a dictionary."""
        return {
            "ap": self.ap,
            "np": self.np
        }
    
    def __str__(self) -> str:
        """String conversion returns absolute path for compatibility."""
        return self.ap

    def __repr__(self) -> str:
        """Detailed representation showing both paths."""
        return f"SKPath(ap='{self.ap}', np='{self.np}')"
    
    def __eq__(self, other) -> bool:
        """Compare SKPaths based on their absolute paths."""
        if isinstance(other, SKPath):
            return self._absolute_path == other._absolute_path
        elif isinstance(other, (str, Path)):
            return self._absolute_path == Path(other).resolve()
        return False
    
    def __hash__(self) -> int:
        """Hash based on absolute path for use in sets/dicts."""
        return hash(self._absolute_path)
    
    def __truediv__(self, other) -> 'SKPath':
        """Support path joining with / operator."""
        return SKPath(self._absolute_path / other, self._project_root)
    
    def __fspath__(self) -> str:
        """Support for os.fspath()."""
        return str(self._absolute_path)
    



























# ============================================================================
# Convenience Functions - Direct access to path operations
# ============================================================================

def get_project_root(expected_name: Optional[str] = None) -> Optional[Path]:
    """
    Find the project root directory starting from the caller's file location.
    
    Uses sophisticated indicator-based detection requiring necessary files
    (LICENSE, README, requirements) and scoring based on project structure.
    
    Args:
        expected_name: Expected project name (returns None if name doesn't match)
        
    Returns:
        Path object pointing to project root, or None if not found
        
    Raises:
        RuntimeError: If project root detection fails completely

    Example:
    ```python
        root = get_project_root()
        root = get_project_root(expected_name="MyProject")
    """
    result = _get_project_root(expected_name=expected_name)
    if result is None and expected_name is None:
        raise RuntimeError("Could not detect project root. Ensure your project has necessary files (LICENSE, README, requirements).")
    return result

def get_caller_path() -> SKPath:
    """
    Get the SKPath of the file that called this function.
    
    Uses magical caller detection to find the user's file, ignoring any
    internal suitkaise library calls in the process.
    
    Returns:
        SKPath object for the calling file
        
    Raises:
        RuntimeError: If caller detection fails

    Example:
    ```python
        caller_path = get_caller_path()
        print(caller_path.ap)  # Absolute path of the caller file
        print(caller_path.np)  # Normalized path relative to project root
    """
    caller_file = _get_non_sk_caller_file_path()
    if caller_file is None:
        raise RuntimeError("Could not detect caller file path")
    return SKPath(caller_file)

def get_module_path(obj: Any) -> Optional[SKPath]:
    """
    Get a module file path as an SKPath.
    
    This function can handle:
    - Objects (finds the module where the object is defined)
    - Module names as strings (e.g., '__main__', 'sys', 'pathlib')
    - Module objects directly
    
    Useful for introspection, debugging, or finding where objects are defined.

    Args:
        obj: The object to inspect, module name string, or module object

    Returns:
        SKPath object for the module file, or None if not found

    Raises:
        ImportError: If obj is a module name string that cannot be imported

    Example:
    ```python
        # Get current module path
        current_module = get_module_path(__name__)
        
        # Get path where a class is defined
        class_module = get_module_path(MyClass)
        
        # Get path of built-in or installed module
        pathlib_module = get_module_path('pathlib')
        sys_module = get_module_path('sys')  # Returns None for built-ins
        
        # This will raise ImportError
        invalid_module = get_module_path('non_existent_module')
    ```
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
    Get the directory of the current calling file.
    
    Returns:
        SKPath object for the calling file's directory
        
    Example:
    ```python
        current_dir = get_current_dir()
        print(current_dir.ap)  # Absolute path of the current directory
        print(current_dir.np)  # Normalized path relative to project root
    """
    return SKPath(_get_current_dir())


def get_cwd() -> SKPath:
    """
    Get the current working directory as an SKPath.
    
    Returns:
        SKPath object for current working directory

    Example:
    ```python
        cwd = get_cwd()
        print(cwd.ap)  # Absolute path of the current working directory
        print(cwd.np)  # Normalized path relative to project root
    """
    return SKPath(_get_cwd())

def equalpaths(path1: Union[str, Path, SKPath], path2: Union[str, Path, SKPath]) -> bool:
    """
    Check if two paths are equal, handling different path types intelligently.
    
    Args:
        path1: First path to compare
        path2: Second path to compare
        
    Returns:
        True if paths point to the same location

    Example:
    ```python
        result = equalpaths("/path/to/file.txt", "file.txt")
        print(result)  # True if both paths resolve to the same location

        skpath1 = SKPath()
        result = equalpaths(skpath1, "/path/to/file.txt")
        print(result)  # True if skpath1 (this module) matches the file.txt location

        if equalpaths(path1, path2):
            do_something()
    """
    # Extract absolute paths for comparison
    abs1 = str(path1) if isinstance(path1, SKPath) else str(Path(path1).resolve())
    abs2 = str(path2) if isinstance(path2, SKPath) else str(Path(path2).resolve())
    
    return _equal_paths(abs1, abs2)

def equalnormpaths(path1: Union[str, Path, SKPath], path2: Union[str, Path, SKPath]) -> bool:
    """
    Check if two normalized paths (SKPath.np) are equal.

    Normalized paths are relative to your project root.

    Can be helpful for path data saved from different operating systems or formats,
    that should still be considered equivalent within the same project context.
    
    Args:
        path1: First path to compare
        path2: Second path to compare
        
    Returns:
        True if normalized paths are equivalent

    Example:
    ```python
        result = equalnormpaths("/path/to/file.txt", "file.txt")
        print(result)  # True if both paths normalize to the same relative location

        skpath1 = SKPath()
        result = equalnormpaths(skpath1, "/path/to/file.txt")
        print(result)  # True if skpath1 (this module) matches the normalized file.txt location

        if equalnormpaths(path1, path2):
            do_something()
    """
    if isinstance(path1, SKPath):
        np1 = path1.np
    else:
        np1 = SKPath(path1).np

    if isinstance(path2, SKPath):
        np2 = path2.np
    else:
        np2 = SKPath(path2).np
    
    return np1 == np2

def path_id(path: Union[str, Path, SKPath], short: bool = False) -> str:
    """
    Generate a reproducible ID for a path.
    
    Args:
        path: Path to generate ID for
        short: If True, return a shortened version of the ID
        
    Returns:
        Reproducible string ID for the path

    Example:
    ```python
        id_full = path_id("/path/to/file.txt")
        print(id_full)  # Full ID based on absolute path

        id_short = path_id("/path/to/file.txt", short=True)
        print(id_short)  # Shortened ID based on normalized path

        # result will be consistent across runs and platforms
    """
    path_str = str(path) if isinstance(path, SKPath) else str(path)
    return _path_id(path_str, short=short)

def path_id_short(path: Union[str, Path, SKPath]) -> str:
    """
    Generate a short reproducible ID for a path.
    
    Args:
        path: Path to generate ID for
        
    Returns:
        Short reproducible string ID for the path

    Example:
    ```python
        my_path_shortened_id = path_idshort(my_path)

        # result will be consistent across runs and platforms
    """
    return path_id(path, short=True)

def get_all_project_paths(except_paths: Optional[Union[str, List[str]]] = None,
                         as_str: bool = False,
                         dont_ignore: bool = False,
                         force_root: Optional[Union[str, Path]] = None) -> List[Union[SKPath, str]]:
    """
    Get all paths in the current project with intelligent filtering.
    
    Automatically respects .gitignore and .dockerignore files unless overridden.
    
    Args:
        except_paths: Paths to exclude from results
        as_str: Return string paths instead of SKPath objects
        dont_ignore: Include paths that would normally be ignored
        force_root: Force a specific project root
        
    Returns:
        List of paths in the project (SKPaths or strings based on as_str)

    Example:
    ```python
        # get all project paths
        proj_path_list = skpath.get_all_project_paths(
            except_paths="this/one/path/i/dont/want"
        )

        # as abspath strings instead of skpaths
        proj_path_list = skpath.get_all_project_paths(
            except_paths="this/one/path/i/dont/want", as_str=True
        )

        # including all .gitignore and .skignore paths
        proj_path_list = skpath.get_all_project_paths(
            except_paths="this/one/path/i/dont/want", dont_ignore=True
        )
    """
    # Get raw paths from internal function
    raw_paths = _get_all_project_paths(
        except_paths=except_paths,
        as_str=True,  # Always get strings first
        dont_ignore=dont_ignore,
        force_root=force_root
    )
    
    if as_str:
        return raw_paths
    else:
        # Convert to SKPaths
        project_root = force_root or get_project_root()
        return [SKPath(path, project_root) for path in raw_paths]
    

def get_project_structure(force_root: Optional[Union[str, Path]] = None,
                         except_paths: Optional[Union[str, List[str]]] = None,
                         dont_ignore: bool = False) -> Dict:
    """
    Get a nested dictionary representing the project structure.
    
    Automatically respects .gitignore and .dockerignore files unless overridden.
    
    Args:
        force_root: Custom root directory (defaults to detected project root)
        except_paths: Paths to exclude from results
        dont_ignore: Include paths that would normally be ignored
        
    Returns:
        Nested dictionary representing directory structure

    Example:
    ```python
        project_structure = get_project_structure()
        print(project_structure)  # Nested dict of project directories and files

        # Force a specific root directory
        custom_structure = get_project_structure(force_root="/path/to/custom/root")
        print(custom_structure)

        # Exclude specific paths
        custom_structure = get_project_structure(
            force_root="/path/to/custom/root",
            except_paths=["/path/to/exclude"]
        )
    ```

    Example Result:
    ```python
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
    """
    return _get_project_structure(force_root, except_paths, dont_ignore)


def get_formatted_project_tree(force_root: Optional[Union[str, Path]] = None,
                               max_depth: int = 3,
                               show_files: bool = True,
                               except_paths: Optional[Union[str, List[str]]] = None,
                               dont_ignore: bool = False) -> str:
    """
    Get a formatted string representation of the project structure.

    Uses tree-like characters (│, ├─, └─) to create a visual hierarchy.
    Automatically respects .gitignore and .dockerignore files unless overridden.
    
    Args:
        force_root: Custom root directory (defaults to detected project root)
        max_depth: Maximum depth to display (prevents huge output)
        show_files: Whether to show files or just directories
        except_paths: Paths to exclude from results
        dont_ignore: Include paths that would normally be ignored
        
    Returns:
        Formatted string representing directory structure

    Example:
    ```python
        tree_str = get_formatted_project_tree()
        print(tree_str)  # Displays project structure as a tree

        # Force a specific root directory
        custom_tree_str = get_formatted_project_tree(force_root="/path/to/custom/root")
        print(custom_tree_str)

        # Exclude specific paths
        custom_tree_str = get_formatted_project_tree(
            force_root="/path/to/custom/root",
            except_paths=["/path/to/exclude"]
        )
    ```

    Sample formatted tree (first 15 lines):
        tmplyff3mg7/
        ├── __pycache__/
        │   └── main.cpython-39.pyc
        ├── docs/
        │   └── api.md
        ├── src/
        │   ├── config.json
        │   ├── main.py
        │   └── utils.py
        ├── tests/
        ... and more
    """
    return _get_formatted_project_tree(force_root, max_depth, show_files, except_paths, dont_ignore)

def force_project_root(path: Union[str, Path, SKPath]) -> None:
    """
    Force the project root to a specific path globally.
    
    Useful for uninitialized projects or testing scenarios.
    
    Args:
        path: Path to use as project root
        
    Raises:
        FileNotFoundError: If path doesn't exist
        NotADirectoryError: If path is not a directory

    Example:
    ```python
        force_project_root("/path/to/my/project")
        # Now all SKPath operations will use this as the project root
    """
    path_str = str(path) if isinstance(path, SKPath) else str(path)
    _force_project_root(path_str)


def clear_forced_project_root() -> None:
    """
    Clear any forced project root, returning to auto-detection.
    
    ```python
        clear_forced_project_root()
        # Now project root will be auto-detected again
    """
    _clear_forced_project_root()


def get_forced_project_root() -> Optional[Path]:
    """
    Get the currently forced project root, if any.
    
    ```python
        forced_root = get_forced_project_root()
        if forced_root:
            print(f"Forced project root: {forced_root}")
            clear_forced_project_root()  # Clear it if needed
        else:
            print("No forced project root set")
    """
    return _get_forced_project_root()

# ============================================================================
# AutoPath Decorator - Automatic Path Conversion Magic
# ============================================================================

def autopath(autofill: bool = False, 
             defaultpath: Optional[Union[str, Path, SKPath]] = None):
    """
    Decorator that automatically converts path parameters to appropriate types.
    
    This decorator provides magical path handling by:
    1. Converting valid path strings to SKPath objects (if function accepts them)
    2. Converting SKPath objects to strings (if function only accepts strings)
    3. Auto-filling missing paths with caller location or default
    4. Handling type compatibility automatically
    
    Args:
        autofill: If True, use caller file path when path parameter is None
        defaultpath: Default path to use when path parameter is None
        
    Returns:
        Decorated function with automatic path conversion
        
    Example:
        @autopath()
        def process_file(path: Union[str, SKPath] = None):
            # path will be auto-converted to SKPath if it's a valid path string
            pass
        
        @autopath(autofill=True)
        def process_current_file(path: Union[str, SKPath] = None):
            # If no path provided, uses caller's file location
            pass
        
        @autopath(defaultpath="./default/location")
        def save_file(data, path: Union[str, SKPath] = None):
            # If no path provided, uses default location
            pass
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
                
                # Determine if parameter accepts SKPath objects
                accepts_skpath = (
                    param_annotation == SKPath or
                    (hasattr(param_annotation, '__origin__') and 
                     hasattr(param_annotation, '__args__') and
                     SKPath in getattr(param_annotation, '__args__', []))
                )
                
                # Determine if parameter accepts strings
                accepts_str = (
                    param_annotation == str or
                    param_annotation == inspect.Parameter.empty or
                    (hasattr(param_annotation, '__origin__') and 
                     hasattr(param_annotation, '__args__') and
                     str in getattr(param_annotation, '__args__', []))
                )
                
                # Convert based on current type and what function accepts
                if isinstance(param_value, SKPath):
                    # SKPath object
                    if not accepts_skpath and accepts_str:
                        # Function only accepts strings, convert to string
                        bound_args.arguments[param_name] = str(param_value)
                    # Otherwise, leave as SKPath
                
                elif isinstance(param_value, (str, Path)):
                    # String or Path object
                    try:
                        # Check if it's a valid path
                        path_obj = Path(param_value)
                        
                        # Additional validation: check if it looks like a reasonable path
                        # Skip conversion if it's clearly not a path (no separators, no extensions, too generic)
                        path_str = str(param_value)
                        looks_like_path = (
                            '/' in path_str or '\\' in path_str or  # Has path separators
                            '.' in path_str or                      # Has extension or relative reference
                            path_str in ['.', '..'] or              # Special path references
                            path_obj.is_absolute()                  # Is absolute path
                        )
                        
                        if looks_like_path and accepts_skpath:
                            # Convert to SKPath if function accepts them
                            bound_args.arguments[param_name] = SKPath(param_value)
                        elif looks_like_path and accepts_str and not isinstance(param_value, str):
                            # Convert Path to string if needed
                            bound_args.arguments[param_name] = str(path_obj.resolve())
                        # Otherwise leave as-is (not a path-like string)
                        
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

def create(path: Optional[Union[str, Path]] = None, 
           project_root: Optional[Path] = None) -> SKPath:
    """
    Create an SKPath object from a given path.
    
    Factory function for creating SKPath objects with optional project root override.
    
    Args:
        path: The path to convert to SKPath (auto-detects caller if None)
        project_root: Project root path (auto-detected if None)
        
    Returns:
        SKPath object

    Example:
    ```python
        # Create SKPath from a specific path
        my_path = create("/path/to/my/file.txt")
        
        # Create SKPath using caller's file location
        my_caller_path = create()
        
        # Create SKPath with custom project root
        my_custom_path = create("/path/to/my/file.txt", project_root="/path/to/project")
    """
    return SKPath(path, project_root)

# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main class
    'SKPath',
    
    # Convenience functions
    'get_project_root',
    'get_caller_path', 
    'get_current_dir',
    'get_cwd',
    'equalpaths',
    'equalnormpaths',
    'path_id',
    'path_id_short',
    'get_all_project_paths',
    'get_project_structure',
    'get_formatted_project_tree',
    
    # Project root management
    'force_project_root',
    'clear_forced_project_root', 
    'get_forced_project_root',
    
    # Decorators
    'autopath',
    
    # Factory functions
    'create',
]