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
from ._int.ir_json import ir_to_json as _ir_to_json
from ._int.ir_json import ir_to_jsonable as _ir_to_jsonable

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


def serialize_ir(obj, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        ir = cerial.serialize_ir(my_complex_object)
        ```
    ────────────────────────────────────────────────────────\n

    Build and return the intermediate representation (IR) without pickling.
    
    Args:
        obj: Object to convert to IR
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print serialization progress
        
    Returns:
        IR: Nested dict/list structure of pickle-native types
    """
    if debug or verbose:
        serializer = Cerializer(debug=debug, verbose=verbose)
        return serializer.serialize_ir(obj)
    return _default_serializer.serialize_ir(obj)


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


def ir_to_jsonable(ir):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        ir = cerial.serialize_ir(obj)
        jsonable = cerial.ir_to_jsonable(ir)
        ```
    ────────────────────────────────────────────────────────\n

    Convert a cerial IR into a JSON-serializable structure.
    """
    return _ir_to_jsonable(ir)


def ir_to_json(ir, *, indent: int | None = 2, sort_keys: bool = True) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        ir = cerial.serialize_ir(obj)
        json_text = cerial.ir_to_json(ir)
        ```
    ────────────────────────────────────────────────────────\n

    Convert a cerial IR into JSON text.
    """
    return _ir_to_json(ir, indent=indent, sort_keys=sort_keys)


def to_jsonable(obj, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        jsonable = cerial.to_jsonable(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize an object to IR and return a JSON-serializable structure.
    """
    ir = serialize_ir(obj, debug=debug, verbose=verbose)
    return _ir_to_jsonable(ir)


def to_json(
    obj,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
    debug: bool = False,
    verbose: bool = False,
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        json_text = cerial.to_json(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize an object to IR and return JSON text.
    """
    ir = serialize_ir(obj, debug=debug, verbose=verbose)
    return _ir_to_json(ir, indent=indent, sort_keys=sort_keys)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main functions
    'serialize',
    'serialize_ir',
    'deserialize',
    'ir_to_jsonable',
    'ir_to_json',
    'to_jsonable',
    'to_json',
    
    # Classes for advanced usage
    'Cerializer',
    'Decerializer',
    
    # Exceptions
    'SerializationError',
    'DeserializationError',
]
