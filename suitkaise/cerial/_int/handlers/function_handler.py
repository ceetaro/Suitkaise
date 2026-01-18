"""
Handler for function objects.

Includes regular functions, closures, partial functions, and bound methods.
Functions are tricky because they contain bytecode, closures, and references to globals.
"""

import types
import functools
from typing import Any, Dict, Tuple
from .base_class import Handler


class FunctionSerializationError(Exception):
    """Raised when function serialization fails."""
    pass


class FunctionHandler(Handler):
    """
    Serializes function objects.
    
    Two strategies:
    1. Reference-based (fast): Store module + qualname, import on the other end
       - Used for module-level functions, class methods
       - ~100x faster, ~100x smaller
    
    2. Full serialization (slow): Store bytecode, globals, closures, etc.
       - Used for closures, nested functions, dynamically created functions
       - Complete but expensive
    
    This handles:
    - Regular functions defined at module level (reference)
    - Class methods (reference)
    - Functions in __main__ (full - can't import)
    - Nested functions/closures (full - have captured state)
    - But NOT lambdas (see LambdaHandler)
    """
    
    type_name = "function"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a function (but not a lambda)."""
        if not isinstance(obj, types.FunctionType):
            return False
        # Exclude lambdas - they have their own handler
        return obj.__name__ != '<lambda>'
    
    def _can_use_reference(self, func: types.FunctionType) -> bool:
        """
        Check if function can be serialized by reference.
        
        Requirements:
        - Has __module__ and __qualname__
        - Not a closure (no captured variables)
        - Not in __main__ (can't import __main__)
        - qualname doesn't contain '<locals>' (nested function)
        - Can actually look up and get the same function back
        
        Returns:
            bool: True if reference serialization is safe
        """
        # Must have module and qualname
        module_name = getattr(func, '__module__', None)
        qualname = getattr(func, '__qualname__', None)
        if not module_name or not qualname:
            return False
        
        # Can't import from __main__
        if module_name == '__main__':
            return False
        
        # Nested functions have '<locals>' in qualname
        if '<locals>' in qualname:
            return False
        
        # Closures have captured variables
        if func.__closure__ is not None:
            return False
        
        # Verify we can actually look it up and get the same function
        try:
            import importlib
            module = importlib.import_module(module_name)
            
            # Navigate qualname (handles class methods like MyClass.method)
            obj = module
            for part in qualname.split('.'):
                obj = getattr(obj, part)
            
            # Must be the exact same function object
            if obj is not func:
                return False
            
        except (ImportError, AttributeError, TypeError):
            return False
        
        return True
    
    def extract_state(self, obj: types.FunctionType) -> Dict[str, Any]:
        """
        Extract function state - tries reference first, falls back to full.
        
        Reference format (fast):
        - module: module name
        - qualname: qualified name
        - serialization_type: "reference"
        
        Full format (slow):
        - code, globals, name, defaults, etc.
        - serialization_type: "full"
        """
        # Try reference-based serialization first (fast path)
        if self._can_use_reference(obj):
            return {
                "serialization_type": "reference",
                "module": obj.__module__,
                "qualname": obj.__qualname__,
            }
        
        # Fall back to full serialization (slow path)
        return self._extract_full_state(obj)
    
    def _extract_full_state(self, obj: types.FunctionType) -> Dict[str, Any]:
        """
        Extract full function components for complete serialization.
        
        Used when reference-based serialization isn't possible.
        """
        # Get code object
        code = obj.__code__
        
        # Get only the globals that this function references
        # This is important - we don't want to serialize the entire global namespace
        referenced_globals = {}
        for name in code.co_names:
            if name in obj.__globals__:
                # Skip __builtins__ - it's a huge module (157+ items) that always 
                # exists on the other end. We'll restore it during reconstruction.
                if name == '__builtins__':
                    continue
                try:
                    referenced_globals[name] = obj.__globals__[name]
                except (KeyError, TypeError):
                    # Some globals might not exist or be serializable, skip them
                    pass
        
        # NOTE: We intentionally do NOT include __builtins__ here.
        # __builtins__ is a module with 157+ items that exists on every Python process.
        # Serializing it would add ~1.5KB overhead to every function.
        # During reconstruction, we'll inject the target process's __builtins__.
        
        # Get closure cell contents
        # Closures capture variables from enclosing scopes
        closure_values = None
        if obj.__closure__:
            closure_values = []
            for cell in obj.__closure__:
                try:
                    closure_values.append(cell.cell_contents)
                except ValueError:
                    # Cell is empty (variable not yet assigned in closure)
                    closure_values.append(None)
        
        return {
            "serialization_type": "full",
            "code": code,  # Will be recursively serialized by CodeObjectHandler
            "globals": referenced_globals,  # Dict will be recursively serialized
            "name": obj.__name__,
            "defaults": obj.__defaults__,  # Tuple of default values
            "kwdefaults": obj.__kwdefaults__,  # Dict of keyword defaults
            "closure": closure_values,  # List of captured variables
            "annotations": obj.__annotations__,  # Type annotations
            "doc": obj.__doc__,
            "module": obj.__module__,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> types.FunctionType:
        """
        Reconstruct function from state.
        
        Handles both reference and full serialization formats.
        """
        serialization_type = state.get("serialization_type", "full")
        
        if serialization_type == "reference":
            return self._reconstruct_from_reference(state)
        else:
            return self._reconstruct_full(state)
    
    def _reconstruct_from_reference(self, state: Dict[str, Any]) -> types.FunctionType:
        """
        Reconstruct function by importing it from module.
        
        Fast path - just look up the function by module + qualname.
        """
        import importlib
        
        module_name = state["module"]
        qualname = state["qualname"]
        
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise FunctionSerializationError(
                f"Cannot import module '{module_name}' for function '{qualname}'. "
                f"Ensure the module exists in the target process."
            ) from e
        
        # Navigate qualname (handles class methods like MyClass.method)
        obj = module
        for part in qualname.split('.'):
            try:
                obj = getattr(obj, part)
            except AttributeError as e:
                raise FunctionSerializationError(
                    f"Cannot find function '{qualname}' in module '{module_name}'. "
                    f"Ensure the function definition exists in the target process."
                ) from e
        
        if not callable(obj):
            raise FunctionSerializationError(
                f"'{qualname}' in '{module_name}' is not callable"
            )
        
        return obj
    
    def _reconstruct_full(self, state: Dict[str, Any]) -> types.FunctionType:
        """
        Reconstruct function from full bytecode serialization.
        
        Slow path - rebuild from code object, globals, closures, etc.
        """
        # Get code and globals (already deserialized)
        code = state["code"]
        globals_dict = state["globals"]
        
        # Inject __builtins__ from the target process
        # We don't serialize __builtins__ (it's huge) - we use the local one
        import builtins
        globals_dict['__builtins__'] = builtins
        
        # Recreate closure cells if needed
        closure = None
        if state.get("closure") is not None:
            # Create cell objects from closure values
            closure = tuple(
                types.CellType(value) if hasattr(types, 'CellType') 
                else self._make_cell(value)
                for value in state["closure"]
            )
        
        # Create function
        func = types.FunctionType(
            code,
            globals_dict,
            name=state["name"],
            argdefs=state.get("defaults"),
            closure=closure
        )
        
        # Restore other attributes
        if state.get("kwdefaults"):
            func.__kwdefaults__ = state["kwdefaults"]
        if state.get("annotations"):
            func.__annotations__ = state["annotations"]
        if state.get("doc"):
            func.__doc__ = state["doc"]
        
        return func
    
    def _make_cell(self, value: Any) -> Any:
        """
        Create a cell object containing a value.
        
        Cells are used for closure variables. Python doesn't expose
        a direct way to create them, so we use this trick.
        """
        # Create a closure that captures the value
        def _closure():
            return value
        return _closure.__closure__[0]


class PartialFunctionHandler(Handler):
    """
    Serializes functools.partial objects.
    
    Partial functions are functions with some arguments pre-filled.
    They're commonly used for callback functions and function factories.
    
    Example:
        multiply = lambda x, y: x * y
        double = functools.partial(multiply, 2)
        double(5)  # Returns 10
    """
    
    type_name = "partial_function"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a functools.partial."""
        return isinstance(obj, functools.partial)
    
    def extract_state(self, obj: functools.partial) -> Dict[str, Any]:
        """
        Extract partial function components.
        
        What we capture:
        - func: The wrapped function (will be recursively serialized)
        - args: Positional arguments already bound
        - keywords: Keyword arguments already bound
        """
        return {
            "func": obj.func,  # Will be recursively serialized
            "args": obj.args,  # Tuple will be recursively serialized
            "keywords": obj.keywords,  # Dict will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> functools.partial:
        """
        Reconstruct partial function.
        
        Simply create new partial with same function and arguments.
        """
        return functools.partial(
            state["func"],
            *state["args"],
            **state["keywords"]
        )


class BoundMethodHandler(Handler):
    """
    Serializes bound method objects.
    
    Bound methods are methods bound to an instance.
    Example:
        obj = MyClass()
        method = obj.some_method  # This is a bound method
    
    Also handles built-in bound methods (e.g., list.append).
    
    They contain:
    - The instance (self)
    - The underlying function
    
    Note: Pickle can't serialize bound methods, but we can!
    """
    
    type_name = "bound_method"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a bound method (Python or built-in)."""
        if isinstance(obj, types.MethodType):
            return obj.__self__ is not None
        if isinstance(obj, types.BuiltinMethodType):
            return obj.__self__ is not None
        return False
    
    def extract_state(self, obj: types.MethodType) -> Dict[str, Any]:
        """
        Extract bound method components.
        
        What we capture:
        - instance: The instance the method is bound to (self)
        - function_name: Name of the method
        
        Note: We store the function name rather than the function object
        itself, because the function is part of the class definition
        and will already exist when we reconstruct.
        """
        instance = obj.__self__
        if isinstance(obj, types.MethodType):
            function_name = obj.__func__.__name__
        else:
            function_name = getattr(obj, "__name__", None)
            if function_name is None:
                raise FunctionSerializationError("Cannot determine built-in method name.")
        
        return {
            "instance": instance,  # Will be recursively serialized
            "function_name": function_name,
            "class_name": instance.__class__.__name__,
            "module": instance.__class__.__module__,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> types.MethodType:
        """
        Reconstruct bound method.
        
        Process:
        1. Get the deserialized instance
        2. Get the method by name from the instance
        
        The method already exists on the class, so we just need
        to get it bound to the instance.
        """
        # Instance has already been deserialized
        instance = state["instance"]
        
        # Get method from instance by name
        # This automatically creates a bound method
        method = getattr(instance, state["function_name"])
        
        return method


class LambdaHandler(Handler):
    """
    Serializes lambda functions.
    
    Lambdas are anonymous functions with special handling.
    They use the same serialization approach as regular functions,
    but we handle them separately for clarity and potential
    future optimizations.
    """
    
    type_name = "lambda"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a lambda.
        
        Lambdas are function objects with name '<lambda>'.
        """
        return isinstance(obj, types.FunctionType) and obj.__name__ == '<lambda>'
    
    def extract_state(self, obj: types.FunctionType) -> Dict[str, Any]:
        """
        Extract lambda state - same as function.
        
        Lambdas are just anonymous functions, so we use the same
        extraction logic as FunctionHandler.
        """
        # Reuse FunctionHandler logic
        func_handler = FunctionHandler()
        return func_handler.extract_state(obj)
    
    def reconstruct(self, state: Dict[str, Any]) -> types.FunctionType:
        """Reconstruct lambda - same as function."""
        # Reuse FunctionHandler logic
        func_handler = FunctionHandler()
        return func_handler.reconstruct(state)


class StaticMethodHandler(Handler):
    """
    Serializes static method objects.
    
    Static methods are methods that don't receive self or cls.
    They're decorated with @staticmethod.
    """
    
    type_name = "static_method"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a staticmethod."""
        return isinstance(obj, staticmethod)
    
    def extract_state(self, obj: staticmethod) -> Dict[str, Any]:
        """
        Extract static method.
        
        Static methods wrap a function.
        """
        return {
            "func": obj.__func__,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> staticmethod:
        """Reconstruct static method."""
        return staticmethod(state["func"])


class ClassMethodHandler(Handler):
    """
    Serializes class method objects.
    
    Class methods are methods that receive the class as first argument.
    They're decorated with @classmethod.
    """
    
    type_name = "class_method"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a classmethod."""
        return isinstance(obj, classmethod)
    
    def extract_state(self, obj: classmethod) -> Dict[str, Any]:
        """
        Extract class method.
        
        Class methods wrap a function.
        """
        return {
            "func": obj.__func__,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> classmethod:
        """Reconstruct class method."""
        return classmethod(state["func"])

