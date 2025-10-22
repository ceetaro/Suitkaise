"""
Handler for pipe objects.

Pipes are inter-process communication channels.
"""

import os
import multiprocessing
import multiprocessing.connection
from typing import Any, Dict
from .base_class import Handler


class PipeSerializationError(Exception):
    """Raised when pipe serialization fails."""
    pass


class OSPipeHandler(Handler):
    """
    Serializes os.pipe file descriptor pairs (6% importance).
    
    os.pipe() returns a tuple of (read_fd, write_fd).
    These are raw file descriptors that don't transfer across processes.
    
    Important: Pipes are inherently process-local. We can't meaningfully
    serialize them for cross-process use.
    """
    
    type_name = "os_pipe"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a pipe fd tuple.
        
        This is tricky since pipes are just tuples of ints.
        We don't want to handle random tuples, so we return False.
        """
        # We don't auto-detect pipes since they're just (int, int) tuples
        return False
    
    def extract_state(self, obj: tuple) -> Dict[str, Any]:
        """Extract pipe file descriptors."""
        return {
            "read_fd": obj[0],
            "write_fd": obj[1],
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> tuple:
        """
        Reconstruct pipe.
        
        File descriptors don't transfer, so we create a new pipe.
        """
        # Create new pipe with different file descriptors
        return os.pipe()


class MultiprocessingPipeHandler(Handler):
    """
    Serializes multiprocessing.Pipe connection objects.
    
    multiprocessing.Pipe() returns a tuple of (conn1, conn2) Connection objects.
    These are more sophisticated than os.pipe and handle object serialization.
    """
    
    type_name = "mp_pipe"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a multiprocessing Connection.
        
        These are the objects returned by multiprocessing.Pipe().
        """
        return isinstance(obj, multiprocessing.connection.Connection)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract pipe connection state.
        
        What we capture:
        - readable: Whether connection is readable
        - writable: Whether connection is writable
        - closed: Whether connection is closed
        
        Note: The actual pipe connection doesn't transfer.
        We'll create a new pipe on reconstruction.
        """
        return {
            "readable": obj.readable,
            "writable": obj.writable,
            "closed": obj.closed,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct pipe connection.
        
        Creates new pipe and returns one end.
        Note: The other end is lost, which makes this not very useful.
        Pipes are inherently paired, so serializing one end doesn't
        make much sense.
        """
        # Create new pipe
        conn1, conn2 = multiprocessing.Pipe(duplex=True)
        
        # Return one end (but the other end is lost)
        # This is a fundamental limitation of serializing pipes
        return conn1


class MultiprocessingManagerHandler(Handler):
    """
    Serializes multiprocessing.Manager and proxy objects (4% importance).
    
    Managers provide shared objects that can be used across processes.
    They create proxy objects that communicate with a server process.
    """
    
    type_name = "mp_manager"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a Manager or proxy.
        
        This is tricky since there are many proxy types.
        """
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), '__module__', '')
        
        # Check for manager or proxy objects
        is_manager = 'Manager' in obj_type_name or 'Proxy' in obj_type_name
        is_mp = 'multiprocessing' in obj_module
        
        return is_manager and is_mp
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract manager/proxy state.
        
        What we capture:
        - type_name: Type of proxy (ListProxy, DictProxy, etc.)
        - value: The current value (if accessible)
        
        Note: Managers communicate with a server process via sockets.
        This doesn't transfer across processes. We extract the value
        and create a new manager/proxy.
        """
        obj_type_name = type(obj).__name__
        
        # Try to get the underlying value
        value = None
        try:
            # For proxy objects, try to convert to regular Python object
            if 'Proxy' in obj_type_name:
                # Try various methods to get value
                if hasattr(obj, '_getvalue'):
                    value = obj._getvalue()
                elif 'List' in obj_type_name:
                    value = list(obj)
                elif 'Dict' in obj_type_name:
                    value = dict(obj)
                else:
                    # Generic: try to copy
                    value = obj
        except:
            pass
        
        return {
            "type_name": obj_type_name,
            "value": value,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct manager/proxy.
        
        Create new manager and return proxy with same value.
        Note: This creates a NEW manager in the target process.
        """
        # This is complex and varies by proxy type
        # For now, just return the underlying value
        # User can wrap in a new manager if needed
        return state["value"]

