"""
Share Primitives - Low-level building blocks for process-safe shared state.

This module provides the core primitives used by the Share system:
- WriteCounter: Atomic counter for tracking pending writes
- CounterRegistry: Manages counters per object.attr key
- CommandQueue: Queue for coordinator commands
- SourceOfTruth: Manager dict with cerial serialization
"""

import ctypes
import struct
import time
from multiprocessing import Queue, Manager
from multiprocessing import shared_memory
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


class _AtomicCounterRegistry:
    """
    Atomic counter registry backed by shared memory Values.
    
    - Mapping lives in a Manager dict (for dynamic registration)
    - Actual counters are multiprocessing.Value (shared memory)
    - Each process caches Value handles locally for fast access
    """
    
    def __init__(self, manager: Optional[SyncManager] = None):
        self._manager = manager or Manager()
        self._registry = self._manager.dict()  # key -> (pending_name, completed_name)
        self._object_keys = self._manager.dict()  # object_name -> list[key]
        self._lock = self._manager.Lock()
        self._local: Dict[str, tuple[shared_memory.SharedMemory, shared_memory.SharedMemory]] = {}
        self._local_object_keys: Dict[str, list[str]] = {}
        self._owned_names: set[str] = set()

    def __getstate__(self) -> dict:
        """Return picklable state without manager internals."""
        return {
            "_registry": self._registry,
            "_object_keys": self._object_keys,
            "_lock": self._lock,
        }

    def __setstate__(self, state: dict) -> None:
        """Restore from pickled state in child processes."""
        self._manager = None
        self._registry = state["_registry"]
        self._object_keys = state["_object_keys"]
        self._lock = state["_lock"]
        self._local = {}
        self._local_object_keys = {}
        self._owned_names = set()
    
    def register_keys(self, object_name: str, attrs: set[str]) -> None:
        """Register counters for a set of attributes."""
        keys = [f"{object_name}.{attr}" for attr in attrs]
        if not keys:
            return
        with self._lock:
            for key in keys:
                if key not in self._registry:
                    pending = self._create_shared_counter()
                    completed = self._create_shared_counter()
                    self._registry[key] = (pending.name, completed.name)
                    self._local[key] = (pending, completed)
                    self._owned_names.update({pending.name, completed.name})
                else:
                    self._local[key] = self._attach_shared_counter(self._registry[key])
            existing = list(self._object_keys.get(object_name, []))
            merged = list(dict.fromkeys(existing + keys))
            self._object_keys[object_name] = merged
            self._local_object_keys[object_name] = merged
    
    def _create_shared_counter(self) -> shared_memory.SharedMemory:
        shm = shared_memory.SharedMemory(create=True, size=ctypes.sizeof(ctypes.c_int))
        struct.pack_into("i", shm.buf, 0, 0)
        return shm

    def _attach_shared_counter(
        self,
        counter_entry: tuple[str, str],
    ) -> tuple[shared_memory.SharedMemory, shared_memory.SharedMemory]:
        pending_name, completed_name = counter_entry
        return (
            shared_memory.SharedMemory(name=pending_name),
            shared_memory.SharedMemory(name=completed_name),
        )

    def _ensure_counter(self, key: str) -> tuple[shared_memory.SharedMemory, shared_memory.SharedMemory]:
        with self._lock:
            counter = self._registry.get(key)
            if counter is None:
                pending = self._create_shared_counter()
                completed = self._create_shared_counter()
                self._registry[key] = (pending.name, completed.name)
                object_name = key.rsplit(".", 1)[0]
                existing = list(self._object_keys.get(object_name, []))
                merged = list(dict.fromkeys(existing + [key]))
                self._object_keys[object_name] = merged
                self._local_object_keys[object_name] = merged
                self._local[key] = (pending, completed)
                self._owned_names.update({pending.name, completed.name})
                return self._local[key]
            self._local[key] = self._attach_shared_counter(counter)
            return self._local[key]
    
    def _get_counter(
        self,
        key: str,
    ) -> tuple[shared_memory.SharedMemory, shared_memory.SharedMemory]:
        counter = self._local.get(key)
        if counter is not None:
            return counter
        return self._ensure_counter(key)
    
    def increment_pending(self, key: str) -> int:
        counter = self._get_counter(key)
        pending, _ = counter
        with self._lock:
            value = struct.unpack_from("i", pending.buf, 0)[0] + 1
            struct.pack_into("i", pending.buf, 0, value)
            return value
    
    def update_after_write(self, key: str) -> None:
        counter = self._get_counter(key)
        pending, completed = counter
        with self._lock:
            pending_val = struct.unpack_from("i", pending.buf, 0)[0]
            pending_val = max(0, pending_val - 1)
            struct.pack_into("i", pending.buf, 0, pending_val)
            completed_val = struct.unpack_from("i", completed.buf, 0)[0] + 1
            struct.pack_into("i", completed.buf, 0, completed_val)
    
    def get_read_targets(self, keys: list[str]) -> dict[str, int]:
        targets: dict[str, int] = {}
        for key in keys:
            counter = self._get_counter(key)
            pending, completed = counter
            with self._lock:
                pending_val = struct.unpack_from("i", pending.buf, 0)[0]
                completed_val = struct.unpack_from("i", completed.buf, 0)[0]
            targets[key] = completed_val + pending_val
        return targets
    
    def wait_for_read(self, keys: list[str], timeout: float = 1.0) -> bool:
        if not keys:
            return True
        targets = self.get_read_targets(keys)
        start = time.perf_counter()
        for key, target in targets.items():
            counter = self._get_counter(key)
            if counter is None:
                continue
            _, completed = counter
            while True:
                with self._lock:
                    if struct.unpack_from("i", completed.buf, 0)[0] >= target:
                        break
                if time.perf_counter() - start > timeout:
                    return False
                time.sleep(0.0001)
        return True
    
    def keys_for_object(self, object_name: str) -> list[str]:
        keys = self._local_object_keys.get(object_name)
        if keys is not None:
            return keys
        keys = list(self._object_keys.get(object_name, []))
        self._local_object_keys[object_name] = keys
        return keys

    def reset(self) -> None:
        """Clear all counters and local caches."""
        names: list[str] = []
        with self._lock:
            for pending_name, completed_name in list(self._registry.values()):
                names.extend([pending_name, completed_name])
            self._registry.clear()
            self._object_keys.clear()
            local = list(self._local.values())
            self._local.clear()
            self._local_object_keys.clear()
        for pending, completed in local:
            try:
                pending.close()
            except Exception:
                pass
            try:
                completed.close()
            except Exception:
                pass
        for name in set(names + list(self._owned_names)):
            try:
                shm = shared_memory.SharedMemory(name=name)
                shm.close()
                shm.unlink()
            except Exception:
                pass
        self._owned_names.clear()


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
