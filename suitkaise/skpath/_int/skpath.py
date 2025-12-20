


class PathDetectionError(RuntimeError):
    """
    Exception raised when automatic detection fails in SKPath operations.
    
    This occurs when SKPath cannot automatically detect:
    - Caller file paths (for zero-argument SKPath initialization)
    - Project root directories
    - Module file paths
    
    Solutions:
    1. Provide explicit parameters instead of relying on auto-detection
    2. Ensure you're running from a valid project with proper structure
    3. Use force_project_root() to manually set the project root
    """
    
    def __init__(self, detection_type: str, context: str = ""):
        self.detection_type = detection_type
        self.context = context
        
        if context:
            message = f"Could not auto-detect {detection_type} in {context}. Please provide explicit parameters."
        else:
            message = f"Could not auto-detect {detection_type}. Please provide explicit parameters."
            
        super().__init__(message)


class MultiplePathsError(ValueError):
    """
    Exception raised when SKPath encounters multiple files with the same name.
    
    This occurs when trying to create an SKPath with just a filename (e.g., 'api.py')
    and multiple files with that name exist under the project root.
    
    Recommended solutions:
    1. Use relative paths: SKPath('feature1/api.py') vs SKPath('feature2/api.py')
    2. Use unique filenames: SKPath('feature1_api.py') vs SKPath('feature2_api.py')
    """
    
    def __init__(self, filename: str, matches: List[Path], project_root: Path):
        """
        Initialize MultiplePathsError with detailed information.
        
        Args:
            filename: The ambiguous filename that was requested
            matches: List of absolute paths that matched the filename
            project_root: The project root where the search was performed
        """
        relative_matches = [match.relative_to(project_root) for match in matches]
        
        message = (
            f"Ambiguous path '{filename}' - found {len(matches)} matches under project root:\n" +
            "\n".join(f"  - {match}" for match in relative_matches) +
            f"\n\nRecommended solutions:\n" +
            f"  1. Use relative paths: SKPath('{relative_matches[0].parent}/{filename}')\n" +
            f"  2. Use unique filenames: SKPath('{relative_matches[0].parent.name}_{filename}')\n" +
            f"\nFor better project organization, consider:\n" +
            f"  - Using descriptive directory structures (feature1/api.py, feature2/api.py)\n" +
            f"  - Adopting unique naming conventions (feature1_api.py, feature2_api.py)"
        )
        
        super().__init__(message)
        self.filename = filename
        self.matches = matches
        self.project_root = project_root
        self.relative_matches = relative_matches

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
            `PathDetectionError`: If `path` is `None` and caller detection fails
            `FileNotFoundError`: If provided `path` doesn't exist under project root
            `MultiplePathsError`: If ambiguous filename matches multiple files
        """
        # Handle zero-argument magic initialization
        if path is None:
            try:
                caller_file = _get_non_sk_caller_file_path()
                if caller_file is None:
                    raise PathDetectionError("caller file path", "SKPath initialization")
            except RuntimeError:
                raise PathDetectionError("caller file path", "SKPath initialization")
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

    def id(self, length: int = 32) -> str:
        """
        Return the path ID based on absolute path.
        
        Each unique absolute path gets a unique ID, ensuring that multiple
        `SKPath` objects pointing to the same file will have the same ID,
        regardless of how they were created (relative vs absolute input).
        
        Args:
            length: Length of the hash to return (1-32, default 32)
        
        Returns:
            MD5-based path identifier truncated to specified length
        """
        return id(self, length=length)
    
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