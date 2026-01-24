"""
Skpath Class

Enhanced path object with automatic project root detection, 
cross-platform path normalization, and rich functionality.
"""

from __future__ import annotations

import os
import shutil
import threading
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

from .caller_paths import detect_caller_path
from .exceptions import PathDetectionError, NotAFileError
from .id_utils import (
    decode_path_id,
    encode_path_id,
    hash_path_md5,
    is_valid_encoded_id,
    normalize_separators,
    to_os_separators,
)
from .root_detection import detect_project_root

# thread-safe lock for Skpath operations
_skpath_lock = threading.RLock()


class Skpath:
    """
    Enhanced path object with project-aware normalization.
    
    Skpath automatically detects your project root and provides:
    - `ap`: Absolute path with normalized separators (/)
    - `rp`: Path relative to project root
    - `id`: Reversible encoded ID for the path
    - Full pathlib.Path compatibility
    
    Usage:
        # Create from caller's file path
        path = Skpath()
        
        # Create from string or Path
        path = Skpath("myproject/feature/file.txt")
        path = Skpath(Path("myproject/feature/file.txt"))
        
        # Create from encoded ID
        path = Skpath(encoded_id_string)
        
    Properties mirror pathlib.Path: name, stem, suffix, suffixes, parent, 
    parts, exists, is_file, is_dir, etc.
    """
    
    __slots__ = ("_path", "_root", "_ap", "_rp", "_id", "_hash")

    @classmethod
    def _from_path(cls, path: Path, root: Path | None = None) -> "Skpath":
        """
        Fast-path constructor from a resolved Path.

        Skips path resolution and root detection for bulk scans.
        """
        obj = cls.__new__(cls)
        obj._path = path
        obj._root = root
        obj._ap = None
        obj._rp = None
        obj._id = None
        obj._hash = None
        return obj
    
    def __init__(
        self,
        path: str | Path | "Skpath" | None = None,
        *,
        _skip_frames: int = 0,
    ):
        """
        Initialize an Skpath.
        
        Args:
            path: Path to wrap. Can be:
                - None: Use caller's file path
                - str: Path string or encoded ID
                - Path: pathlib.Path object
                - Skpath: Another Skpath (copies values)
                
            _skip_frames: Internal - additional stack frames to skip
        """
        self._path: Path
        self._root: Path | None = None
        self._ap: str | None = None
        self._rp: str | None = None
        self._id: str | None = None
        self._hash: int | None = None
        
        # handle None - use caller's path
        if path is None:
            self._path = detect_caller_path(skip_frames=_skip_frames + 1)
        
        # handle Skpath - copy values
        elif isinstance(path, Skpath):
            self._path = path._path
            self._root = path._root
            self._ap = path._ap
            self._rp = path._rp
            self._id = path._id
            self._hash = path._hash
        
        # handle Path
        elif isinstance(path, Path):
            self._path = path.resolve()
        
        # handle string
        elif isinstance(path, str):
            self._path = self._resolve_string_path(path, _skip_frames + 1)
        
        else:
            raise TypeError(
                f"Skpath expects str, Path, Skpath, or None, got {type(path).__name__}"
            )
    
    def _resolve_string_path(self, path_str: str, skip_frames: int) -> Path:
        """
        Resolve a string to a Path, trying both path and encoded ID interpretations.
        
        Priority:
        1. If it looks like a path (has separators or exists), use as path
        2. If it could be an encoded ID, try to decode it
        3. Fall back to treating as path
        """
        # check if it looks like a path (has separators)
        if "/" in path_str or "\\" in path_str:
            return Path(path_str).resolve()
        
        # check if the path exists as-is (relative path without separators)
        test_path = Path(path_str)
        if test_path.exists():
            return test_path.resolve()
        
        # try as encoded ID
        if is_valid_encoded_id(path_str):
            decoded = decode_path_id(path_str)
            if decoded is not None:
                decoded_path = Path(decoded)
                # if decoded path is relative, resolve from project root
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
        
        # fall back to treating as path (may not exist, that's OK)
        return Path(path_str).resolve()


    
    # core properties

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
    def rp(self) -> str:
        """
        Relative path to project root (with normalized separators).
        
        Returns empty string if path is outside project root.
        """
        if self._rp is None:
            self._rp = self._compute_rp()
        return self._rp
    
    def _compute_rp(self) -> str:
        """Compute the relative path to project root."""
        try:
            root = self.root_path
            rel_path = self._path.relative_to(root)
            return normalize_separators(str(rel_path))
        except (ValueError, PathDetectionError):
            # path is outside project root or root couldn't be detected
            return ""
    
    @property
    def id(self) -> str:
        """
        Reversible encoded ID for the path.
        
        Uses base64url encoding of rp (if available) or ap.
        Can be used to reconstruct the Skpath: Skpath(encoded_id)
        """
        if self._id is None:
            # prefer rp for cross-platform compatibility
            path_to_encode = self.rp if self.rp else self.ap
            self._id = encode_path_id(path_to_encode)
        return self._id


    @property
    def root(self) -> "Skpath":
        """
        Project root as Skpath object.
        """
        return Skpath(self.root_path)
    
    @property
    def root_str(self) -> str:
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
    


    # pathlib compatible properties

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
    def parent(self) -> "Skpath":
        """The parent directory as an Skpath."""
        return Skpath(self._path.parent)
    
    @property
    def parents(self) -> tuple["Skpath", ...]:
        """All parent directories as Skpath objects."""
        return tuple(Skpath(p) for p in self._path.parents)
    
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
    def is_empty(self) -> bool:
        """Whether the path is an empty directory (no files or subdirs).
        
        Raises:
            NotADirectoryError: If path is not a directory
        """
        if not self._path.is_dir():
            raise NotADirectoryError(f"is_empty requires a directory: {self._path}")
        # use any() with iterdir() for early exit - faster than list()
        return not any(self._path.iterdir())
    
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
    


    # additional properties
    
    @property
    def as_dict(self) -> dict[str, Any]:
        """
        Get a dictionary representation of the path.
        
        Returns:
            Dict with ap, rp, root, name, and exists
        """
        return {
            "ap": self.ap,
            "rp": self.rp,
            "root": self.root if self._root else None,
            "name": self.name,
            "exists": self.exists,
        }

    
    @property
    def platform(self) -> str:
        """
        Absolute path with platform-native separators.
        
        On Windows, uses backslashes (\\).
        On Mac/Linux, uses forward slashes (/).
        
        Use this when you need to pass a path to OS-specific tools,
        display paths to users in their native format, or integrate
        with platform-specific APIs.
        """
        return to_os_separators(self.ap)
    
    

    # pathlib methods

    def iterdir(self) -> Generator["Skpath", None, None]:
        """
        Iterate over directory contents.
        
        Yields:
            Skpath for each item in the directory
            
        Raises:
            NotADirectoryError: If path is not a directory
        """
        for item in self._path.iterdir():
            yield Skpath(item)
    
    def glob(self, pattern: str) -> Generator["Skpath", None, None]:
        """
        Find paths matching a pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.txt")
            
        Yields:
            Skpath for each matching path
        """
        for item in self._path.glob(pattern):
            yield Skpath(item)
    
    def rglob(self, pattern: str) -> Generator["Skpath", None, None]:
        """
        Recursively find paths matching a pattern.
        
        Args:
            pattern: Glob pattern (e.g., "*.txt")
            
        Yields:
            Skpath for each matching path
        """
        for item in self._path.rglob(pattern):
            yield Skpath(item)
    
    def relative_to(self, other: str | Path | "Skpath") -> "Skpath":
        """
        Get the path relative to another path.
        
        Args:
            other: Base path to be relative to
            
        Returns:
            New Skpath with the relative path
            
        Raises:
            ValueError: If this path is not relative to other
        """
        if isinstance(other, Skpath):
            other_path = other._path
        elif isinstance(other, str):
            other_path = Path(other).resolve()
        else:
            other_path = other.resolve()
        
        rel = self._path.relative_to(other_path)
        return Skpath(rel)
    
    def with_name(self, name: str) -> "Skpath":
        """
        Return a new path with the name changed.
        
        Args:
            name: New filename (e.g., "newfile.txt")
            
        Returns:
            New Skpath with the changed name
        """
        return Skpath(self._path.with_name(name))
    
    def with_stem(self, stem: str) -> "Skpath":
        """
        Return a new path with the stem changed.
        
        Args:
            stem: New stem (filename without extension)
            
        Returns:
            New Skpath with the changed stem
        """
        return Skpath(self._path.with_stem(stem))
    
    def with_suffix(self, suffix: str) -> "Skpath":
        """
        Return a new path with the suffix changed.
        
        Args:
            suffix: New suffix (e.g., ".txt")
            
        Returns:
            New Skpath with the changed suffix
        """
        return Skpath(self._path.with_suffix(suffix))
    
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
    
    def rmdir(self) -> None:
        """Remove this directory. Directory must be empty.
        
        Raises:
            OSError: If directory is not empty
            NotADirectoryError: If path is not a directory
        """
        self._path.rmdir()
    
    def unlink(self, missing_ok: bool = False) -> None:
        """Remove this file or symbolic link.
        
        Args:
            missing_ok: Don't raise if file doesn't exist
            
        Raises:
            NotAFileError: If path is a directory
        """
        # check upfront - unlink on a directory raises different errors on different OSes
        # (IsADirectoryError on Linux, PermissionError on macOS)
        if self._path.is_dir():
            raise NotAFileError(f"Cannot unlink directory: {self._path}")
        self._path.unlink(missing_ok=missing_ok)
    
    def copy_to(
        self,
        destination: str | Path | "Skpath",
        *,
        overwrite: bool = False,
        parents: bool = True,
    ) -> "Skpath":
        """
        Copy this path to a destination.
        
        Args:
            destination: Target path or directory
            overwrite: Remove existing destination if True
            parents: Create parent directories if needed
        
        Returns:
            Skpath pointing to the copied path
        """
        if not self._path.exists():
            raise FileNotFoundError(f"Source path not found: {self._path}")
        
        if isinstance(destination, Skpath):
            dest_path = destination._path
        elif isinstance(destination, Path):
            dest_path = destination
        else:
            dest_path = Path(destination)
        
        if dest_path.exists() and dest_path.is_dir():
            if self._path.is_file() or self._path.is_dir():
                dest_path = dest_path / self._path.name
        
        if parents:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if dest_path.exists():
            if not overwrite:
                raise FileExistsError(f"Destination already exists: {dest_path}")
            if dest_path.is_dir():
                shutil.rmtree(dest_path)
            else:
                dest_path.unlink()
        
        if self._path.is_dir():
            shutil.copytree(self._path, dest_path)
        else:
            shutil.copy2(self._path, dest_path)
        
        return Skpath(dest_path)
    
    def move_to(
        self,
        destination: str | Path | "Skpath",
        *,
        overwrite: bool = False,
        parents: bool = True,
    ) -> "Skpath":
        """
        Move this path to a destination.
        
        Args:
            destination: Target path or directory
            overwrite: Remove existing destination if True
            parents: Create parent directories if needed
        
        Returns:
            Skpath pointing to the moved path
        """
        if not self._path.exists():
            raise FileNotFoundError(f"Source path not found: {self._path}")
        
        if isinstance(destination, Skpath):
            dest_path = destination._path
        elif isinstance(destination, Path):
            dest_path = destination
        else:
            dest_path = Path(destination)
        
        if dest_path.exists() and dest_path.is_dir():
            if self._path.is_file() or self._path.is_dir():
                dest_path = dest_path / self._path.name
        
        if parents:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if dest_path.exists():
            if not overwrite:
                raise FileExistsError(f"Destination already exists: {dest_path}")
            if dest_path.is_dir():
                shutil.rmtree(dest_path)
            else:
                dest_path.unlink()
        
        shutil.move(str(self._path), str(dest_path))
        return Skpath(dest_path)
    
    def resolve(self) -> "Skpath":
        """
        Return the absolute path, resolving any symlinks.
        
        Returns:
            New Skpath with resolved path
        """
        return Skpath(self._path.resolve())
    
    def absolute(self) -> "Skpath":
        """
        Return an absolute version of the path.
        
        Returns:
            New Skpath with absolute path
        """
        return Skpath(self._path.absolute())
    


    # dunder methods
    
    def __str__(self) -> str:
        """Return the absolute path with normalized separators."""
        return self.ap
    
    def __repr__(self) -> str:
        """Return a string representation for debugging."""
        display_path = self.rp if self.rp else self.ap
        return f"Skpath('{display_path}')"
    
    def __fspath__(self) -> str:
        """
        Return the path for os.fspath() compatibility.
        
        Uses OS-native separators for file system operations.
        """
        return to_os_separators(self.ap)
    
    def __truediv__(self, other: str | Path | "Skpath") -> "Skpath":
        """
        Join paths using the / operator.
        
        Args:
            other: Path component to append
            
        Returns:
            New Skpath with joined path
        """
        if isinstance(other, Skpath):
            other_str = other._path.name if other._path.is_absolute() else str(other._path)
        elif isinstance(other, Path):
            other_str = str(other)
        else:
            other_str = other
        
        return Skpath(self._path / other_str)
    
    def __rtruediv__(self, other: str | Path) -> "Skpath":
        """Support path / skpath syntax."""
        if isinstance(other, Path):
            return Skpath(other / self._path)
        else:
            return Skpath(Path(other) / self._path)
    
    def __eq__(self, other: Any) -> bool:
        """
        Check equality with another path.
        
        Converts both to Skpath and compares:
        1. First by relative path (rp)
        2. Falls back to absolute path (ap) if rp's aren't equal
        """
        if other is None:
            return False
        
        try:
            # convert to Skpath if needed
            if isinstance(other, Skpath):
                other_skpath = other
            elif isinstance(other, (str, Path)):
                other_skpath = Skpath(other)
            else:
                return NotImplemented
            
            # compare rp first
            if self.rp and other_skpath.rp and self.rp == other_skpath.rp:
                return True
            
            # all back to ap comparison
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
        
        Uses MD5 hash of rp (or ap if outside project root).
        """
        if self._hash is None:
            path_to_hash = self.rp if self.rp else self.ap
            self._hash = hash_path_md5(path_to_hash)
        return self._hash
    
    def __bool__(self) -> bool:
        """Skpath is always truthy (path exists or not)."""
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
