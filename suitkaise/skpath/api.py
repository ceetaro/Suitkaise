class SKPath:
    """
    A smart path object that maintains both absolute and normalized paths.
    
    SKPath provides easy access to both the full system path and the path
    relative to the project root, with intelligent string conversion for
    compatibility with standard path operations.

    """
    
    def __init__(self, path: Union[str, Path], project_root: Optional[Path] = None):
        """
        Initialize an SKPath object.
        
        Args:
            path: The path to wrap (can be relative or absolute)
            project_root: Project root path (auto-detected if None)
        """
        self._absolute_path = Path(path).resolve() or _get_non_sk_caller_file_path()
        self._project_root = project_root or _get_project_root(self._absolute_path)
        self._normalized_path = self._calculate_normalized_path()

    def _calculate_normalized_path(self) -> str:
        """Calculate the normalized path relative to project root."""
        if self._project_root is None:
            # If we can't find project root, normalized path is just the filename
            return self._absolute_path.name
        
        try:
            # Get path relative to project root
            relative_path = self._absolute_path.relative_to(self._project_root)
            return str(relative_path)
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
    def parent(self) -> 'SKPath':
        """The parent directory as an SKPath."""
        return SKPath(self._absolute_path.parent, self._project_root)
    
    def exists(self) -> bool:
        """Check if the path exists."""
        return self._absolute_path.exists()
    
    def is_file(self) -> bool:
        """Check if the path is a file."""
        return self._absolute_path.is_file()
    
    def is_dir(self) -> bool:
        """Check if the path is a directory."""
        return self._absolute_path.is_dir()
    
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
    
def create(path: Optional[Union[str, Path]], 
                project_root: Optional[Path] = None) -> SKPath:
    """
    Create an SKPath object from a given path.
    
    Args:
        path: The path to convert to SKPath
        project_root: Project root path (auto-detected if None)
        
    Returns:
        SKPath object
    """
    return SKPath(path, project_root)