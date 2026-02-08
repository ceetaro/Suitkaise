"""
Handler for file handle objects.

File handles are open file objects. We serialize the path, mode, position,
encoding, and other parameters, then reopen the file in the target process.
"""

import io
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from suitkaise.paths.api import detect_project_root
except Exception:  # pragma: no cover - optional dependency
    detect_project_root = None
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
    
    NOTE: This assumes the file exists in the target process's
    filesystem. For cross-machine serialization, files must be in 
    shared storage or at equivalent paths.
    """
    
    type_name = "file_handle"
    _project_root: Path | None = None
    _project_root_checked: bool = False
    
    @classmethod
    def _get_project_root(cls) -> Path | None:
        if cls._project_root_checked:
            return cls._project_root
        
        cls._project_root_checked = True
        if detect_project_root is None:
            cls._project_root = None
            return None
        
        try:
            cls._project_root = detect_project_root()
        except Exception:
            cls._project_root = None
        
        return cls._project_root
    
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
        - is_pipe: Whether this is a subprocess pipe (not a real file)
        
        Note: We try to get skpath-relative path if available,
        otherwise fall back to absolute path.
        """
        # check if file is closed first
        is_closed = obj.closed
        
        # get file path/name - may be an int for subprocess pipes
        file_path = obj.name
        is_pipe = isinstance(file_path, int)  # subprocess pipes have int file descriptors as names
        
        # for closed files or pipes, we store minimal state
        if is_closed or is_pipe:
            return {
                "path": str(file_path) if not is_pipe else None,
                "relative_path": None,
                "mode": getattr(obj, 'mode', 'r'),  # default to 'r' if no mode
                "position": 0,
                "encoding": getattr(obj, 'encoding', None),
                "errors": getattr(obj, 'errors', None),
                "newline": getattr(obj, 'newline', None),
                "closed": is_closed,
                "is_pipe": is_pipe,
            }
        
        # try to compute a relative path only if the file is inside the project root.
        # avoid Skpath on temp/system paths to prevent expensive root detection and exceptions.
        relative_path: Optional[str] = None
        try:
            absolute_path = str(Path(file_path).resolve())
        except Exception:
            absolute_path = str(file_path)
        
        project_root = self._get_project_root()
        if project_root is not None:
            try:
                relative_path = Path(absolute_path).relative_to(project_root).as_posix()
            except ValueError:
                relative_path = None
        
        # get current position in file
        try:
            position = obj.tell()
        except (OSError, IOError, ValueError):
            # ValueError can occur on closed files
            position = 0
        
        # get mode - may not exist on all file-like objects
        mode = getattr(obj, 'mode', 'r')
        
        # get encoding info (for text mode files)
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
            "closed": is_closed,
            "is_pipe": is_pipe,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct file handle.
        
        Process:
        1. Check if this was a pipe or closed file - return placeholder
        2. Try relative path first (using skpath), fall back to absolute
        3. Open file with same mode and encoding
        4. Seek to same position
        
        If file doesn't exist or can't be opened, raise clear error.
        """
        # handle pipes (subprocess stdout/stderr) - these can't be meaningfully reconstructed
        if state.get("is_pipe", False):
            # return a closed BytesIO as a placeholder for the pipe
            placeholder = io.BytesIO()
            placeholder.close()
            return placeholder
        
        # handle closed files - return a placeholder that represents the closed state
        if state.get("closed", False):
            # return a placeholder object that represents the closed file
            class ClosedFilePlaceholder:
                """Placeholder for a file that was closed when serialized."""
                def __init__(self, original_path, original_mode):
                    self.name = original_path
                    self.mode = original_mode
                    self.closed = True
                    self._was_closed_at_serialization = True
                
                def __repr__(self):
                    return f"<ClosedFilePlaceholder path={self.name!r} mode={self.mode!r}>"
                
                def read(self, *args, **kwargs):
                    raise ValueError("I/O operation on closed file.")
                
                def write(self, *args, **kwargs):
                    raise ValueError("I/O operation on closed file.")
                
                def tell(self):
                    raise ValueError("I/O operation on closed file.")
                
                def seek(self, *args, **kwargs):
                    raise ValueError("I/O operation on closed file.")
            
            return ClosedFilePlaceholder(state.get("path"), state.get("mode"))
        
        # determine which path to use
        if state.get("relative_path"):
            try:
                from suitkaise.paths.api import Skpath
                # try relative path (better for cross-machine)
                sk_path = Skpath(state["relative_path"])
                file_path = sk_path.ap
            except ImportError:
                # Skpath not available, fall back to absolute path
                file_path = state["path"]
            except (ValueError, TypeError):
                # invalid path, fall back to absolute
                file_path = state["path"]
            except Exception as e:
                # unexpected error, log and fall back
                import warnings
                warnings.warn(f"Unexpected error resolving relative path {state['relative_path']}: {e}")
                file_path = state["path"]
        else:
            file_path = state["path"]
        
        # build kwargs for open()
        open_kwargs = {
            "mode": state["mode"],
        }
    
        # add encoding kwargs for text mode
        if state.get("encoding"):
            open_kwargs["encoding"] = state["encoding"]
        if state.get("errors"):
            open_kwargs["errors"] = state["errors"]
        if state.get("newline") is not None:
            open_kwargs["newline"] = state["newline"]
        
        # open file
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
        
        # seek to same position
        try:
            file_obj.seek(state["position"])
        except (OSError, IOError) as e:
            # position might be invalid (file shorter in target), ignore
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
        We check for temp-file-specific attributes and that it is file-like.
        
        Python version notes:
        - Pre-3.12: wrapper has 'name' and 'delete' directly
        - 3.12+: wrapper has 'name' and '_closer' (delete moved to _closer)
        
        The file-like check (tell/seek/read) excludes internal helpers like
        _TemporaryFileCloser that have 'name'/'delete' but are not file objects.
        """
        if not hasattr(obj, 'name'):
            return False
        
        # Check for temp-file markers: 'delete' (pre-3.12) or '_closer' (3.12+)
        if not (hasattr(obj, 'delete') or hasattr(obj, '_closer')):
            return False
        
        # Must be file-like — excludes internal helpers like _TemporaryFileCloser
        if not (hasattr(obj, 'tell') and hasattr(obj, 'seek') and hasattr(obj, 'read')):
            return False
        
        try:
            name_value = obj.name
        except Exception:
            return False
        
        if isinstance(name_value, int):
            return False
        
        try:
            name_path = Path(str(name_value)).resolve()
            temp_dir = Path(tempfile.gettempdir()).resolve()
            return name_path == temp_dir or temp_dir in name_path.parents
        except Exception:
            return False
    
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
        # save current position
        original_pos = obj.tell()
        
        # read file content
        obj.seek(0)
        if 'b' in obj.mode:
            content = obj.read()
        else:
            content = obj.read()
        
        # restore position
        obj.seek(original_pos)
        
        # try to extract tempfile-specific attributes
        suffix = getattr(obj, 'suffix', '')
        prefix = getattr(obj, 'prefix', 'tmp')
        # Python 3.12+ moved 'delete' to _closer
        delete = getattr(obj, 'delete', None)
        if delete is None and hasattr(obj, '_closer'):
            delete = getattr(obj._closer, 'delete', True)
        if delete is None:
            delete = True
        
        # record the original temp file path for reference
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
            "original_name": original_name,  # for debugging/logging
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

        Better to give you as close of a representation of the original file as possible,
        instead of ignoring it and giving you a serialization error.
        """
        # create kwargs for NamedTemporaryFile
        kwargs = {
            "mode": state["mode"],
            "delete": state["delete"],
            "suffix": state["suffix"],
            "prefix": state["prefix"],
        }
        
        if state["encoding"]:
            kwargs["encoding"] = state["encoding"]
        
        # create new temp file
        temp_file = tempfile.NamedTemporaryFile(**kwargs)
        
        # write content
        temp_file.write(state["content"])
        temp_file.flush()
        
        # seek to same position
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
        # save current position
        original_pos = obj.tell()
        
        # read all content
        obj.seek(0)
        content = obj.read()
        
        # restore position
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
        # create new StringIO with content
        string_io = io.StringIO(state["content"])
        
        # seek to same position
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
        - closed: Whether the BytesIO is closed
        """
        # check if closed first
        if obj.closed:
            return {
                "content": b"",
                "position": 0,
                "closed": True,
            }
        
        # save current position
        original_pos = obj.tell()
        
        # read all content
        obj.seek(0)
        content = obj.read()
        
        # restore position
        obj.seek(original_pos)
        
        return {
            "content": content,
            "position": original_pos,
            "closed": False,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> io.BytesIO:
        """
        Reconstruct BytesIO.
        
        Process:
        1. Handle closed state if applicable
        2. Create new BytesIO with content
        3. Seek to same position
        """
        # handle closed BytesIO (e.g., subprocess pipe placeholders)
        if state.get("closed", False):
            closed_io = io.BytesIO(b"")
            closed_io.close()
            return closed_io
        
        # create new BytesIO with content
        bytes_io = io.BytesIO(state["content"])
        
        # seek to same position
        bytes_io.seek(state["position"])
        
        return bytes_io

