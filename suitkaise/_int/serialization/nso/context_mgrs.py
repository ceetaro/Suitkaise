"""
Context Managers Serialization Handler

This module provides serialization support for context manager objects that
implement the context management protocol (__enter__ and __exit__ methods)
and cannot be pickled due to resource management state or contained resources.

SUPPORTED OBJECTS:
==================

1. FILE CONTEXT MANAGERS:
   - File objects used with 'with' statements
   - Text and binary file contexts
   - Temporary file contexts

2. THREADING CONTEXT MANAGERS:
   - Lock contexts (with threading.Lock())
   - RLock, Semaphore, and other threading contexts
   - Custom threading context managers

3. STANDARD LIBRARY CONTEXTS:
   - contextlib.closing() contexts
   - contextlib.suppress() contexts
   - contextlib.redirect_stdout/stderr contexts
   - contextlib.ExitStack contexts

4. DATABASE CONTEXTS:
   - Database transaction contexts
   - Connection contexts with automatic commit/rollback

5. CUSTOM CONTEXT MANAGERS:
   - User-defined classes with __enter__/__exit__
   - contextlib.contextmanager decorated functions
   - Resource management contexts

SERIALIZATION STRATEGY:
======================

Context manager serialization is challenging because:
- Context managers manage resources that may not be serializable
- They have internal state about entry/exit status
- They may hold references to external resources
- Some contexts are meant to be single-use
- Exit behavior may depend on exception state

Our approach:
1. **Detect context manager type** (file, lock, custom, etc.)
2. **Extract managed resource info** when possible
3. **Store context configuration** for recreation
4. **Handle context state** (entered, exited, exception state)
5. **Recreate contexts** in a fresh, usable state
6. **Provide functional placeholders** for unrecreatable contexts

LIMITATIONS:
============
- Context state (entered/exited) is reset on recreation
- Managed resources may be closed/released during serialization
- Exception handling state cannot be preserved
- Some contexts are single-use and cannot be recreated identically
- Custom context logic may be lost if it depends on closures
- Nested contexts in ExitStack may not preserve order perfectly

"""

import contextlib
import threading
import sys
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, ContextManager

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class ContextManagersHandler(_NSO_Handler):
    """Handler for context manager objects and context management protocols."""
    
    def __init__(self):
        """Initialize the context managers handler."""
        super().__init__()
        self._handler_name = "ContextManagersHandler"
        self._priority = 10  # High priority since contexts are common in modern Python
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given context manager object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for __enter__ and __exit__ methods (context protocol)
        - Check for specific context manager types
        - Check for contextlib objects
        - Exclude objects that are better handled by other handlers
        """
        try:
            # Primary check: context management protocol
            has_enter = hasattr(obj, '__enter__')
            has_exit = hasattr(obj, '__exit__')
            
            if has_enter and has_exit:
                # This looks like a context manager, but check if it should be handled elsewhere
                
                # Exclude objects that have dedicated handlers
                obj_type_name = type(obj).__name__
                obj_module = getattr(type(obj), '__module__', '')
                
                # Don't handle these - they have specialized handlers
                excluded_types = {
                    'Connection',  # Database connections (sqlite handler)
                    'Logger',      # Logging objects (loggers handler)
                }
                
                if obj_type_name in excluded_types:
                    return False
                
                # Don't handle basic file objects if they have a dedicated handler
                if hasattr(obj, 'read') and hasattr(obj, 'write') and hasattr(obj, 'close'):
                    # This is a file-like object, let the file handles handler deal with it
                    return False
                
                # Don't handle basic threading primitives - let locks handler deal with them
                if 'threading' in obj_module and obj_type_name in {'Lock', 'RLock', 'Semaphore', 'Event'}:
                    return False
                
                return True
            
            # Check for specific contextlib objects
            if obj_module and 'contextlib' in obj_module:
                contextlib_types = {
                    'closing', 'suppress', 'redirect_stdout', 'redirect_stderr',
                    'ExitStack', 'nullcontext', 'contextmanager'
                }
                if obj_type_name in contextlib_types:
                    return True
            
            # Check for context manager decorators/wrappers
            if hasattr(obj, '__wrapped__') and hasattr(obj.__wrapped__, '__enter__'):
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a context manager object to a dictionary representation.
        
        Args:
            obj: Context manager object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the context manager
            
        SERIALIZATION PROCESS:
        1. Determine context manager type and characteristics
        2. Extract managed resource information
        3. Store context configuration and state
        4. Handle specific context manager types
        5. Store recreation strategy
        """
        # Base serialization data
        data = {
            "context_type": self._get_context_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "context_state": self._get_context_state(obj),
            "managed_resource": None,
            "context_config": {},
            "serialization_strategy": None,
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        context_type = data["context_type"]
        
        if context_type == "file_context":
            data.update(self._serialize_file_context(obj))
            data["serialization_strategy"] = "file_context_recreation"
            
        elif context_type == "threading_context":
            data.update(self._serialize_threading_context(obj))
            data["serialization_strategy"] = "threading_context_recreation"
            
        elif context_type == "contextlib_context":
            data.update(self._serialize_contextlib_context(obj))
            data["serialization_strategy"] = "contextlib_context_recreation"
            
        elif context_type == "database_context":
            data.update(self._serialize_database_context(obj))
            data["serialization_strategy"] = "database_context_recreation"
            
        elif context_type == "custom_context":
            data.update(self._serialize_custom_context(obj))
            data["serialization_strategy"] = "custom_context_recreation"
            
        else:
            # Unknown context type
            data.update(self._serialize_unknown_context(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a context manager object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized context manager data
            
        Returns:
            Recreated context manager object
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore context manager with configuration
        4. Handle errors gracefully with functional placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        context_type = data.get("context_type", "unknown")
        
        try:
            if strategy == "file_context_recreation":
                return self._deserialize_file_context(data)
            
            elif strategy == "threading_context_recreation":
                return self._deserialize_threading_context(data)
            
            elif strategy == "contextlib_context_recreation":
                return self._deserialize_contextlib_context(data)
            
            elif strategy == "database_context_recreation":
                return self._deserialize_database_context(data)
            
            elif strategy == "custom_context_recreation":
                return self._deserialize_custom_context(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_context(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a functional placeholder
            return self._create_context_placeholder(context_type, str(e))
    
    # ========================================================================
    # CONTEXT TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_context_type(self, obj: Any) -> str:
        """
        Determine the specific type of context manager.
        
        Args:
            obj: Context manager object to analyze
            
        Returns:
            String identifying the context manager type
        """
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), '__module__', '')
        
        # File-like contexts
        if hasattr(obj, 'read') or hasattr(obj, 'write') or hasattr(obj, 'name'):
            if hasattr(obj, '__enter__') and hasattr(obj, '__exit__'):
                return "file_context"
        
        # Threading contexts (that aren't basic primitives)
        if 'threading' in obj_module or obj_type_name.endswith('Context'):
            return "threading_context"
        
        # Contextlib contexts
        if 'contextlib' in obj_module:
            return "contextlib_context"
        
        # Database contexts
        if 'connection' in obj_type_name.lower() or 'transaction' in obj_type_name.lower():
            return "database_context"
        
        # Check for specific patterns
        if hasattr(obj, 'acquire') and hasattr(obj, 'release'):
            return "threading_context"
        
        if hasattr(obj, 'commit') and hasattr(obj, 'rollback'):
            return "database_context"
        
        # Default to custom
        return "custom_context"
    
    def _get_context_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract context manager state information.
        
        Args:
            obj: Context manager object
            
        Returns:
            Dictionary with state information
        """
        state = {
            "is_entered": False,
            "is_exited": False,
            "exception_state": None
        }
        
        try:
            # Try to detect if context is currently entered
            # This is heuristic since there's no standard way
            
            # Some context managers have _entered or similar attributes
            for attr_name in ['_entered', '_in_context', '_active']:
                if hasattr(obj, attr_name):
                    state["is_entered"] = bool(getattr(obj, attr_name))
                    break
            
            # Some have _closed or similar for exit state
            for attr_name in ['_closed', '_exited', '_finished']:
                if hasattr(obj, attr_name):
                    state["is_exited"] = bool(getattr(obj, attr_name))
                    break
        
        except Exception:
            pass  # State detection failed, use defaults
        
        return state
    
    # ========================================================================
    # FILE CONTEXT SERIALIZATION
    # ========================================================================
    
    def _serialize_file_context(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize file context managers.
        
        Store file information for recreation.
        """
        result = {
            "file_path": None,
            "file_mode": None,
            "file_encoding": None,
            "file_position": None,
            "is_temporary": False
        }
        
        try:
            # Get file information
            if hasattr(obj, 'name'):
                result["file_path"] = getattr(obj, 'name')
            
            if hasattr(obj, 'mode'):
                result["file_mode"] = getattr(obj, 'mode')
            
            if hasattr(obj, 'encoding'):
                result["file_encoding"] = getattr(obj, 'encoding')
            
            # Get current position if possible
            try:
                if hasattr(obj, 'tell'):
                    result["file_position"] = obj.tell()
            except (OSError, IOError):
                pass
            
            # Check if it's a temporary file
            if hasattr(obj, 'name') and obj.name:
                file_path = str(obj.name)
                if 'tmp' in file_path.lower() or 'temp' in file_path.lower():
                    result["is_temporary"] = True
        
        except Exception as e:
            result["note"] = f"Error extracting file context info: {e}"
        
        result["recreation_possible"] = bool(result["file_path"])
        
        return result
    
    def _deserialize_file_context(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize file context managers.
        """
        file_path = data.get("file_path")
        file_mode = data.get("file_mode", "r")
        file_encoding = data.get("file_encoding")
        file_position = data.get("file_position")
        is_temporary = data.get("is_temporary", False)
        
        if not file_path:
            # Create a placeholder file context
            return self._create_placeholder_file_context()
        
        try:
            # If it was a temporary file and doesn't exist, create a new temp file
            if is_temporary and not os.path.exists(file_path):
                temp_file = tempfile.NamedTemporaryFile(mode=file_mode, delete=False)
                if file_encoding and 'b' not in file_mode:
                    temp_file = tempfile.NamedTemporaryFile(mode=file_mode, encoding=file_encoding, delete=False)
                return temp_file
            
            # Try to open the original file
            open_kwargs = {"mode": file_mode}
            if file_encoding and 'b' not in file_mode:
                open_kwargs["encoding"] = file_encoding
            
            file_obj = open(file_path, **open_kwargs)
            
            # Restore position if possible
            if file_position is not None:
                try:
                    file_obj.seek(file_position)
                except (OSError, IOError):
                    pass
            
            return file_obj
            
        except Exception as e:
            # If file recreation fails, create a placeholder
            return self._create_placeholder_file_context()
    
    def _create_placeholder_file_context(self) -> Any:
        """Create a placeholder file context manager."""
        import io
        
        class PlaceholderFileContext:
            def __init__(self):
                self._stream = io.StringIO("Placeholder file content")
                self.name = "<placeholder_file>"
                self.mode = "r"
            
            def __enter__(self):
                return self._stream
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            def read(self, *args):
                return self._stream.read(*args)
            
            def write(self, data):
                return self._stream.write(data)
            
            def close(self):
                self._stream.close()
        
        return PlaceholderFileContext()
    
    # ========================================================================
    # THREADING CONTEXT SERIALIZATION
    # ========================================================================
    
    def _serialize_threading_context(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize threading context managers.
        """
        result = {
            "threading_type": type(obj).__name__,
            "threading_module": getattr(type(obj), '__module__', ''),
            "resource_info": {}
        }
        
        try:
            # Try to extract information about the managed resource
            for attr_name in ['_lock', '_resource', '_obj', '_target']:
                if hasattr(obj, attr_name):
                    resource = getattr(obj, attr_name)
                    result["resource_info"][attr_name] = {
                        "type": type(resource).__name__,
                        "module": getattr(type(resource), '__module__', ''),
                        "repr": repr(resource)[:100]
                    }
        
        except Exception as e:
            result["note"] = f"Error extracting threading context info: {e}"
        
        result["recreation_possible"] = True  # Can usually create new threading contexts
        
        return result
    
    def _deserialize_threading_context(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize threading context managers.
        """
        threading_type = data.get("threading_type", "Lock")
        
        try:
            # Create appropriate threading context
            if threading_type == "Lock":
                lock = threading.Lock()
                return self._create_lock_context(lock)
            
            elif threading_type == "RLock":
                lock = threading.RLock()
                return self._create_lock_context(lock)
            
            elif threading_type == "Semaphore":
                semaphore = threading.Semaphore()
                return self._create_lock_context(semaphore)
            
            else:
                # Default to basic lock context
                lock = threading.Lock()
                return self._create_lock_context(lock)
                
        except Exception:
            # If threading context creation fails, create a placeholder
            return self._create_placeholder_threading_context()
    
    def _create_lock_context(self, lock) -> Any:
        """Create a context manager for a lock object."""
        class LockContext:
            def __init__(self, lock):
                self._lock = lock
            
            def __enter__(self):
                self._lock.acquire()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self._lock.release()
        
        return LockContext(lock)
    
    def _create_placeholder_threading_context(self) -> Any:
        """Create a placeholder threading context manager."""
        class PlaceholderThreadingContext:
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return PlaceholderThreadingContext()
    
    # ========================================================================
    # CONTEXTLIB CONTEXT SERIALIZATION
    # ========================================================================
    
    def _serialize_contextlib_context(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize contextlib context managers.
        """
        result = {
            "contextlib_type": type(obj).__name__,
            "wrapped_object": None,
            "context_args": [],
            "context_kwargs": {}
        }
        
        try:
            obj_type_name = type(obj).__name__
            
            # Handle specific contextlib types
            if obj_type_name == "closing":
                # Extract the object being closed
                if hasattr(obj, 'thing'):
                    wrapped = obj.thing
                    result["wrapped_object"] = {
                        "type": type(wrapped).__name__,
                        "module": getattr(type(wrapped), '__module__', ''),
                        "repr": repr(wrapped)[:100]
                    }
            
            elif obj_type_name == "suppress":
                # Extract the exceptions being suppressed
                if hasattr(obj, '_exceptions'):
                    result["context_args"] = [exc.__name__ for exc in obj._exceptions if hasattr(exc, '__name__')]
            
            elif obj_type_name in ("redirect_stdout", "redirect_stderr"):
                # Extract the target stream
                if hasattr(obj, '_new_target'):
                    target = obj._new_target
                    result["wrapped_object"] = {
                        "type": type(target).__name__,
                        "repr": repr(target)[:100]
                    }
            
            elif obj_type_name == "ExitStack":
                # ExitStack is more complex - we'll recreate empty
                result["note"] = "ExitStack recreated empty - contexts not preserved"
        
        except Exception as e:
            result["note"] = f"Error extracting contextlib info: {e}"
        
        result["recreation_possible"] = True
        
        return result
    
    def _deserialize_contextlib_context(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize contextlib context managers.
        """
        contextlib_type = data.get("contextlib_type", "nullcontext")
        wrapped_object = data.get("wrapped_object")
        context_args = data.get("context_args", [])
        
        try:
            if contextlib_type == "closing":
                # Create closing context with placeholder object
                import io
                placeholder = io.StringIO()
                return contextlib.closing(placeholder)
            
            elif contextlib_type == "suppress":
                # Recreate suppress context with exceptions
                exception_types = []
                for exc_name in context_args:
                    try:
                        # Try to get built-in exceptions
                        exc_type = getattr(__builtins__, exc_name, Exception)
                        exception_types.append(exc_type)
                    except Exception:
                        continue
                
                if exception_types:
                    return contextlib.suppress(*exception_types)
                else:
                    return contextlib.suppress(Exception)
            
            elif contextlib_type == "redirect_stdout":
                import io
                return contextlib.redirect_stdout(io.StringIO())
            
            elif contextlib_type == "redirect_stderr":
                import io
                return contextlib.redirect_stderr(io.StringIO())
            
            elif contextlib_type == "ExitStack":
                return contextlib.ExitStack()
            
            else:
                # Default to nullcontext
                if hasattr(contextlib, 'nullcontext'):
                    return contextlib.nullcontext()
                else:
                    # Older Python versions don't have nullcontext
                    return self._create_null_context()
                
        except Exception:
            # If contextlib recreation fails, create a null context
            return self._create_null_context()
    
    def _create_null_context(self) -> Any:
        """Create a null context manager (does nothing)."""
        class NullContext:
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        return NullContext()
    
    # ========================================================================
    # DATABASE CONTEXT SERIALIZATION
    # ========================================================================
    
    def _serialize_database_context(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize database context managers.
        """
        result = {
            "database_type": type(obj).__name__,
            "connection_info": None,
            "transaction_state": {}
        }
        
        try:
            # Try to extract connection information
            for attr_name in ['connection', '_connection', 'conn', '_conn']:
                if hasattr(obj, attr_name):
                    conn = getattr(obj, attr_name)
                    result["connection_info"] = {
                        "type": type(conn).__name__,
                        "module": getattr(type(conn), '__module__', ''),
                        "repr": repr(conn)[:100]
                    }
                    break
            
            # Try to extract transaction state
            for attr_name in ['_in_transaction', '_savepoint', '_autocommit']:
                if hasattr(obj, attr_name):
                    result["transaction_state"][attr_name] = getattr(obj, attr_name)
        
        except Exception as e:
            result["note"] = f"Error extracting database context info: {e}"
        
        result["recreation_possible"] = False  # Database contexts are complex
        
        return result
    
    def _deserialize_database_context(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize database context managers.
        """
        # Database contexts are too complex to recreate reliably
        # Return a placeholder that doesn't affect transactions
        
        class PlaceholderDatabaseContext:
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            def commit(self):
                pass
            
            def rollback(self):
                pass
        
        return PlaceholderDatabaseContext()
    
    # ========================================================================
    # CUSTOM CONTEXT SERIALIZATION
    # ========================================================================
    
    def _serialize_custom_context(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize custom context managers.
        """
        result = {
            "custom_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "custom_attributes": {},
            "has_wrapped": False,
            "wrapped_function": None
        }
        
        try:
            # Try to extract simple attributes
            for attr_name in dir(obj):
                if not attr_name.startswith('__') and not callable(getattr(obj, attr_name)):
                    try:
                        attr_value = getattr(obj, attr_name)
                        if isinstance(attr_value, (str, int, float, bool, type(None))):
                            result["custom_attributes"][attr_name] = attr_value
                    except Exception:
                        continue
            
            # Check if it's a contextmanager-decorated function
            if hasattr(obj, '__wrapped__'):
                result["has_wrapped"] = True
                wrapped = obj.__wrapped__
                result["wrapped_function"] = {
                    "name": getattr(wrapped, '__name__', '<unknown>'),
                    "module": getattr(wrapped, '__module__', None),
                    "qualname": getattr(wrapped, '__qualname__', None)
                }
        
        except Exception as e:
            result["note"] = f"Error extracting custom context info: {e}"
        
        result["recreation_possible"] = False  # Custom contexts are hard to recreate
        
        return result
    
    def _deserialize_custom_context(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize custom context managers.
        """
        custom_class = data.get("custom_class", "unknown")
        custom_attributes = data.get("custom_attributes", {})
        
        # Custom contexts are too varied to recreate reliably
        # Return a functional placeholder
        
        class PlaceholderCustomContext:
            def __init__(self, original_class, attributes):
                self._original_class = original_class
                self._attributes = attributes
                # Set simple attributes
                for name, value in attributes.items():
                    try:
                        setattr(self, name, value)
                    except Exception:
                        pass
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            def __repr__(self):
                return f"<PlaceholderCustomContext for {self._original_class}>"
        
        return PlaceholderCustomContext(custom_class, custom_attributes)
    
    # ========================================================================
    # UNKNOWN CONTEXT SERIALIZATION
    # ========================================================================
    
    def _serialize_unknown_context(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown context manager types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "has_enter": hasattr(obj, '__enter__'),
            "has_exit": hasattr(obj, '__exit__'),
            "note": f"Unknown context manager type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_context(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown context manager types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        
        class UnknownContextPlaceholder:
            def __init__(self, context_type):
                self.context_type = context_type
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            def __repr__(self):
                return f"<UnknownContextPlaceholder type='{self.context_type}'>"
        
        return UnknownContextPlaceholder(object_type)
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _create_context_placeholder(self, context_type: str, error_message: str) -> Any:
        """
        Create a placeholder context manager for objects that failed to deserialize.
        """
        class ErrorContextPlaceholder:
            def __init__(self, ctx_type, error):
                self.context_type = ctx_type
                self.error = error
            
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            
            def __repr__(self):
                return f"<ErrorContextPlaceholder type='{self.context_type}' error='{self.error}'>"
        
        return ErrorContextPlaceholder(context_type, error_message)


# Create a singleton instance for auto-registration
context_managers_handler = ContextManagersHandler()