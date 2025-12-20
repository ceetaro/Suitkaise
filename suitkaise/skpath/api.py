


# NOTE: wrap everything with SKPath here if importing from somewhere else

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
        `PathDetectionError`: If project root detection fails completely

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
        `PathDetectionError`: If caller detection fails

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
            raise PathDetectionError("caller file path", "get_caller_path function call")
    except RuntimeError:
        raise PathDetectionError("caller file path", "get_caller_path function call")
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

# combine with this cleanly 

# def _get_module_file_path(obj: Any) -> Optional[Path]:
#     """
#     Get the file path of the module for an object or module name.
    
#     Args:
#         obj: Object to inspect, or module name string, or module object
        
#     Returns:
#         Path to the module file, or None if not found
#     """
#     try:
#         # Case 1: obj is a string (module name)
#         if isinstance(obj, str):
#             try:
#                 # Try to import the module by name
#                 import importlib
#                 module = importlib.import_module(obj)
#                 if hasattr(module, '__file__') and module.__file__:
#                     return Path(module.__file__).resolve()
#             except (ImportError, ModuleNotFoundError):
#                 # Module doesn't exist or can't be imported
#                 return None
        
#         # Case 2: obj is a Path object (not a module, return None)
#         elif isinstance(obj, Path):
#             return None
        
#         # Case 3: obj is already a module object
#         elif hasattr(obj, '__file__'):
#             if obj.__file__:
#                 return Path(obj.__file__).resolve()
        
#         # Case 4: obj is any other object - get its module
#         elif hasattr(obj, '__module__'):
#             module = inspect.getmodule(obj)
#             if module and hasattr(module, '__file__') and module.__file__:
#                 return Path(module.__file__).resolve()
        
#         # Case 5: Try inspect.getmodule directly
#         else:
#             module = inspect.getmodule(obj)
#             if module and hasattr(module, '__file__') and module.__file__:
#                 return Path(module.__file__).resolve()
                
#     except (OSError, ValueError, AttributeError):
#         # Handle any path resolution or module access errors
#         pass
    
#     return None

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
    return SKPath(Path.cwd())

def equalpaths(path1: Union[str, Path, SKPath], path2: Union[str, Path, SKPath]) -> bool:
    """
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


def id(path: Union[str, Path, SKPath], *, length: int = 32) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import skpath
        
        # Full 32-character ID
        full_id = skpath.id(filepath)
        
        # Short 8-character ID
        short_id = skpath.id(filepath, length=8)
        ```
    ────────────────────────────────────────────────────────\n

    Reproducible path fingerprint with consistent hashing.
    
    Generates an MD5 hash of the absolute path, truncated to the specified length.
    Same path will always generate the same ID across runs and platforms.
    
    Args:
        `path`: Path to generate ID for
        `length`: Length of the hash to return (1-32, default 32)
        
    Returns:
        Reproducible string ID for the path

    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Creating unique cache keys for processed files
        
        @skpath.autopath()
        def process_image(image_path: SKPath):
            cache_key = skpath.id(image_path, length=8)
            cache_file = image_path.root / "cache" / f"processed_{cache_key}.jpg"
            
            if cache_file.exists():
                return cache_file  # Already processed
            
            # Process image and save to cache...
        ```
    ────────────────────────────────────────────────────────
    """

# def _path_id(path: Union[str, Path], short: bool = False) -> str:
#     """
#     Generate a reproducible ID for a path.
    
#     Args:
#         path: Path to generate ID for
#         short: If True, return a shortened version of the ID
#         - full id is 32 characters long
#         - short id is 8 characters long
        
#     Returns:
#         Reproducible string ID for the path
#     """
#     abs_path = str(Path(path).resolve())
    
#     # Create hash
#     hash_obj = hashlib.md5(abs_path.encode())
#     hash_str = hash_obj.hexdigest()
    
#     # Create readable ID from path components
#     path_parts = Path(abs_path).parts
#     if short:
#         # Use only filename and short hash
#         filename = Path(abs_path).stem.replace('.', '_')
#         short_hash = hash_str[:8]
#         return f"{filename}_{short_hash}"
#     else:
#         # Use path components and full hash
#         safe_parts = [part.replace('.', '_').replace('-', '_') for part in path_parts[-3:]]
#         readable = '_'.join(safe_parts)
#         # create an id that is 32 characters long
#         return f"{readable}_{hash_str}"

def get_project_paths(
    *,
    root: Optional[Union[str, Path]] = None,
    exclude: Optional[Union[str, List[str]]] = None,
    as_strings: bool = False,
    use_ignore_files: bool = True
) -> Sequence[Union[SKPath, str]]:
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
        `root`: Custom root directory (defaults to detected project root)
        `exclude`: Paths to exclude from results
        `as_strings`: Return string paths instead of `SKPath` objects (memory efficiency)
        `use_ignore_files`: Respect .*ignore files (default True)
        
    Returns:
        List of paths in the project (`SKPath`s or strings based on `as_strings`)

    ────────────────────────────────────────────────────────
        ```python
        # get all project paths, except paths starting with this/one/path/i/dont/want
        
        # - root allows you to start from subdirectories (default is auto-detected project root)
        # - use_ignore_files=False will include all paths, including .gitignore paths (default is True)
        # - as_strings=True will return a list of strings instead of SKPath objects (default is False)
        # - exclude is a list of paths to exclude from the results (default is None)
        
        proj_path_list = skpath.get_project_paths(exclude="this/one/path/i/dont/want")
        
        # as abspath strings instead of skpaths
        proj_path_list = skpath.get_project_paths(exclude="unwanted", as_strings=True)
        
        # including all normally-ignored paths
        proj_path_list = skpath.get_project_paths(use_ignore_files=False)
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
            all_paths = skpath.get_project_paths(as_strings=True)
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
        - Selective exclusion - `exclude` parameter for custom filtering  
        - Memory efficiency - `as_strings=True` option to avoid creating `SKPath` objects when not needed
        - Customizable root - `root` parameter to use a set root instead of auto-detecting
    """
    # Get raw paths from internal function
    resolved_root = Path(root).resolve() if root is not None else None
    raw = _get_all_project_paths(
        exclude=exclude,
        as_strings=True,  # Always get strings first
        use_ignore_files=use_ignore_files,
        root=resolved_root
    )
    raw_paths: List[str] = [str(p) for p in raw]
    
    if as_strings:
        return raw_paths
    else:
        if resolved_root is not None:
            return [SKPath(path, resolved_root) for path in raw_paths]
        else:
            return [SKPath(path) for path in raw_paths]
    

def get_project_structure(
    *,
    root: Optional[Union[str, Path]] = None,
    exclude: Optional[Union[str, List[str]]] = None,
    use_ignore_files: bool = True
) -> Dict:
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
        `root`: Custom root directory (defaults to detected project root)
        `exclude`: Paths to exclude from results
        `use_ignore_files`: Respect .*ignore files (default True)
        
    Returns:
        Nested dictionary representing directory structure

    ────────────────────────────────────────────────────────
        ```python
        # get a nested dictionary representing your project structure
        
        # - root allows you to start from subdirectories (default is auto-detected project root)
        # - use_ignore_files=False will include all normally-ignored paths (default is True)
        # - exclude is a list of paths to exclude from the results (default is None)
        
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
        - Selective exclusion - `exclude` parameter for custom filtering  
        - Customizable root - `root` parameter to use a set root instead of auto-detecting
    """
    return _get_project_structure(
        root=root,
        exclude=exclude,
        use_ignore_files=use_ignore_files
    )


def get_formatted_project_tree(
    *,
    root: Optional[Union[str, Path]] = None,
    depth: int = 3,
    include_files: bool = True,
    exclude: Optional[Union[str, List[str]]] = None,
    use_ignore_files: bool = True
) -> str:
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
        `root`: Custom root directory (defaults to detected project root)
        `depth`: Maximum depth to display (prevents huge output)
        `include_files`: Whether to show files or just directories
        `exclude`: Paths to exclude from results
        `use_ignore_files`: Respect `.*ignore` files (default `True`)

    Returns:
        Formatted string representing directory structure

    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Project documentation generation

        def generate_project_structure_overview():
            \"\"\"Generate markdown documentation with project structure.\"\"\"

            tree = skpath.get_formatted_project_tree(
                include_files=False,  # Just directories for overview
                depth=3
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
        - Selective exclusion - `exclude` parameter for custom filtering  
        - Customizable root - `root` parameter to use a set root instead of auto-detecting
        - Depth limiting with `depth` to prevent huge output
    """
    return _get_formatted_project_tree(
        root=root,
        depth=depth,
        include_files=include_files,
        exclude=exclude,
        use_ignore_files=use_ignore_files
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

# implement this here and make sure everything works as expected

# def _force_project_root(path: Union[str, Path]) -> None:
#     """
#     Force the project root to a specific path globally.
    
#     Args:
#         path: Path to use as project root
#     """
#     _global_detector.force_project_root(path)
#     # Clear cache when forcing a new root
#     with _cache_lock:
#         # Save current auto-detected root before overriding
#         global _previous_auto_root, _previous_auto_cache_key
#         _previous_auto_root = _project_root_cache['root']
#         _previous_auto_cache_key = _project_root_cache['cache_key']
#         _project_root_cache['cache_key'] = None
#         _project_root_cache['root'] = None


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
# def _clear_forced_project_root() -> None:
#     """Clear any forced project root, returning to auto-detection."""
#     _global_detector.clear_forced_root()
#     # Restore previous auto-detected root if available; otherwise clear
#     with _cache_lock:
#         global _previous_auto_root, _previous_auto_cache_key
#         if _previous_auto_root is not None and _previous_auto_cache_key is not None:
#             _project_root_cache['cache_key'] = _previous_auto_cache_key
#             _project_root_cache['root'] = _previous_auto_root
#         else:
#             _project_root_cache['cache_key'] = None
#             _project_root_cache['root'] = None
#         _previous_auto_root = None
#         _previous_auto_cache_key = None


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

# def _get_forced_project_root() -> Optional[Path]:
#     """Get the currently forced project root, if any."""
#     return _global_detector.get_forced_root()


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
    'id',
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