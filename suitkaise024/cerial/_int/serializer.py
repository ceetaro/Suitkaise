# Central Serializer for Cerial
#
# PLAN - What needs to be accomplished:
#
# TOP LEVEL (serialize function):
# 1. reset all tracking state (circular reference tracker, depth counter, etc)
# 2. call the recursive serializer to build the intermediate representation
# 3. use pickle.dumps() to convert the IR to bytes
# 4. return the bytes
#
# RECURSIVE LEVEL (_serialize_recursive function):
# 0. check recursion depth hasn't exceeded safety limit
#
# 1. check if we've already serialized this exact object (circular reference check)
#    - if yes: return a reference marker pointing to the already-serialized version
#    - if no: mark this object as seen and continue
#
# 2. check if base pickle can handle this object type natively
#    - if primitive (int, str, None, etc): return as-is
#    - if collection (dict, list, tuple, set, frozenset): recursively serialize the CONTENTS
#      (this is important - we handle the container but need to process what's inside)
#
# 3. object is complex - find the right handler for it
#    - if no handler found: try pickle anyway as last resort, or error
#
# 4. use the handler to extract state from the object
#    - handler returns a dict/list of the object's state
#    - but this state might contain MORE complex objects!
#
# 5. recursively serialize the extracted state
#    - THIS IS THE KEY STEP!
#    - the handler gave us state that might have locks, loggers, nested objects
#    - we need to recursively process ALL of that until everything is pickle-native
#
# 6. wrap the now-fully-serialized state with metadata
#    - add type markers, handler info, object ID
#    - return this wrapped structure
#
# HELPER FUNCTIONS NEEDED:
# - check if object type is pickle-native
# - check if object type can be part of circular references
# - find the right handler for an object type
#
# FINAL RESULT:
# A nested dict/list structure where EVERYTHING is pickle-native
# (only dicts, lists, tuples, sets, ints, strings, bools, None, etc)
# No locks, no loggers, no complex objects - all converted to simple data
# Then pickle can serialize it to bytes

import pickle
from typing import Any, Dict, Optional
from .handlers import ALL_HANDLERS

class SerializationError(Exception):
    """Raised when serialization fails."""
    pass

class Cerializer:
    """
    Central serializer that coordinates object serialization.
    
    Maintains handler registry and recursively serializes objects,
    tracking circular references.
    """
    
    def __init__(self, debug: bool = False, verbose: bool = False):
        """
        Initialize serializer with handler registry and state tracking.
        
        Args:
            debug: Enable debug mode (more detailed error messages)
            verbose: Enable verbose mode (print serialization progress)
        """
        # Handler registry
        self.handlers = ALL_HANDLERS
        
        # Configuration
        self.debug = debug
        self.verbose = verbose
        
        # Handler cache: maps type -> handler (persists across serialize() calls)
        # Handlers are static, so caching by type is safe and avoids repeated lookups
        self._handler_cache: Dict[type, Optional[Any]] = {}
        
        # State tracking (reset for each serialize() call)
        self.seen_objects: Dict[int, Any] = {}
        self._serialization_depth = 0
        self._max_depth = 1000
        self._object_path: list = []  # Breadcrumb trail for error reporting
        
        # Debug tracking
        self._all_object_ids: set = set()  # All __object_id__ values added
        self._all_circular_refs: set = set()  # All __cerial_ref__ values created
        self._circular_ref_details: list = []  # (obj_id, type, path) for each circular ref
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize any Python object to bytes.
        
        Entry point that resets state, builds IR, and pickles it.
        
        Args:
            obj: Object to serialize
            
        Returns:
            bytes: Serialized representation
            
        Raises:
            SerializationError: If serialization fails
        """
        # Step 1: Reset state for fresh serialization
        self.seen_objects = {}
        self._serialization_depth = 0
        self._object_path = []
        self._all_object_ids = set()
        self._all_circular_refs = set()
        self._circular_ref_details = []
        
        if self.verbose:
            print(f"[CERIAL] Starting serialization of {type(obj).__name__}")
        
        # Step 2: Build intermediate representation (nested dicts/lists)
        try:
            ir = self._serialize_recursive(obj)
        except SerializationError:
            # Already a SerializationError with good message, just re-raise
            raise
        except Exception as e:
            # Unexpected error - wrap it
            path_str = " -> ".join(self._object_path) if self._object_path else "root"
            raise SerializationError(
                f"\n{'='*70}\n"
                f"SERIALIZATION FAILED\n"
                f"{'='*70}\n"
                f"Path: {path_str}\n"
                f"Type: {type(obj).__name__}\n"
                f"Error: {e}\n"
                f"{'='*70}"
            ) from e
        
        if self.verbose:
            print(f"[CERIAL] Built IR successfully, size: {len(str(ir))} chars")
        
        # Step 3: Use pickle to convert IR to bytes
        try:
            result = pickle.dumps(ir, protocol=pickle.HIGHEST_PROTOCOL)
            if self.verbose:
                print(f"[CERIAL] Serialization complete, bytes: {len(result)}")
            return result
        except Exception as e:
            raise SerializationError(
                f"\n{'='*70}\n"
                f"PICKLE FAILED ON IR\n"
                f"{'='*70}\n"
                f"The intermediate representation was built successfully,\n"
                f"but pickle.dumps() failed to serialize it.\n"
                f"This suggests the IR contains non-picklable objects.\n"
                f"This is a bug in a handler or the serializer.\n"
                f"\nError: {e}\n"
                f"{'='*70}"
            ) from e
    
    def _serialize_recursive(self, obj: Any) -> Any:
        """
        Recursively serialize object to intermediate representation.
        
        Converts object to nested dict/list structure of pickle-native types.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Intermediate representation (pickle-native nested structure)
        """
        # Fast path: Immutable primitives can skip ALL overhead
        # These types are never circular and pickle handles them natively
        # Place this FIRST to avoid depth/path tracking overhead
        if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
            return obj
        
        # Step 0: Check recursion depth for safety
        self._serialization_depth += 1
        if self._serialization_depth > self._max_depth:
            path_str = " -> ".join(self._object_path) if self._object_path else "root"
            raise RecursionError(
                f"Serialization depth exceeded {self._max_depth}.\n"
                f"Path: {path_str}\n"
                f"This indicates a circular reference or deeply nested structure."
            )
        
        # Add current object to breadcrumb trail
        obj_name = f"{type(obj).__name__}"
        if self.debug:
            obj_name += f"@{id(obj)}"
        self._object_path.append(obj_name)
        
        if self.verbose:
            # Show path context with color-coded levels
            # Take last 6 levels, truncate each to 10 chars, color code
            path_levels = self._object_path[-6:]
            
            # Color codes: red -> orange -> yellow -> green -> blue -> purple
            # Colors cycle based on actual depth, so depth 1,7,13 = red, 2,8,14 = orange, etc.
            colors = [
                "\033[91m",      # Red (depths 1, 7, 13, ...)
                "\033[38;5;208m", # Orange (depths 2, 8, 14, ...)
                "\033[93m",      # Yellow (depths 3, 9, 15, ...)
                "\033[92m",      # Green (depths 4, 10, 16, ...)
                "\033[94m",      # Blue (depths 5, 11, 17, ...)
                "\033[95m",      # Magenta/Purple (depths 6, 12, 18, ...)
            ]
            reset = "\033[0m"
            
            # Build colored path string
            colored_parts = []
            # Calculate actual depth for each displayed level
            total_levels = len(self._object_path)
            start_depth = total_levels - len(path_levels)  # Depth of first displayed level
            
            for i, level in enumerate(path_levels):
                # Truncate to 10 chars
                truncated = level[:10] if len(level) > 10 else level
                # Color based on actual depth (1-indexed, so depth 1 = colors[0])
                actual_depth = start_depth + i + 1
                color = colors[(actual_depth - 1) % 6]
                colored_parts.append(f"{color}{truncated}{reset}")
            
            path_str = " → ".join(colored_parts)
            if len(self._object_path) > 6:
                path_str = "... → " + path_str
            
            indent = "  " * min(self._serialization_depth, 5)  # Cap indent at 5 levels
            print(f"{indent}[{self._serialization_depth}] {path_str}")
        
        try:
            # Step 1: Check for circular references
            obj_id = id(obj)
            
            # Only track objects that can participate in circular refs
            if self._is_circular_capable(obj):
                if obj_id in self.seen_objects:
                    # Already serialized - return reference marker
                    self._all_circular_refs.add(obj_id)
                    path_str = " → ".join(self._object_path[-3:])
                    self._circular_ref_details.append((obj_id, type(obj).__name__, path_str))
                    return {"__cerial_ref__": obj_id}
                # Mark as seen
                self.seen_objects[obj_id] = obj
            
            # Step 2: Check if base pickle can handle natively
            if self._is_pickle_native(obj):
                # Step 2a: Primitives - check if they need __object_id__ (for circular refs)
                # Singletons and immutable primitives
                if obj is None or obj is Ellipsis or obj is NotImplemented:
                    # Check if circular ref
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cerial_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    return obj
                
                if isinstance(obj, (bool, int, float, complex, str, bytes, bytearray)):
                    # These are never circular (immutable primitives)
                    return obj
                
                if isinstance(obj, (range, slice)):
                    # Check if circular ref
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cerial_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    return obj
                
                # Step 2b: Collections - recursively serialize contents
                # BUT: Check for special collection types first (Counter, defaultdict, etc.)
                # These are dict/list subclasses but pickle handles them correctly
                if self._is_special_pickle_native(obj):
                    # Special collections types - return as-is (with object_id if needed)
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cerial_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    return obj
                
                elif isinstance(obj, dict):
                    # Fast path: if all keys and values are primitives, copy directly
                    if self._is_all_primitive_dict(obj):
                        # Direct copy - no recursion needed
                        result = {
                            "__cerial_type__": "dict",
                            "items": list(obj.items()),  # Direct copy
                        }
                        if obj_id in self.seen_objects:
                            result["__object_id__"] = obj_id
                            self._all_object_ids.add(obj_id)
                        return result
                    
                    # Slow path: recursively serialize BOTH keys and values
                    # Keys can be tuples/frozensets with complex objects inside
                    serialized_items = [
                        (self._serialize_recursive(k), self._serialize_recursive(v))
                        for k, v in obj.items()
                    ]
                    result = {
                        "__cerial_type__": "dict",
                        "items": serialized_items,
                    }
                    # Add object_id if this dict is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                elif isinstance(obj, list):
                    # Recursively serialize list items
                    # Lists come out as plain lists (not wrapped) unless they have circular refs
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    # If list is circular-capable, wrap it with metadata
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cerial_type__": "list",
                            "items": serialized_items,
                            "__object_id__": obj_id,
                        }
                    return serialized_items
                
                elif isinstance(obj, tuple):
                    # Recursively serialize tuple items
                    # Need special handling to preserve tuple type
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    result = {
                        "__cerial_type__": "tuple",
                        "items": serialized_items,
                    }
                    # Add object_id if this tuple is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                elif isinstance(obj, set):
                    # Recursively serialize set items
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    result = {
                        "__cerial_type__": "set",
                        "items": serialized_items,
                    }
                    # Add object_id if this set is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                elif isinstance(obj, frozenset):
                    # Recursively serialize frozenset items
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    result = {
                        "__cerial_type__": "frozenset",
                        "items": serialized_items,
                    }
                    # Add object_id if this frozenset is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                # Step 2c: Other pickle-native types (datetime, UUID, Decimal, Path, etc.)
                # These implement __reduce__ properly
                # BUT: if they're circular-capable and were seen, we need to track their ID
                else:
                    # Check if this object needs an __object_id__ (is in seen_objects)
                    if obj_id in self.seen_objects:
                        # Wrap with metadata to include __object_id__
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cerial_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    else:
                        # No circular refs, return as-is
                        return obj
            
            # Step 2.5: Check for simple instance fast path
            if self._is_simple_instance(obj):
                if self.verbose:
                    indent = "  " * min(self._serialization_depth, 5)
                    print(f"{indent}    ↳ Simple instance fast path")
                # Register object for circular reference support
                self.seen_objects[obj_id] = obj
                self._all_object_ids.add(obj_id)
                return {
                    "__cerial_type__": "simple_class_instance",
                    "__object_id__": obj_id,
                    "module": type(obj).__module__,
                    "qualname": type(obj).__qualname__,
                    "attrs": dict(obj.__dict__),  # Direct copy of primitive attrs
                }
            
            # Step 2.6: Check for pickle-native function fast path
            # Functions that can be imported by reference don't need cerial overhead
            # Just let pickle handle them with its efficient GLOBAL opcode
            if self._is_pickle_native_function(obj):
                if self.verbose:
                    indent = "  " * min(self._serialization_depth, 5)
                    print(f"{indent}    ↳ Pickle-native function (reference)")
                # Register object for circular reference support
                self.seen_objects[obj_id] = obj
                self._all_object_ids.add(obj_id)
                # Wrap in IR with object_id so deserializer can register it
                return {
                    "__cerial_type__": "pickle_native_func",
                    "__object_id__": obj_id,
                    "value": obj,
                }
            
            # Step 3: Find handler for complex object
            handler = self._find_handler(obj)
            
            if handler is None:
                # No handler found - try pickle as last resort
                try:
                    pickle.dumps(obj)
                    # If we get here, pickle can handle it
                    if self.verbose:
                        indent = "  " * min(self._serialization_depth, 5)
                        print(f"{indent}    ↳ Pickle native (no handler)")
                    
                    # Check if it needs __object_id__ (for circular refs)
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cerial_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    
                    return obj
                except Exception as pickle_err:
                    path_str = " -> ".join(self._object_path)
                    raise SerializationError(
                        f"\n{'='*70}\n"
                        f"NO HANDLER FOUND\n"
                        f"{'='*70}\n"
                        f"Path: {path_str}\n"
                        f"Type: {type(obj).__name__}\n"
                        f"Module: {type(obj).__module__}\n"
                        f"\nNo cerial handler exists for this type,\n"
                        f"and base pickle cannot serialize it either.\n"
                        f"\nPickle error: {pickle_err}\n"
                        f"{'='*70}"
                    ) from pickle_err
            
            if self.verbose:
                indent = "  " * min(self._serialization_depth, 5)
                print(f"{indent}    ↳ Handler: {handler.__class__.__name__}")
            
            # Step 4: Use handler to extract state
            try:
                state = handler.extract_state(obj)
            except Exception as e:
                path_str = " -> ".join(self._object_path)
                raise SerializationError(
                    f"\n{'='*70}\n"
                    f"HANDLER FAILED\n"
                    f"{'='*70}\n"
                    f"Path: {path_str}\n"
                    f"Handler: {handler.__class__.__name__}\n"
                    f"Object: {type(obj).__name__}\n"
                    f"\nThe handler failed to extract state from this object.\n"
                    f"\nError: {e}\n"
                    f"{'='*70}"
                ) from e
            
            # Step 5: RECURSIVELY serialize the extracted state
            # This is critical - the handler returns state that may contain complex objects
            serialized_state = self._serialize_recursive(state)
            
            # Step 6: Wrap in metadata
            # ALWAYS include object_id for handler objects - keeps things simple and consistent
            self._all_object_ids.add(obj_id)
            return {
                "__cerial_type__": handler.type_name,
                "__handler__": handler.__class__.__name__,
                "__object_id__": obj_id,
                "state": serialized_state,
            }
        
        finally:
            # Always clean up tracking state when exiting
            self._serialization_depth -= 1
            if self._object_path:
                self._object_path.pop()
    
    def _is_special_pickle_native(self, obj: Any) -> bool:
        """
        Check if object is a special pickle-native type that should not be decomposed.
        
        These are subclasses of basic collections (Counter, defaultdict, etc.) that
        pickle handles correctly and should be serialized as-is.
        """
        try:
            import collections
            
            if isinstance(obj, (
                collections.Counter,
                collections.defaultdict,
                collections.OrderedDict,
                collections.deque,
                collections.ChainMap
            )):
                return True
        except (ImportError, AttributeError):
            pass
        
        return False
    
    def _is_pickle_native(self, obj: Any) -> bool:
        """
        Check if object is natively supported by pickle.
        
        Returns True for primitives and collections that pickle handles.
        Note: Collection contents still need recursive processing!
        
        Args:
            obj: Object to check
            
        Returns:
            bool: True if pickle-native
        """
        # Check for special singletons
        if obj is None or obj is Ellipsis or obj is NotImplemented:
            return True
        
        # Check for basic primitive types
        if isinstance(obj, (bool, int, float, complex, str, bytes, bytearray)):
            return True
        
        # Check for collections (we'll recursively handle their contents)
        if isinstance(obj, (list, tuple, dict, set, frozenset)):
            return True
        
        # Check for other pickle-native types
        if isinstance(obj, (range, slice)):
            return True
        
        # Standard library pickle-native types (implement __reduce__ properly)
        try:
            import datetime
            import decimal
            import uuid
            import pathlib
            import collections
            import fractions
            
            # datetime module types
            if isinstance(obj, (datetime.datetime, datetime.date, datetime.time, datetime.timedelta)):
                return True
            
            # Numeric types
            if isinstance(obj, (decimal.Decimal, fractions.Fraction)):
                return True
            
            # UUID
            if isinstance(obj, uuid.UUID):
                return True
            
            # pathlib.Path and subclasses
            if isinstance(obj, pathlib.Path):
                return True
            
            # collections module types
            if isinstance(obj, (collections.defaultdict, collections.OrderedDict, 
                              collections.Counter, collections.deque, collections.ChainMap)):
                return True
        
        except ImportError:
            # Module not available, skip these checks
            pass
        
        return False
    
    def _is_circular_capable(self, obj: Any) -> bool:
        """
        Check if object can participate in circular references.
        
        Returns False for immutable primitives (int, str, etc).
        Returns True for collections and class instances.
        
        Args:
            obj: Object to check
            
        Returns:
            bool: True if object needs circular reference tracking
        """
        # Primitives never participate in circular references
        if isinstance(obj, (type(None), bool, int, float, complex, str, bytes)):
            return False
        
        # Immutable collections need tracking (can contain circular refs)
        if isinstance(obj, (tuple, frozenset)):
            return True
        
        # Everything else might have circular refs
        # (mutable collections, class instances, etc.)
        return True
    
    # Primitive types that can be directly copied without recursion
    _PRIMITIVE_TYPES = (type(None), bool, int, float, str, bytes)
    
    def _is_all_primitive_dict(self, d: dict) -> bool:
        """
        Check if dict contains only primitive keys and values.
        
        Used for fast path serialization - if all entries are primitives,
        we can copy the dict directly without recursion.
        
        Args:
            d: Dict to check
            
        Returns:
            bool: True if all keys and values are primitives
        """
        for key, value in d.items():
            # Check key
            if not isinstance(key, self._PRIMITIVE_TYPES):
                return False
            # Check value
            if not isinstance(value, self._PRIMITIVE_TYPES):
                return False
        return True
    
    def _is_simple_instance(self, obj: Any) -> bool:
        """
        Check if object is a "simple" class instance eligible for fast path.
        
        Simple instances have:
        - User-defined class (not built-in types)
        - Module-level class (no '<locals>' in qualname)
        - No __slots__ (uses __dict__)
        - No custom __serialize__ method
        - All attrs in __dict__ are primitives
        
        These can skip circular ref tracking and use flat IR.
        
        Args:
            obj: Object to check
            
        Returns:
            bool: True if simple instance eligible for fast path
        """
        import types
        import functools
        import sys
        
        obj_class = type(obj)
        module_name = obj_class.__module__
        
        # Exclude built-in types that have __dict__ but aren't user classes
        # These include: functions, modules, methods, code objects, etc.
        if module_name == 'builtins':
            return False
        
        # Exclude standard library modules - they have dedicated handlers
        # Simple instance fast path is only for user-defined classes
        stdlib_modules = {
            'functools', 'io', 'logging', 'threading', 'multiprocessing',
            'queue', 'collections', 'datetime', 'pathlib', 'uuid', 're',
            'sqlite3', 'tempfile', 'socket', 'ssl', 'http', 'urllib',
            'email', 'json', 'pickle', 'copy', 'weakref', 'abc', 'typing',
            'dataclasses', 'enum', 'decimal', 'fractions', 'numbers',
            'itertools', 'operator', 'contextlib', 'asyncio', 'concurrent',
        }
        # Check if module is in stdlib or is a submodule of stdlib
        top_module = module_name.split('.')[0]
        if top_module in stdlib_modules:
            return False
        
        # Also exclude _io (C implementation of io module)
        if module_name.startswith('_'):
            return False
        
        # Exclude function-like objects explicitly
        if isinstance(obj, (types.FunctionType, types.MethodType, types.ModuleType,
                           types.CodeType, types.BuiltinFunctionType, functools.partial)):
            return False
        
        # Must have __dict__
        if not hasattr(obj, '__dict__'):
            return False
        
        # Must not have __slots__ (complicates reconstruction)
        if hasattr(obj_class, '__slots__'):
            return False
        
        # Must be module-level class (can import by qualname)
        qualname = getattr(obj_class, '__qualname__', '')
        if '<locals>' in qualname:
            return False
        
        # Must not have custom serialization
        if hasattr(obj, '__serialize__'):
            return False
        
        # All attrs must be primitives
        try:
            obj_dict = obj.__dict__
            if not isinstance(obj_dict, dict):
                return False
            for value in obj_dict.values():
                if not isinstance(value, self._PRIMITIVE_TYPES):
                    return False
        except Exception:
            return False
        
        return True
    
    def _is_pickle_native_function(self, obj: Any) -> bool:
        """
        Check if object is a function that pickle can handle natively.
        
        Pickle can serialize module-level functions using its GLOBAL opcode,
        which just stores (module, qualname) - very efficient.
        
        Requirements for pickle-native functions:
        - Is a FunctionType (not builtin, not lambda)
        - Has __module__ and __qualname__
        - Not from __main__ (can't import __main__)
        - No '<locals>' in qualname (not a nested/closure function)
        - No closure (captured variables would need serialization)
        - Can actually be looked up and returns the same object
        
        Returns:
            bool: True if pickle can handle this function directly
        """
        import types
        
        # Must be a function
        if not isinstance(obj, types.FunctionType):
            return False
        
        # Lambdas can't be referenced by name
        if obj.__name__ == '<lambda>':
            return False
        
        # Must have module and qualname
        module_name = getattr(obj, '__module__', None)
        qualname = getattr(obj, '__qualname__', None)
        if not module_name or not qualname:
            return False
        
        # Can't import from __main__
        if module_name == '__main__':
            return False
        
        # Nested functions have '<locals>' in qualname
        if '<locals>' in qualname:
            return False
        
        # Closures have captured variables - need full serialization
        if obj.__closure__ is not None:
            return False
        
        # Verify we can actually look it up and get the same function
        try:
            import importlib
            module = importlib.import_module(module_name)
            
            # Navigate qualname (handles class methods like MyClass.method)
            looked_up = module
            for part in qualname.split('.'):
                looked_up = getattr(looked_up, part)
            
            # Must be the exact same function object
            if looked_up is not obj:
                return False
                
        except (ImportError, AttributeError, TypeError):
            return False
        
        return True
    
    def _serialize_simple_instance(self, obj: Any) -> dict:
        """
        Serialize a simple instance using flat IR format.
        
        Fast path that skips:
        - Circular reference tracking (primitives can't have circular refs)
        - Recursive serialization (attrs are all primitives)
        - Handler lookup (we know how to handle it)
        
        Args:
            obj: Simple instance to serialize
            
        Returns:
            Flat IR dict
        """
        obj_class = type(obj)
        return {
            "__cerial_type__": "simple_class_instance",
            "module": obj_class.__module__,
            "qualname": obj_class.__qualname__,
            "attrs": dict(obj.__dict__),  # Direct copy - all primitives
        }
    
    def _find_handler(self, obj: Any) -> Optional[Any]:
        """
        Find appropriate handler for object.
        
        Uses type-based caching to avoid repeated lookups.
        Cache persists across serialize() calls since handlers are static.
        
        Args:
            obj: Object to find handler for
            
        Returns:
            Handler instance or None
        """
        obj_type = type(obj)
        
        # Check cache first (fast path)
        if obj_type in self._handler_cache:
            return self._handler_cache[obj_type]
        
        # Slow path: find handler by checking each one
        handler = self._find_handler_slow(obj)
        
        # Cache the result (even None - means no handler for this type)
        self._handler_cache[obj_type] = handler
        return handler
    
    def _find_handler_slow(self, obj: Any) -> Optional[Any]:
        """
        Find handler by checking each handler in order.
        
        This is the slow path - only called once per type.
        
        Args:
            obj: Object to find handler for
            
        Returns:
            Handler instance or None
        """
        # Try each handler in order
        # Order matters - specific handlers come before general ones
        for handler in self.handlers:
            try:
                if handler.can_handle(obj):
                    return handler
            except Exception as e:
                # Handler's can_handle() raised exception
                if self.debug:
                    print(f"  {'  ' * self._serialization_depth}Handler {handler.__class__.__name__}.can_handle() raised: {e}")
                # Skip this handler and continue
                continue
        
        # No handler found
        return None



