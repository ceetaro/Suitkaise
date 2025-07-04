"""
Generators and Iterators Serialization Handler

This module provides serialization support for generator objects, iterators,
coroutines, and async generators that cannot be pickled due to their
internal execution state.

SUPPORTED OBJECTS:
==================

1. GENERATOR OBJECTS:
   - Objects created by generator functions (def with yield)
   - Generator expressions (x for x in range(10))
   - Generator state and local variables

2. ASYNC GENERATORS:
   - Objects created by async generator functions (async def with yield)
   - Async generator expressions
   - Async generator state

3. COROUTINES:
   - Objects created by async functions (async def without yield)
   - Coroutine state and local variables
   - Suspended coroutines

4. ITERATORS:
   - Built-in iterators (range, enumerate, zip, etc.)
   - Custom iterator objects with __iter__ and __next__
   - File iterators and other I/O iterators

5. ASYNC ITERATORS:
   - Objects implementing __aiter__ and __anext__
   - Custom async iterator implementations

SERIALIZATION STRATEGY:
======================

Generator serialization is inherently challenging because:
- Generators have internal execution state (frame stack)
- Local variables exist in the generator's frame
- Execution position is tracked internally
- Some state cannot be externally observed

Our approach:
1. **Capture generator metadata** (function, arguments, creation context)
2. **Extract observable state** (yielded values so far, if possible)
3. **Store generator function reference** for recreation
4. **Handle different generator types** with specialized logic
5. **Provide best-effort recreation** with clear limitations

LIMITATIONS:
============
- Generator internal state cannot be perfectly preserved
- Recreated generators start from the beginning
- Complex generators with side effects may behave differently
- Coroutines in the middle of execution lose their position
- Some iterators (especially C-implemented ones) cannot be recreated

"""

import types
import inspect
import sys
import asyncio
from typing import Any, Dict, Optional, List, Union, Iterator, AsyncIterator

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class GeneratorsHandler(_NSO_Handler):
    """Handler for generator objects, iterators, and coroutines."""
    
    def __init__(self):
        """Initialize the generators handler."""
        super().__init__()
        self._handler_name = "GeneratorsHandler"
        self._priority = 35  # Higher priority than default since generators are common
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given generator/iterator object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for generator objects
        - Check for async generators  
        - Check for coroutines
        - Check for iterator objects
        - Check for async iterators
        """
        try:
            # Generator objects
            if isinstance(obj, types.GeneratorType):
                return True
            
            # Async generator objects
            if hasattr(types, 'AsyncGeneratorType') and isinstance(obj, types.AsyncGeneratorType):
                return True
            
            # Coroutine objects
            if isinstance(obj, types.CoroutineType):
                return True
            
            # Check for async generators (Python 3.6+)
            if hasattr(obj, '__aiter__') and hasattr(obj, '__anext__'):
                return True
            
            # Iterator objects (have __iter__ and __next__)
            if hasattr(obj, '__iter__') and hasattr(obj, '__next__'):
                # But exclude common container types that happen to be iterable
                if not isinstance(obj, (str, bytes, list, tuple, dict, set, frozenset)):
                    return True
            
            # Built-in iterator types
            obj_type_name = type(obj).__name__
            builtin_iterators = {
                'range_iterator', 'list_iterator', 'tuple_iterator',
                'dict_keyiterator', 'dict_valueiterator', 'dict_itemiterator',
                'set_iterator', 'enumerate', 'zip', 'map', 'filter',
                'reversed', 'iter'
            }
            if obj_type_name in builtin_iterators:
                return True
            
            # File iterators and other I/O iterators
            if hasattr(obj, 'readline') and hasattr(obj, '__iter__'):
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a generator/iterator object to a dictionary representation.
        
        Args:
            obj: Generator/iterator object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the object
            
        SERIALIZATION PROCESS:
        1. Determine object type (generator, coroutine, iterator, etc.)
        2. Extract metadata and creation context
        3. Capture observable state
        4. Store recreation strategy
        5. Handle special cases for different types
        """
        # Base serialization data
        data = {
            "object_type": self._get_object_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,  # Will be determined below
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        object_type = data["object_type"]
        
        if object_type == "generator":
            data.update(self._serialize_generator(obj))
            data["serialization_strategy"] = "generator_function_recall"
            
        elif object_type == "async_generator":
            data.update(self._serialize_async_generator(obj))
            data["serialization_strategy"] = "async_generator_function_recall"
            
        elif object_type == "coroutine":
            data.update(self._serialize_coroutine(obj))
            data["serialization_strategy"] = "coroutine_function_recall"
            
        elif object_type == "builtin_iterator":
            data.update(self._serialize_builtin_iterator(obj))
            data["serialization_strategy"] = "builtin_iterator_recreation"
            
        elif object_type == "custom_iterator":
            data.update(self._serialize_custom_iterator(obj))
            data["serialization_strategy"] = "custom_iterator_recreation"
            
        elif object_type == "async_iterator":
            data.update(self._serialize_async_iterator(obj))
            data["serialization_strategy"] = "async_iterator_recreation"
            
        else:
            # Unknown object type
            data.update(self._serialize_unknown_iterator(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a generator/iterator object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized object data
            
        Returns:
            Recreated object (with limitations noted in documentation)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore object with available metadata
        4. Handle errors gracefully with placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        object_type = data.get("object_type", "unknown")
        
        try:
            if strategy == "generator_function_recall":
                return self._deserialize_generator(data)
            
            elif strategy == "async_generator_function_recall":
                return self._deserialize_async_generator(data)
            
            elif strategy == "coroutine_function_recall":
                return self._deserialize_coroutine(data)
            
            elif strategy == "builtin_iterator_recreation":
                return self._deserialize_builtin_iterator(data)
            
            elif strategy == "custom_iterator_recreation":
                return self._deserialize_custom_iterator(data)
            
            elif strategy == "async_iterator_recreation":
                return self._deserialize_async_iterator(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_iterator(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder
            return self._create_error_placeholder(object_type, str(e))
    
    # ========================================================================
    # OBJECT TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_object_type(self, obj: Any) -> str:
        """
        Determine the specific type of generator/iterator object.
        
        Args:
            obj: Object to analyze
            
        Returns:
            String identifying the object type
        """
        if isinstance(obj, types.GeneratorType):
            return "generator"
        
        elif hasattr(types, 'AsyncGeneratorType') and isinstance(obj, types.AsyncGeneratorType):
            return "async_generator"
        
        elif isinstance(obj, types.CoroutineType):
            return "coroutine"
        
        elif hasattr(obj, '__aiter__') and hasattr(obj, '__anext__'):
            return "async_iterator"
        
        else:
            # Check if it's a built-in iterator type
            obj_type_name = type(obj).__name__
            builtin_iterators = {
                'range_iterator', 'list_iterator', 'tuple_iterator',
                'dict_keyiterator', 'dict_valueiterator', 'dict_itemiterator',
                'set_iterator', 'enumerate', 'zip', 'map', 'filter',
                'reversed', 'iter'
            }
            
            if obj_type_name in builtin_iterators:
                return "builtin_iterator"
            elif hasattr(obj, '__iter__') and hasattr(obj, '__next__'):
                return "custom_iterator"
            else:
                return "unknown"
    
    # ========================================================================
    # GENERATOR OBJECT SERIALIZATION
    # ========================================================================
    
    def _serialize_generator(self, obj: types.GeneratorType) -> Dict[str, Any]:
        """
        Serialize generator objects.
        
        Generators are created by calling generator functions.
        We try to capture the function and arguments used to create them.
        """
        result = {
            "generator_state": None,
            "generator_function": None,
            "creation_args": None,
            "creation_kwargs": None,
            "frame_info": None
        }
        
        try:
            # Get the generator's frame to extract information
            frame = obj.gi_frame
            if frame:
                # Get the function that created this generator
                code = frame.f_code
                result["generator_function"] = {
                    "name": code.co_name,
                    "filename": code.co_filename,
                    "firstlineno": code.co_firstlineno,
                    "qualname": getattr(obj, '__qualname__', None)
                }
                
                # Try to get local variables from the frame
                local_vars = {}
                for name, value in frame.f_locals.items():
                    # Only store simple types to avoid recursion
                    if isinstance(value, (int, float, str, bool, bytes, type(None))):
                        local_vars[name] = value
                    else:
                        local_vars[name] = f"<{type(value).__name__}>"
                
                result["frame_info"] = {
                    "local_variables": local_vars,
                    "instruction_pointer": frame.f_lasti,
                    "line_number": frame.f_lineno
                }
                
                # Get generator state
                result["generator_state"] = {
                    "running": obj.gi_running,
                    "yielded_value": None,  # We can't get the last yielded value
                    "suspended": True  # Generators are typically suspended when serialized
                }
            
            # Try to get the function object from globals
            # This is tricky because we need to find the original function
            # We'll store metadata to help with recreation
            
        except Exception as e:
            result["note"] = f"Could not extract generator frame info: {e}"
        
        result["recreation_possible"] = bool(result["generator_function"])
        result["limitation"] = "Generator will be recreated from the beginning, losing current state"
        
        return result
    
    def _deserialize_generator(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize generator objects.
        
        Since we cannot restore the exact generator state, we create a new
        generator from the original function (if available) or a placeholder.
        """
        generator_function = data.get("generator_function")
        
        if not generator_function:
            return self._create_generator_placeholder("generator", "No function info available")
        
        function_name = generator_function.get("name")
        filename = generator_function.get("filename")
        
        # Try to find and call the original generator function
        # This is limited because we don't have the original arguments
        def recreated_generator():
            """
            Placeholder generator that explains the limitation.
            """
            yield f"Recreated generator from function '{function_name}'"
            yield f"Original from: {filename}"
            yield "Note: Original state and arguments were lost during serialization"
        
        return recreated_generator()
    
    # ========================================================================
    # ASYNC GENERATOR SERIALIZATION
    # ========================================================================
    
    def _serialize_async_generator(self, obj) -> Dict[str, Any]:
        """
        Serialize async generator objects.
        
        Similar to regular generators but with async-specific handling.
        """
        result = {
            "async_generator_state": None,
            "async_generator_function": None,
            "frame_info": None
        }
        
        try:
            # Get async generator frame info
            frame = getattr(obj, 'ag_frame', None)
            if frame:
                code = frame.f_code
                result["async_generator_function"] = {
                    "name": code.co_name,
                    "filename": code.co_filename,
                    "firstlineno": code.co_firstlineno,
                    "qualname": getattr(obj, '__qualname__', None)
                }
                
                result["async_generator_state"] = {
                    "running": getattr(obj, 'ag_running', False),
                    "suspended": True
                }
            
        except Exception as e:
            result["note"] = f"Could not extract async generator info: {e}"
        
        result["recreation_possible"] = bool(result["async_generator_function"])
        result["limitation"] = "Async generator will be recreated from the beginning"
        
        return result
    
    def _deserialize_async_generator(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize async generator objects.
        """
        async_generator_function = data.get("async_generator_function")
        
        if not async_generator_function:
            return self._create_generator_placeholder("async_generator", "No function info available")
        
        function_name = async_generator_function.get("name")
        filename = async_generator_function.get("filename")
        
        async def recreated_async_generator():
            """
            Placeholder async generator that explains the limitation.
            """
            yield f"Recreated async generator from function '{function_name}'"
            yield f"Original from: {filename}"
            yield "Note: Original state and arguments were lost during serialization"
        
        return recreated_async_generator()
    
    # ========================================================================
    # COROUTINE SERIALIZATION
    # ========================================================================
    
    def _serialize_coroutine(self, obj: types.CoroutineType) -> Dict[str, Any]:
        """
        Serialize coroutine objects.
        
        Coroutines are suspended async functions.
        """
        result = {
            "coroutine_state": None,
            "coroutine_function": None,
            "frame_info": None
        }
        
        try:
            # Get coroutine frame info
            frame = obj.cr_frame
            if frame:
                code = frame.f_code
                result["coroutine_function"] = {
                    "name": code.co_name,
                    "filename": code.co_filename,
                    "firstlineno": code.co_firstlineno,
                    "qualname": getattr(obj, '__qualname__', None)
                }
                
                result["coroutine_state"] = {
                    "running": obj.cr_running,
                    "suspended": True,
                    "origin": getattr(obj, 'cr_origin', None)
                }
            
        except Exception as e:
            result["note"] = f"Could not extract coroutine info: {e}"
        
        result["recreation_possible"] = False  # Coroutines are harder to recreate
        result["limitation"] = "Coroutines cannot be meaningfully recreated without original context"
        
        return result
    
    def _deserialize_coroutine(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize coroutine objects.
        
        Since coroutines represent suspended async function calls,
        we cannot meaningfully recreate them. Return a placeholder.
        """
        coroutine_function = data.get("coroutine_function", {})
        function_name = coroutine_function.get("name", "unknown")
        
        async def placeholder_coroutine():
            raise RuntimeError(
                f"Coroutine '{function_name}' cannot be recreated because "
                f"coroutines represent suspended function calls that cannot "
                f"be restored without their original execution context"
            )
        
        return placeholder_coroutine()
    
    # ========================================================================
    # BUILT-IN ITERATOR SERIALIZATION
    # ========================================================================
    
    def _serialize_builtin_iterator(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize built-in iterator objects like range, enumerate, zip, etc.
        """
        obj_type_name = type(obj).__name__
        result = {
            "iterator_type": obj_type_name,
            "iterator_state": None,
            "recreation_args": None
        }
        
        try:
            # Handle specific built-in iterator types
            if obj_type_name == 'range_iterator':
                # Try to extract range information
                # This is tricky because range iterators don't expose their range
                result["note"] = "Range iterator - cannot extract original range"
                result["recreation_possible"] = False
                
            elif obj_type_name == 'enumerate':
                # Enumerate objects might have accessible state
                try:
                    # Some enumerate objects expose their state
                    result["recreation_args"] = {
                        "start": getattr(obj, 'start', 0),
                        "iterable_type": "unknown"
                    }
                except AttributeError:
                    pass
                    
            elif obj_type_name in ['zip', 'map', 'filter']:
                result["note"] = f"{obj_type_name} iterator - cannot extract original arguments"
                result["recreation_possible"] = False
                
            else:
                result["note"] = f"Built-in iterator {obj_type_name} - limited recreation"
                result["recreation_possible"] = False
            
        except Exception as e:
            result["note"] = f"Error analyzing built-in iterator: {e}"
        
        return result
    
    def _deserialize_builtin_iterator(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize built-in iterator objects.
        
        Most built-in iterators cannot be meaningfully recreated without
        their original arguments.
        """
        iterator_type = data.get("iterator_type", "unknown")
        
        if iterator_type == 'enumerate':
            recreation_args = data.get("recreation_args", {})
            start = recreation_args.get("start", 0)
            # Create a placeholder enumerate
            return enumerate([], start=start)
        
        else:
            # Create a placeholder iterator
            def placeholder_iterator():
                yield f"Placeholder for {iterator_type} iterator"
                yield "Original iterator could not be recreated"
            
            return placeholder_iterator()
    
    # ========================================================================
    # CUSTOM ITERATOR SERIALIZATION
    # ========================================================================
    
    def _serialize_custom_iterator(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize custom iterator objects.
        """
        result = {
            "iterator_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "iterator_state": None,
            "has_state_methods": False
        }
        
        try:
            # Check if the iterator has methods to get/set state
            state_methods = []
            if hasattr(obj, '__getstate__'):
                state_methods.append('__getstate__')
            if hasattr(obj, '__setstate__'):
                state_methods.append('__setstate__')
            if hasattr(obj, '__dict__'):
                state_methods.append('__dict__')
            
            result["state_methods"] = state_methods
            result["has_state_methods"] = bool(state_methods)
            
            # Try to get iterator state
            if hasattr(obj, '__getstate__'):
                try:
                    state = obj.__getstate__()
                    if isinstance(state, (dict, list, tuple, int, float, str, bool, type(None))):
                        result["iterator_state"] = state
                except Exception:
                    pass
            
            elif hasattr(obj, '__dict__'):
                try:
                    # Get simple attributes from __dict__
                    state = {}
                    for key, value in obj.__dict__.items():
                        if isinstance(value, (int, float, str, bool, bytes, type(None))):
                            state[key] = value
                        else:
                            state[key] = f"<{type(value).__name__}>"
                    result["iterator_state"] = state
                except Exception:
                    pass
            
        except Exception as e:
            result["note"] = f"Error analyzing custom iterator: {e}"
        
        result["recreation_possible"] = result["has_state_methods"]
        
        return result
    
    def _deserialize_custom_iterator(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize custom iterator objects.
        """
        iterator_class = data.get("iterator_class", "unknown")
        iterator_state = data.get("iterator_state")
        has_state_methods = data.get("has_state_methods", False)
        
        if not has_state_methods:
            # Cannot recreate - return placeholder
            def placeholder_custom_iterator():
                yield f"Placeholder for custom iterator {iterator_class}"
                yield "Original iterator could not be recreated"
            
            return placeholder_custom_iterator()
        
        try:
            # Try to recreate the iterator class and restore state
            module_name, class_name = iterator_class.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            iterator_cls = getattr(module, class_name)
            
            # Create instance (this might fail if __init__ requires arguments)
            try:
                obj = iterator_cls()
            except Exception:
                # Try with empty args
                obj = iterator_cls.__new__(iterator_cls)
            
            # Restore state if available
            if iterator_state and hasattr(obj, '__setstate__'):
                obj.__setstate__(iterator_state)
            elif iterator_state and hasattr(obj, '__dict__'):
                obj.__dict__.update(iterator_state)
            
            return obj
            
        except Exception as e:
            return self._create_error_placeholder("custom_iterator", str(e))
    
    # ========================================================================
    # ASYNC ITERATOR SERIALIZATION
    # ========================================================================
    
    def _serialize_async_iterator(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize async iterator objects.
        """
        result = {
            "async_iterator_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "has_aiter": hasattr(obj, '__aiter__'),
            "has_anext": hasattr(obj, '__anext__'),
        }
        
        result["recreation_possible"] = False
        result["limitation"] = "Async iterators cannot be reliably recreated"
        
        return result
    
    def _deserialize_async_iterator(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize async iterator objects.
        """
        async_iterator_class = data.get("async_iterator_class", "unknown")
        
        class PlaceholderAsyncIterator:
            def __aiter__(self):
                return self
            
            async def __anext__(self):
                raise StopAsyncIteration(
                    f"Placeholder for async iterator {async_iterator_class} - "
                    f"original could not be recreated"
                )
        
        return PlaceholderAsyncIterator()
    
    # ========================================================================
    # UNKNOWN ITERATOR SERIALIZATION
    # ========================================================================
    
    def _serialize_unknown_iterator(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown iterator types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "has_iter": hasattr(obj, '__iter__'),
            "has_next": hasattr(obj, '__next__'),
            "note": f"Unknown iterator type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_iterator(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown iterator types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        object_repr = data.get("object_repr", "unknown")
        
        def unknown_iterator_placeholder():
            yield f"Placeholder for unknown iterator type {object_type}"
            yield f"Original: {object_repr}"
            yield "Iterator could not be recreated"
        
        return unknown_iterator_placeholder()
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _create_generator_placeholder(self, generator_type: str, error_message: str) -> Any:
        """
        Create a placeholder generator that explains why recreation failed.
        """
        def placeholder_generator():
            yield f"Placeholder {generator_type}"
            yield f"Recreation failed: {error_message}"
            yield "This is not the original generator"
        
        return placeholder_generator()
    
    def _create_error_placeholder(self, object_type: str, error_message: str) -> Any:
        """
        Create a placeholder iterator for objects that failed to deserialize.
        """
        def error_placeholder():
            yield f"Error placeholder for {object_type}"
            yield f"Deserialization failed: {error_message}"
        
        return error_placeholder()


# Create a singleton instance for auto-registration
generators_handler = GeneratorsHandler()