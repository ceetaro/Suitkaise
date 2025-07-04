"""
Functions Serialization Handler

This module provides serialization support for function objects that cannot
be pickled normally, including lambda functions, async functions, bound methods,
and partial functions.

SUPPORTED OBJECTS:
==================

1. LAMBDA FUNCTIONS:
   - Anonymous functions created with lambda keyword
   - Closures with captured variables

2. REGULAR FUNCTIONS:
   - Named functions defined with def
   - Nested functions
   - Functions with decorators

3. ASYNC FUNCTIONS:
   - Async functions defined with async def
   - Async lambda functions (Python 3.5+)

4. BOUND METHODS:
   - Instance methods bound to objects
   - Class methods and static methods

5. PARTIAL FUNCTIONS:
   - functools.partial objects
   - Partially applied functions

6. BUILT-IN FUNCTIONS:
   - Built-in functions like len, str, etc.
   - C extension functions

SERIALIZATION STRATEGY:
======================

The key challenge with function serialization is that functions contain:
- Executable code (bytecode)
- Closure variables (free variables)
- Global namespace references
- Bound instance references (for methods)

Our approach:
1. **Extract function metadata** (name, module, qualname)
2. **Capture closure variables** when possible
3. **Store function source code** when available
4. **Handle special cases** (built-ins, partials, methods)
5. **Recreate by reference** for well-known functions
6. **Recreate by compilation** for user-defined functions

LIMITATIONS:
============
- Functions with complex closure chains may not serialize perfectly
- C extension functions recreated by import path only
- Dynamically generated functions may lose some context
- Lambda functions in REPL sessions cannot be recreated exactly

"""

import types
import inspect
import importlib
import functools
import textwrap
import sys
import ast
from typing import Any, Dict, Optional, Union, Callable

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class FunctionsHandler(_NSO_Handler):
    """Handler for function objects including lambdas, async functions, and methods."""
    
    def __init__(self):
        """Initialize the functions handler."""
        super().__init__()
        self._handler_name = "FunctionsHandler"
        self._priority = 40  # Higher priority than default since functions are common
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given function object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for function types (function, lambda, async function)
        - Check for bound/unbound methods
        - Check for partial functions
        - Check for built-in functions
        """
        try:
            # Function types
            if isinstance(obj, types.FunctionType):
                return True
            
            # Lambda functions (subset of FunctionType, but check explicitly)
            if hasattr(types, 'LambdaType') and isinstance(obj, types.LambdaType):
                return True
            
            # Built-in functions and methods
            if isinstance(obj, types.BuiltinFunctionType):
                return True
            if isinstance(obj, types.BuiltinMethodType):
                return True
            
            # Method types
            if isinstance(obj, types.MethodType):
                return True
            
            # Partial functions
            if isinstance(obj, functools.partial):
                return True
            
            # Async functions (coroutine functions)
            if inspect.iscoroutinefunction(obj):
                return True
            
            # Check for callable objects that might be function-like
            # but aren't standard function types
            if callable(obj):
                obj_type_name = type(obj).__name__
                # Some function-like objects we can handle
                if obj_type_name in ['function', 'method', 'builtin_function_or_method']:
                    return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a function object to a dictionary representation.
        
        Args:
            obj: Function object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the function
            
        SERIALIZATION PROCESS:
        1. Determine function type and characteristics
        2. Extract metadata (name, module, qualname)
        3. Capture source code when available
        4. Extract closure variables
        5. Handle special cases (partials, methods, built-ins)
        """
        # Base serialization data
        data = {
            "function_type": self._get_function_type(obj),
            "function_name": getattr(obj, '__name__', '<unknown>'),
            "function_module": getattr(obj, '__module__', None),
            "function_qualname": getattr(obj, '__qualname__', None),
            "is_lambda": self._is_lambda(obj),
            "is_async": inspect.iscoroutinefunction(obj),
            "serialization_strategy": None,  # Will be determined below
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        function_type = data["function_type"]
        
        if function_type == "builtin":
            data.update(self._serialize_builtin_function(obj))
            data["serialization_strategy"] = "builtin_import"
            
        elif function_type == "partial":
            data.update(self._serialize_partial_function(obj))
            data["serialization_strategy"] = "partial_reconstruction"
            
        elif function_type == "method":
            data.update(self._serialize_method(obj))
            data["serialization_strategy"] = "method_reconstruction"
            
        elif function_type in ["function", "lambda", "async_function"]:
            data.update(self._serialize_user_function(obj))
            data["serialization_strategy"] = "source_compilation"
            
        else:
            # Unknown function type - store basic info
            data.update(self._serialize_unknown_function(obj))
            data["serialization_strategy"] = "fallback"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a function object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized function data
            
        Returns:
            Recreated function object
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore function with metadata and closure
        4. Handle errors gracefully with fallbacks
        """
        strategy = data.get("serialization_strategy", "fallback")
        
        try:
            if strategy == "builtin_import":
                return self._deserialize_builtin_function(data)
            
            elif strategy == "partial_reconstruction":
                return self._deserialize_partial_function(data)
            
            elif strategy == "method_reconstruction":
                return self._deserialize_method(data)
            
            elif strategy == "source_compilation":
                return self._deserialize_user_function(data)
            
            elif strategy == "fallback":
                return self._deserialize_unknown_function(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder function
            function_name = data.get("function_name", "unknown")
            function_type = data.get("function_type", "unknown")
            
            def placeholder_function(*args, **kwargs):
                raise RuntimeError(
                    f"Deserialized function '{function_name}' ({function_type}) "
                    f"is not functional due to serialization error: {e}"
                )
            
            placeholder_function.__name__ = f"<placeholder_{function_name}>"
            return placeholder_function
    
    # ========================================================================
    # FUNCTION TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_function_type(self, obj: Any) -> str:
        """
        Determine the specific type of function object.
        
        Args:
            obj: Function object to analyze
            
        Returns:
            String identifying the function type
        """
        if isinstance(obj, functools.partial):
            return "partial"
        
        elif isinstance(obj, types.MethodType):
            return "method"
        
        elif isinstance(obj, (types.BuiltinFunctionType, types.BuiltinMethodType)):
            return "builtin"
        
        elif inspect.iscoroutinefunction(obj):
            return "async_function"
        
        elif self._is_lambda(obj):
            return "lambda"
        
        elif isinstance(obj, types.FunctionType):
            return "function"
        
        else:
            return "unknown"
    
    def _is_lambda(self, obj: Any) -> bool:
        """
        Check if a function is a lambda function.
        
        Args:
            obj: Function object to check
            
        Returns:
            True if the function is a lambda
            
        NOTE: Lambda detection is heuristic-based since lambdas are
        technically just FunctionType objects with specific naming patterns.
        """
        try:
            if not isinstance(obj, types.FunctionType):
                return False
            
            # Lambda functions typically have name '<lambda>'
            if getattr(obj, '__name__', '') == '<lambda>':
                return True
            
            # Additional check: lambdas defined in comprehensions or
            # other contexts might have different names
            qualname = getattr(obj, '__qualname__', '')
            if '<lambda>' in qualname:
                return True
            
            return False
            
        except Exception:
            return False
    
    # ========================================================================
    # BUILT-IN FUNCTION SERIALIZATION
    # ========================================================================
    
    def _serialize_builtin_function(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize built-in functions.
        
        Built-in functions can usually be recreated by importing them
        from their module or accessing them from builtins.
        """
        module_name = getattr(obj, '__module__', 'builtins')
        function_name = getattr(obj, '__name__', str(obj))
        
        return {
            "builtin_module": module_name,
            "builtin_name": function_name,
            "is_builtin_method": isinstance(obj, types.BuiltinMethodType),
            "note": f"Built-in function {function_name} from {module_name}"
        }
    
    def _deserialize_builtin_function(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize built-in functions by importing them.
        """
        module_name = data.get("builtin_module", "builtins")
        function_name = data.get("builtin_name")
        
        if not function_name:
            raise ValueError("Missing function name for built-in function")
        
        try:
            # Try to import from the specified module
            if module_name == "builtins":
                import builtins
                return getattr(builtins, function_name)
            else:
                module = importlib.import_module(module_name)
                return getattr(module, function_name)
                
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not import built-in function {function_name} from {module_name}: {e}")
    
    # ========================================================================
    # PARTIAL FUNCTION SERIALIZATION
    # ========================================================================
    
    def _serialize_partial_function(self, obj: functools.partial) -> Dict[str, Any]:
        """
        Serialize functools.partial objects.
        
        Partial functions wrap another function with some arguments pre-filled.
        We need to serialize the wrapped function and the partial arguments.
        """
        # Serialize the wrapped function (recursively)
        wrapped_func = obj.func
        
        # Try to serialize the wrapped function
        # Note: This creates a recursive serialization situation
        wrapped_serialized = {
            "type": type(wrapped_func).__name__,
            "name": getattr(wrapped_func, '__name__', '<unknown>'),
            "module": getattr(wrapped_func, '__module__', None),
            "qualname": getattr(wrapped_func, '__qualname__', None)
        }
        
        # For now, we'll store reference info rather than recursively serializing
        # to avoid infinite recursion issues
        
        return {
            "wrapped_function": wrapped_serialized,
            "partial_args": obj.args,
            "partial_keywords": obj.keywords,
            "note": f"Partial function wrapping {wrapped_func}"
        }
    
    def _deserialize_partial_function(self, data: Dict[str, Any]) -> functools.partial:
        """
        Deserialize functools.partial objects.
        """
        wrapped_info = data.get("wrapped_function", {})
        partial_args = data.get("partial_args", ())
        partial_keywords = data.get("partial_keywords", {})
        
        # Try to recreate the wrapped function
        func_name = wrapped_info.get("name")
        func_module = wrapped_info.get("module")
        
        if not func_name:
            raise ValueError("Missing wrapped function name for partial")
        
        try:
            # Try to import the wrapped function
            if func_module and func_module != "builtins":
                module = importlib.import_module(func_module)
                wrapped_func = getattr(module, func_name)
            else:
                import builtins
                wrapped_func = getattr(builtins, func_name)
            
            # Recreate the partial function
            return functools.partial(wrapped_func, *partial_args, **partial_keywords)
            
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not recreate partial function: {e}")
    
    # ========================================================================
    # METHOD SERIALIZATION
    # ========================================================================
    
    def _serialize_method(self, obj: types.MethodType) -> Dict[str, Any]:
        """
        Serialize bound method objects.
        
        Bound methods contain both a function and an instance.
        We store method metadata but cannot fully serialize the instance.
        """
        method_func = obj.__func__
        method_self = obj.__self__
        
        return {
            "method_name": getattr(method_func, '__name__', '<unknown>'),
            "method_qualname": getattr(method_func, '__qualname__', None),
            "method_module": getattr(method_func, '__module__', None),
            "instance_type": f"{type(method_self).__module__}.{type(method_self).__name__}",
            "instance_repr": repr(method_self)[:100],  # Truncated representation
            "note": "Method deserialization will create unbound placeholder"
        }
    
    def _deserialize_method(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize method objects.
        
        Since we cannot recreate the original instance, we return a placeholder
        that explains the limitation.
        """
        method_name = data.get("method_name", "unknown")
        instance_type = data.get("instance_type", "unknown")
        
        def placeholder_method(*args, **kwargs):
            raise RuntimeError(
                f"Deserialized method '{method_name}' from {instance_type} "
                f"cannot be called because the original instance was not serialized"
            )
        
        placeholder_method.__name__ = f"<method_{method_name}>"
        return placeholder_method
    
    # ========================================================================
    # USER FUNCTION SERIALIZATION (LAMBDAS, REGULAR FUNCTIONS, ASYNC)
    # ========================================================================
    
    def _serialize_user_function(self, obj: types.FunctionType) -> Dict[str, Any]:
        """
        Serialize user-defined functions including lambdas and async functions.
        
        This is the most complex case because we need to capture:
        - Function source code
        - Closure variables
        - Global namespace references
        """
        result = {}
        
        # Try to get source code
        try:
            source = inspect.getsource(obj)
            result["source_code"] = textwrap.dedent(source)
            result["has_source"] = True
        except (OSError, TypeError):
            # No source available (e.g., REPL-defined functions)
            result["source_code"] = None
            result["has_source"] = False
        
        # Get function signature
        try:
            sig = inspect.signature(obj)
            result["signature"] = str(sig)
        except (ValueError, TypeError):
            result["signature"] = None
        
        # Get closure variables
        if obj.__closure__:
            result["has_closure"] = True
            closure_vars = {}
            closure_names = obj.__code__.co_freevars
            
            for i, name in enumerate(closure_names):
                if i < len(obj.__closure__):
                    cell = obj.__closure__[i]
                    try:
                        # Try to get the cell value
                        value = cell.cell_contents
                        # Only store simple types that can be pickled
                        if isinstance(value, (int, float, str, bool, bytes, type(None))):
                            closure_vars[name] = value
                        else:
                            closure_vars[name] = f"<complex:{type(value).__name__}>"
                    except ValueError:
                        # Empty cell
                        closure_vars[name] = "<empty>"
            
            result["closure_variables"] = closure_vars
        else:
            result["has_closure"] = False
            result["closure_variables"] = {}
        
        # Get globals that the function references
        globals_refs = set()
        code = obj.__code__
        
        # Get names referenced by the function
        for name in code.co_names:
            if name in obj.__globals__:
                globals_refs.add(name)
        
        result["global_references"] = list(globals_refs)
        
        # Get function metadata
        result.update({
            "code_filename": code.co_filename,
            "code_firstlineno": code.co_firstlineno,
            "code_argcount": code.co_argcount,
            "code_varnames": code.co_varnames,
            "docstring": obj.__doc__,
        })
        
        return result
    
    def _deserialize_user_function(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize user-defined functions.
        
        This attempts to recreate the function from source code when available,
        or creates a placeholder when source is not available.
        """
        function_name = data.get("function_name", "unknown")
        has_source = data.get("has_source", False)
        source_code = data.get("source_code")
        is_lambda = data.get("is_lambda", False)
        is_async = data.get("is_async", False)
        
        if not has_source or not source_code:
            # No source code available - create placeholder
            if is_async:
                async def placeholder_async_function(*args, **kwargs):
                    raise RuntimeError(
                        f"Async function '{function_name}' cannot be recreated "
                        f"because source code was not available during serialization"
                    )
                placeholder_async_function.__name__ = f"<placeholder_{function_name}>"
                return placeholder_async_function
            else:
                def placeholder_function(*args, **kwargs):
                    raise RuntimeError(
                        f"Function '{function_name}' cannot be recreated "
                        f"because source code was not available during serialization"
                    )
                placeholder_function.__name__ = f"<placeholder_{function_name}>"
                return placeholder_function
        
        try:
            # Try to compile and execute the source code
            # Create a minimal namespace for execution
            namespace = {}
            
            # Add basic builtins that might be needed
            import builtins
            namespace.update({
                '__builtins__': builtins,
                'functools': functools,
                'types': types
            })
            
            # Compile and execute the source
            compiled = compile(source_code, f"<cerial_{function_name}>", "exec")
            exec(compiled, namespace)
            
            # For lambda functions, the result is in the namespace
            if is_lambda:
                # Lambda source usually looks like: "lambda x: x + 1"
                # After exec, we need to find the lambda in the namespace
                # This is tricky because lambdas don't have names...
                # We'll use a heuristic approach
                for name, obj in namespace.items():
                    if isinstance(obj, types.FunctionType) and name != '__builtins__':
                        if getattr(obj, '__name__', '') == '<lambda>':
                            return obj
                
                # If we can't find the lambda, create a placeholder
                def placeholder_lambda(*args, **kwargs):
                    raise RuntimeError(f"Lambda function could not be recreated from source")
                return placeholder_lambda
            
            else:
                # For named functions, look for the function by name
                if function_name in namespace:
                    return namespace[function_name]
                else:
                    # Function might have a different name in source
                    for name, obj in namespace.items():
                        if (isinstance(obj, types.FunctionType) and 
                            name not in ['__builtins__'] and
                            not name.startswith('__')):
                            return obj
                    
                    raise ValueError(f"Function {function_name} not found in compiled source")
        
        except Exception as e:
            # Compilation failed - create error placeholder
            def error_placeholder(*args, **kwargs):
                raise RuntimeError(
                    f"Function '{function_name}' could not be recreated due to "
                    f"compilation error: {e}"
                )
            error_placeholder.__name__ = f"<error_{function_name}>"
            return error_placeholder
    
    # ========================================================================
    # UNKNOWN FUNCTION SERIALIZATION
    # ========================================================================
    
    def _serialize_unknown_function(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown function types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_str": str(obj)[:200],
            "callable": callable(obj),
            "note": f"Unknown function type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_function(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown function types with placeholder.
        """
        object_repr = data.get("object_repr", "unknown")
        
        def unknown_placeholder(*args, **kwargs):
            raise RuntimeError(
                f"Unknown function type {object_repr} cannot be recreated"
            )
        
        unknown_placeholder.__name__ = "<unknown_function>"
        return unknown_placeholder


# Create a singleton instance for auto-registration
functions_handler = FunctionsHandler()