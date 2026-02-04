"""
Handler for pipe objects.

Pipes are inter-process communication channels.
"""
from __future__ import annotations

import os
import multiprocessing
import multiprocessing.connection
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
from .base_class import Handler
from .reconnector import Reconnector


class PipeSerializationError(Exception):
    """Raised when pipe serialization fails."""
    pass


@dataclass
class PipeReconnector(Reconnector):
    """
    Recreates multiprocessing pipes on demand.
    
    Since connection handles don't survive across processes, we return a
    PipeReconnector that can generate a fresh pipe and provide both ends.
    """
    duplex: bool = True
    preferred_end: str = "either"
    readable: bool = True
    writable: bool = True
    has_endpoint: bool = False
    endpoint: str | None = None
    _pipe_pair: Optional[Tuple[Any, Any]] = field(default=None, init=False, repr=False)
    
    def __post_init__(self) -> None:
        if self.endpoint in ("read", "write"):
            self.has_endpoint = True
            return
        if self.preferred_end in ("read", "write"):
            self.endpoint = self.preferred_end
            self.has_endpoint = True
    
    def reconnect(self) -> Any:
        """
        Return a connection end matching the original directionality.
        """
        conn, _ = self._ensure_pipe()
        return conn
    
    def peer(self) -> Any:
        """
        Return the peer connection end.
        """
        _, peer_conn = self._ensure_pipe()
        return peer_conn
    
    def pair(self) -> Tuple[Any, Any]:
        """
        Return both ends of the newly created pipe.
        """
        return self._ensure_pipe()

    
    def _ensure_pipe(self) -> Tuple[Any, Any]:
        if self._pipe_pair is None:
            conn1, conn2 = multiprocessing.Pipe(duplex=self.duplex)
            if self.preferred_end == "read":
                self._pipe_pair = (conn1, conn2)
            elif self.preferred_end == "write":
                self._pipe_pair = (conn2, conn1)
            else:
                self._pipe_pair = (conn1, conn2)
        return self._pipe_pair


class OSPipeHandler(Handler):
    """
    Serializes os.pipe file descriptor pairs.
    
    os.pipe() returns a tuple of (read_fd, write_fd).
    These are raw file descriptors that don't transfer across processes.
    
    Important: Pipes are inherently process-local. We can't meaningfully
    serialize them for cross-process use. Reconstruction is best-effort.
    """
    
    type_name = "os_pipe"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a pipe fd tuple.
        
        This is tricky since pipes are just tuples of ints.
        We don't want to handle random tuples, so we return False.
        """
        # we don't auto-detect pipes since they're just (int, int) tuples
        return False
    
    def extract_state(self, obj: tuple) -> Dict[str, Any]:
        """Extract pipe file descriptors and basic metadata."""
        if not isinstance(obj, tuple) or len(obj) != 2:
            raise PipeSerializationError("os.pipe state must be a (read_fd, write_fd) tuple.")
        read_fd, write_fd = obj
        if not isinstance(read_fd, int) or not isinstance(write_fd, int):
            raise PipeSerializationError("os.pipe fds must be integers.")
        try:
            os.fstat(read_fd)
            os.fstat(write_fd)
        except OSError as exc:
            raise PipeSerializationError("Invalid pipe file descriptor.") from exc
        
        read_inheritable = os.get_inheritable(read_fd)
        write_inheritable = os.get_inheritable(write_fd)
        read_blocking = os.get_blocking(read_fd) if hasattr(os, "get_blocking") else None
        write_blocking = os.get_blocking(write_fd) if hasattr(os, "get_blocking") else None
        return {
            "read_fd": read_fd,
            "write_fd": write_fd,
            "read_inheritable": read_inheritable,
            "write_inheritable": write_inheritable,
            "read_blocking": read_blocking,
            "write_blocking": write_blocking,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> tuple:
        """
        Reconstruct pipe.
        
        Best-effort:
        - If the original fds are still valid in-process, dup them.
        - Otherwise, create a new pipe.
        """
        read_fd = state.get("read_fd")
        write_fd = state.get("write_fd")
        
        def _dup_fd(fd: Any) -> int | None:
            if not isinstance(fd, int):
                return None
            try:
                return os.dup(fd)
            except OSError:
                return None
        
        new_read = _dup_fd(read_fd)
        new_write = _dup_fd(write_fd)
        if new_read is None or new_write is None:
            # clean up any partial dup and create a fresh pipe
            if new_read is not None:
                try:
                    os.close(new_read)
                except OSError:
                    pass
            if new_write is not None:
                try:
                    os.close(new_write)
                except OSError:
                    pass
            new_read, new_write = os.pipe()
        
        # restore inheritable/blocking flags when possible
        if "read_inheritable" in state:
            os.set_inheritable(new_read, bool(state["read_inheritable"]))
        if "write_inheritable" in state:
            os.set_inheritable(new_write, bool(state["write_inheritable"]))
        if hasattr(os, "set_blocking"):
            read_blocking = state.get("read_blocking")
            if read_blocking is not None:
                os.set_blocking(new_read, bool(read_blocking))
            write_blocking = state.get("write_blocking")
            if write_blocking is not None:
                os.set_blocking(new_write, bool(write_blocking))
        
        return new_read, new_write


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
        - duplex: Whether the pipe is duplex
        - preferred_end: Which end to return on reconnect
        
        Note: The actual pipe connection doesn't transfer.
        We'll create a new pipe on reconstruction and return a reconnection helper.
        """
        readable = obj.readable
        writable = obj.writable
        duplex = bool(readable and writable)
        if readable and not writable:
            preferred_end = "read"
        elif writable and not readable:
            preferred_end = "write"
        else:
            preferred_end = "either"
        return {
            "readable": readable,
            "writable": writable,
            "closed": obj.closed,
            "duplex": duplex,
            "preferred_end": preferred_end,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> PipeReconnector:
        """
        Reconstruct pipe connection.
        
        Returns a PipeReconnector that can create a fresh pipe and
        provide both ends. This lets users pass one end to another
        process via a Share or Queue when needed.
        """
        return PipeReconnector(
            duplex=bool(state.get("duplex", True)),
            preferred_end=str(state.get("preferred_end", "either")),
            readable=bool(state.get("readable", True)),
            writable=bool(state.get("writable", True)),
        )


class MultiprocessingManagerHandler(Handler):
    """
    Serializes multiprocessing.Manager and proxy objects.
    
    Managers provide shared objects that can be used across processes.
    They create proxy objects that communicate with a server process.
    
    We keep this hands-off and do not attempt to reconnect to the original
    Manager server. Share is the recommended cross-process mechanism.
    """
    
    type_name = "mp_manager"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a Manager or proxy.
        
        This is tricky since there are many proxy types.
        """
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), "__module__", "")
        
        # check for manager or proxy objects
        is_manager = 'Manager' in obj_type_name or 'Proxy' in obj_type_name
        is_mp = 'multiprocessing' in obj_module
        
        return is_manager and is_mp
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract manager/proxy state.
        
        What we capture:
        - type_name: Type of proxy (ListProxy, DictProxy, etc.)
        - value: The current value (if accessible)
        
        NOTE: Managers communicate with a server process via sockets.
        This doesn't transfer across processes. We extract the value
        and create a new manager/proxy.
        
        Detailed behavior:
        - Prefer the proxy's __reduce__ protocol for a safe rebuild.
        - If reduce fails, avoid touching manager internals and fall back
          to the proxy's current value (if accessible).
        - We do NOT reconnect to the original Manager server or preserve
          auth keys/addresses. This keeps behavior hands-off and secure.
        """
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), "__module__", "")
        
        def _contains_auth(value: Any) -> bool:
            try:
                from multiprocessing.process import AuthenticationString
            except Exception:
                AuthenticationString = None  # type: ignore
            if AuthenticationString is not None and isinstance(value, AuthenticationString):
                return True
            if isinstance(value, (list, tuple, set)):
                return any(_contains_auth(item) for item in value)
            if isinstance(value, dict):
                return any(_contains_auth(k) or _contains_auth(v) for k, v in value.items())
            return False

        # avoid reduce for manager/proxy objects to prevent authkey leaks
        if "multiprocessing.managers" in obj_module:
            value = None
            try:
                if hasattr(obj, "items"):
                    value = dict(obj)
                elif hasattr(obj, "__iter__"):
                    value = list(obj)
            except Exception:
                value = None
            return {
                "type_name": obj_type_name,
                "value": value,
            }

        # prefer using the proxy's reduce protocol (stable across processes)
        try:
            reducer = obj.__reduce__()
            if isinstance(reducer, tuple) and len(reducer) >= 2:
                func, args = reducer[:2]
                reducer_tail = reducer[2:] if len(reducer) > 2 else ()
                reducer_payload = (args,) + reducer_tail
                if not _contains_auth(reducer_payload):
                    return {
                        "type_name": obj_type_name,
                        "rebuild": func,
                        "args": args,
                    }
        except Exception:
            pass
        
        # avoid dereferencing proxies or manager internals.
        # these can contain unpicklable auth keys or locks.
        value = None
        try:
            if hasattr(obj, "items"):
                value = dict(obj)
            elif hasattr(obj, "__iter__"):
                value = list(obj)
        except Exception:
            value = None
        return {
            "type_name": obj_type_name,
            "value": value,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct manager/proxy.
        
        Create new manager and return proxy with same value.
        NOTE: This creates a NEW manager in the target process.
        If rebuild is unavailable, returns the stored value.
        """
        if "rebuild" in state and "args" in state:
            try:
                return state["rebuild"](*state["args"])
            except Exception:
                return None
        return state.get("value")

