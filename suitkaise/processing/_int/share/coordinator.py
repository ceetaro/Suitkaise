"""
Share Coordinator - Background process that handles all writes.

The coordinator is the single process that:
1. Consumes commands from the command queue
2. Executes methods on local mirror objects
3. Commits updated state to the source of truth
4. Decrements write counters to signal completion

This ensures all writes are serialized and consistent.
"""

import multiprocessing
from multiprocessing import Process, Event
from multiprocessing.managers import SyncManager
from typing import Any, Dict, Optional

from .primitives import _AtomicCounterRegistry
import time
import traceback


class _Coordinator:
    """
    Background coordinator process for handling shared state writes.
    
    The coordinator runs in a separate process and is responsible for:
    - Consuming commands from the command queue
    - Executing commands on mirror objects
    - Committing state to the source of truth
    - Decrementing write counters after commits
    
    Only one coordinator should exist per Share instance.
    """
    
    def __init__(
        self,
        manager: Optional[SyncManager] = None,
        *,
        command_queue: Any | None = None,
        counter_registry: Any | None = None,
        source_store: Any | None = None,
        source_lock: Any | None = None,
        object_names: Any | None = None,
    ):
        """
        Create a new coordinator.
        
        Args:
            manager: Optional SyncManager to use. Creates one if not provided.
        """
        from multiprocessing import Manager
        
        self._manager = manager
        
        # shared primitives - all use Manager for cross-process access
        if command_queue is None or counter_registry is None or source_store is None or source_lock is None or object_names is None:
            self._manager = manager or Manager()
            self._command_queue = self._manager.Queue()
            # write tracking with atomic counters (prevents read starvation)
            self._counter_registry = _AtomicCounterRegistry(self._manager)
            self._source_store = self._manager.dict()  # object_name -> serialized bytes
            self._source_lock = self._manager.Lock()
            # object name registry (which objects are registered)
            self._object_names = self._manager.list()
        else:
            self._command_queue = command_queue
            self._counter_registry = counter_registry
            self._source_store = source_store
            self._source_lock = source_lock
            self._object_names = object_names
        
        # process management
        self._process: Optional[Process] = None
        self._stop_event: Optional[Event] = None
        self._error_event: Optional[Event] = None
        
        # configuration
        self._poll_timeout = 0.1  # how long to wait for commands

    def get_state(self) -> dict:
        """Return proxy state for sharing this coordinator across processes."""
        # only include the manager-backed primitives and config needed to reconstruct
        return {
            "command_queue": self._command_queue,
            "counter_registry": self._counter_registry,
            "source_store": self._source_store,
            "source_lock": self._source_lock,
            "object_names": self._object_names,
            "poll_timeout": self._poll_timeout,
        }

    @classmethod
    def from_state(cls, state: dict) -> "_Coordinator":
        """Create a coordinator instance bound to existing shared proxies."""
        coord = cls(
            manager=None,
            command_queue=state["command_queue"],
            counter_registry=state["counter_registry"],
            source_store=state["source_store"],
            source_lock=state["source_lock"],
            object_names=state["object_names"],
        )
        coord._poll_timeout = state.get("poll_timeout", 0.1)
        return coord
    
    def register_object(self, object_name: str, obj: Any, attrs: set[str] | None = None) -> None:
        """
        Register an object for the coordinator to manage.
        
        Called when an object is assigned to Share.
        Stores initial state in source of truth.
        
        Args:
            object_name: Name of the shared object.
            obj: The object to register.
        """
        from suitkaise import cucumber
        
        # persist initial serialized state as source of truth
        with self._source_lock:
            serialized = cucumber.serialize(obj)
            self._source_store[object_name] = serialized
        
        # track names for introspection and cleanup
        if object_name not in list(self._object_names):
            self._object_names.append(object_name)
        
        # register counter keys for read/write synchronization
        if attrs:
            self._counter_registry.register_keys(object_name, attrs)
    
    def get_object(self, object_name: str) -> Optional[Any]:
        """
        Get current state of an object from source of truth.
        
        Args:
            object_name: Name of the shared object.
        
        Returns:
            Deserialized object or None if not found.
        """
        from suitkaise import cucumber
        
        with self._source_lock:
            serialized = self._source_store.get(object_name)
            if serialized is None:
                return None
            return cucumber.deserialize(serialized)
    
    def queue_command(
        self,
        object_name: str,
        method_name: str,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        written_attrs: Optional[list[str]] = None,
    ) -> None:
        """
        Queue a command for the coordinator to process.
        
        Args:
            object_name: Name of the shared object.
            method_name: Method to call on the object.
            args: Positional arguments for the method.
            kwargs: Keyword arguments for the method.
            written_attrs: List of attr names this command writes to.
        """
        from suitkaise import cucumber
        
        if kwargs is None:
            kwargs = {}
        if written_attrs is None:
            written_attrs = []
        
        # serialize args/kwargs so complex objects survive process boundaries
        serialized_args = cucumber.serialize(args)
        serialized_kwargs = cucumber.serialize(kwargs)
        
        command = (object_name, method_name, serialized_args, serialized_kwargs, written_attrs)
        self._command_queue.put(command)
    
    def increment_pending(self, key: str) -> int:
        """
        Increment the pending write counter.
        
        Called by workers before queueing a command.
        
        Args:
            key: Counter key in format "object_name.attr_name"
        
        Returns:
            New pending count.
        """
        return self._counter_registry.increment_pending(key)
    
    def get_read_target(self, key: str) -> int:
        """
        Get the target completion count for a read to wait for.
        
        Captures current state: completed + pending = how many writes
        must finish before this read can proceed.
        
        This prevents read starvation: new writes that arrive after
        this snapshot don't extend the wait.
        
        Args:
            key: Counter key in format "object_name.attr_name"
        
        Returns:
            Target completion count to wait for.
        """
        targets = self._counter_registry.get_read_targets([key])
        return targets.get(key, 0)
    
    def wait_for_read(self, keys: list[str], timeout: float = 1.0) -> bool:
        """
        Wait for reads to be safe on the specified attrs.
        
        Uses completion counters to prevent starvation:
        - Captures target = completed + pending at start
        - Waits until completed >= target
        - New writes after snapshot don't extend wait
        
        Args:
            keys: List of counter keys to wait for.
            timeout: Maximum seconds to wait total.
        
        Returns:
            True if all attrs are safe to read, False if timeout.
        """
        return self._counter_registry.wait_for_read(keys, timeout=timeout)

    def get_object_keys(self, object_name: str) -> list[str]:
        """Get all registered counter keys for an object."""
        return self._counter_registry.keys_for_object(object_name)

    def remove_object(self, object_name: str) -> None:
        """Remove an object from coordinator state."""
        with self._source_lock:
            try:
                if object_name in self._source_store:
                    del self._source_store[object_name]
            except Exception:
                try:
                    del self._source_store[object_name]
                except Exception:
                    pass
        # remove from name registry (may contain duplicates on some managers)
        try:
            if object_name in list(self._object_names):
                self._object_names.remove(object_name)
        except Exception:
            try:
                while True:
                    self._object_names.remove(object_name)
            except Exception:
                pass
        # release counters and shared memory slots for this object's attrs
        try:
            self._counter_registry.remove_object(object_name)
        except Exception:
            pass
        # tell the coordinator process to drop its mirror cache
        try:
            self._command_queue.put(("__remove__", object_name, None, None, None))
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all registered objects and counters."""
        with self._source_lock:
            self._source_store.clear()
        try:
            self._object_names[:] = []
        except Exception:
            try:
                self._object_names.clear()
            except Exception:
                pass
        self._counter_registry.reset()
        # clear coordinator-side mirrors
        self._command_queue.put(("__clear__", None, None, None, None))
    
    def start(self) -> None:
        """
        Start the coordinator background process.
        
        The coordinator will run until stop() is called.
        """
        if self._process is not None and self._process.is_alive():
            return  # already running
        
        # use manager-backed Events when available to avoid SemLock issues on spawn
        if self._manager is not None:
            self._stop_event = self._manager.Event()
            self._error_event = self._manager.Event()
        else:
            self._stop_event = Event()
            self._error_event = Event()
        
        self._process = Process(
            target=_coordinator_main,
            args=(
                self._command_queue,
                self._counter_registry,
                self._source_store,
                self._source_lock,
                self._stop_event,
                self._error_event,
                self._poll_timeout,
            ),
            daemon=True,
        )
        self._process.start()
    
    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the coordinator gracefully.
        
        Signals the coordinator to stop and waits for it to finish
        processing any remaining commands.
        
        Args:
            timeout: Maximum seconds to wait for shutdown.
        
        Returns:
            True if stopped cleanly, False if timed out.
        """
        if self._process is None or not self._process.is_alive():
            return True
        
        # signal shutdown and wait for the process to exit gracefully
        if self._stop_event is not None:
            try:
                self._stop_event.set()
            except (OSError, EOFError, BrokenPipeError, ConnectionRefusedError):
                # Manager connection already dead — process likely exited
                pass
        
        self._process.join(timeout=timeout)
        
        if self._process.is_alive():
            # force kill if didn't stop gracefully
            self._process.terminate()
            self._process.join(timeout=1.0)
            return False
        # cleanup shared-memory counters after stopping
        try:
            self._counter_registry.reset()
        except Exception:
            pass
        return True
    
    def kill(self) -> None:
        """
        Forcefully terminate the coordinator immediately.
        """
        # used as a last resort when shutdown hangs
        if self._process is not None and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)
            if self._process.is_alive():
                self._process.kill()
    
    @property
    def is_alive(self) -> bool:
        """Check if the coordinator process is running."""
        return self._process is not None and self._process.is_alive()
    
    @property
    def has_error(self) -> bool:
        """Check if the coordinator encountered an error."""
        return self._error_event is not None and self._error_event.is_set()
    
    def __repr__(self) -> str:
        status = "running" if self.is_alive else "stopped"
        if self.has_error:
            status = "error"
        objects = list(self._object_names)
        return f"Coordinator(status={status}, objects={objects})"


def _coordinator_main(
    command_queue,
    counter_registry: _AtomicCounterRegistry,
    source_store,
    source_lock,
    stop_event: Event,
    error_event: Event,
    poll_timeout: float,
) -> None:
    """
    Main function for the coordinator process.
    
    Runs the command processing loop until stop_event is set.
    
    Args:
        command_queue: Manager Queue to consume from.
        pending_counts: Manager dict of pending write counts.
        completed_counts: Manager dict of completed write counts.
        counter_lock: Manager Lock for counter access.
        source_store: Manager dict for source of truth.
        source_lock: Manager Lock for source access.
        stop_event: Event to signal shutdown.
        error_event: Event to signal errors to parent.
        poll_timeout: Seconds to wait for each queue.get().
    """
    import queue as queue_module
    from suitkaise import cucumber
    
    # local cache of deserialized objects for efficiency
    mirrors: Dict[str, Any] = {}
    
    def _stop_requested() -> bool:
        try:
            return stop_event.is_set()
        except (EOFError, BrokenPipeError, FileNotFoundError, OSError):
            # manager connection is gone; treat as shutdown
            return True

    def _safe_set_error() -> None:
        try:
            error_event.set()
        except (EOFError, BrokenPipeError, FileNotFoundError, OSError):
            # manager connection is gone; can't report error
            return

    try:
        while not _stop_requested():
            # try to get a command
            try:
                command = command_queue.get(timeout=poll_timeout)
            except queue_module.Empty:
                continue  # no command, check stop_event again
            except (EOFError, BrokenPipeError, FileNotFoundError, OSError):
                break
            
            if command is None:
                continue
            
            # unpack command
            object_name, method_name, serialized_args, serialized_kwargs, written_attrs = command
            
            if object_name == "__clear__":
                # reset coordinator-side mirror cache
                mirrors.clear()
                continue

            if object_name == "__remove__":
                # explicitly drop a single object mirror
                target_name = method_name
                if target_name:
                    mirrors.pop(target_name, None)
                    with source_lock:
                        try:
                            if target_name in source_store:
                                del source_store[target_name]
                        except Exception:
                            try:
                                del source_store[target_name]
                            except Exception:
                                pass
                continue
            
            # deserialize args/kwargs for the method invocation
            try:
                args = cucumber.deserialize(serialized_args)
                kwargs = cucumber.deserialize(serialized_kwargs)
            except Exception:
                _safe_set_error()
                _update_counters_after_write(counter_registry, object_name, written_attrs)
                continue
            
            # get the mirror object (from cache or source of truth)
            mirror = mirrors.get(object_name)
            if mirror is None:
                with source_lock:
                    serialized = source_store.get(object_name)
                    if serialized is not None:
                        mirror = cucumber.deserialize(serialized)
                        mirrors[object_name] = mirror
            
            if mirror is None:
                # object not found, update counters and skip
                _update_counters_after_write(counter_registry, object_name, written_attrs)
                continue
            
            # execute the method on the mirror
            try:
                method = getattr(mirror, method_name)
                method(*args, **kwargs)
            except Exception as e:
                # log error but continue processing
                traceback.print_exc()
            
            # commit updated state to source of truth
            with source_lock:
                serialized = cucumber.serialize(mirror)
                source_store[object_name] = serialized
            
            # update counters: decrement pending, increment completed
            _update_counters_after_write(counter_registry, object_name, written_attrs)
    
    except Exception as e:
        # fatal error in coordinator loop
        _safe_set_error()
        traceback.print_exc()
        raise


def _update_counters_after_write(
    counter_registry: _AtomicCounterRegistry,
    object_name: str,
    written_attrs: list[str],
) -> None:
    """
    Update counters after a write is processed.
    
    Decrements pending count and increments completed count for each attr.
    This allows reads to track completion without starvation.
    
    Args:
        pending_counts: Manager dict of pending write counts.
        completed_counts: Manager dict of completed write counts.
        counter_lock: Manager Lock for counter access.
        object_name: Name of the shared object.
        written_attrs: List of attr names that were written.
    """
    for attr in written_attrs:
        key = f"{object_name}.{attr}"
        counter_registry.update_after_write(key)
