"""
Share Primitives - Low-level building blocks for process-safe shared state.

This module provides the core primitives used by the Share system:
- WriteCounter: Atomic counter for tracking pending writes
- CounterRegistry: Manages counters per object.attr key
- CommandQueue: Queue for coordinator commands
- SourceOfTruth: Manager dict with cerial serialization
"""

import ctypes
import time
from multiprocessing import Value, Queue, Manager, Lock
from multiprocessing.managers import SyncManager
from typing import Any, Dict, Optional, Tuple


class _WriteCounter:
    """
    Atomic counter for tracking pending writes to an attribute.
    
    Workers increment before queueing a write command.
    Coordinator decrements after processing the command.
    Readers wait until counter reaches 0 before reading.
    
    Uses reference counting (not toggle) so multiple concurrent
    writes are tracked correctly.
    """
    
    def __init__(self):
        """Create a new write counter initialized to 0."""
        self._count = Value(ctypes.c_int, 0)
        self._lock = Lock()
    
    def increment(self) -> int:
        """
        Increment the pending write count.
        
        Called by workers before queueing a write command.
        
        Returns:
            New count value after increment.
        """
        with self._lock:
            self._count.value += 1
            return self._count.value
    
    def decrement(self) -> int:
        """
        Decrement the pending write count.
        
        Called by coordinator after processing a write command.
        Will not go below 0.
        
        Returns:
            New count value after decrement.
        """
        with self._lock:
            self._count.value = max(0, self._count.value - 1)
            return self._count.value
    
    @property
    def pending(self) -> int:
        """Get the current pending write count."""
        return self._count.value
    
    @property
    def is_clear(self) -> bool:
        """Check if there are no pending writes."""
        return self._count.value == 0
    
    def wait_for_clear(self, timeout: float = 1.0) -> bool:
        """
        Block until there are no pending writes.
        
        Uses busy-wait with 100μs sleep intervals.
        
        Args:
            timeout: Maximum seconds to wait. Default 1.0.
        
        Returns:
            True if counter cleared, False if timeout reached.
        """
        start = time.perf_counter()
        while self._count.value > 0:
            if time.perf_counter() - start > timeout:
                return False
            time.sleep(0.0001)  # 100μs
        return True
    
    def __repr__(self) -> str:
        return f"WriteCounter(pending={self.pending})"


class _CounterRegistry:
    """
    Manages write counters for object attributes.
    
    Uses a Manager dict internally so counters are shared across processes.
    Counters are stored as integers (not WriteCounter objects) for shareability.
    Keys are in the format "object_name.attr_name".
    
    Thread/process-safe via Manager's internal synchronization.
    """
    
    def __init__(self, manager: Optional[SyncManager] = None):
        """
        Create a new counter registry.
        
        Args:
            manager: Optional SyncManager to use. Creates one if not provided.
        """
        self._manager = manager or Manager()
        self._counts = self._manager.dict()  # key -> int
        self._lock = self._manager.Lock()
    
    def get_count(self, key: str) -> int:
        """
        Get the current count for a key.
        
        Args:
            key: Counter key in format "object_name.attr_name"
        
        Returns:
            Current count, or 0 if key doesn't exist.
        """
        with self._lock:
            return self._counts.get(key, 0)
    
    def increment(self, key: str) -> int:
        """
        Increment the counter for a key (creating if needed).
        
        Args:
            key: Counter key in format "object_name.attr_name"
        
        Returns:
            New count value after increment.
        """
        with self._lock:
            current = self._counts.get(key, 0)
            new_value = current + 1
            self._counts[key] = new_value
            return new_value
    
    def decrement(self, key: str) -> int:
        """
        Decrement the counter for a key.
        
        Args:
            key: Counter key in format "object_name.attr_name"
        
        Returns:
            New count value after decrement, or 0 if counter doesn't exist.
        """
        with self._lock:
            current = self._counts.get(key, 0)
            new_value = max(0, current - 1)
            self._counts[key] = new_value
            return new_value
    
    def is_clear(self, key: str) -> bool:
        """
        Check if a counter has no pending writes.
        
        Args:
            key: Counter key in format "object_name.attr_name"
        
        Returns:
            True if count is 0 or key doesn't exist.
        """
        return self.get_count(key) == 0
    
    def wait_for_key(self, key: str, timeout: float = 1.0) -> bool:
        """
        Wait for a single counter to clear.
        
        Uses busy-wait with 100μs sleep intervals.
        
        Args:
            key: Counter key to wait for.
            timeout: Maximum seconds to wait.
        
        Returns:
            True if counter cleared, False if timeout reached.
        """
        start = time.perf_counter()
        while not self.is_clear(key):
            if time.perf_counter() - start > timeout:
                return False
            time.sleep(0.0001)  # 100μs
        return True
    
    def wait_for_keys(self, keys: list[str], timeout: float = 1.0) -> bool:
        """
        Wait for all specified counters to clear.
        
        Args:
            keys: List of counter keys to wait for.
            timeout: Maximum seconds to wait total.
        
        Returns:
            True if all counters cleared, False if timeout reached.
        """
        start = time.perf_counter()
        for key in keys:
            remaining = timeout - (time.perf_counter() - start)
            if remaining <= 0:
                return False
            
            if not self.wait_for_key(key, timeout=remaining):
                return False
        
        return True
    
    def keys(self) -> list[str]:
        """Get all registered counter keys."""
        with self._lock:
            return list(self._counts.keys())
    
    def __repr__(self) -> str:
        with self._lock:
            pending = {k: v for k, v in self._counts.items() if v > 0}
        return f"CounterRegistry(pending={pending})"


class _CommandQueue:
    """
    Queue for sending commands to the coordinator.
    
    Commands are tuples of (object_name, method_name, args, kwargs).
    Uses multiprocessing.Queue for cross-process communication.
    """
    
    def __init__(self):
        """Create a new command queue."""
        self._queue: Queue = Queue()
    
    def put(
        self,
        object_name: str,
        method_name: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        written_attrs: Optional[list[str]] = None,
    ) -> None:
        """
        Queue a command for the coordinator.
        
        Args:
            object_name: Name of the shared object.
            method_name: Method to call on the object.
            args: Positional arguments for the method.
            kwargs: Keyword arguments for the method.
            written_attrs: List of attr names this command writes to.
                          Used by coordinator to know which counters to decrement.
        """
        if kwargs is None:
            kwargs = {}
        if written_attrs is None:
            written_attrs = []
        
        command = (object_name, method_name, args, kwargs, written_attrs)
        self._queue.put(command)
    
    def get(self, timeout: Optional[float] = None) -> Optional[Tuple[str, str, tuple, dict, list]]:
        """
        Get the next command from the queue.
        
        Args:
            timeout: Maximum seconds to wait. None = block forever.
        
        Returns:
            Tuple of (object_name, method_name, args, kwargs, written_attrs),
            or None if timeout reached.
        """
        import queue as queue_module
        
        try:
            return self._queue.get(timeout=timeout)
        except queue_module.Empty:
            return None
    
    def get_nowait(self) -> Optional[Tuple[str, str, tuple, dict, list]]:
        """
        Get the next command without blocking.
        
        Returns:
            Command tuple or None if queue is empty.
        """
        return self.get(timeout=0)
    
    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty()
    
    def __repr__(self) -> str:
        return f"CommandQueue(empty={self.empty()})"


class _SourceOfTruth:
    """
    Manager dict that stores serialized object state.
    
    Only the coordinator writes to this.
    Workers read from this (after passing read barriers).
    
    Values are stored as cerial-serialized bytes for cross-process safety.
    """
    
    def __init__(self, manager: Optional[SyncManager] = None):
        """
        Create a new source of truth.
        
        Args:
            manager: Optional SyncManager to use. Creates one if not provided.
        """
        self._manager = manager or Manager()
        self._store = self._manager.dict()
        self._lock = self._manager.Lock()
    
    def set(self, object_name: str, obj: Any) -> None:
        """
        Store an object's state.
        
        Serializes the object with cerial before storing.
        
        Args:
            object_name: Name of the shared object.
            obj: The object to store.
        """
        from suitkaise import cerial
        
        with self._lock:
            serialized = cerial.serialize(obj)
            self._store[object_name] = serialized
    
    def get(self, object_name: str) -> Optional[Any]:
        """
        Retrieve an object's state.
        
        Deserializes with cerial after retrieving.
        
        Args:
            object_name: Name of the shared object.
        
        Returns:
            The deserialized object, or None if not found.
        """
        from suitkaise import cerial
        
        with self._lock:
            serialized = self._store.get(object_name)
            if serialized is None:
                return None
            return cerial.deserialize(serialized)
    
    def get_raw(self, object_name: str) -> Optional[bytes]:
        """
        Get the raw serialized bytes without deserializing.
        
        Args:
            object_name: Name of the shared object.
        
        Returns:
            Serialized bytes or None if not found.
        """
        with self._lock:
            return self._store.get(object_name)
    
    def set_raw(self, object_name: str, serialized: bytes) -> None:
        """
        Store raw serialized bytes directly.
        
        Args:
            object_name: Name of the shared object.
            serialized: Pre-serialized bytes.
        """
        with self._lock:
            self._store[object_name] = serialized
    
    def delete(self, object_name: str) -> bool:
        """
        Remove an object from the store.
        
        Args:
            object_name: Name of the shared object.
        
        Returns:
            True if object was deleted, False if it didn't exist.
        """
        with self._lock:
            if object_name in self._store:
                del self._store[object_name]
                return True
            return False
    
    def keys(self) -> list[str]:
        """Get all stored object names."""
        with self._lock:
            return list(self._store.keys())
    
    def __contains__(self, object_name: str) -> bool:
        """Check if an object exists in the store."""
        with self._lock:
            return object_name in self._store
    
    def __repr__(self) -> str:
        with self._lock:
            keys = list(self._store.keys())
        return f"SourceOfTruth(objects={keys})"
