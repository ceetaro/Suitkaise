"""
Handler for memory-related objects.

Includes memory-mapped files, shared memory, and raw file descriptors.
"""

import mmap
import os
import sys
import multiprocessing
from typing import Any, Dict, Optional
from .base_class import Handler

# Try to import shared_memory (Python 3.8+)
try:
    from multiprocessing import shared_memory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False
    shared_memory = None  # type: ignore


class MemorySerializationError(Exception):
    """Raised when memory object serialization fails."""
    pass


class MMapHandler(Handler):
    """
    Serializes mmap.mmap objects (9% importance).
    
    Memory-mapped files map file contents into memory.
    We serialize the file backing the mmap and the current position.
    
    Important: The actual memory mapping doesn't transfer across processes.
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
        - access: Access mode (ACCESS_READ, ACCESS_WRITE, etc.)
        - closed: Whether mmap is closed
        
        Note: For anonymous mmaps (no file backing), we capture the content.
        """
        # Get current position
        position = obj.tell()
        
        # Get length
        length = obj.size()
        
        # Get file descriptor
        fileno = obj.fileno() if hasattr(obj, 'fileno') else -1
        
        # Determine if this is an anonymous mmap (no file backing)
        is_anonymous = fileno == -1
        
        # For anonymous mmaps, save the content
        if is_anonymous:
            obj.seek(0)
            content = obj.read()
            obj.seek(position)
        else:
            content = None
        
        return {
            "fileno": fileno,
            "length": length,
            "position": position,
            "closed": obj.closed,
            "is_anonymous": is_anonymous,
            "content": content,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> mmap.mmap:
        """
        Reconstruct mmap.
        
        Process:
        - For file-backed mmaps: reopen file and create new mmap
        - For anonymous mmaps: create new anonymous mmap with same content
        
        Note: File descriptor numbers don't transfer across processes,
        so we can't use the original fileno. This handler is limited
        for file-backed mmaps.
        """
        if state["is_anonymous"]:
            # Create anonymous mmap with content
            length = state["length"]
            mm = mmap.mmap(-1, length)
            
            if state["content"]:
                mm.write(state["content"])
            
            mm.seek(state["position"])
            return mm
        else:
            # File-backed mmap - we can't easily recreate this without
            # the file path. Raise an error with instructions.
            raise NotImplementedError(
                "Cannot reconstruct file-backed mmap without file path. "
                "File descriptors don't transfer across processes. "
                "Consider using FileHandleHandler for the underlying file instead."
            )


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
        # Get name and size
        name = obj.name
        size = obj.size
        
        # Read content
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
        
        # Try to attach to existing shared memory block
        try:
            shm = shared_memory.SharedMemory(
                name=state["name"],
                create=False,
                size=state["size"]
            )
        except FileNotFoundError:
            # Shared memory block doesn't exist, create new one
            shm = shared_memory.SharedMemory(
                name=state["name"],
                create=True,
                size=state["size"]
            )
        
        # Write content
        shm.buf[:] = state["content"]
        
        return shm


class FileDescriptorHandler(Handler):
    """
    Serializes raw file descriptor integers (3% importance).
    
    File descriptors are OS-level handles to open files.
    They don't transfer across processes, but we can try to
    serialize the file path and reopen.
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
        # We don't auto-detect file descriptors since they're just ints
        # Users should explicitly handle file objects instead
        return False
    
    def extract_state(self, obj: int) -> Dict[str, Any]:
        """
        Extract file descriptor information.
        
        Try to get file path from file descriptor (platform-specific).
        """
        path: Optional[str] = None
        
        # Try platform-specific methods to get path from fd
        if sys.platform.startswith('linux'):
            # Linux: use /proc/self/fd/
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
        
        return {
            "fd": obj,
            "path": path,
            "platform": sys.platform,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> int:
        """
        Reconstruct file descriptor.
        
        This is very limited - file descriptors don't transfer across processes.
        """
        raise MemorySerializationError(
            f"Raw file descriptors cannot be serialized across processes. "
            f"Use file handle objects instead (open file objects). "
            f"Original fd={state['fd']}, path={state.get('path', 'unknown')}, "
            f"platform={state.get('platform', 'unknown')}"
        )

