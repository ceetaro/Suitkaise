"""
Cerial Core - Internal Cross-Process Serialization Engine for Suitkaise

This module provides the core serialization functionality that powers cross-process
communication in Suitkaise. Built on standard Python pickle with enhanced handlers
for non-serializable objects (NSOs) and SK-specific objects.

ARCHITECTURE OVERVIEW:
======================

1. STRATEGY SYSTEM: Decides how to serialize each object
   - Standard Pickle: Fast, reliable for most objects
   - Enhanced Cerial: For complex objects that pickle can't handle
   - Skip Object: Returns placeholder for unsupported objects

2. HANDLER REGISTRY: Manages specialized serialization handlers
   - Auto-discovery of available handlers
   - Priority-based handler selection
   - Registration/unregistration of custom handlers

3. NSO HANDLERS: Specialized handlers for Non-Serializable Objects
   - Threading locks, semaphores, events
   - Lambda functions and complex functions
   - File handles and I/O streams
   - Suitkaise-specific objects (SKPath, Timer, etc.)

4. CONTAINER PROCESSING: Handles complex nested structures
   - Recursively processes containers (dict, list, tuple, set)
   - Preserves structure while handling embedded NSOs
   - Creates cerial envelopes for enhanced serialization

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
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Union, Callable, Type, Tuple, Iterator
from functools import wraps
from enum import Enum

from suitkaise._int.core.path_ops import _is_suitkaise_module, _get_module_file_path

# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class CerialError(Exception):
    """
    Base exception for Cerial serialization errors.
    
    All cerial-specific exceptions inherit from this base class,
    making it easy to catch any cerial-related error.
    """
    pass


class CerializationError(CerialError):
    """
    Raised when serialization fails.
    
    This includes failures in both standard pickle and enhanced
    cerial serialization methods.
    """
    pass


class DecerializationError(CerialError):
    """
    Raised when deserialization fails.
    
    This includes failures in both standard pickle and enhanced
    cerial deserialization methods.
    """
    pass


# ============================================================================
# STRATEGY ENUMERATION
# ============================================================================

class _SerializationStrategy(Enum):
    """
    Strategy enumeration for handling different object types.
    
    This enum defines the three possible approaches for serializing objects:
    - STANDARD_PICKLE: Use regular Python pickle (fastest, most reliable)
    - ENHANCED_CERIAL: Use our custom enhanced serialization with handlers
    - SKIP_OBJECT: Skip this object and return a placeholder
    
    The strategy is determined by analyzing each object and checking:
    1. Whether any registered handler can process it
    2. Whether it's a known NSO type that needs enhancement
    3. Whether it has explicit strategy override
    4. Default fallback to standard pickle
    """
    STANDARD_PICKLE = "standard"      # Use regular pickle
    ENHANCED_CERIAL = "enhanced"      # Use our enhanced serialization
    SKIP_OBJECT = "skip"              # Skip this object (return placeholder)


# ============================================================================
# NSO HANDLER BASE CLASS
# ============================================================================

class _NSO_Handler:
    """
    Base class for Non-Serializable Object handlers.
    
    Each handler is responsible for serializing/deserializing specific
    types of objects that standard pickle cannot handle. This includes:
    - Threading primitives (locks, semaphores, events)
    - Lambda functions and complex function objects
    - File handles and I/O streams
    - Suitkaise-specific objects
    
    HANDLER LIFECYCLE:
    1. can_handle(obj): Check if this handler can process the object
    2. serialize(obj): Convert object to dictionary representation
    3. deserialize(data): Recreate object from dictionary representation
    
    PRIORITY SYSTEM:
    - Lower priority numbers = higher actual priority
    - Default priority is 50
    - Handlers are tried in priority order
    """

    def __init__(self):
        """
        Initialize the NSO handler.
        
        Sets up handler metadata including name, priority, and
        the set of types this handler can process.
        """
        self._types_handled: Set[Type] = set()
        self._handler_name: str = self.__class__.__name__
        self._priority: int = 50  # Default priority, lower = higher priority
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given object.
        
        Args:
            obj: The object to check
            
        Returns:
            True if this handler can process the object
            
        This method should be implemented by each handler to define
        which objects it can process. It should be fast since it's
        called for every object during strategy determination.
        """
        raise NotImplementedError("Subclasses must implement can_handle()")
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize the object to a dictionary representation.
        
        Args:
            obj: The object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the object
            
        The returned dictionary should contain only pickle-serializable
        data types (strings, numbers, lists, dicts, etc.). Complex
        objects should be broken down into their essential components.
        """
        raise NotImplementedError("Subclasses must implement serialize()")
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize the object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized object data
            
        Returns:
            Recreated object instance
            
        This method recreates the object using the data saved during
        serialization. It should handle missing or invalid data gracefully.
        """
        raise NotImplementedError("Subclasses must implement deserialize()")
    
    def get_priority(self) -> int:
        """Get handler priority (lower = higher priority)."""
        return self._priority
    
    def set_priority(self, priority: int) -> None:
        """Set handler priority."""
        self._priority = priority
    
    def get_handler_info(self) -> Dict[str, Any]:
        """
        Get information about this handler.
        
        Returns:
            Dictionary with handler metadata including name, priority,
            types handled, and module information.
        """
        return {
            "name": self._handler_name,
            "priority": self._priority,
            "types_handled": [str(t) for t in self._types_handled],
            "module": self.__module__
        }


# ============================================================================
# CERIAL REGISTRY - THE HEART OF THE SYSTEM
# ============================================================================

class _CerialRegistry:
    """
    Registry for NSO handlers and serialization strategies.
    
    This is the central coordination point for the entire cerial system.
    It manages:
    - Handler registration and discovery
    - Strategy determination for objects
    - Performance statistics tracking
    - Debug mode and configuration
    
    HANDLER MANAGEMENT:
    - Handlers are stored in priority order (lower number = higher priority)
    - Auto-discovery can find and register handlers automatically
    - Handlers can be registered/unregistered at runtime
    
    STRATEGY DETERMINATION:
    1. Check if any registered handler can handle the object
    2. Check if object needs enhanced serialization (NSO detection)
    3. Check for explicit type strategy overrides
    4. Default to standard pickle
    
    PERFORMANCE TRACKING:
    - Counts serializations, deserializations, enhanced operations
    - Tracks timing information
    - Monitors error rates and fallback usage
    """
    
    def __init__(self):
        """Initialize the registry with empty handlers and default settings."""
        self._handlers: List[_NSO_Handler] = []
        self._type_strategies: Dict[Type, _SerializationStrategy] = {}
        self._debug_mode: bool = False
        self._auto_discovery_enabled: bool = True
        self._performance_stats: Dict[str, Any] = {
            "serializations": 0,
            "deserializations": 0,
            "enhanced_serializations": 0,
            "fallback_to_pickle": 0,
            "errors": 0,
            "total_time": 0.0
        }
    
    def register_handler(self, handler: _NSO_Handler) -> None:
        """
        Register an NSO handler.
        
        Args:
            handler: Handler instance to register
            
        The handler is inserted in the correct position based on priority.
        If a handler with the same name already exists, it's replaced.
        """
        if not isinstance(handler, _NSO_Handler):
            raise TypeError("Handler must be an instance of _NSO_Handler")
        
        # Remove any existing handler with the same name
        self._handlers = [h for h in self._handlers if h._handler_name != handler._handler_name]
        
        # Insert based on priority (lower priority number = higher actual priority)
        inserted = False
        for i, existing_handler in enumerate(self._handlers):
            if handler.get_priority() < existing_handler.get_priority():
                self._handlers.insert(i, handler)
                inserted = True
                break
        
        if not inserted:
            self._handlers.append(handler)
        
        if self._debug_mode:
            print(f"Registered NSO handler: {handler._handler_name} (priority: {handler.get_priority()})")
    
    def unregister_handler(self, handler_name: str) -> bool:
        """
        Unregister a handler by name.
        
        Args:
            handler_name: Name of handler to remove
            
        Returns:
            True if handler was found and removed
        """
        original_count = len(self._handlers)
        self._handlers = [h for h in self._handlers if h._handler_name != handler_name]
        removed = len(self._handlers) < original_count
        
        if removed and self._debug_mode:
            print(f"Unregistered NSO handler: {handler_name}")
        
        return removed
    
    def get_handler(self, obj: Any) -> Optional[_NSO_Handler]:
        """
        Get the appropriate handler for an object.
        
        Args:
            obj: Object to find handler for
            
        Returns:
            Handler that can process the object, or None if no handler available
            
        Handlers are tried in priority order until one claims it can
        handle the object.
        """
        for handler in self._handlers:
            try:
                if handler.can_handle(obj):
                    return handler
            except Exception as e:
                # Handler check failed, continue to next handler
                if self._debug_mode:
                    print(f"Handler {handler._handler_name} check failed: {e}")
                continue
        return None
    
    def get_all_handlers(self) -> List[_NSO_Handler]:
        """Get all registered handlers (copy to prevent modification)."""
        return self._handlers.copy()
    
    def get_handler_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered handlers."""
        return [handler.get_handler_info() for handler in self._handlers]
    
    def set_type_strategy(self, obj_type: Type, strategy: _SerializationStrategy) -> None:
        """
        Set serialization strategy for a specific type.
        
        Args:
            obj_type: Type to set strategy for
            strategy: Strategy to use for this type
            
        This allows manual override of the automatic strategy determination.
        """
        self._type_strategies[obj_type] = strategy
    
    def get_type_strategy(self, obj: Any) -> _SerializationStrategy:
        """
        Get serialization strategy for an object.
        
        Args:
            obj: Object to determine strategy for
            
        Returns:
            Strategy enum indicating how to serialize this object
            
        STRATEGY DETERMINATION ORDER:
        1. Check if any registered handler can handle this object
        2. Check if object needs enhanced serialization (NSO detection)
        3. Check for explicit type strategy override
        4. Default to standard pickle
        """
        obj_type = type(obj)
        
        # FIRST: Check if any registered handler can handle this object
        # This takes priority over default type strategies
        if self.get_handler(obj) is not None:
            return _SerializationStrategy.ENHANCED_CERIAL
        
        # SECOND: Check for specific NSO types that need enhanced serialization
        if self._needs_enhanced_serialization(obj):
            return _SerializationStrategy.ENHANCED_CERIAL
        
        # THIRD: Check exact type match for explicitly set strategies
        if obj_type in self._type_strategies:
            return self._type_strategies[obj_type]
        
        # DEFAULT: Fall back to standard pickle
        return _SerializationStrategy.STANDARD_PICKLE
    
    def _needs_enhanced_serialization(self, obj: Any) -> bool:
        """
        Check if object needs enhanced serialization based on type.
        
        Args:
            obj: Object to check
            
        Returns:
            True if object is a known NSO type that needs enhancement
            
        This method detects common NSO types that standard pickle
        cannot handle, including:
        - Function types (lambda, function, generator)
        - Threading objects (locks, semaphores, events)
        - Suitkaise-specific objects
        - File handles and I/O objects
        """
        try:
            # Get the type name for comparison
            obj_type_name = type(obj).__name__
            obj_module_name = getattr(type(obj), '__module__', '')
            
            # Function and lambda types - check each type individually to avoid isinstance errors
            try:
                if hasattr(types, 'LambdaType') and isinstance(obj, types.LambdaType):
                    return True
            except (TypeError, AttributeError):
                pass
                
            try:
                if hasattr(types, 'FunctionType') and isinstance(obj, types.FunctionType):
                    return True
            except (TypeError, AttributeError):
                pass
                
            try:
                if hasattr(types, 'GeneratorType') and isinstance(obj, types.GeneratorType):
                    return True
            except (TypeError, AttributeError):
                pass
            
            # Threading objects - check by type name since threading.Lock() etc. are factories
            threading_types = {
                'lock', '_RLock', 'Semaphore', 'BoundedSemaphore', 
                'Condition', 'Event', 'Barrier'
            }
            if obj_type_name in threading_types or 'threading' in obj_module_name:
                return True
            
            # Check for _thread module objects (low-level lock implementations)
            if '_thread' in obj_module_name:
                return True

            # SK-specific objects - check if from suitkaise module
            if hasattr(obj, '__module__'):
                try:
                    obj_module_file = _get_module_file_path(obj)
                    if obj_module_file and _is_suitkaise_module(obj_module_file):
                        return True
                except:
                    pass  # If we can't determine module, continue with other checks

            # File handles - check for common file-like object attributes
            if hasattr(obj, 'read') and hasattr(obj, 'write') and hasattr(obj, 'close'):
                return True
            
            return False
            
        except Exception:
            # If any error occurs in type checking, default to False
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
    
    def enable_auto_discovery(self) -> None:
        """Enable automatic handler discovery."""
        self._auto_discovery_enabled = True
        if self._debug_mode:
            print("Cerial auto-discovery enabled.")
    
    def disable_auto_discovery(self) -> None:
        """Disable automatic handler discovery."""
        self._auto_discovery_enabled = False
        if self._debug_mode:
            print("Cerial auto-discovery disabled.")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics (copy to prevent modification)."""
        return self._performance_stats.copy()
    
    def reset_performance_stats(self) -> None:
        """Reset performance statistics to zero."""
        self._performance_stats = {
            "serializations": 0,
            "deserializations": 0,
            "enhanced_serializations": 0,
            "fallback_to_pickle": 0,
            "errors": 0,
            "total_time": 0.0
        }
        if self._debug_mode:
            print("Cerial performance stats reset.")
    
    def _record_operation(self, operation: str, duration: float = 0.0) -> None:
        """
        Record performance statistics.
        
        Args:
            operation: Type of operation performed
            duration: Time taken for the operation
        """
        if operation in self._performance_stats:
            self._performance_stats[operation] += 1
        self._performance_stats["total_time"] += duration
    

    def discover_and_register_handlers(self) -> int:
        """
        Discover and register all available handlers.
        
        Returns:
            Number of handlers discovered and registered
            
        This method tries to import known handler modules and
        automatically register any handler instances found.
        """
        if not self._auto_discovery_enabled:
            return 0
        
        registered_count = 0
        
        handler_modules = [
            'suitkaise._int.serialization.nso.locks',
            'suitkaise._int.serialization.nso.sk_objects', 
            'suitkaise._int.serialization.nso.functions',
            'suitkaise._int.serialization.nso.file_handles',
            'suitkaise._int.serialization.nso.generators',
            'suitkaise._int.serialization.nso.weakrefs',
            'suitkaise._int.serialization.nso.re_patterns', 
            'suitkaise._int.serialization.nso.sqlite_conns',
            'suitkaise._int.serialization.nso.loggers',
            'suitkaise._int.serialization.nso.context_mgrs',
            'suitkaise._int.serialization.nso.dynamic_modules',
            'suitkaise._int.serialization.nso.queues'
        ]
        
        for module_name in handler_modules:
            try:
                import importlib
                module = importlib.import_module(module_name)
                
                # Look for handler instances in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, _NSO_Handler):
                        # Check if this handler is already registered
                        already_registered = any(
                            h._handler_name == attr._handler_name 
                            for h in self._handlers
                        )
                        if not already_registered:
                            self.register_handler(attr)
                            registered_count += 1
                            
            except ImportError:
                if self._debug_mode:
                    print(f"Could not import handler module: {module_name}")
            except Exception as e:
                if self._debug_mode:
                    print(f"Error loading handlers from {module_name}: {e}")
        
        if self._debug_mode and registered_count > 0:
            print(f"Auto-discovered and registered {registered_count} handlers")
        
        return registered_count

# Global registry instance
_registry = _CerialRegistry()


# ============================================================================
# CONTAINER PROCESSING FUNCTIONS
# ============================================================================

def _contains_nso_objects(obj: Any, max_depth: int = 3, _current_depth: int = 0) -> bool:
    """
    Check if an object contains any NSOs in its nested structure.
    
    Args:
        obj: Object to check
        max_depth: Maximum depth to search (prevents infinite recursion)
        _current_depth: Current recursion depth (internal use)
        
    Returns:
        True if any nested object needs enhanced serialization
        
    This function recursively searches through container objects
    (dict, list, tuple, set) to find any embedded NSOs that would
    require enhanced serialization.
    """
    if _current_depth >= max_depth:
        return False
    
    try:
        # Check if this object itself needs enhanced serialization
        if _registry._needs_enhanced_serialization(obj):
            return True
        
        # Check if any handler can handle this object
        if _registry.get_handler(obj) is not None:
            return True
        
        # Recursively check common container types
        if isinstance(obj, dict):
            for key, value in obj.items():
                if _contains_nso_objects(key, max_depth, _current_depth + 1):
                    return True
                if _contains_nso_objects(value, max_depth, _current_depth + 1):
                    return True
        
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                if _contains_nso_objects(item, max_depth, _current_depth + 1):
                    return True
        
        elif isinstance(obj, set):
            for item in obj:
                if _contains_nso_objects(item, max_depth, _current_depth + 1):
                    return True
        
        return False
        
    except Exception:
        # If any error occurs during checking, assume no NSOs to be safe
        return False


def _serialize_container_recursive(obj: Any) -> Any:
    """
    Recursively serialize a container, handling NSOs individually.
    
    Args:
        obj: Object to serialize recursively
        
    Returns:
        Serialized representation that can be safely pickled
        
    This function walks through nested container structures and
    creates cerial wrappers for any NSOs it finds, while leaving
    pickle-compatible objects unchanged.
    """
    try:
        # If this object needs enhanced serialization, handle it specially
        if _registry._needs_enhanced_serialization(obj) or _registry.get_handler(obj):
            # Create a cerial wrapper for this individual NSO
            handler = _registry.get_handler(obj)
            if handler:
                return {
                    "__cerial_nso__": True,
                    "__handler_class__": handler._handler_name,
                    "__original_type__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                    "__data__": handler.serialize(obj)
                }
            else:
                # Fallback: just store type info
                return {
                    "__cerial_nso__": True,
                    "__original_type__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                    "__fallback__": f"Could not serialize {type(obj).__name__}"
                }
        
        # Handle container types recursively
        elif isinstance(obj, dict):
            return {key: _serialize_container_recursive(value) for key, value in obj.items()}
        
        elif isinstance(obj, list):
            return [_serialize_container_recursive(item) for item in obj]
        
        elif isinstance(obj, tuple):
            return tuple(_serialize_container_recursive(item) for item in obj)
        
        elif isinstance(obj, set):
            return {_serialize_container_recursive(item) for item in obj}
        
        else:
            # For simple objects that pickle can handle, return as-is
            return obj
            
    except Exception:
        # If anything fails, return a placeholder
        return {
            "__cerial_nso__": True,
            "__original_type__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            "__error__": f"Serialization failed for {type(obj).__name__}"
        }


def _deserialize_container_recursive(obj: Any) -> Any:
    """
    Recursively deserialize a container, handling NSOs individually.
    
    Args:
        obj: Serialized object to deserialize recursively
        
    Returns:
        Deserialized object with NSOs restored
        
    This function walks through the serialized container structure
    and recreates NSOs using their appropriate handlers, while
    leaving simple objects unchanged.
    """
    try:
        if _registry.is_debug_mode():
            print(f"_deserialize_container_recursive called with: {type(obj)}")
            if isinstance(obj, dict) and len(obj) < 5:  # Only show small dicts
                print(f"  Object keys: {list(obj.keys()) if isinstance(obj, dict) else 'Not a dict'}")
        
        # Check if this is a cerial NSO wrapper
        if isinstance(obj, dict) and obj.get("__cerial_nso__"):
            handler_class_name = obj.get("__handler_class__")
            
            if _registry.is_debug_mode():
                print(f"  Found NSO wrapper, handler: {handler_class_name}")
            
            # If we have a fallback or error, return a placeholder
            if "__fallback__" in obj or "__error__" in obj:
                return f"<Unserialized {obj.get('__original_type__', 'Unknown')}>"
            
            # Find and use the appropriate handler
            if handler_class_name:
                for registered_handler in _registry._handlers:
                    if registered_handler._handler_name == handler_class_name:
                        data = obj.get("__data__")
                        if data is not None:
                            result = registered_handler.deserialize(data)
                            if _registry.is_debug_mode():
                                print(f"  Deserialized NSO to: {type(result)}")
                            return result
                        break
            
            # If we can't deserialize, return a placeholder
            return f"<Unhandled {obj.get('__original_type__', 'Unknown')}>"
        
        # Handle container types recursively
        elif isinstance(obj, dict):
            if _registry.is_debug_mode():
                print(f"  Processing dict with {len(obj)} keys")
            result = {key: _deserialize_container_recursive(value) for key, value in obj.items()}
            if _registry.is_debug_mode():
                print(f"  Dict result has keys: {list(result.keys())}")
            return result
        
        elif isinstance(obj, list):
            if _registry.is_debug_mode():
                print(f"  Processing list with {len(obj)} items")
            return [_deserialize_container_recursive(item) for item in obj]
        
        elif isinstance(obj, tuple):
            if _registry.is_debug_mode():
                print(f"  Processing tuple with {len(obj)} items")
            return tuple(_deserialize_container_recursive(item) for item in obj)
        
        elif isinstance(obj, set):
            if _registry.is_debug_mode():
                print(f"  Processing set with {len(obj)} items")
            return {_deserialize_container_recursive(item) for item in obj}
        
        else:
            # For simple objects, return as-is
            if _registry.is_debug_mode():
                print(f"  Returning simple object: {type(obj)}")
            return obj
            
    except Exception as e:
        if _registry.is_debug_mode():
            print(f"  Error in _deserialize_container_recursive: {e}")
        # If anything fails, return the original object or a placeholder
        if isinstance(obj, dict) and obj.get("__original_type__"):
            return f"<Failed {obj.get('__original_type__', 'Unknown')}>"
        return obj


def _serialize_enhanced_container(obj: Any) -> bytes:
    """
    Enhanced serialization for containers that hold NSO objects.
    
    Args:
        obj: Container object to serialize
        
    Returns:
        Serialized bytes with cerial header
        
    This function handles containers (dict, list, etc.) that contain
    NSOs mixed with regular objects. It creates a special container
    envelope and recursively processes the contents.
    """
    # Recursively serialize the container, handling NSOs individually
    serialized_container = _serialize_container_recursive(obj)
    
    # Create a special container envelope
    cerial_envelope = {
        "__cerial_data__": True,
        "__cerial_version__": "0.1.0",
        "__handler_class__": "ContainerHandler", 
        "__original_type__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
        "__data__": serialized_container
    }
    
    # Use standard pickle for the envelope
    return pickle.dumps(cerial_envelope)


# ============================================================================
# ENHANCED SERIALIZATION FUNCTIONS
# ============================================================================

def _is_enhanced_cerial_data(data: bytes) -> bool:
    """
    Check if data was serialized using enhanced cerial.
    
    Args:
        data: Serialized bytes
        
    Returns:
        True if data contains cerial envelope
        
    This function quickly checks if the given bytes represent
    enhanced cerial data by trying to load the envelope and
    checking for the cerial marker.
    """
    try:
        # Try to load as pickle and check for cerial envelope
        obj = pickle.loads(data)
        return isinstance(obj, dict) and obj.get("__cerial_data__") is True
    except Exception:
        return False


def _serialize_enhanced(obj: Any) -> bytes:
    """
    Enhanced serialization for NSOs and SK objects.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Serialized bytes with cerial header
        
    This function handles individual NSOs by finding the appropriate
    handler and creating a cerial envelope with the serialized data.
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
        "__handler_class__": handler._handler_name,
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
        
    This function handles cerial envelopes by extracting the handler
    information and data, then using the appropriate handler to
    recreate the object.
    
    CRITICAL FIX: This function now properly handles ContainerHandler
    by calling _deserialize_container_recursive instead of trying to
    find a handler named "ContainerHandler".
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
    
    # Special case: ContainerHandler for enhanced containers
    if handler_class_name == "ContainerHandler":
        serialized_data = envelope.get("__data__")
        if serialized_data is None:
            raise DecerializationError("Missing data in container envelope")
        # THIS IS THE KEY FIX: Properly deserialize container data
        return _deserialize_container_recursive(serialized_data)
    
    # Find handler by class name for individual NSOs
    handler = None
    for registered_handler in _registry._handlers:
        if registered_handler._handler_name == handler_class_name:
            handler = registered_handler
            break
    
    if handler is None:
        raise DecerializationError(f"Handler not found: {handler_class_name}")
    
    # Deserialize using handler
    serialized_data = envelope.get("__data__")
    if serialized_data is None:
        raise DecerializationError("Missing data in cerial envelope")
    
    return handler.deserialize(serialized_data)


# ============================================================================
# CORE SERIALIZATION FUNCTIONS
# ============================================================================

def serialize(obj: Any, fallback_to_pickle: bool = True) -> bytes:
    """
    Serialize an object using appropriate strategy.
    
    Args:
        obj: Object to serialize
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        Serialized bytes
        
    Raises:
        CerializationError: If serialization fails and fallback is disabled
        
    SERIALIZATION FLOW:
    1. Determine strategy (standard pickle vs enhanced cerial)
    2. Try primary strategy
    3. If primary fails and fallback enabled, try alternative
    4. If container contains NSOs, use enhanced container serialization
    5. Record performance statistics
    """
    start_time = time.time()
    
    try:
        strategy = _registry.get_type_strategy(obj)
        
        if strategy == _SerializationStrategy.STANDARD_PICKLE:
            # Use standard pickle for most objects
            try:
                result = pickle.dumps(obj)
                _registry._record_operation("serializations", time.time() - start_time)
                return result
            except Exception as e:
                # If standard pickle fails, check if enhanced serialization might help
                if _registry.is_debug_mode():
                    print(f"Standard pickle failed: {e}")
                    print(f"Checking if object contains NSOs...")
                
                if fallback_to_pickle and _contains_nso_objects(obj):
                    if _registry.is_debug_mode():
                        print(f"Object contains NSOs, using enhanced container serialization...")
                    try:
                        # Force enhanced serialization for objects containing NSOs
                        result = _serialize_enhanced_container(obj)
                        _registry._record_operation("enhanced_serializations", time.time() - start_time)
                        return result
                    except Exception as enhanced_error:
                        _registry._record_operation("errors")
                        raise CerializationError(
                            f"Standard pickle failed: {e}, "
                            f"Enhanced container serialization also failed: {enhanced_error}"
                        )
                else:
                    if _registry.is_debug_mode():
                        print(f"Object does not contain NSOs or fallback disabled")
                    _registry._record_operation("errors")
                    raise CerializationError(f"Standard pickle failed: {e}")
        
        elif strategy == _SerializationStrategy.ENHANCED_CERIAL:
            # Use enhanced serialization
            try:
                result = _serialize_enhanced(obj)
                _registry._record_operation("enhanced_serializations", time.time() - start_time)
                return result
            except Exception as e:
                if fallback_to_pickle:
                    # Fall back to standard pickle
                    try:
                        result = pickle.dumps(obj)
                        _registry._record_operation("fallback_to_pickle", time.time() - start_time)
                        return result
                    except Exception as pickle_error:
                        _registry._record_operation("errors")
                        raise CerializationError(
                            f"Enhanced serialization failed: {e}, "
                            f"Pickle fallback also failed: {pickle_error}"
                        )
                else:
                    _registry._record_operation("errors")
                    raise CerializationError(f"Enhanced serialization failed: {e}")
        
        elif strategy == _SerializationStrategy.SKIP_OBJECT:
            # Return placeholder for skipped objects
            result = pickle.dumps({"__cerial_placeholder__": True, "type": str(type(obj))})
            _registry._record_operation("serializations", time.time() - start_time)
            return result
        
        else:
            _registry._record_operation("errors")
            raise CerializationError(f"Unknown serialization strategy: {strategy}")
            
    except Exception as e:
        _registry._record_operation("errors")
        raise


def deserialize(data: bytes, fallback_to_pickle: bool = True) -> Any:
    """
    Deserialize an object from bytes.
    
    Args:
        data: Serialized bytes
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        Deserialized object
        
    Raises:
        DecerializationError: If deserialization fails and fallback is disabled
        
    DESERIALIZATION FLOW:
    1. Check if data is enhanced cerial format
    2. Use appropriate deserialization method
    3. If enhanced fails and fallback enabled, try standard pickle
    4. Record performance statistics
    """
    start_time = time.time()
    
    try:
        # First, try to detect if this is enhanced cerial data
        if _is_enhanced_cerial_data(data):
            result = _deserialize_enhanced(data)
            _registry._record_operation("deserializations", time.time() - start_time)
            return result
        else:
            # Use standard pickle
            result = pickle.loads(data)
            _registry._record_operation("deserializations", time.time() - start_time)
            return result
    
    except Exception as e:
        if fallback_to_pickle:
            # Try standard pickle as fallback
            try:
                result = pickle.loads(data)
                _registry._record_operation("fallback_to_pickle", time.time() - start_time)
                return result
            except Exception as pickle_error:
                _registry._record_operation("errors")
                raise DecerializationError(
                    f"Cerial deserialization failed: {e}, "
                    f"Pickle fallback also failed: {pickle_error}"
                )
        else:
            _registry._record_operation("errors")
            raise DecerializationError(f"Deserialization failed: {e}")


# ============================================================================
# BATCH SERIALIZATION CONVENIENCE METHODS
# ============================================================================

def serialize_batch(objects: List[Any], fallback_to_pickle: bool = True) -> List[bytes]:
    """
    Serialize a batch of objects efficiently.
    
    Args:
        objects: List of objects to serialize
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        List of serialized bytes in same order as input
        
    Raises:
        CerializationError: If any serialization fails and fallback is disabled
    """
    results = []
    errors = []
    
    for i, obj in enumerate(objects):
        try:
            serialized = serialize(obj, fallback_to_pickle)
            results.append(serialized)
        except Exception as e:
            errors.append(f"Object {i}: {e}")
            results.append(None)
    
    if errors:
        raise CerializationError(f"Batch serialization had {len(errors)} errors: {errors}")
    
    return results


def deserialize_batch(data_list: List[bytes], fallback_to_pickle: bool = True) -> List[Any]:
    """
    Deserialize a batch of serialized objects efficiently.
    
    Args:
        data_list: List of serialized bytes to deserialize
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        List of deserialized objects in same order as input
        
    Raises:
        DecerializationError: If any deserialization fails and fallback is disabled
    """
    results = []
    errors = []
    
    for i, data in enumerate(data_list):
        try:
            deserialized = deserialize(data, fallback_to_pickle)
            results.append(deserialized)
        except Exception as e:
            errors.append(f"Data {i}: {e}")
            results.append(None)
    
    if errors:
        raise DecerializationError(f"Batch deserialization had {len(errors)} errors: {errors}")
    
    return results


def serialize_dict(obj_dict: Dict[str, Any], fallback_to_pickle: bool = True) -> Dict[str, bytes]:
    """
    Serialize a dictionary of objects, preserving keys.
    
    Args:
        obj_dict: Dictionary of objects to serialize
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        Dictionary with same keys but serialized values
    """
    result = {}
    errors = []
    
    for key, obj in obj_dict.items():
        try:
            result[key] = serialize(obj, fallback_to_pickle)
        except Exception as e:
            errors.append(f"Key '{key}': {e}")
    
    if errors:
        raise CerializationError(f"Dictionary serialization had {len(errors)} errors: {errors}")
    
    return result


def deserialize_dict(data_dict: Dict[str, bytes], fallback_to_pickle: bool = True) -> Dict[str, Any]:
    """
    Deserialize a dictionary of serialized objects, preserving keys.
    
    Args:
        data_dict: Dictionary of serialized bytes to deserialize
        fallback_to_pickle: Whether to fall back to standard pickle on failure
        
    Returns:
        Dictionary with same keys but deserialized values
    """
    result = {}
    errors = []
    
    for key, data in data_dict.items():
        try:
            result[key] = deserialize(data, fallback_to_pickle)
        except Exception as e:
            errors.append(f"Key '{key}': {e}")
    
    if errors:
        raise DecerializationError(f"Dictionary deserialization had {len(errors)} errors: {errors}")
    
    return result


# ============================================================================
# HANDLER REGISTRATION AND MANAGEMENT
# ============================================================================

def register_handler(priority: int = 50):
    """
    Decorator to automatically register an NSO handler.
    
    Args:
        priority: Handler priority (lower = higher priority)
        
    Example:
        @register_handler(priority=10)
        class MyCustomHandler(_NSO_Handler):
            def can_handle(self, obj):
                return isinstance(obj, MyCustomType)
            # ... rest of implementation
    """
    def decorator(handler_class: Type[_NSO_Handler]):
        # Create instance and set priority
        handler_instance = handler_class()
        handler_instance.set_priority(priority)
        
        # Register immediately
        _registry.register_handler(handler_instance)
        
        # Return the class unchanged
        return handler_class
    
    return decorator


def register_nso_handler(handler: _NSO_Handler) -> None:
    """
    Register a new NSO handler globally.
    
    Args:
        handler: NSO handler instance
    """
    _registry.register_handler(handler)


def unregister_handler(handler_name: str) -> bool:
    """
    Unregister a handler by name.
    
    Args:
        handler_name: Name of handler to remove
        
    Returns:
        True if handler was found and removed
    """
    return _registry.unregister_handler(handler_name)


def get_registered_handlers() -> List[Dict[str, Any]]:
    """Get information about all registered handlers."""
    return _registry.get_handler_info()


def discover_handlers() -> int:
    """
    Discover and register all available handlers.
    
    Returns:
        Number of handlers discovered and registered
    """
    return _registry.discover_and_register_handlers()


# ============================================================================
# CONFIGURATION AND CONTROL FUNCTIONS  
# ============================================================================

def enable_debug_mode() -> None:
    """Enable debug mode for detailed serialization logging."""
    _registry.enable_debug_mode()


def disable_debug_mode() -> None:
    """Disable debug mode."""
    _registry.disable_debug_mode()


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return _registry.is_debug_mode()


def enable_auto_discovery() -> None:
    """Enable automatic handler discovery."""
    _registry.enable_auto_discovery()


def disable_auto_discovery() -> None:
    """Disable automatic handler discovery."""
    _registry.disable_auto_discovery()


def get_performance_stats() -> Dict[str, Any]:
    """Get performance statistics for cerial operations."""
    return _registry.get_performance_stats()


def reset_performance_stats() -> None:
    """Reset performance statistics."""
    _registry.reset_performance_stats()


# ============================================================================
# TESTING AND ANALYSIS FUNCTIONS
# ============================================================================

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
        "handler": handler._handler_name if handler else None,
        "needs_enhanced": strategy == _SerializationStrategy.ENHANCED_CERIAL,
        "can_fallback_to_pickle": True,  # We always try pickle as fallback
        "object_size": sys.getsizeof(obj),
        "handler_priority": handler.get_priority() if handler else None
    }


def test_serialization(obj: Any, include_roundtrip: bool = True) -> Dict[str, Any]:
    """
    Test serialization of an object without permanently serializing it.
    
    Args:
        obj: Object to test
        include_roundtrip: Whether to test full roundtrip serialization
        
    Returns:
        Dictionary with test results
    """
    results = {
        "object_type": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
        "object_size": sys.getsizeof(obj),
        "standard_pickle_works": False,
        "enhanced_cerial_works": False,
        "handler_available": False,
        "strategy": None,
        "serialized_size": None,
        "roundtrip_successful": False,
        "performance": {},
        "errors": []
    }
    
    # Test standard pickle
    try:
        start_time = time.time()
        pickled = pickle.dumps(obj)
        pickle_time = time.time() - start_time
        
        results["standard_pickle_works"] = True
        results["serialized_size"] = len(pickled)
        results["performance"]["pickle_time"] = pickle_time
        
        if include_roundtrip:
            start_time = time.time()
            unpickled = pickle.loads(pickled)
            unpickle_time = time.time() - start_time
            results["performance"]["unpickle_time"] = unpickle_time
            
    except Exception as e:
        results["errors"].append(f"Standard pickle failed: {e}")
    
    # Test enhanced cerial
    handler = _registry.get_handler(obj)
    if handler:
        results["handler_available"] = True
        try:
            start_time = time.time()
            serialized = handler.serialize(obj)
            cerial_serialize_time = time.time() - start_time
            
            results["enhanced_cerial_works"] = True
            results["performance"]["cerial_serialize_time"] = cerial_serialize_time
            
            if include_roundtrip:
                start_time = time.time()
                deserialized = handler.deserialize(serialized)
                cerial_deserialize_time = time.time() - start_time
                results["performance"]["cerial_deserialize_time"] = cerial_deserialize_time
                results["roundtrip_successful"] = True
                
        except Exception as e:
            results["errors"].append(f"Enhanced cerial failed: {e}")
    
    # Get strategy
    strategy = _registry.get_type_strategy(obj)
    results["strategy"] = strategy.value
    
    return results


def benchmark_serialization(obj: Any, iterations: int = 100) -> Dict[str, Any]:
    """
    Benchmark serialization performance for an object.
    
    Args:
        obj: Object to benchmark
        iterations: Number of iterations to run
        
    Returns:
        Dictionary with benchmark results
    """
    results = {
        "iterations": iterations,
        "object_type": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
        "object_size": sys.getsizeof(obj),
        "pickle_times": [],
        "cerial_times": [],
        "pickle_avg": 0.0,
        "cerial_avg": 0.0,
        "cerial_overhead": 0.0,
        "errors": []
    }
    
    # Benchmark pickle
    for _ in range(iterations):
        try:
            start = time.time()
            serialized = serialize(obj, fallback_to_pickle=True)
            deserialized = deserialize(serialized, fallback_to_pickle=True)
            duration = time.time() - start
            results["pickle_times"].append(duration)
        except Exception as e:
            results["errors"].append(f"Pickle iteration failed: {e}")
    
    if results["pickle_times"]:
        results["pickle_avg"] = sum(results["pickle_times"]) / len(results["pickle_times"])
    
    # Calculate overhead if we have both measurements
    if results["pickle_avg"] > 0 and results["cerial_avg"] > 0:
        results["cerial_overhead"] = ((results["cerial_avg"] - results["pickle_avg"]) / results["pickle_avg"]) * 100
    
    return results


# ============================================================================
# INITIALIZATION
# ============================================================================

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

# Auto-discover handlers on module load if enabled
if _registry._auto_discovery_enabled:
    _registry.discover_and_register_handlers()