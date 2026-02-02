# Central Serializer for Cucumber
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

class Serializer:
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
        # handler registry
        self.handlers = ALL_HANDLERS
        
        # configuration
        self.debug = debug
        self.verbose = verbose
        
        # handler cache: maps type -> handler (persists across serialize() calls)
        # handlers are static, so caching by type is safe and avoids repeated lookups
        self._handler_cache: Dict[type, Optional[Any]] = {}
        
        # state tracking (reset for each serialize() call)
        self.seen_objects: Dict[int, Any] = {}
        self._serialization_depth = 0
        self._max_depth = 1000
        self._object_path: list = []  # breadcrumb trail for error reporting
        
        # Debug tracking
        self._all_object_ids: set = set()  # all __object_id__ values added
        self._all_circular_refs: set = set()  # all __cucumber_ref__ values created
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
        # reset state for fresh serialization
        self.seen_objects = {}
        self._serialization_depth = 0
        self._object_path = []
        self._all_object_ids = set()
        self._all_circular_refs = set()
        self._circular_ref_details = []
        
        if self.verbose:
            print(f"[CUCUMBER] Starting serialization of {type(obj).__name__}")
        
        # build intermediate representation (nested dicts/lists)
        try:
            ir = self._serialize_recursive(obj)
        except SerializationError:
            # already a SerializationError with good message, just re-raise
            raise
        except Exception as e:
            # unexpected error - wrap it
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
            print(f"[CUCUMBER] Built IR successfully, size: {len(str(ir))} chars")
        
        # use pickle to convert IR to bytes
        try:
            result = pickle.dumps(ir, protocol=pickle.HIGHEST_PROTOCOL)
            if self.verbose:
                print(f"[CUCUMBER] Serialization complete, bytes: {len(result)}")
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

    def serialize_ir(self, obj: Any) -> Any:
        """
        Build and return the intermediate representation (IR) without pickling.
        """
        # reset state for fresh serialization
        self.seen_objects = {}
        self._serialization_depth = 0
        self._object_path = []
        self._all_object_ids = set()
        self._all_circular_refs = set()
        self._circular_ref_details = []
        
        if self.verbose:
            print(f"[CUCUMBER] Starting IR build for {type(obj).__name__}")
        
        try:
            return self._serialize_recursive(obj)
        except SerializationError:
            raise
        except Exception as e:
            path_str = " -> ".join(self._object_path) if self._object_path else "root"
            raise SerializationError(
                f"\n{'='*70}\n"
                f"IR BUILD FAILED\n"
                f"{'='*70}\n"
                f"Path: {path_str}\n"
                f"Type: {type(obj).__name__}\n"
                f"Error: {e}\n"
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
        # fast path: Immutable primitives can skip ALL overhead
        # these types are never circular and pickle handles them natively
        # place this FIRST to avoid depth/path tracking overhead
        if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
            return obj
        
        # check recursion depth for safety
        self._serialization_depth += 1
        if self._serialization_depth > self._max_depth:
            path_str = " -> ".join(self._object_path) if self._object_path else "root"
            raise RecursionError(
                f"Serialization depth exceeded {self._max_depth}.\n"
                f"Path: {path_str}\n"
                f"This indicates a circular reference or deeply nested structure."
            )
        
        # add current object to breadcrumb trail
        obj_name = f"{type(obj).__name__}"
        if self.debug:
            obj_name += f"@{id(obj)}"
        self._object_path.append(obj_name)
        
        if self.verbose:
            # show path context with color-coded levels
            # take last 6 levels, truncate each to 10 chars, color code
            path_levels = self._object_path[-6:]
            
            # color codes: red -> orange -> yellow -> green -> blue -> purple
            # colors cycle based on actual depth, so depth 1,7,13 = red, 2,8,14 = orange, etc.
            colors = [
                "\033[91m",      # red (depths 1, 7, 13, ...)
                "\033[38;5;208m", # orange (depths 2, 8, 14, ...)
                "\033[93m",      # yellow (depths 3, 9, 15, ...)
                "\033[92m",      # green (depths 4, 10, 16, ...)
                "\033[94m",      # blue (depths 5, 11, 17, ...)
                "\033[95m",      # magenta/purple (depths 6, 12, 18, ...)
            ]
            reset = "\033[0m"
            
            # build colored path string
            colored_parts = []
            # calculate actual depth for each displayed level
            total_levels = len(self._object_path)
            start_depth = total_levels - len(path_levels)  # depth of first displayed level
            
            for i, level in enumerate(path_levels):
                # truncate to 10 chars
                truncated = level[:10] if len(level) > 10 else level
                # color based on actual depth (1-indexed, so depth 1 = colors[0])
                actual_depth = start_depth + i + 1
                color = colors[(actual_depth - 1) % 6]
                colored_parts.append(f"{color}{truncated}{reset}")
            
            path_str = " → ".join(colored_parts)
            if len(self._object_path) > 6:
                path_str = "... → " + path_str
            
            indent = "  " * min(self._serialization_depth, 5)  # cap indent at 5 levels
            print(f"{indent}[{self._serialization_depth}] {path_str}")
        
        try:
            # check for circular references
            obj_id = id(obj)
            
            # only track objects that can participate in circular refs
            if self._is_circular_capable(obj):
                if obj_id in self.seen_objects:
                    # already serialized - return reference marker
                    self._all_circular_refs.add(obj_id)
                    path_str = " → ".join(self._object_path[-3:])
                    self._circular_ref_details.append((obj_id, type(obj).__name__, path_str))
                    return {"__cucumber_ref__": obj_id}
                # mark as seen
                self.seen_objects[obj_id] = obj
            
            # check if base pickle can handle natively
            if self._is_pickle_native(obj):
                # primitives - check if they need __object_id__ (for circular refs)
                # singletons and immutable primitives
                if obj is None or obj is Ellipsis or obj is NotImplemented:
                    # check if circular ref
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cucumber_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    return obj
                
                if isinstance(obj, (bool, int, float, complex, str, bytes, bytearray)):
                    # these are never circular (immutable primitives)
                    return obj
                
                if isinstance(obj, (range, slice)):
                    # check if circular ref
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cucumber_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    return obj
                
                # collections - recursively serialize contents
                # check for special collection types first (Counter, defaultdict, etc.)
                # these are dict/list subclasses but pickle handles them correctly
                if self._is_special_pickle_native(obj):
                    # special collections types - return as-is (with object_id if needed)
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cucumber_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    return obj
                
                elif isinstance(obj, dict):
                    # fast path: if all keys and values are primitives, copy directly
                    if self._is_all_primitive_dict(obj):
                        # direct copy - no recursion needed
                        result = {
                            "__cucumber_type__": "dict",
                            "items": list(obj.items()),  # direct copy
                        }
                        if obj_id in self.seen_objects:
                            result["__object_id__"] = obj_id
                            self._all_object_ids.add(obj_id)
                        return result
                    
                    # slow path: recursively serialize BOTH keys and values
                    # keys can be tuples/frozensets with complex objects inside
                    serialized_items = [
                        (self._serialize_recursive(k), self._serialize_recursive(v))
                        for k, v in obj.items()
                    ]
                    result = {
                        "__cucumber_type__": "dict",
                        "items": serialized_items,
                    }
                    # add object_id if this dict is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                elif isinstance(obj, list):
                    # recursively serialize list items
                    # lists come out as plain lists (not wrapped) unless they have circular refs
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    # if list is circular-capable, wrap it with metadata
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cucumber_type__": "list",
                            "items": serialized_items,
                            "__object_id__": obj_id,
                        }
                    return serialized_items
                
                elif isinstance(obj, tuple):
                    # recursively serialize tuple items
                    # need special handling to preserve tuple type
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    result = {
                        "__cucumber_type__": "tuple",
                        "items": serialized_items,
                    }
                    # add object_id if this tuple is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                elif isinstance(obj, set):
                    # recursively serialize set items
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    result = {
                        "__cucumber_type__": "set",
                        "items": serialized_items,
                    }
                    # add object_id if this set is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                elif isinstance(obj, frozenset):
                    # recursively serialize frozenset items
                    serialized_items = [
                        self._serialize_recursive(item)
                        for item in obj
                    ]
                    result = {
                        "__cucumber_type__": "frozenset",
                        "items": serialized_items,
                    }
                    # add object_id if this frozenset is circular-capable (was tracked)
                    if obj_id in self.seen_objects:
                        result["__object_id__"] = obj_id
                        self._all_object_ids.add(obj_id)
                    return result
                
                # other pickle-native types (datetime, UUID, Decimal, Path, etc.)
                # these implement __reduce__ properly
                # BUT: if they're circular-capable and were seen, we need to track their ID
                else:
                    # check if this object needs an __object_id__ (is in seen_objects)
                    if obj_id in self.seen_objects:
                        # Wrap with metadata to include __object_id__
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cucumber_type__": "pickle_native",
                            "__object_id__": obj_id,
                            "value": obj,
                        }
                    else:
                        # no circular refs, return as-is
                        return obj
            
            # check for simple instance fast path
            if self._is_simple_instance(obj):
                if self.verbose:
                    indent = "  " * min(self._serialization_depth, 5)
                    print(f"{indent}    ↳ Simple instance fast path")
                # register object for circular reference support
                self.seen_objects[obj_id] = obj
                self._all_object_ids.add(obj_id)
                return {
                    "__cucumber_type__": "simple_class_instance",
                    "__object_id__": obj_id,
                    "module": type(obj).__module__,
                    "qualname": type(obj).__qualname__,
                    "attrs": dict(obj.__dict__),  # direct copy of primitive attrs
                }
            
            # check for pickle-native function fast path
            # functions that can be imported by reference don't need cucumber overhead
            # just let pickle handle them with its efficient GLOBAL opcode
            if self._is_pickle_native_function(obj):
                if self.verbose:
                    indent = "  " * min(self._serialization_depth, 5)
                    print(f"{indent}    ↳ Pickle-native function (reference)")
                # register object for circular reference support
                self.seen_objects[obj_id] = obj
                self._all_object_ids.add(obj_id)
                # wrap in IR with object_id so deserializer can register it
                return {
                    "__cucumber_type__": "pickle_native_func",
                    "__object_id__": obj_id,
                    "value": obj,
                }
            
            # find handler for complex object
            handler = self._find_handler(obj)
            
            if handler is None:
                # no handler found - try pickle as last resort
                try:
                    pickle.dumps(obj)
                    # if we get here, pickle can handle it
                    if self.verbose:
                        indent = "  " * min(self._serialization_depth, 5)
                        print(f"{indent}    ↳ Pickle native (no handler)")
                    
                    # check if it needs __object_id__ (for circular refs)
                    if obj_id in self.seen_objects:
                        self._all_object_ids.add(obj_id)
                        return {
                            "__cucumber_type__": "pickle_native",
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
                        f"\nNo cucumber handler exists for this type,\n"
                        f"and base pickle cannot serialize it either.\n"
                        f"\nPickle error: {pickle_err}\n"
                        f"{'='*70}"
                    ) from pickle_err
            
            if self.verbose:
                indent = "  " * min(self._serialization_depth, 5)
                print(f"{indent}    ↳ Handler: {handler.__class__.__name__}")
            
            # use handler to extract state
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
            
            # RECURSIVELY serialize the extracted state
            # this is critical - the handler returns state that may contain complex objects
            serialized_state = self._serialize_recursive(state)
            
            # wrap in metadata
            # ALWAYS include object_id for handler objects - keeps things simple and consistent
            self._all_object_ids.add(obj_id)
            return {
                "__cucumber_type__": handler.type_name,
                "__handler__": handler.__class__.__name__,
                "__object_id__": obj_id,
                "state": serialized_state,
            }
        
        finally:
            # always clean up tracking state when exiting
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
        # check for special singletons
        if obj is None or obj is Ellipsis or obj is NotImplemented:
            return True
        
        # check for basic primitive types
        if isinstance(obj, (bool, int, float, complex, str, bytes, bytearray)):
            return True
        
        # check for collections (we'll recursively handle their contents)
        if isinstance(obj, (list, tuple, dict, set, frozenset)):
            return True
        
        # check for other pickle-native types
        if isinstance(obj, (range, slice)):
            return True
        
        # standard library pickle-native types (implement __reduce__ properly)
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
            
            # numeric types
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
            # module not available, skip these checks
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
        # primitives never participate in circular references
        if isinstance(obj, (type(None), bool, int, float, complex, str, bytes)):
            return False
        
        # immutable collections need tracking (can contain circular refs)
        if isinstance(obj, (tuple, frozenset)):
            return True
        
        # everything else might have circular refs
        # (mutable collections, class instances, etc.)
        return True
    
    # primitive types that can be directly copied without recursion
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
            # check key
            if not isinstance(key, self._PRIMITIVE_TYPES):
                return False
            # check value
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
        
        # exclude built-in types that have __dict__ but aren't user classes
        # these include: functions, modules, methods, code objects, etc.
        if module_name == 'builtins':
            return False
        
        # exclude standard library modules - they have dedicated handlers
        # simple instance fast path is only for user-defined classes
        stdlib_modules = {
            'functools', 'io', 'logging', 'threading', 'multiprocessing',
            'queue', 'collections', 'datetime', 'pathlib', 'uuid', 're',
            'sqlite3', 'tempfile', 'socket', 'ssl', 'http', 'urllib',
            'email', 'json', 'pickle', 'copy', 'weakref', 'abc', 'typing',
            'dataclasses', 'enum', 'decimal', 'fractions', 'numbers',
            'itertools', 'operator', 'contextlib', 'asyncio', 'concurrent',
        }
        # check if module is in stdlib or is a submodule of stdlib
        top_module = module_name.split('.')[0]
        if top_module in stdlib_modules:
            return False
        
        # also exclude _io (C implementation of io module)
        if module_name.startswith('_'):
            return False
        
        # exclude function-like objects explicitly
        if isinstance(obj, (types.FunctionType, types.MethodType, types.ModuleType,
                           types.CodeType, types.BuiltinFunctionType, functools.partial)):
            return False
        
        # must have __dict__
        if not hasattr(obj, '__dict__'):
            return False
        
        # must not have __slots__ (complicates reconstruction)
        if hasattr(obj_class, '__slots__'):
            return False
        
        # must be module-level class (can import by qualname)
        qualname = getattr(obj_class, '__qualname__', '')
        if '<locals>' in qualname:
            return False
        
        # must not have custom serialization
        if hasattr(obj, '__serialize__'):
            return False
        
        # all attrs must be primitives
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
        
        # must be a function
        if not isinstance(obj, types.FunctionType):
            return False
        
        # lambdas can't be referenced by name
        if obj.__name__ == '<lambda>':
            return False
        
        # must have module and qualname
        module_name = getattr(obj, '__module__', None)
        qualname = getattr(obj, '__qualname__', None)
        if not module_name or not qualname:
            return False
        
        # can't import from __main__
        if module_name == '__main__':
            return False
        
        # nested functions have '<locals>' in qualname
        if '<locals>' in qualname:
            return False
        
        # closures have captured variables - need full serialization
        if obj.__closure__ is not None:
            return False
        
        # verify we can actually look it up and get the same function
        try:
            import importlib
            module = importlib.import_module(module_name)
            
            # navigate qualname (handles class methods like MyClass.method)
            looked_up = module
            for part in qualname.split('.'):
                looked_up = getattr(looked_up, part)
            
            # must be the exact same function object
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
            "__cucumber_type__": "simple_class_instance",
            "module": obj_class.__module__,
            "qualname": obj_class.__qualname__,
            "attrs": dict(obj.__dict__),  # direct copy - all primitives
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
        
        # check cache first (fast path)
        if obj_type in self._handler_cache:
            return self._handler_cache[obj_type]
        
        # slow path: find handler by checking each one
        handler = self._find_handler_slow(obj)
        
        # cache the result (even None - means no handler for this type)
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
        # try each handler in order
        # order matters - specific handlers come before general ones
        for handler in self.handlers:
            try:
                if handler.can_handle(obj):
                    return handler
            except Exception as e:
                # handler's can_handle() raised exception
                if self.debug:
                    print(f"  {'  ' * self._serialization_depth}Handler {handler.__class__.__name__}.can_handle() raised: {e}")
                # skip this handler and continue
                continue
        
        # no handler found
        return None



