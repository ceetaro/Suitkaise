"""
SKPath Class

Enhanced path object with automatic project root detection, 
cross-platform path normalization, and rich functionality.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

from .caller_paths import detect_caller_path
from .exceptions import PathDetectionError
from .id_utils import (
    decode_path_id,
    encode_path_id,
    hash_path_md5,
    is_valid_encoded_id,
    normalize_separators,
    to_os_separators,
)
from .root_detection import detect_project_root

# Thread-safe lock for SKPath operations
_skpath_lock = threading.RLock()


class SKPath:
    """
    Enhanced path object with project-aware normalization.
    
    SKPath automatically detects your project root and provides:
    - `ap`: Absolute path with normalized separators (/)
    - `np`: Normalized path relative to project root
    - `id`: Reversible encoded ID for the path
    - Full pathlib.Path compatibility
    
    Usage:
        # Create from caller's file path
        path = SKPath()
        
        # Create from string or Path
        path = SKPath("myproject/feature/file.txt")
        path = SKPath(Path("myproject/feature/file.txt"))
        
        # Create from encoded ID
        path = SKPath(encoded_id_string)
        
    Properties mirror pathlib.Path: name, stem, suffix, suffixes, parent, 
    parts, exists, is_file, is_dir, etc.
    """
    
    __slots__ = ("_path", "_root", "_ap", "_np", "_id", "_hash")
    
    def __init__(
        self,
        path: str | Path | "SKPath" | None = None,
        *,
        _skip_frames: int = 0,
    ):
        """
        Initialize an SKPath.
        
        Args:
            path: Path to wrap. Can be:
                - None: Use caller's file path
                - str: Path string or encoded ID
                - Path: pathlib.Path object
                - SKPath: Another SKPath (copies values)
                
            _skip_frames: Internal - additional stack frames to skip
        """
        self._path: Path
        self._root: Path | None = None
        self._ap: str | None = None
        self._np: str | None = None
        self._id: str | None = None
        self._hash: int | None = None
        
        # Handle None - use caller's path
        if path is None:
            self._path = detect_caller_path(skip_frames=_skip_frames + 1)
        
        # Handle SKPath - copy values
        elif isinstance(path, SKPath):
            self._path = path._path
            self._root = path._root
            self._ap = path._ap
            self._np = path._np
            self._id = path._id
            self._hash = path._hash
        
        # Handle Path
        elif isinstance(path, Path):
            self._path = path.resolve()
        
        # Handle string
        elif isinstance(path, str):
            self._path = self._resolve_string_path(path, _skip_frames + 1)
        
        else:
            raise TypeError(
                f"SKPath expects str, Path, SKPath, or None, got {type(path).__name__}"
            )
    
    def _resolve_string_path(self, path_str: str, skip_frames: int) -> Path:
        """
        Resolve a string to a Path, trying both path and encoded ID interpretations.
        
        Priority:
        1. If it looks like a path (has separators or exists), use as path
        2. If it could be an encoded ID, try to decode it
        3. Fall back to treating as path
        """
        # Check if it looks like a path (has separators)
        if "/" in path_str or "\\" in path_str:
            return Path(path_str).resolve()
        
        # Check if the path exists as-is (relative path without separators)
        test_path = Path(path_str)
        if test_path.exists():
            return test_path.resolve()
        
        # Try as encoded ID
        if is_valid_encoded_id(path_str):
            decoded = decode_path_id(path_str)
            if decoded is not None:
                decoded_path = Path(decoded)
                # If decoded path is relative, resolve from project root
                if not decoded_path.is_absolute():
                    try:
                        root = detect_project_root()
                        full_path = root / decoded_path
                        if full_path.exists():
                            return full_path.resolve()
                    except PathDetectionError:
                        pass
                elif decoded_path.exists():
                    return decoded_path.resolve()
        
        # Fall back to treating as path (may not exist, that's OK)
        return Path(path_str).resolve()
    
    # ========================================================================
    # Core Properties
    # ========================================================================
    
    @property
    def ap(self) -> str:
        """
        Absolute path with normalized separators (/).
        
        Always available, even for paths outside project root.
        """
        if self._ap is None:
            self._ap = normalize_separators(str(self._path))
        return self._ap
    
    @property
    def np(self) -> str:
        """
        Normalized path relative to project root.
        
        Returns empty string if path is outside project root.
        """
        if self._np is None:
            self._np = self._compute_np()
        return self._np
    
    def _compute_np(self) -> str:
        """Compute the normalized path relative to project root."""
        try:
            root = self.root_path
            rel_path = self._path.relative_to(root)
            return normalize_separators(str(rel_path))
        except (ValueError, PathDetectionError):
            # Path is outside project root or root couldn't be detected
            return ""
    
    @property
    def id(self) -> str:
        """
        Reversible encoded ID for the path.
        
        Uses base64url encoding of np (if available) or ap.
        Can be used to reconstruct the SKPath: SKPath(encoded_id)
        """
        if self._id is None:
            # Prefer np for cross-platform compatibility
            path_to_encode = self.np if self.np else self.ap
            self._id = encode_path_id(path_to_encode)
        return self._id
    
    @property
    def root(self) -> str:
        """
        Project root path as string with normalized separators.
        """
        return normalize_separators(str(self.root_path))
    
    @property
    def root_path(self) -> Path:
        """
        Project root as Path object.
        
        Raises:
            PathDetectionError: If project root cannot be detected
        """
        if self._root is None:
            self._root = detect_project_root(from_path=self._path)
        return self._root
    
    # ========================================================================
    # pathlib.Path Compatible Properties
    # ========================================================================
    
    @property
    def name(self) -> str:
        """The final component of the path (filename with extension)."""
        return self._path.name
    
    @property
    def stem(self) -> str:
        """The final component without its suffix."""
        return self._path.stem
    
    @property
    def suffix(self) -> str:
        """The file extension of the final component."""
        return self._path.suffix
    
    @property
    def suffixes(self) -> list[str]:
        """A list of all file extensions."""
        return self._path.suffixes
    
    @property
    def parent(self) -> "SKPath":
        """The parent directory as an SKPath."""
        return SKPath(self._path.parent)
    
    @property
    def parents(self) -> tuple["SKPath", ...]:
        """All parent directories as SKPath objects."""
        return tuple(SKPath(p) for p in self._path.parents)
    
    @property
    def parts(self) -> tuple[str, ...]:
        """The path components as a tuple."""
        return self._path.parts
    
    @property
    def exists(self) -> bool:
        """Whether the path exists."""
        return self._path.exists()
    
    @property
    def is_file(self) -> bool:
        """Whether the path is a file."""
        return self._path.is_file()
    
    @property
    def is_dir(self) -> bool:
        """Whether the path is a directory."""
        return self._path.is_dir()
    
    @property
    def is_symlink(self) -> bool:
        """Whether the path is a symbolic link."""
        return self._path.is_symlink()
    
    @property
    def stat(self) -> os.stat_result:
        """
        Return stat info for the path.
        
        Raises:
            FileNotFoundError: If path doesn't exist
        """
        return self._path.stat()
    
    @property
    def lstat(self) -> os.stat_result:
        """
        Return stat info for the path (don't follow symlinks).
        
        Raises:
            FileNotFoundError: If path doesn't exist
        """
        return self._path.lstat()
    
    # ========================================================================
    # Additional Properties
    # ========================================================================
    
    @property
    def as_dict(self) -> dict[str, Any]:
        """
        Get a dictionary representation of the path.
        
        Returns:
            Dict with ap, np, root, name, and exists
        """
        return {
            "ap": self.ap,
            "np": self.np,
            "root": self.root if self._root else None,
            "name": self.name,
            "exists": self.exists,
        }
    
    # ========================================================================
    # pathlib.Path Compatible Methods
    # ========================================================================
    
    def iterdir(self) -> Generator["SKPath", None, None]:
        """
        Iterate over directory contents.
        
        Yields:
            SKPath for each item in the directory
            
        Raises:
            NotADirectoryError: If path is not a directory
        """
        for item in self._path.iterdir():
            yield SKPath(item)
    
    def glob(self, pattern: str) -> Generator["SKPath", None, None]:
        """
        Find paths matching a pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.txt")
            
        Yields:
            SKPath for each matching path
        """
        for item in self._path.glob(pattern):
            yield SKPath(item)
    
    def rglob(self, pattern: str) -> Generator["SKPath", None, None]:
        """
        Recursively find paths matching a pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.txt")
            
        Yields:
            SKPath for each matching path
        """
        for item in self._path.rglob(pattern):
            yield SKPath(item)
    
    def relative_to(self, other: str | Path | "SKPath") -> "SKPath":
        """
        Get the path relative to another path.
        
        Args:
            other: Base path to be relative to
            
        Returns:
            New SKPath with the relative path
            
        Raises:
            ValueError: If this path is not relative to other
        """
        if isinstance(other, SKPath):
            other_path = other._path
        elif isinstance(other, str):
            other_path = Path(other).resolve()
        else:
            other_path = other.resolve()
        
        rel = self._path.relative_to(other_path)
        return SKPath(rel)
    
    def with_name(self, name: str) -> "SKPath":
        """
        Return a new path with the name changed.
        
        Args:
            name: New filename (e.g., "newfile.txt")
            
        Returns:
            New SKPath with the changed name
        """
        return SKPath(self._path.with_name(name))
    
    def with_stem(self, stem: str) -> "SKPath":
        """
        Return a new path with the stem changed.
        
        Args:
            stem: New stem (filename without extension)
            
        Returns:
            New SKPath with the changed stem
        """
        return SKPath(self._path.with_stem(stem))
    
    def with_suffix(self, suffix: str) -> "SKPath":
        """
        Return a new path with the suffix changed.
        
        Args:
            suffix: New suffix (e.g., ".txt")
            
        Returns:
            New SKPath with the changed suffix
        """
        return SKPath(self._path.with_suffix(suffix))
    
    def mkdir(
        self,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        """
        Create the directory.
        
        Args:
            mode: Directory permissions (default: 0o777)
            parents: Create parent directories if needed
            exist_ok: Don't raise if directory exists
        """
        self._path.mkdir(mode=mode, parents=parents, exist_ok=exist_ok)
    
    def touch(self, mode: int = 0o666, exist_ok: bool = True) -> None:
        """
        Create the file if it doesn't exist, or update its timestamp.
        
        Args:
            mode: File permissions (default: 0o666)
            exist_ok: Don't raise if file exists
        """
        self._path.touch(mode=mode, exist_ok=exist_ok)
    
    def resolve(self) -> "SKPath":
        """
        Return the absolute path, resolving any symlinks.
        
        Returns:
            New SKPath with resolved path
        """
        return SKPath(self._path.resolve())
    
    def absolute(self) -> "SKPath":
        """
        Return an absolute version of the path.
        
        Returns:
            New SKPath with absolute path
        """
        return SKPath(self._path.absolute())
    
    # ========================================================================
    # Dunder Methods
    # ========================================================================
    
    def __str__(self) -> str:
        """Return the absolute path with normalized separators."""
        return self.ap
    
    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        display_path = self.np if self.np else self.ap
        return f"SKPath('{display_path}')"
    
    def __fspath__(self) -> str:
        """
        Return the path for os.fspath() compatibility.
        
        Uses OS-native separators for file system operations.
        """
        return to_os_separators(self.ap)
    
    def __truediv__(self, other: str | Path | "SKPath") -> "SKPath":
        """
        Join paths using the / operator.
        
        Args:
            other: Path component to append
            
        Returns:
            New SKPath with joined path
        """
        if isinstance(other, SKPath):
            other_str = other._path.name if other._path.is_absolute() else str(other._path)
        elif isinstance(other, Path):
            other_str = str(other)
        else:
            other_str = other
        
        return SKPath(self._path / other_str)
    
    def __rtruediv__(self, other: str | Path) -> "SKPath":
        """Support path / skpath syntax."""
        if isinstance(other, Path):
            return SKPath(other / self._path)
        else:
            return SKPath(Path(other) / self._path)
    
    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another path.
        
        Converts both to SKPath and compares:
        1. First by normalized path (np)
        2. Falls back to absolute path (ap) if np's aren't equal
        """
        if other is None:
            return False
        
        try:
            # Convert to SKPath if needed
            if isinstance(other, SKPath):
                other_skpath = other
            elif isinstance(other, (str, Path)):
                other_skpath = SKPath(other)
            else:
                return NotImplemented
            
            # Compare np first
            if self.np and other_skpath.np and self.np == other_skpath.np:
                return True
            
            # Fall back to ap comparison
            return self.ap == other_skpath.ap
            
        except (PathDetectionError, TypeError):
            return False
    
    def __ne__(self, other: Any) -> bool:
        """Check inequality."""
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result
    
    def __hash__(self) -> int:
        """
        Return hash for use in sets and dict keys.
        
        Uses MD5 hash of np (or ap if outside project root).
        """
        if self._hash is None:
            path_to_hash = self.np if self.np else self.ap
            self._hash = hash_path_md5(path_to_hash)
        return self._hash
    
    def __bool__(self) -> bool:
        """SKPath is always truthy (path exists or not)."""
        return True
    
    def __len__(self) -> int:
        """Return the number of path parts."""
        return len(self.parts)
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over path parts."""
        return iter(self.parts)
    
    def __contains__(self, item: str) -> bool:
        """Check if a string is in the path parts."""
        return item in self.parts
