def _parse_gitignore_file(gitignore_path: Path) -> Set[str]:
    """
    Parse a .gitignore or .dockerignore file and extract ignore patterns.
    
    Args:
        gitignore_path: Path to the ignore file
        
    Returns:
        Set of ignore patterns from the file
    """
    patterns = set()
    
    if not gitignore_path.exists():
        return patterns
    
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Remove leading slash for consistency
                if line.startswith('/'):
                    line = line[1:]
                
                # Convert gitignore patterns to fnmatch patterns
                # Simple conversion - more sophisticated parsing could be added
                patterns.add(line)
                
    except (OSError, UnicodeDecodeError):
        # If we can't read the file, return empty set
        pass
    
    return patterns


def _get_cached_ignore_patterns(project_root: Path) -> Set[str]:
    """
    Get ignore patterns for a project root with caching.
    
    Caches patterns based on project root and modification times of ignore files.
    Cache is invalidated if any ignore file is modified or if different project root.
    
    Args:
        project_root: Project root directory to scan for ignore files
        
    Returns:
        Set of ignore patterns from all .*ignore files
    """
    if not project_root or not project_root.exists():
        return set()
    
    # Find all ignore files and their modification times
    ignore_files = []
    try:
        for item in project_root.iterdir():
            if item.is_file() and item.name.startswith('.') and 'ignore' in item.name:
                try:
                    mtime = item.stat().st_mtime
                    ignore_files.append((item, mtime))
                except (OSError, PermissionError):
                    continue
    except (OSError, PermissionError):
        # Fallback to specific known ignore files if directory scan fails
        for ignore_name in ['.gitignore', '.dockerignore']:
            ignore_path = project_root / ignore_name
            if ignore_path.exists():
                try:
                    mtime = ignore_path.stat().st_mtime
                    ignore_files.append((ignore_path, mtime))
                except (OSError, PermissionError):
                    continue
    
    # Create cache key from project root and file modification times
    cache_key = str(project_root) + '|' + '|'.join(f"{path}:{mtime}" for path, mtime in ignore_files)
    
    # Check cache
    with _cache_lock:
        if (_ignore_patterns_cache['cache_key'] == cache_key and 
            _ignore_patterns_cache['patterns'] is not None and
            time.time() - _ignore_patterns_cache['timestamp'] < 300):  # 5 minute cache
            return _ignore_patterns_cache['patterns'].copy()
    
    # Cache miss - parse all ignore files
    patterns = set()
    for ignore_path, _ in ignore_files:
        patterns.update(_parse_gitignore_file(ignore_path))
    
    # Update cache
    with _cache_lock:
        _ignore_patterns_cache['cache_key'] = cache_key
        _ignore_patterns_cache['patterns'] = patterns.copy()
        _ignore_patterns_cache['timestamp'] = time.time()
    
    return patterns


def _get_all_project_paths(except_paths: Optional[Union[str, List[str]]] = None,
                          as_str: bool = False,
                          ignore: bool = True,
                          force_root: Optional[Union[str, Path]] = None) -> List[Union[Path, str]]:
    """
    Get all paths in the current project.
    
    Args:
        except_paths: Paths to exclude from results
        as_str: Return string paths instead of Path objects
        ignore: Respect .gitignore and .dockerignore files (default True)
        force_root: Force a specific project root
        
    Returns:
        List of paths in the project
    """
    if force_root:
        project_root = Path(force_root).resolve()
    else:
        project_root = _get_project_root()
    
    if project_root is None:
        return []
    
    # Convert except_paths to set for faster lookup
    if except_paths is None:
        except_set = set()
    elif isinstance(except_paths, str):
        except_set = {except_paths}
    else:
        except_set = set(except_paths)
    
    # Default ignore patterns
    ignore_patterns = {
        '__pycache__', '.git', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', 'env', '.env',
        'dist', 'build', '*.egg-info'
    } if not ignore else set()
    
    # Add patterns from all .*ignore files using cached function
    if not ignore:
        ignore_patterns.update(_get_cached_ignore_patterns(project_root))
    
    all_paths = []
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored."""
        path_name = path.name
        
        # Check except_paths
        if path_name in except_set:
            return True
        
        # Check ignore patterns
        if ignore:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(path_name.lower(), pattern.lower()):
                    return True
        
        return False
    
    # Walk the project directory
    try:
        for root, dirs, files in os.walk(project_root):
            root_path = Path(root)
            
            # Filter directories in-place to avoid walking ignored dirs
            dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]
            
            # Add files
            for file in files:
                file_path = root_path / file
                if not should_ignore(file_path):
                    if as_str:
                        all_paths.append(str(file_path))
                    else:
                        all_paths.append(file_path)
    
    except (PermissionError, OSError):
        # If we can't walk the directory, return empty list
        pass
    
    return all_paths


def _get_project_structure(force_root: Optional[Union[str, Path]] = None,
                          except_paths: Optional[Union[str, List[str]]] = None,
                          ignore: bool = True) -> Dict:
    """
    Get a nested dictionary representing the project structure.
    
    Args:
        force_root: Custom root directory (defaults to detected project root)
        except_paths: Paths to exclude from results
        ignore: Include paths that would normally be ignored
        
    Returns:
        Nested dictionary representing directory structure
    """
    if force_root is None:
        root = _get_project_root()
    else:
        root = Path(force_root).resolve()
    
    if root is None or not root.exists():
        return {}
    
    # Convert except_paths to set for faster lookup
    if except_paths is None:
        except_set = set()
    elif isinstance(except_paths, str):
        except_set = {except_paths}
    else:
        except_set = set(except_paths)
    
    # Default ignore patterns
    ignore_patterns = {
        '__pycache__', '.git', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', 'env', '.env',
        'dist', 'build', '*.egg-info'
    } if not ignore else set()
    
    # Add patterns from all .*ignore files using cached function
    if not ignore:
        ignore_patterns.update(_get_cached_ignore_patterns(root))
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored."""
        path_name = path.name
        
        # Check except_paths
        if path_name in except_set:
            return True
        
        # Check ignore patterns
        if ignore:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(path_name.lower(), pattern.lower()):
                    return True
        
        return False
    
    def build_structure(path: Path) -> Dict:
        """Recursively build structure dictionary."""
        structure = {}
        
        try:
            for item in path.iterdir():
                if should_ignore(item):
                    continue
                    
                if item.is_dir():
                    structure[item.name] = build_structure(item)
                else:
                    structure[item.name] = 'file'
        except PermissionError:
            pass
        
        return structure
    
    return build_structure(root)


def _get_formatted_project_tree(force_root: Optional[Union[str, Path]] = None,
                                max_depth: int = 3,
                                show_files: bool = True,
                                except_paths: Optional[Union[str, List[str]]] = None,
                                ignore: bool = True) -> str:
    """
    Get a formatted string representation of the project structure.

    Uses tree-like characters (│, ├─, └─) to create a visual hierarchy.
    
    Args:
        force_root: Custom root directory (defaults to detected project root)
        max_depth: Maximum depth to display (prevents huge output)
        show_files: Whether to show files or just directories
        except_paths: Paths to exclude from results
        ignore: Include paths that would normally be ignored (default True)
        
    Returns:
        Formatted string representing directory structure
    """
    # Ensure unicode box drawing is supported (per fdl/_int/setup/unicode.py)
    try:
        from ...fdl._int.setup.unicode import _supports_box_drawing
        if not _supports_box_drawing():
            raise RuntimeError(
                "Unicode tree characters are not supported; cannot render formatted project tree. "
                "Use get_project_structure() for programmatic access or enable a unicode-capable terminal."
            )
    except Exception as e:
        # If detection import fails or unicode unsupported, raise a clear error as requested
        raise RuntimeError(
            f"Unicode capability check failed or unsupported for formatted project tree: {e}"
        )

    if force_root is None:
        root = _get_project_root()
    else:
        root = Path(force_root).resolve()
    
    if root is None or not root.exists():
        return "No project root found"
    
    # Convert except_paths to set for faster lookup
    if except_paths is None:
        except_set = set()
    elif isinstance(except_paths, str):
        except_set = {except_paths}
    else:
        except_set = set(except_paths)
    
    # Default ignore patterns
    ignore_patterns = {
        '__pycache__', '.git', '.pytest_cache', '.mypy_cache',
        'node_modules', '.venv', 'venv', 'env', '.env',
        'dist', 'build', '*.egg-info'
    } if not ignore else set()
    
    # Add patterns from all .*ignore files using cached function
    if not ignore:
        ignore_patterns.update(_get_cached_ignore_patterns(root))
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored."""
        path_name = path.name
        
        # Check except_paths
        if path_name in except_set:
            return True
        
        # Check ignore patterns
        if ignore:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(path_name.lower(), pattern.lower()):
                    return True
        
        return False
    
    def format_tree(path: Path, prefix: str = "", depth: int = 0) -> List[str]:
        """Recursively format the tree structure."""
        if depth > max_depth:
            return []
        
        lines = []
        
        try:
            # Get directory contents, separated into dirs and files
            items = list(path.iterdir())
            
            # Filter out ignored items
            dirs = [item for item in items if item.is_dir() and not should_ignore(item)]
            files = [item for item in items if item.is_file() and not should_ignore(item)] if show_files else []
            
            # Sort for consistent output
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())
            
            all_items = dirs + files
            
            for i, item in enumerate(all_items):
                is_last = i == len(all_items) - 1
                
                # Choose the appropriate tree characters
                current_prefix = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")
                
                # Add the current item
                if item.is_dir():
                    lines.append(f"{prefix}{current_prefix}{item.name}/")
                    # Recursively add subdirectory contents
                    lines.extend(format_tree(item, next_prefix, depth + 1))
                else:
                    lines.append(f"{prefix}{current_prefix}{item.name}")
                    
        except PermissionError:
            lines.append(f"{prefix}[Permission Denied]")
        
        return lines
    
    # Start the tree with the root directory name
    tree_lines = [f"{root.name}/"]
    tree_lines.extend(format_tree(root))
    
    return "\n".join(tree_lines)