"""
Handler for context manager objects.

Context managers implement the __enter__ and __exit__ protocol.
We serialize the underlying object and recreate the context manager.
"""

import types
from typing import Any, Dict
from .base_class import Handler


class ContextManagerSerializationError(Exception):
    """Raised when context manager serialization fails."""
    pass


class ContextManagerHandler(Handler):
    """
    Serializes context manager objects.
    
    Context managers implement __enter__ and __exit__ methods.
    Common examples:
    - open() file objects (already handled by FileHandleHandler)
    - threading.Lock (already handled by LockHandler)
    - Custom context managers
    
    Strategy:
    - Check if it's a context manager wrapper (contextlib.contextmanager)
    - For custom context managers, serialize the object itself
    - The __enter__ and __exit__ methods are part of the class definition
    
    Note: This handler focuses on custom context managers that aren't 
    covered by more specific handlers (files, locks, etc.).
    """
    
    type_name = "context_manager"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a context manager.
        
        We check for __enter__ and __exit__ methods.
        However, we skip objects that have more specific handlers:
        - File handles (have specific handler)
        - Locks (have specific handler)
        - Database connections (have specific handler)
        """
        # Must have __enter__ and __exit__
        has_enter = hasattr(type(obj), '__enter__')
        has_exit = hasattr(type(obj), '__exit__')
        
        if not (has_enter and has_exit):
            return False
        
        # Skip types that have more specific handlers
        # These are already covered by other handlers
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), '__module__', '')
        
        # Skip file-like objects (FileHandleHandler)
        if hasattr(obj, 'read') or hasattr(obj, 'write'):
            return False
        
        # Skip locks and threading objects (LockHandler, etc.)
        if 'threading' in obj_module or 'multiprocessing' in obj_module:
            return False
        
        # Skip database connections (handled by DatabaseConnectionHandler)
        if 'connection' in obj_type_name.lower() or 'cursor' in obj_type_name.lower():
            return False
        
        # Skip generators (GeneratorHandler)
        if isinstance(obj, types.GeneratorType):
            return False
        
        # Skip custom __serialize__/__deserialize__ objects (ClassInstanceHandler)
        if hasattr(obj, '__serialize__') and hasattr(type(obj), '__deserialize__'):
            return False
        
        # This is a custom context manager - handle it
        return True
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract context manager state.
        
        For most context managers, we just serialize the object itself.
        The __enter__ and __exit__ methods are part of the class definition.
        
        What we capture:
        - module: Object's module
        - class_name: Object's class name
        - instance_dict: Object's __dict__ (if it has one)
        - is_active: Whether context is currently entered (if we can determine)
        """
        obj_class = type(obj)
        
        # Get instance state
        instance_dict = {}
        if hasattr(obj, '__dict__'):
            instance_dict = dict(obj.__dict__)
        
        # Try to determine if context is active
        # This is difficult to determine generically, so we just note it
        is_active = False
        # We can't reliably determine if __enter__ was called without 
        # side effects, so we assume it's not active
        
        return {
            "module": obj_class.__module__,
            "class_name": obj_class.__name__,
            "qualname": obj_class.__qualname__,
            "instance_dict": instance_dict,
            "is_active": is_active,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct context manager.
        
        We recreate the object using __new__ and populate its __dict__.
        We do NOT call __enter__ - the user must do that if needed.
        """
        # Import module
        import importlib
        
        try:
            module = importlib.import_module(state["module"])
        except ImportError as e:
            raise ContextManagerSerializationError(
                f"Cannot import module '{state['module']}' for context manager {state['class_name']}"
            ) from e
        
        # Get class
        parts = state["qualname"].split('.')
        cls = module
        for part in parts:
            try:
                cls = getattr(cls, part)
            except AttributeError as e:
                raise ContextManagerSerializationError(
                    f"Cannot find class '{state['qualname']}' in module '{state['module']}'"
                ) from e
        
        # Create instance without calling __init__
        obj = cls.__new__(cls)
        
        # Populate __dict__
        if state["instance_dict"]:
            obj.__dict__.update(state["instance_dict"])
        
        # Note: We do NOT call __enter__
        # The context manager is reconstructed but not entered
        # User must call __enter__ if they want to use it as a context manager
        
        return obj


class ContextlibGeneratorHandler(Handler):
    """
    Serializes context managers created with @contextlib.contextmanager.
    
    These are generator-based context managers.
    """
    
    type_name = "contextlib_generator"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a contextlib generator-based context manager.
        
        These have a specific type from contextlib.
        """
        obj_type_name = type(obj).__name__
        obj_module = getattr(type(obj), '__module__', '')
        
        # contextlib decorators create _GeneratorContextManager objects
        return (
            'contextlib' in obj_module and
            'GeneratorContextManager' in obj_type_name
        )
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract generator-based context manager state.
        
        These wrap a generator function.
        """
        # Get the underlying generator function
        func = getattr(obj, 'func', None)
        args = getattr(obj, 'args', ())
        kwds = getattr(obj, 'kwds', {})
        
        return {
            "func": func,  # Will be recursively serialized by FunctionHandler
            "args": args,
            "kwds": kwds,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct generator-based context manager.
        
        We need to recreate it by calling the generator function.
        """
        import contextlib
        
        # The func should be deserialized back to the original generator function
        # Call it with the same args/kwds to create a new context manager
        func = state["func"]
        
        # If func is already a context manager decorator, call it
        # Otherwise, wrap it
        if hasattr(func, '__enter__') and hasattr(func, '__exit__'):
            return func
        
        # Call the generator function to create the context manager
        return func(*state["args"], **state["kwds"])

