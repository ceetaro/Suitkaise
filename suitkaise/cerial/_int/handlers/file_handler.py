"""
Handler for file handle objects.

File handles are open file objects. We serialize the path, mode, position,
encoding, and other parameters, then reopen the file in the target process.
"""

import io
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from .base_class import Handler


class FileSerializationError(Exception):
    """Raised when file serialization fails."""
    pass


class FileHandleHandler(Handler):
    """
    Serializes open file handle objects.
    
    Strategy:
    - Extract file path, mode, position, encoding
    - Use skpath for relative path resolution (if available)
    - On reconstruction, reopen file and seek to same position
    
    Important: This assumes the file exists in the target process's
    filesystem. For cross-machine serialization, files must be in 
    shared storage or at equivalent paths.
    """
    
    type_name = "file_handle"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is an open file handle.
        
        We check for common file types: TextIOWrapper, BufferedReader, etc.
        """
        return isinstance(obj, (
            io.TextIOWrapper,
            io.BufferedWriter,
            io.BufferedReader,
            io.BufferedRandom,
            io.FileIO,
        ))
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract file handle state.
        
        What we capture:
        - name: File path (absolute path)
        - mode: File open mode ('r', 'w', 'a', 'rb', etc.)
        - position: Current position in file (from tell())
        - encoding: Text encoding (for text mode files)
        - errors: Error handling mode (for text mode files)
        - newline: Newline handling (for text mode files)
        - closed: Whether file is closed
        
        Note: We try to get skpath-relative path if available,
        otherwise fall back to absolute path.
        """
        # Get file path
        file_path = obj.name
        
        # Try to make path relative using skpath (if available)
        relative_path: Optional[str] = None
        absolute_path: str
        try:
            from suitkaise.skpath.api import SKPath
            sk_path = SKPath(file_path)
            # Store both absolute and relative paths
            relative_path = str(sk_path.np)
            absolute_path = str(sk_path.ap)
        except ImportError:
            # skpath not available - use absolute path only
            relative_path = None
            absolute_path = str(file_path)
        except (ValueError, TypeError):
            # Path outside project or invalid path - use absolute only
            relative_path = None
            absolute_path = str(file_path)
        except Exception as e:
            # Unexpected skpath error - log and use absolute path
            import warnings
            warnings.warn(f"Unexpected error using skpath for file {file_path}: {e}")
            relative_path = None
            absolute_path = str(file_path)
        
        # Get current position in file
        try:
            position = obj.tell()
        except (OSError, IOError):
            position = 0
        
        # Get mode
        mode = obj.mode
        
        # Get encoding info (for text mode files)
        encoding = getattr(obj, 'encoding', None)
        errors = getattr(obj, 'errors', None)
        newline = getattr(obj, 'newline', None)
        
        return {
            "path": absolute_path,
            "relative_path": relative_path,
            "mode": mode,
            "position": position,
            "encoding": encoding,
            "errors": errors,
            "newline": newline,
            "closed": obj.closed,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct file handle.
        
        Process:
        1. Try relative path first (using skpath), fall back to absolute
        2. Open file with same mode and encoding
        3. Seek to same position
        
        If file doesn't exist or can't be opened, raise clear error.
        """
        # If file was closed, we can't really reconstruct it meaningfully
        # But we'll try anyway for completeness
        
        # Determine which path to use
        if state["relative_path"]:
            try:
                from suitkaise.skpath.api import SKPath
                # Try relative path (better for cross-machine)
                sk_path = SKPath(state["relative_path"])
                file_path = sk_path.ap
            except ImportError:
                # skpath not available, fall back to absolute path
                file_path = state["path"]
            except (ValueError, TypeError):
                # Invalid path, fall back to absolute
                file_path = state["path"]
            except Exception as e:
                # Unexpected error - log and fall back
                import warnings
                warnings.warn(f"Unexpected error resolving relative path {state['relative_path']}: {e}")
                file_path = state["path"]
        else:
            file_path = state["path"]
        
        # Build kwargs for open()
        open_kwargs = {
            "mode": state["mode"],
        }
        
        # Add encoding kwargs for text mode
        if state["encoding"]:
            open_kwargs["encoding"] = state["encoding"]
        if state["errors"]:
            open_kwargs["errors"] = state["errors"]
        if state["newline"] is not None:
            open_kwargs["newline"] = state["newline"]
        
        # Open file
        try:
            file_obj = open(file_path, **open_kwargs)
        except FileNotFoundError as e:
            raise FileSerializationError(
                f"Cannot reconstruct file handle: file not found at {file_path}. "
                f"Ensure the file exists in the target process's filesystem."
            ) from e
        except Exception as e:
            raise FileSerializationError(
                f"Cannot reconstruct file handle for {file_path}: {e}"
            ) from e
        
        # Seek to same position
        try:
            file_obj.seek(state["position"])
        except (OSError, IOError) as e:
            # Position might be invalid (file shorter in target), ignore
            pass
        
        return file_obj


class TemporaryFileHandler(Handler):
    """
    Serializes tempfile.NamedTemporaryFile objects.
    
    Temporary files are trickier because they're meant to be deleted.
    We serialize their content and recreate a new temp file.
    """
    
    type_name = "temp_file"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a NamedTemporaryFile.
        
        This is tricky because NamedTemporaryFile returns a file-like object.
        We check if it has the 'delete' attribute which is specific to temp files.
        """
        return (
            hasattr(obj, 'name') and 
            hasattr(obj, 'delete') and
            '/tmp' in str(obj.name)  # Heuristic: temp files usually in /tmp
        )
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract temporary file state.
        
        What we capture:
        - mode: File mode
        - position: Current position
        - content: The actual file content (read it all)
        - suffix: File suffix (e.g., '.txt')
        - prefix: File prefix
        - delete: Whether to delete on close
        
        Note: We read the entire file content to preserve it.
        """
        # Save current position
        original_pos = obj.tell()
        
        # Read file content
        obj.seek(0)
        if 'b' in obj.mode:
            content = obj.read()
        else:
            content = obj.read()
        
        # Restore position
        obj.seek(original_pos)
        
        # Try to extract tempfile-specific attributes
        suffix = getattr(obj, 'suffix', '')
        prefix = getattr(obj, 'prefix', 'tmp')
        delete = getattr(obj, 'delete', True)
        
        # Record the original temp file path for reference
        # (though we'll create a new one with different name)
        original_name = obj.name
        
        return {
            "mode": obj.mode,
            "position": original_pos,
            "content": content,
            "suffix": suffix,
            "prefix": prefix,
            "delete": delete,
            "encoding": getattr(obj, 'encoding', None),
            "original_name": original_name,  # For debugging/logging
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct temporary file.
        
        Process:
        1. Create new NamedTemporaryFile with same properties
        2. Write content back
        3. Seek to same position
        
        Note: This creates a NEW temp file with DIFFERENT name than the original.
        The original path was: {state.get('original_name', 'unknown')}
        
        This is a fundamental limitation of serializing temporary files -
        they are process-local and system-managed. The content and properties
        are preserved, but not the exact file path.
        """
        # Create kwargs for NamedTemporaryFile
        kwargs = {
            "mode": state["mode"],
            "delete": state["delete"],
            "suffix": state["suffix"],
            "prefix": state["prefix"],
        }
        
        if state["encoding"]:
            kwargs["encoding"] = state["encoding"]
        
        # Create new temp file
        temp_file = tempfile.NamedTemporaryFile(**kwargs)
        
        # Write content
        temp_file.write(state["content"])
        temp_file.flush()
        
        # Seek to same position
        temp_file.seek(state["position"])
        
        return temp_file


class StringIOHandler(Handler):
    """
    Serializes io.StringIO objects.
    
    StringIO is an in-memory text stream. We capture the content and position.
    """
    
    type_name = "string_io"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a StringIO."""
        return isinstance(obj, io.StringIO)
    
    def extract_state(self, obj: io.StringIO) -> Dict[str, Any]:
        """
        Extract StringIO state.
        
        What we capture:
        - content: The full string buffer
        - position: Current position (from tell())
        """
        # Save current position
        original_pos = obj.tell()
        
        # Read all content
        obj.seek(0)
        content = obj.read()
        
        # Restore position
        obj.seek(original_pos)
        
        return {
            "content": content,
            "position": original_pos,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> io.StringIO:
        """
        Reconstruct StringIO.
        
        Process:
        1. Create new StringIO with content
        2. Seek to same position
        """
        # Create new StringIO with content
        string_io = io.StringIO(state["content"])
        
        # Seek to same position
        string_io.seek(state["position"])
        
        return string_io


class BytesIOHandler(Handler):
    """
    Serializes io.BytesIO objects.
    
    BytesIO is an in-memory binary stream. We capture the content and position.
    """
    
    type_name = "bytes_io"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a BytesIO."""
        return isinstance(obj, io.BytesIO)
    
    def extract_state(self, obj: io.BytesIO) -> Dict[str, Any]:
        """
        Extract BytesIO state.
        
        What we capture:
        - content: The full bytes buffer
        - position: Current position (from tell())
        """
        # Save current position
        original_pos = obj.tell()
        
        # Read all content
        obj.seek(0)
        content = obj.read()
        
        # Restore position
        obj.seek(original_pos)
        
        return {
            "content": content,
            "position": original_pos,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> io.BytesIO:
        """
        Reconstruct BytesIO.
        
        Process:
        1. Create new BytesIO with content
        2. Seek to same position
        """
        # Create new BytesIO with content
        bytes_io = io.BytesIO(state["content"])
        
        # Seek to same position
        bytes_io.seek(state["position"])
        
        return bytes_io

