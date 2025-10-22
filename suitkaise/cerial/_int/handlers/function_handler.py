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
    
    Functions are complex objects containing:
    - Bytecode (compiled code)
    - Closure variables (captured from enclosing scope)
    - Global variable references
    - Default argument values
    - Annotations
    
    Strategy:
    - Extract all function components
    - On reconstruction, use types.FunctionType to rebuild
    
    This handles:
    - Regular functions defined at module level
    - Functions in __main__ (which pickle can't handle)
    - Nested functions (closures)
    - But NOT lambdas (see LambdaHandler)
    """
    
    type_name = "function"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a function (but not a lambda)."""
        if not isinstance(obj, types.FunctionType):
            return False
        # Exclude lambdas - they have their own handler
        return obj.__name__ != '<lambda>'
    
    def extract_state(self, obj: types.FunctionType) -> Dict[str, Any]:
        """
        Extract function components.
        
        What we capture:
        - __code__: Code object (bytecode) - will be recursively serialized
        - __globals__: Global variables the function references
        - __name__: Function name
        - __defaults__: Default argument values
        - __kwdefaults__: Keyword-only default values
        - __closure__: Closure variables (captured from outer scope)
        - __annotations__: Type annotations
        - __doc__: Documentation string
        - __module__: Module name
        
        Note: We only capture globals that the function actually references,
        not the entire global namespace (which could be huge).
        """
        # Get code object
        code = obj.__code__
        
        # Get only the globals that this function references
        # This is important - we don't want to serialize the entire global namespace
        referenced_globals = {}
        for name in code.co_names:
            if name in obj.__globals__:
                try:
                    referenced_globals[name] = obj.__globals__[name]
                except (KeyError, TypeError):
                    # Some globals might not exist or be serializable, skip them
                    pass
        
        # Always include __builtins__ so function can access built-in functions
        if '__builtins__' in obj.__globals__:
            referenced_globals['__builtins__'] = obj.__globals__['__builtins__']
        
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
        Reconstruct function from components.
        
        Process:
        1. Get deserialized code object and globals
        2. Recreate closure cells if needed
        3. Use types.FunctionType to create function
        4. Restore defaults, annotations, etc.
        """
        # Get code and globals (already deserialized)
        code = state["code"]
        globals_dict = state["globals"]
        
        # Recreate closure cells if needed
        closure = None
        if state["closure"] is not None:
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
            argdefs=state["defaults"],
            closure=closure
        )
        
        # Restore other attributes
        if state["kwdefaults"]:
            func.__kwdefaults__ = state["kwdefaults"]
        if state["annotations"]:
            func.__annotations__ = state["annotations"]
        if state["doc"]:
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
    
    They contain:
    - The instance (self)
    - The underlying function
    
    Note: Pickle can't serialize bound methods, but we can!
    """
    
    type_name = "bound_method"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a bound method."""
        return isinstance(obj, types.MethodType)
    
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
        return {
            "instance": obj.__self__,  # Will be recursively serialized
            "function_name": obj.__func__.__name__,
            "class_name": obj.__self__.__class__.__name__,
            "module": obj.__self__.__class__.__module__,
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

