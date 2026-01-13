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
    
    def __init__(self, manager: Optional[SyncManager] = None):
        """
        Create a new coordinator.
        
        Args:
            manager: Optional SyncManager to use. Creates one if not provided.
        """
        from multiprocessing import Manager
        
        self._manager = manager or Manager()
        
        # Shared primitives - all use Manager for cross-process access
        self._command_queue = self._manager.Queue()
        
        # Write tracking with completion counters (prevents read starvation)
        # pending_counts: how many writes are currently queued (goes up and down)
        # completed_counts: how many writes have finished (monotonically increasing)
        self._pending_counts = self._manager.dict()    # key -> int
        self._completed_counts = self._manager.dict()  # key -> int
        self._counter_lock = self._manager.Lock()
        
        self._source_store = self._manager.dict()  # object_name -> serialized bytes
        self._source_lock = self._manager.Lock()
        
        # Object name registry (which objects are registered)
        self._object_names = self._manager.list()
        
        # Process management
        self._process: Optional[Process] = None
        self._stop_event: Optional[Event] = None
        self._error_event: Optional[Event] = None
        
        # Configuration
        self._poll_timeout = 0.1  # How long to wait for commands
    
    def register_object(self, object_name: str, obj: Any) -> None:
        """
        Register an object for the coordinator to manage.
        
        Called when an object is assigned to Share.
        Stores initial state in source of truth.
        
        Args:
            object_name: Name of the shared object.
            obj: The object to register.
        """
        from suitkaise import cerial
        
        with self._source_lock:
            serialized = cerial.serialize(obj)
            self._source_store[object_name] = serialized
        
        if object_name not in list(self._object_names):
            self._object_names.append(object_name)
    
    def get_object(self, object_name: str) -> Optional[Any]:
        """
        Get current state of an object from source of truth.
        
        Args:
            object_name: Name of the shared object.
        
        Returns:
            Deserialized object or None if not found.
        """
        from suitkaise import cerial
        
        with self._source_lock:
            serialized = self._source_store.get(object_name)
            if serialized is None:
                return None
            return cerial.deserialize(serialized)
    
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
        from suitkaise import cerial
        
        if kwargs is None:
            kwargs = {}
        if written_attrs is None:
            written_attrs = []
        
        # Serialize args/kwargs with cerial for complex objects
        serialized_args = cerial.serialize(args)
        serialized_kwargs = cerial.serialize(kwargs)
        
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
        with self._counter_lock:
            current = self._pending_counts.get(key, 0)
            new_value = current + 1
            self._pending_counts[key] = new_value
            return new_value
    
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
        with self._counter_lock:
            completed = self._completed_counts.get(key, 0)
            pending = self._pending_counts.get(key, 0)
            return completed + pending
    
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
        # Capture targets for all keys atomically
        with self._counter_lock:
            targets = {}
            for key in keys:
                completed = self._completed_counts.get(key, 0)
                pending = self._pending_counts.get(key, 0)
                targets[key] = completed + pending
        
        # Wait for each key to reach its target
        start = time.perf_counter()
        for key, target in targets.items():
            while True:
                with self._counter_lock:
                    completed = self._completed_counts.get(key, 0)
                
                if completed >= target:
                    break
                
                if time.perf_counter() - start > timeout:
                    return False
                
                time.sleep(0.0001)  # 100μs
        
        return True
    
    def start(self) -> None:
        """
        Start the coordinator background process.
        
        The coordinator will run until stop() is called.
        """
        if self._process is not None and self._process.is_alive():
            return  # Already running
        
        self._stop_event = Event()
        self._error_event = Event()
        
        self._process = Process(
            target=_coordinator_main,
            args=(
                self._command_queue,
                self._pending_counts,
                self._completed_counts,
                self._counter_lock,
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
        
        if self._stop_event is not None:
            self._stop_event.set()
        
        self._process.join(timeout=timeout)
        
        if self._process.is_alive():
            # Force kill if didn't stop gracefully
            self._process.terminate()
            self._process.join(timeout=1.0)
            return False
        
        return True
    
    def kill(self) -> None:
        """
        Forcefully terminate the coordinator immediately.
        """
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
    pending_counts,
    completed_counts,
    counter_lock,
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
    from suitkaise import cerial
    
    # Local cache of deserialized objects for efficiency
    mirrors: Dict[str, Any] = {}
    
    try:
        while not stop_event.is_set():
            # Try to get a command
            try:
                command = command_queue.get(timeout=poll_timeout)
            except queue_module.Empty:
                continue  # No command, check stop_event again
            
            if command is None:
                continue
            
            # Unpack command
            object_name, method_name, serialized_args, serialized_kwargs, written_attrs = command
            
            # Deserialize args/kwargs
            args = cerial.deserialize(serialized_args)
            kwargs = cerial.deserialize(serialized_kwargs)
            
            # Get the mirror object (from cache or source of truth)
            mirror = mirrors.get(object_name)
            if mirror is None:
                with source_lock:
                    serialized = source_store.get(object_name)
                    if serialized is not None:
                        mirror = cerial.deserialize(serialized)
                        mirrors[object_name] = mirror
            
            if mirror is None:
                # Object not found, update counters and skip
                _update_counters_after_write(
                    pending_counts, completed_counts, counter_lock,
                    object_name, written_attrs
                )
                continue
            
            # Execute the method on the mirror
            try:
                method = getattr(mirror, method_name)
                method(*args, **kwargs)
            except Exception as e:
                # Log error but continue processing
                traceback.print_exc()
            
            # Commit updated state to source of truth
            with source_lock:
                serialized = cerial.serialize(mirror)
                source_store[object_name] = serialized
            
            # Update counters: decrement pending, increment completed
            _update_counters_after_write(
                pending_counts, completed_counts, counter_lock,
                object_name, written_attrs
            )
    
    except Exception as e:
        # Fatal error in coordinator loop
        error_event.set()
        traceback.print_exc()
        raise


def _update_counters_after_write(
    pending_counts,
    completed_counts,
    counter_lock,
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
    with counter_lock:
        for attr in written_attrs:
            key = f"{object_name}.{attr}"
            
            # Decrement pending
            pending = pending_counts.get(key, 0)
            pending_counts[key] = max(0, pending - 1)
            
            # Increment completed
            completed = completed_counts.get(key, 0)
            completed_counts[key] = completed + 1
