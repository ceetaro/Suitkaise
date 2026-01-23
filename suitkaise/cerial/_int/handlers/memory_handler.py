"""
Handler for memory-related objects.

Includes memory-mapped files, shared memory, and raw file descriptors.
 
Limitations:
- Raw file descriptors are reconstructed on a best-effort basis by reopening
  the original path when possible. This cannot guarantee the same underlying
  file or state across processes.

This is a Python limitation, so I did my best to work around it.
"""

import mmap
import os
import sys
import multiprocessing
from typing import Any, Dict, Optional
from .base_class import Handler

# try to import shared_memory (Python 3.8+)
try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False
    shared_memory = None  # type: ignore


class MemorySerializationError(Exception):
    """Raised when memory object serialization fails."""
    pass


class MemoryViewHandler(Handler):
    """
    Serializes memoryview objects.
    
    Converts memoryview to bytes and reconstructs from bytes.
    """
    
    type_name = "memoryview"
    
    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, memoryview)
    
    def extract_state(self, obj: memoryview) -> Dict[str, Any]:
        try:
            data = obj.tobytes()
        except Exception as e:
            raise MemorySerializationError(f"Cannot serialize memoryview: {e}") from e
        return {"data": data}
    
    def reconstruct(self, state: Dict[str, Any]) -> memoryview:
        data = state.get("data", b"")
        return memoryview(data)


class MMapHandler(Handler):
    """
    Serializes mmap.mmap objects.
    
    Memory-mapped files map file contents into memory.
    We serialize the file backing the mmap and the current position.
    
    NOTE: The actual memory mapping doesn't transfer across processes.
    We recreate a new mapping to the same file.
    """
    
    type_name = "mmap"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is an mmap."""
        return isinstance(obj, mmap.mmap)
    
    def extract_state(self, obj: mmap.mmap) -> Dict[str, Any]:
        """
        Extract mmap state.
        
        What we capture:
        - fileno: File descriptor number
        - length: Length of mapping
        - position: Current position in mapping
        - file_path: Path to backing file (if we can determine it)
        - content: Full mmap content (for cross-process transfer)
        - closed: Whether mmap is closed
        
        Strategy:
        For inter-process communication, we ALWAYS save the content.
        We also try to get the file path for file-backed mmaps.
        This enables reliable multiple round-trips across processes.
        """
        # get current position
        try:
            position = obj.tell()
        except (OSError, ValueError):
            position = 0
        
        # get length
        try:
            length = obj.size()
        except (OSError, ValueError):
            # if size() fails, the mmap is invalid/closed
            # try to read all content to determine size
            try:
                current = obj.tell()
                obj.seek(0)
                content = obj.read()
                length = len(content)
                obj.seek(current)
            except:
                # completely invalid mmap
                raise MemorySerializationError(
                    "Cannot serialize mmap: object is closed or in invalid state"
                )
        
        # try to get file descriptor
        fileno = -1
        try:
            if hasattr(obj, 'fileno'):
                fileno = obj.fileno()
        except (OSError, ValueError):
            # bad file descriptor or invalid mmap
            fileno = -1
        
        # try to get file path from file descriptor (for file-backed mmaps)
        file_path: Optional[str] = None
        if fileno != -1:
            if sys.platform.startswith('linux'):
                # linux: use /proc/self/fd/
                try:
                    file_path = os.readlink(f'/proc/self/fd/{fileno}')
                except (OSError, FileNotFoundError):
                    pass
            
            elif sys.platform == 'darwin':
                # macOS: use fcntl.F_GETPATH
                try:
                    import fcntl
                    path_bytes = fcntl.fcntl(fileno, fcntl.F_GETPATH, bytes(1024))
                    file_path = path_bytes.rstrip(b'\x00').decode('utf-8')
                except (ImportError, OSError, AttributeError):
                    pass
        
        # ALWAYS save content for reliable cross-process transfer
        # even for file-backed mmaps, the file might not exist in target process
        obj.seek(0)
        content = obj.read()
        obj.seek(position)
        
        # determine if this is anonymous (no file backing found)
        is_anonymous = fileno == -1 or file_path is None
        
        return {
            "fileno": fileno,
            "length": length,
            "position": position,
            "closed": obj.closed,
            "is_anonymous": is_anonymous,
            "file_path": file_path,
            "content": content,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> mmap.mmap:
        """
        Reconstruct mmap.
        
        Strategy:
        1. If we have a file_path and the file exists, try to create a file-backed mmap
        2. Otherwise, create an anonymous mmap with the saved content
        3. This ensures reliable reconstruction across processes
        
        The content is always preserved, making this work for inter-process
        communication even when the backing file doesn't exist in target process.
        """
        # try file-backed mmap first (if we have a path and file exists)
        file_path = state.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                # open the file and create a file-backed mmap
                with open(file_path, 'r+b') as f:
                    mm = mmap.mmap(f.fileno(), state["length"])
                    mm.seek(state["position"])
                    return mm
            except (OSError, ValueError, IOError):
                # file-backed mmap failed, fall back to anonymous
                pass
        
        # fall back to anonymous mmap with content
        # this works reliably across processes
        length = state["length"]
        mm = mmap.mmap(-1, length)
        
        if state["content"]:
            mm.write(state["content"])
        
        mm.seek(state["position"])
        return mm


class SharedMemoryHandler(Handler):
    """
    Serializes multiprocessing.shared_memory.SharedMemory objects (3% importance).
    
    Shared memory allows multiple processes to access the same memory region.
    We serialize the name and content.
    """
    
    type_name = "shared_memory"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a SharedMemory."""
        if not HAS_SHARED_MEMORY:
            return False
        return isinstance(obj, shared_memory.SharedMemory)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract shared memory state.
        
        What we capture:
        - name: Shared memory block name
        - size: Size in bytes
        - content: The actual memory content
        - create: Whether this process created the block
        """
        # get name and size
        name = obj.name
        size = obj.size
        
        # read content
        content = bytes(obj.buf[:])
        
        return {
            "name": name,
            "size": size,
            "content": content,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> 'shared_memory.SharedMemory':  # type: ignore
        """
        Reconstruct shared memory.
        
        Try to attach to existing shared memory block by name.
        If it doesn't exist, create a new one.
        """
        if not HAS_SHARED_MEMORY:
            raise MemorySerializationError(
                "Cannot reconstruct SharedMemory: not available in Python < 3.8"
            )
        
        content = state["content"]
        expected_size = len(content)

        # try to attach to existing shared memory block
        try:
            shm = shared_memory.SharedMemory(
                name=state["name"],
                create=False,
                size=state["size"]
            )
            # some platforms may attach with a different size; if so, write what fits
        except FileNotFoundError:
            # shared memory block doesn't exist, create new one
            try:
                shm = shared_memory.SharedMemory(
                    name=state["name"],
                    create=True,
                    size=expected_size
                )
            except FileExistsError:
                # another process created it; attach instead
                shm = shared_memory.SharedMemory(
                    name=state["name"],
                    create=False,
                    size=state["size"]
                )
        
        # write content (truncate if existing shared memory is smaller)
        if shm.size >= expected_size:
            shm.buf[:expected_size] = content
        else:
            shm.buf[:] = content[:shm.size]
        
        return shm


class FileDescriptorHandler(Handler):
    """
    Serializes raw file descriptor integers (3% importance).
    
    File descriptors are OS-level handles to open files.
    They don't transfer across processes, but we can try to
    serialize the file path and reopen.
    
    Limitation:
        Reconstruction is best-effort only. We reopen the path and attempt
        to restore access flags and file position, but the underlying file
        may be different, permissions may change, and some flags cannot be
        restored across processes.
    """
    
    type_name = "file_descriptor"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a raw file descriptor.
        
        This is tricky - file descriptors are just ints.
        We don't actually want to handle random ints, so
        we return False here. User should serialize the file
        handle instead.
        """
        # we don't auto-detect file descriptors since they're just ints
        # users should explicitly handle file objects instead
        return False
    
    def extract_state(self, obj: int) -> Dict[str, Any]:
        """
        Extract file descriptor information.
        
        Try to get file path from file descriptor (platform-specific).
        """
        path: Optional[str] = None
        flags: Optional[int] = None
        position: Optional[int] = None
        
        # try platform-specific methods to get path from fd
        if sys.platform.startswith('linux'):
            # linux: use /proc/self/fd/
            try:
                path = os.readlink(f'/proc/self/fd/{obj}')
            except (OSError, FileNotFoundError):
                pass
        
        elif sys.platform == 'darwin':
            # macOS: use fcntl.F_GETPATH
            try:
                import fcntl
                path_bytes = fcntl.fcntl(obj, fcntl.F_GETPATH, bytes(1024))
                path = path_bytes.rstrip(b'\x00').decode('utf-8')
            except (ImportError, OSError, AttributeError):
                pass
        
        # Windows and other platforms: no reliable way to get path from fd
        # Try to capture flags and position where possible (POSIX).
        if sys.platform != 'win32':
            try:
                import fcntl
                flags = fcntl.fcntl(obj, fcntl.F_GETFL)
            except (ImportError, OSError, AttributeError):
                flags = None
            try:
                position = os.lseek(obj, 0, os.SEEK_CUR)
            except OSError:
                position = None
        
        return {
            "fd": obj,
            "path": path,
            "platform": sys.platform,
            "flags": flags,
            "position": position,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> int:
        """
        Reconstruct file descriptor.
        
        This is very limited - file descriptors don't transfer across processes.
        """
        path = state.get("path")
        if not path:
            raise MemorySerializationError(
                f"Raw file descriptors cannot be reconstructed without a path. "
                f"Use file handle objects instead (open file objects). "
                f"Original fd={state.get('fd')}, platform={state.get('platform', 'unknown')}"
            )
        
        flags = state.get("flags")
        if flags is None:
            # best-effort fallback when flags are unknown
            open_flags = os.O_RDONLY
        else:
            # sanitize flags to avoid recreating the file
            open_flags = flags & os.O_ACCMODE
            open_flags |= flags & getattr(os, "O_APPEND", 0)
            open_flags |= flags & getattr(os, "O_NONBLOCK", 0)
            open_flags |= flags & getattr(os, "O_SYNC", 0)
        
        try:
            fd = os.open(path, open_flags)
        except OSError:
            # fallback if access mode was too restrictive
            fd = os.open(path, os.O_RDWR)
        
        position = state.get("position")
        if position is not None:
            try:
                os.lseek(fd, position, os.SEEK_SET)
            except OSError:
                pass
        
        return fd

