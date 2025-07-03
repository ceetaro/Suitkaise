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
    
    def can_handle(self, obj: Any) -> bool:
        """Check if this handler can serialize the given lock object."""
        # Threading module locks
        if isinstance(obj, (
            threading.Lock, threading.RLock, threading.Semaphore, 
            threading.BoundedSemaphore, threading.Condition, 
            threading.Event, threading.Barrier
        )):
            return True
        
        # Multiprocessing locks (when available)
        try:
            if isinstance(obj, (
                multiprocessing.Lock, multiprocessing.RLock, 
                multiprocessing.Semaphore, multiprocessing.BoundedSemaphore,
                multiprocessing.Condition, multiprocessing.Event, 
                multiprocessing.Barrier
            )):
                return True
        except AttributeError:
            # Some multiprocessing types might not be available
            pass
        
        # Check by type name for edge cases
        obj_type_name = obj.__class__.__name__
        if obj_type_name in ['_RLock', '_Lock', '_Semaphore', '_BoundedSemaphore', 
                           '_Condition', '_Event', '_Barrier']:
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
        if isinstance(obj, (threading.Semaphore, threading.BoundedSemaphore)):
            data.update(self._serialize_semaphore(obj))
        
        elif isinstance(obj, (threading.Condition,)):
            data.update(self._serialize_condition(obj))
        
        elif isinstance(obj, (threading.Event,)):
            data.update(self._serialize_event(obj))
        
        elif isinstance(obj, (threading.Barrier,)):
            data.update(self._serialize_barrier(obj))
        
        elif isinstance(obj, (threading.Lock, threading.RLock)):
            data.update(self._serialize_basic_lock(obj))
        
        # Handle multiprocessing locks
        try:
            if isinstance(obj, (multiprocessing.Semaphore, multiprocessing.BoundedSemaphore)):
                data.update(self._serialize_mp_semaphore(obj))
            
            elif isinstance(obj, (multiprocessing.Condition,)):
                data.update(self._serialize_mp_condition(obj))
            
            elif isinstance(obj, (multiprocessing.Event,)):
                data.update(self._serialize_mp_event(obj))
            
            elif isinstance(obj, (multiprocessing.Barrier,)):
                data.update(self._serialize_mp_barrier(obj))
            
            elif isinstance(obj, (multiprocessing.Lock, multiprocessing.RLock)):
                data.update(self._serialize_mp_basic_lock(obj))
                
        except AttributeError:
            # Some multiprocessing types might not be available
            pass
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Deserialize a lock object from dictionary representation."""
        lock_type = data.get("lock_type")
        module = data.get("module", "threading")
        
        # Route to appropriate deserialization method
        if lock_type in ["Semaphore", "BoundedSemaphore"]:
            return self._deserialize_semaphore(data, module)
        
        elif lock_type == "Condition":
            return self._deserialize_condition(data, module)
        
        elif lock_type == "Event":
            return self._deserialize_event(data, module)
        
        elif lock_type == "Barrier":
            return self._deserialize_barrier(data, module)
        
        elif lock_type in ["Lock", "RLock", "_Lock", "_RLock"]:
            return self._deserialize_basic_lock(data, module)
        
        else:
            raise ValueError(f"Unknown lock type: {lock_type}")
    
    def _serialize_semaphore(self, obj: threading.Semaphore) -> Dict[str, Any]:
        """Serialize threading.Semaphore specific data."""
        # Unfortunately, we can't easily get the current value or initial value
        # from a Semaphore object. We'll recreate with default value.
        return {
            "semaphore_type": "bounded" if isinstance(obj, threading.BoundedSemaphore) else "normal",
            "initial_value": 1,  # Default value - we can't detect the actual value
            "note": "Semaphore recreated with default value - actual value unknown"
        }
    
    def _serialize_condition(self, obj: threading.Condition) -> Dict[str, Any]:
        """Serialize threading.Condition specific data."""
        return {
            "has_underlying_lock": obj._lock is not None,
            "note": "Condition recreated with new underlying lock"
        }
    
    def _serialize_event(self, obj: threading.Event) -> Dict[str, Any]:
        """Serialize threading.Event specific data."""
        return {
            "is_set": obj.is_set(),
            "note": "Event state preserved"
        }
    
    def _serialize_barrier(self, obj: threading.Barrier) -> Dict[str, Any]:
        """Serialize threading.Barrier specific data."""
        return {
            "parties": obj.parties,
            "action": None,  # We can't serialize the action function
            "timeout": None,  # We can't get the timeout value
            "note": "Barrier recreated with same party count but no action"
        }
    
    def _serialize_basic_lock(self, obj: threading.Lock) -> Dict[str, Any]:
        """Serialize basic Lock/RLock specific data."""
        return {
            "note": "Basic lock recreated as new instance"
        }
    
    def _serialize_mp_semaphore(self, obj) -> Dict[str, Any]:
        """Serialize multiprocessing.Semaphore specific data."""
        return {
            "semaphore_type": "bounded" if "Bounded" in obj.__class__.__name__ else "normal",
            "initial_value": 1,  # Default value
            "note": "MP Semaphore recreated with default value"
        }
    
    def _serialize_mp_condition(self, obj) -> Dict[str, Any]:
        """Serialize multiprocessing.Condition specific data."""
        return {
            "note": "MP Condition recreated with new underlying lock"
        }
    
    def _serialize_mp_event(self, obj) -> Dict[str, Any]:
        """Serialize multiprocessing.Event specific data."""
        return {
            "is_set": obj.is_set(),
            "note": "MP Event state preserved"
        }
    
    def _serialize_mp_barrier(self, obj) -> Dict[str, Any]:
        """Serialize multiprocessing.Barrier specific data."""
        return {
            "parties": obj.parties,
            "note": "MP Barrier recreated with same party count"
        }
    
    def _serialize_mp_basic_lock(self, obj) -> Dict[str, Any]:
        """Serialize basic multiprocessing Lock/RLock specific data."""
        return {
            "note": "MP basic lock recreated as new instance"
        }
    
    def _deserialize_semaphore(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize semaphore objects."""
        semaphore_type = data.get("semaphore_type", "normal")
        initial_value = data.get("initial_value", 1)
        
        if module == "threading":
            if semaphore_type == "bounded":
                return threading.BoundedSemaphore(initial_value)
            else:
                return threading.Semaphore(initial_value)
        
        elif module == "multiprocessing":
            if semaphore_type == "bounded":
                return multiprocessing.BoundedSemaphore(initial_value)
            else:
                return multiprocessing.Semaphore(initial_value)
        
        else:
            raise ValueError(f"Unknown module for semaphore: {module}")
    
    def _deserialize_condition(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize condition objects."""
        if module == "threading":
            return threading.Condition()
        elif module == "multiprocessing":
            return multiprocessing.Condition()
        else:
            raise ValueError(f"Unknown module for condition: {module}")
    
    def _deserialize_event(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize event objects."""
        is_set = data.get("is_set", False)
        
        if module == "threading":
            event = threading.Event()
        elif module == "multiprocessing":
            event = multiprocessing.Event()
        else:
            raise ValueError(f"Unknown module for event: {module}")
        
        # Restore event state
        if is_set:
            event.set()
        
        return event
    
    def _deserialize_barrier(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize barrier objects."""
        parties = data.get("parties", 1)
        
        if module == "threading":
            return threading.Barrier(parties)
        elif module == "multiprocessing":
            return multiprocessing.Barrier(parties)
        else:
            raise ValueError(f"Unknown module for barrier: {module}")
    
    def _deserialize_basic_lock(self, data: Dict[str, Any], module: str) -> Any:
        """Deserialize basic lock objects."""
        lock_type = data.get("lock_type")
        
        if module == "threading":
            if lock_type in ["RLock", "_RLock"]:
                return threading.RLock()
            else:
                return threading.Lock()
        
        elif module == "multiprocessing":
            if lock_type in ["RLock", "_RLock"]:
                return multiprocessing.RLock()
            else:
                return multiprocessing.Lock()
        
        else:
            raise ValueError(f"Unknown module for basic lock: {module}")


# Create a singleton instance
_locks_handler = LocksHandler()