"""
Cerial API - Serialization for the Unpicklable

This module provides user-friendly serialization for objects that 
standard pickle cannot handle: locks, loggers, file handles, 
thread-local data, and more.

Key Features:
- Serialize complex objects with locks, loggers, and other unpicklables
- Automatic circular reference handling
- Handlers for common unpicklable types
- Clear error messages for debugging
"""

from ._int.serializer import Cerializer, SerializationError
from ._int.deserializer import Decerializer, DeserializationError

# Convenient default instances
_default_serializer = Cerializer()
_default_deserializer = Decerializer()


def serialize(obj, debug: bool = False, verbose: bool = False) -> bytes:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        # Serialize any object to bytes
        data = cerial.serialize(my_complex_object)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize any Python object to bytes.
    
    Handles objects that standard pickle cannot serialize, including:
    - Objects with locks (threading.Lock, threading.RLock, etc.)
    - Objects with loggers (logging.Logger instances)
    - Objects with file handles
    - Objects with circular references
    - Custom classes with unpicklable attributes
    
    Args:
        obj: Object to serialize
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print serialization progress
        
    Returns:
        bytes: Serialized representation
        
    Raises:
        SerializationError: If serialization fails
    
    ────────────────────────────────────────────────────────
        ```python
        # Serialize an object with locks and loggers
        import threading
        import logging
        
        class ComplexService:
            def __init__(self):
                self.lock = threading.Lock()
                self.logger = logging.getLogger("service")
                self.data = {"users": [], "config": {}}
        
        service = ComplexService()
        
        # Cerial handles locks and loggers automatically
        serialized = cerial.serialize(service)
        ```
    ────────────────────────────────────────────────────────
    """
    if debug or verbose:
        serializer = Cerializer(debug=debug, verbose=verbose)
        return serializer.serialize(obj)
    return _default_serializer.serialize(obj)


def deserialize(data: bytes, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        # Deserialize bytes back to an object
        my_object = cerial.deserialize(data)
        ```
    ────────────────────────────────────────────────────────\n

    Deserialize bytes back to a Python object.
    
    Reconstructs objects serialized with cerial.serialize(), including:
    - Recreating locks (as new, unlocked locks)
    - Recreating loggers (reconnected to logging system)
    - Rebuilding circular references
    - Restoring custom class instances
    
    Args:
        data: Serialized bytes from cerial.serialize()
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print deserialization progress
        
    Returns:
        Reconstructed Python object
        
    Raises:
        DeserializationError: If deserialization fails
    
    ────────────────────────────────────────────────────────
        ```python
        # Round-trip example
        original = ComplexService()
        original.data["users"].append("alice")
        
        # Serialize
        serialized = cerial.serialize(original)
        
        # Deserialize
        restored = cerial.deserialize(serialized)
        
        # State is preserved
        assert restored.data["users"] == ["alice"]
        
        # Locks are recreated (new, unlocked)
        assert restored.lock.acquire(blocking=False)  # Can acquire
        restored.lock.release()
        ```
    ────────────────────────────────────────────────────────
    """
    if debug or verbose:
        deserializer = Decerializer(debug=debug, verbose=verbose)
        return deserializer.deserialize(data)
    return _default_deserializer.deserialize(data)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main functions
    'serialize',
    'deserialize',
    
    # Classes for advanced usage
    'Cerializer',
    'Decerializer',
    
    # Exceptions
    'SerializationError',
    'DeserializationError',
]
