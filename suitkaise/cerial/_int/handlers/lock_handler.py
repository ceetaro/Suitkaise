"""
Handler for threading lock objects.

Locks are synchronization primitives used to prevent race conditions.
We serialize their type and locked state, then recreate them in the target process.

IMPORTANT LIMITATION: Lock thread ownership does NOT transfer across processes.
When a lock is reconstructed, it's acquired by the reconstructing thread, not the
original owning thread. This is a fundamental limitation of serializing thread-local state.
"""

import threading
from typing import Any, Dict, Union
from .base_class import Handler


class LockSerializationError(Exception):
    """Raised when lock serialization fails."""
    pass


class LockHandler(Handler):
    """
    Serializes threading.Lock and threading.RLock objects.
    
    Strategy:
    - Capture lock type (Lock vs RLock)
    - Capture locked state (acquired or not)
    - On reconstruction, create new lock and acquire if it was locked
    
    Important: We CANNOT preserve lock ownership across processes.
    The lock owner (thread ID) doesn't make sense in a different process.
    We just preserve whether it was locked or not.
    """
    
    type_name = "lock"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a Lock or RLock.
        
        We handle both regular Lock and RLock (reentrant lock).
        Note: type(obj) might be a private _thread.lock type, so we check
        the module and class name.
        """
        obj_type = type(obj)
        return (
            obj_type == threading.Lock().__class__ or  # threading.Lock
            obj_type == threading.RLock().__class__    # threading.RLock
        )
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract lock state.
        
        What we capture:
        - type_name: "Lock" or "RLock" 
        - locked: Boolean indicating if lock is currently acquired
        
        Note: Lock objects have a locked() method that returns True/False.
        """
        # Determine lock type by comparing to known lock types
        if type(obj) == threading.RLock().__class__:
            lock_type_name = "RLock"
        else:
            lock_type_name = "Lock"
        
        return {
            "lock_type": lock_type_name,
            "locked": obj.locked(),  # True if acquired, False otherwise
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct lock from state.
        
        Process:
        1. Create new lock of the appropriate type
        2. If it was locked, acquire it
        
        Note: The lock will be owned by whoever calls this method in the
        target process. This is the best we can do - lock ownership doesn't
        transfer across processes.
        """
        # Create new lock of appropriate type
        if state["lock_type"] == "RLock":
            lock = threading.RLock()
        else:
            lock = threading.Lock()
        
        # If lock was acquired, acquire it in new process
        # This is a best-effort reconstruction - the owner will be different
        if state["locked"]:
            lock.acquire()
        
        return lock


class SemaphoreHandler(Handler):
    """
    Serializes threading.Semaphore and BoundedSemaphore objects.
    
    Semaphores are counters that allow a fixed number of acquisitions.
    We capture the initial value and current value.
    """
    
    type_name = "semaphore"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a Semaphore or BoundedSemaphore."""
        return isinstance(obj, (threading.Semaphore, threading.BoundedSemaphore))
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract semaphore state.
        
        What we capture:
        - type_name: "Semaphore" or "BoundedSemaphore"
        - initial_value: The starting counter value (stored in _value)
        - current_value: Current counter value
        
        Note: Semaphore internals vary by Python version, so we try
        multiple attributes to get the counter value.
        """
        is_bounded = isinstance(obj, threading.BoundedSemaphore)
        
        # Try to get current value (internal attribute name varies)
        try:
            current_value = obj._value
        except AttributeError:
            # Fallback: assume it's at initial value
            current_value = 1
        
        # Try to get initial value for BoundedSemaphore
        if is_bounded:
            try:
                initial_value = obj._initial_value
            except AttributeError:
                initial_value = current_value
        else:
            initial_value = current_value
        
        return {
            "semaphore_type": "BoundedSemaphore" if is_bounded else "Semaphore",
            "initial_value": initial_value,
            "current_value": current_value,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct semaphore from state.
        
        Process:
        1. Create new semaphore with initial value
        2. Acquire/release to match current value
        
        This gets the counter to the right value, though the actual
        acquisition history is lost (which is fine for most use cases).
        """
        initial = state["initial_value"]
        current = state["current_value"]
        
        # Create semaphore of appropriate type
        if state["semaphore_type"] == "BoundedSemaphore":
            sem = threading.BoundedSemaphore(initial)
        else:
            sem = threading.Semaphore(initial)
        
        # Adjust to current value by acquiring
        # If current < initial, we need to acquire (initial - current) times
        while initial > current:
            sem.acquire()
            initial -= 1
        
        return sem


class BarrierHandler(Handler):
    """
    Serializes threading.Barrier objects.
    
    Barriers synchronize a fixed number of threads at a checkpoint.
    We capture the number of parties (threads) that must arrive.
    """
    
    type_name = "barrier"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a Barrier."""
        return isinstance(obj, threading.Barrier)
    
    def extract_state(self, obj: threading.Barrier) -> Dict[str, Any]:
        """
        Extract barrier state.
        
        What we capture:
        - parties: Number of threads that must arrive at barrier
        - action: Optional function called when all parties arrive
        - timeout: Optional timeout value
        
        Note: We don't capture how many threads are currently waiting,
        since thread state doesn't transfer across processes.
        """
        return {
            "parties": obj.parties,
            "action": obj._action if hasattr(obj, '_action') else None,
            "timeout": obj._timeout if hasattr(obj, '_timeout') else None,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> threading.Barrier:
        """
        Reconstruct barrier with same configuration.
        
        Creates a fresh barrier with same parties count.
        """
        return threading.Barrier(
            state["parties"],
            action=state["action"],
            timeout=state["timeout"]
        )


class ConditionHandler(Handler):
    """
    Serializes threading.Condition objects.
    
    Conditions allow threads to wait for notifications from other threads.
    """
    
    type_name = "condition"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a Condition."""
        return isinstance(obj, threading.Condition)
    
    def extract_state(self, obj: threading.Condition) -> Dict[str, Any]:
        """
        Extract condition state.
        
        What we capture:
        - lock: The underlying lock (RLock by default)
        
        The lock will be recursively serialized by the central serializer.
        """
        return {
            "lock": obj._lock,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> threading.Condition:
        """
        Reconstruct condition with same lock.
        
        The lock has already been deserialized by the central deserializer.
        """
        return threading.Condition(lock=state["lock"])

