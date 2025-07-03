"""
Cerial Core - Internal Cross-Process Serialization Engine for Suitkaise

This module provides the core serialization functionality that powers cross-process
communication in Suitkaise. Built on standard Python pickle with enhanced handlers
for non-serializable objects (NSOs) and SK-specific objects.

Key Features:
- Enhanced serialization for threading locks, lambdas, file handles, generators
- SK-specific object serialization (SKPath, Timer, Stopwatch, etc.)
- Graceful fallback to standard pickle for unsupported objects
- Selective enhancement - only use enhanced serialization when needed
- Error recovery and detailed logging for debugging

Design Philosophy:
- Start with standard pickle (fast, reliable for most objects)
- Enhance only objects that need it (threading locks, lambdas, SK objects)
- Graceful degradation - never fail completely if possible
- Transparent operation - users shouldn't need to think about serialization
"""

import pickle
import types
import threading
import inspect
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Union, Callable, Type, Tuple
from functools import wraps
from enum import Enum

from suitkaise._int.core.path_ops import _is_suitkaise_module, _get_module_file_path

class CerialError(Exception):
    """Base exception for Cerial serialization errors."""
    pass


class CerializationError(CerialError):
    """Raised when serialization fails."""
    pass


class DecerializationError(CerialError):
    """Raised when deserialization fails."""
    pass


class _SerializationStrategy(Enum):
    """Strategy for handling different object types."""
    STANDARD_PICKLE = "standard"      # Use regular pickle
    ENHANCED_CERIAL = "enhanced"      # Use our enhanced serialization
    SKIP_OBJECT = "skip"              # Skip this object (return placeholder)


class _NSO_Handler:
    """Base class for Non-Serializable Object handlers."""

    def __init__(self):
        """Initialize the NSO handler."""
        self._types_handled: Set[Type] = set()
    
    def can_handle(self, obj: Any) -> bool:
        """Check if this handler can serialize the given object."""
        raise NotImplementedError("Subclasses must implement can_handle()")
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """Serialize the object to a dictionary representation."""
        raise NotImplementedError("Subclasses must implement serialize()")
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Deserialize the object from dictionary representation."""
        raise NotImplementedError("Subclasses must implement deserialize()")
    
    
class _CerialRegistry:
    """Registry for NSO handlers and serialization strategies."""
    
    def __init__(self):
        """Initialize the registry with empty handlers."""
        self._handlers: List[_NSO_Handler] = []
        self._type_strategies: Dict[Type, _SerializationStrategy] = {}
        self._debug_mode: bool = False
    
    def register_handler(self, handler: _NSO_Handler) -> None:
        """Register an NSO handler."""
        if not isinstance(handler, _NSO_Handler):
            raise TypeError("Handler must be an instance of _NSO_Handler")
        
        # Add to beginning of list so more specific handlers are checked first
        self._handlers.insert(0, handler)
        
        if self._debug_mode:
            print(f"Registered NSO handler: {handler.__class__.__name__}")
    
    def get_handler(self, obj: Any) -> Optional[_NSO_Handler]:
        """Get the appropriate handler for an object."""
        for handler in self._handlers:
            try:
                if handler.can_handle(obj):
                    return handler
            except Exception as e:
                # Handler check failed, continue to next handler
                if self._debug_mode:
                    print(f"Handler {handler.__class__.__name__} check failed: {e}")
                continue
        return None
    
    def set_type_strategy(self, obj_type: Type, strategy: _SerializationStrategy) -> None:
        """Set serialization strategy for a specific type."""
        self._type_strategies[obj_type] = strategy
    
    def get_type_strategy(self, obj: Any) -> _SerializationStrategy:
        """Get serialization strategy for an object."""
        obj_type = type(obj)
        
        # Check exact type match first
        if obj_type in self._type_strategies:
            return self._type_strategies[obj_type]
        
        # Check if any registered handler can handle this object
        if self.get_handler(obj) is not None:
            return _SerializationStrategy.ENHANCED_CERIAL
        
        # Check for specific NSO types that need enhanced serialization
        if self._needs_enhanced_serialization(obj):
            return _SerializationStrategy.ENHANCED_CERIAL
        
        # Default to standard pickle
        return _SerializationStrategy.STANDARD_PICKLE
    
    def _needs_enhanced_serialization(self, obj: Any) -> bool:
        """Check if object needs enhanced serialization based on type."""

        needs_enhanced = (
            types.LambdaType,
            (threading.Lock, threading.RLock, threading.Semaphore),
            types.GeneratorType
        )

        # SK-specific objects
        if hasattr(obj, '__module__') and _is_suitkaise_module(_get_module_file_path(obj)):
            return True
    
        for nt in needs_enhanced:
            if isinstance(obj, nt):
                return True

        # file handles
        if hasattr(obj, 'read') and hasattr(obj, 'write') and hasattr(obj, 'close'):
            return True
        
        return False
    
    def enable_debug_mode(self) -> None:
        """Enable debug mode for detailed logging."""
        self._debug_mode = True
        print("Cerial debug mode enabled.")

    def disable_debug_mode(self) -> None:
        """Disable debug mode."""
        self._debug_mode = False
        print("Cerial debug mode disabled.")

    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug_mode
    
# Global registry instance
_registry = _CerialRegistry()

def register_nso_handler(handler: _NSO_Handler) -> None:
    """
    Register a new NSO handler globally.
    
    Args:
        handler: NSO handler instance
    """
    _registry.register_handler(handler)


def enable_debug_mode() -> None:
    """Enable debug mode for detailed serialization logging."""
    _registry.enable_debug_mode()


def disable_debug_mode() -> None:
    """Disable debug mode."""
    _registry.disable_debug_mode()


def serialize(obj: Any, fallback_to_pickle: bool = True) -> bytes:
    """
    Serialize an object using appropriate strategy.
    
    Args:
        obj: Object to serialize
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        Serialized bytes
        
    Raises:
        SerializationError: If serialization fails and fallback is disabled
    """
    strategy = _registry.get_type_strategy(obj)
    
    if strategy == _SerializationStrategy.STANDARD_PICKLE:
        # Use standard pickle for most objects
        try:
            return pickle.dumps(obj)
        except Exception as e:
            if fallback_to_pickle:
                # Already using pickle, can't fall back further
                raise CerializationError(f"Standard pickle failed: {e}")
            else:
                raise CerializationError(f"Serialization failed: {e}")
    
    elif strategy == _SerializationStrategy.ENHANCED_CERIAL:
        # Use enhanced serialization
        try:
            return _serialize_enhanced(obj)
        except Exception as e:
            if fallback_to_pickle:
                # Fall back to standard pickle
                try:
                    return pickle.dumps(obj)
                except Exception as pickle_error:
                    raise CerializationError(
                        f"Enhanced serialization failed: {e}, "
                        f"Pickle fallback also failed: {pickle_error}"
                    )
            else:
                raise CerializationError(f"Enhanced serialization failed: {e}")
    
    elif strategy == _SerializationStrategy.SKIP_OBJECT:
        # Return placeholder for skipped objects
        return pickle.dumps({"__cerial_placeholder__": True, "type": str(type(obj))})
    
    else:
        raise CerializationError(f"Unknown serialization strategy: {strategy}")


def deserialize(data: bytes, fallback_to_pickle: bool = True) -> Any:
    """
    Deserialize an object from bytes.
    
    Args:
        data: Serialized bytes
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        Deserialized object
        
    Raises:
        DeserializationError: If deserialization fails and fallback is disabled
    """
    try:
        # First, try to detect if this is enhanced cerial data
        if _is_enhanced_cerial_data(data):
            return _deserialize_enhanced(data)
        else:
            # Use standard pickle
            return pickle.loads(data)
    
    except Exception as e:
        if fallback_to_pickle:
            # Try standard pickle as fallback
            try:
                return pickle.loads(data)
            except Exception as pickle_error:
                raise DecerializationError(
                    f"Cerial deserialization failed: {e}, "
                    f"Pickle fallback also failed: {pickle_error}"
                )
        else:
            raise DecerializationError(f"Deserialization failed: {e}")


def _serialize_enhanced(obj: Any) -> bytes:
    """
    Enhanced serialization for NSOs and SK objects.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Serialized bytes with cerial header
    """
    # Get appropriate handler
    handler = _registry.get_handler(obj)
    
    if handler is None:
        raise CerializationError(f"No handler found for object type: {type(obj)}")
    
    # Serialize using handler
    serialized_data = handler.serialize(obj)
    
    # Add cerial metadata
    cerial_envelope = {
        "__cerial_data__": True,
        "__cerial_version__": "0.1.0",
        "__handler_class__": handler.__class__.__name__,
        "__original_type__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
        "__data__": serialized_data
    }
    
    # Use standard pickle for the envelope
    return pickle.dumps(cerial_envelope)


def _deserialize_enhanced(data: bytes) -> Any:
    """
    Enhanced deserialization for NSOs and SK objects.
    
    Args:
        data: Serialized bytes with cerial header
        
    Returns:
        Deserialized object
    """
    # Load the cerial envelope
    try:
        envelope = pickle.loads(data)
    except Exception as e:
        raise DecerializationError(f"Failed to load cerial envelope: {e}")
    
    # Validate envelope structure
    if not isinstance(envelope, dict) or not envelope.get("__cerial_data__"):
        raise DecerializationError("Invalid cerial envelope format")
    
    # Get handler class name and find matching handler
    handler_class_name = envelope.get("__handler_class__")
    if not handler_class_name:
        raise DecerializationError("Missing handler class name in envelope")
    
    # Find handler by class name
    handler = None
    for registered_handler in _registry._handlers:
        if registered_handler.__class__.__name__ == handler_class_name:
            handler = registered_handler
            break
    
    if handler is None:
        raise DecerializationError(f"Handler not found: {handler_class_name}")
    
    # Deserialize using handler
    serialized_data = envelope.get("__data__")
    if serialized_data is None:
        raise DecerializationError("Missing data in cerial envelope")
    
    return handler.deserialize(serialized_data)


def _is_enhanced_cerial_data(data: bytes) -> bool:
    """
    Check if data was serialized using enhanced cerial.
    
    Args:
        data: Serialized bytes
        
    Returns:
        True if data contains cerial envelope
    """
    try:
        # Try to load as pickle and check for cerial envelope
        obj = pickle.loads(data)
        return isinstance(obj, dict) and obj.get("__cerial_data__") is True
    except Exception:
        return False


def get_serialization_info(obj: Any) -> Dict[str, Any]:
    """
    Get information about how an object would be serialized.
    
    Args:
        obj: Object to analyze
        
    Returns:
        Dictionary with serialization information
    """
    strategy = _registry.get_type_strategy(obj)
    handler = _registry.get_handler(obj)
    
    return {
        "object_type": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
        "strategy": strategy.value,
        "handler": handler.__class__.__name__ if handler else None,
        "needs_enhanced": strategy == _SerializationStrategy.ENHANCED_CERIAL,
        "can_fallback_to_pickle": True  # We always try pickle as fallback
    }


def test_serialization(obj: Any) -> Dict[str, Any]:
    """
    Test serialization of an object without actually serializing it.
    
    Args:
        obj: Object to test
        
    Returns:
        Dictionary with test results
    """
    results = {
        "object_type": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
        "standard_pickle_works": False,
        "enhanced_cerial_works": False,
        "handler_available": False,
        "strategy": None,
        "errors": []
    }
    
    # Test standard pickle
    try:
        pickle.dumps(obj)
        results["standard_pickle_works"] = True
    except Exception as e:
        results["errors"].append(f"Standard pickle failed: {e}")
    
    # Test enhanced cerial
    handler = _registry.get_handler(obj)
    if handler:
        results["handler_available"] = True
        try:
            serialized = handler.serialize(obj)
            handler.deserialize(serialized)
            results["enhanced_cerial_works"] = True
        except Exception as e:
            results["errors"].append(f"Enhanced cerial failed: {e}")
    
    # Get strategy
    strategy = _registry.get_type_strategy(obj)
    results["strategy"] = strategy.value
    
    return results


# Initialize with some basic type strategies
def _initialize_default_strategies():
    """Initialize default serialization strategies for common types."""
    # These types should always use standard pickle
    standard_types = [
        int, float, str, bool, bytes, type(None),
        list, tuple, dict, set, frozenset
    ]
    
    for obj_type in standard_types:
        _registry.set_type_strategy(obj_type, _SerializationStrategy.STANDARD_PICKLE)


# Initialize on module load
_initialize_default_strategies()

