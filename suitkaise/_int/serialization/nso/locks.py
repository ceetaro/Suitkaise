"""
Threading Locks Serialization Handler

This module provides serialization support for threading locks and synchronization
primitives that cannot be pickled normally due to their system-specific state.

Supported Objects:
- threading.Lock
- threading.RLock  
- threading.Semaphore
- threading.BoundedSemaphore
- threading.Condition
- threading.Event
- threading.Barrier
- multiprocessing equivalents

Strategy:
- Store lock type and initialization parameters
- Recreate equivalent lock on deserialization
- Maintain lock characteristics (like semaphore value limits)
- Handle both threading and multiprocessing locks
"""

import threading
import multiprocessing
from typing import Any, Dict, Optional

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class LocksHandler(_NSO_Handler):
    """Handler for threading locks and synchronization primitives."""
    
    def __init__(self):
        """Initialize the locks handler."""
        super().__init__()
        self._handler_name = "LocksHandler"
        self._priority = 50  # Default priority for locks
    
    def can_handle(self, obj: Any) -> bool:
        """Check if this handler can serialize the given lock object."""
        # Get object type name and module for comparison
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), '__module__', '')
        
        # Threading module locks - check by type name and module
        threading_lock_types = {
            'lock', '_RLock', 'Semaphore', 'BoundedSemaphore', 
            'Condition', 'Event', 'Barrier'
        }
        
        if obj_type_name in threading_lock_types:
            return True
        
        # Check by module name for threading objects
        if 'threading' in obj_module or '_thread' in obj_module:
            return True
        
        # Multiprocessing locks (when available)
        try:
            mp_lock_types = {
                'Lock', 'RLock', 'Semaphore', 'BoundedSemaphore',
                'Condition', 'Event', 'Barrier'
            }
            if obj_type_name in mp_lock_types and 'multiprocessing' in obj_module:
                return True
        except AttributeError:
            # Some multiprocessing types might not be available
            pass
        
        # Additional fallback check for lock-like objects
        if hasattr(obj, 'acquire') and hasattr(obj, 'release'):
            # This is likely a lock-like object
            return True
        
        return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """Serialize a lock object to a dictionary representation."""
        obj_type = type(obj)
        obj_module = obj_type.__module__
        obj_name = obj_type.__name__
        
        # Base serialization data
        data = {
            "lock_type": obj_name,
            "module": obj_module,
            "full_type": f"{obj_module}.{obj_name}"
        }
        
        # Handle specific lock types with their parameters
        if 'Semaphore' in obj_name:
            data.update(self._serialize_semaphore(obj))
        
        elif 'Condition' in obj_name:
            data.update(self._serialize_condition(obj))
        
        elif 'Event' in obj_name:
            data.update(self._serialize_event(obj))
        
        elif 'Barrier' in obj_name:
            data.update(self._serialize_barrier(obj))
        
        elif 'lock' in obj_name.lower() or 'Lock' in obj_name:
            data.update(self._serialize_basic_lock(obj))
        
        else:
            # Generic lock-like object
            data.update(self._serialize_basic_lock(obj))
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Deserialize a lock object from dictionary representation."""
        lock_type = data.get("lock_type")
        module = data.get("module", "threading")
        
        # Route to appropriate deserialization method
        if 'Semaphore' in lock_type:
            return self._deserialize_semaphore(data, module)
        
        elif 'Condition' in lock_type:
            return self._deserialize_condition(data, module)
        
        elif 'Event' in lock_type:
            return self._deserialize_event(data, module)
        
        elif 'Barrier' in lock_type:
            return self._deserialize_barrier(data, module)
        
        elif 'lock' in lock_type.lower() or 'Lock' in lock_type:
            return self._deserialize_basic_lock(data, module)
        
        else:
            # Default to basic lock
            return self._deserialize_basic_lock(data, module)
    
    def _serialize_semaphore(self, obj) -> Dict[str, Any]:
        """Serialize semaphore specific data."""
        # Unfortunately, we can't easily get the current value or initial value
        # from a Semaphore object. We'll recreate with default value.
        semaphore_type = "bounded" if "Bounded" in type(obj).__name__ else "normal"
        return {
            "semaphore_type": semaphore_type,
            "initial_value": 1,  # Default value - we can't detect the actual value
            "note": "Semaphore recreated with default value - actual value unknown"
        }
    
    def _serialize_condition(self, obj) -> Dict[str, Any]:
        """Serialize condition specific data."""
        return {
            "has_underlying_lock": hasattr(obj, '_lock') and obj._lock is not None,
            "note": "Condition recreated with new underlying lock"
        }
    
    def _serialize_event(self, obj) -> Dict[str, Any]:
        """Serialize event specific data."""
        try:
            is_set = obj.is_set()
        except AttributeError:
            is_set = False  # Fallback if is_set method not available
        
        return {
            "is_set": is_set,
            "note": "Event state preserved"
        }
    
    def _serialize_barrier(self, obj) -> Dict[str, Any]:
        """Serialize barrier specific data."""
        try:
            parties = getattr(obj, 'parties', 1)
        except AttributeError:
            parties = 1  # Fallback
            
        return {
            "parties": parties,
            "action": None,  # We can't serialize the action function
            "timeout": None,  # We can't get the timeout value
            "note": "Barrier recreated with same party count but no action"
        }
    
    def _serialize_basic_lock(self, obj) -> Dict[str, Any]:
        """Serialize basic Lock/RLock specific data."""
        return {
            "note": "Basic lock recreated as new instance"
        }
    
    def _deserialize_semaphore(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize semaphore objects."""
        semaphore_type = data.get("semaphore_type", "normal")
        initial_value = data.get("initial_value", 1)
        
        if "threading" in module:
            if semaphore_type == "bounded":
                return threading.BoundedSemaphore(initial_value)
            else:
                return threading.Semaphore(initial_value)
        
        elif "multiprocessing" in module:
            if semaphore_type == "bounded":
                return multiprocessing.BoundedSemaphore(initial_value)
            else:
                return multiprocessing.Semaphore(initial_value)
        
        else:
            # Default to threading
            if semaphore_type == "bounded":
                return threading.BoundedSemaphore(initial_value)
            else:
                return threading.Semaphore(initial_value)
    
    def _deserialize_condition(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize condition objects."""
        if "threading" in module:
            return threading.Condition()
        elif "multiprocessing" in module:
            return multiprocessing.Condition()
        else:
            return threading.Condition()
    
    def _deserialize_event(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize event objects."""
        is_set = data.get("is_set", False)
        
        if "threading" in module:
            event = threading.Event()
        elif "multiprocessing" in module:
            event = multiprocessing.Event()
        else:
            event = threading.Event()
        
        # Restore event state
        if is_set:
            event.set()
        
        return event
    
    def _deserialize_barrier(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize barrier objects."""
        parties = data.get("parties", 1)
        
        if "threading" in module:
            return threading.Barrier(parties)
        elif "multiprocessing" in module:
            return multiprocessing.Barrier(parties)
        else:
            return threading.Barrier(parties)
    
    def _deserialize_basic_lock(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize basic lock objects."""
        lock_type = data.get("lock_type", "")
        
        if "threading" in module:
            if "RLock" in lock_type or "_RLock" in lock_type:
                return threading.RLock()
            else:
                return threading.Lock()
        
        elif "multiprocessing" in module:
            if "RLock" in lock_type:
                return multiprocessing.RLock()
            else:
                return multiprocessing.Lock()
        
        else:
            # Default to threading
            if "RLock" in lock_type or "_RLock" in lock_type:
                return threading.RLock()
            else:
                return threading.Lock()


# Create a singleton instance
_locks_handler = LocksHandler()