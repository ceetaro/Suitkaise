"""
Central deserializer for cucumber.

Responsibilities:
- Convert pickled bytes back into the intermediate representation (IR)
- Traverse the IR and reconstruct all objects with exact state
- Handle circular references (objects that reference themselves)
- Dispatch to appropriate handlers for complex object reconstruction
- Track already-reconstructed objects to avoid duplication
- Provide clear error messages when reconstruction fails

This is the inverse of serializer.py.
"""

# STEP 1: UNPICKLE THE BYTES
# - Take serialized bytes as input
# - Use pickle.loads to convert bytes back to the intermediate representation (IR)
# - The IR is nested dicts/lists with metadata markers like "__cucumber_type__"
# - This gives us the structure but not the final objects yet

# STEP 2: IDENTIFY WHAT NEEDS RECONSTRUCTION
# - Scan through the IR to find all objects that need reconstruction
# - Look for metadata markers: "__cucumber_type__", "__handler__", "__object_id__"
# - Primitive types (int, str, etc.) are already final - no reconstruction needed
# - Collections (list, dict, tuple) need their contents reconstructed recursively
# - Handler-marked objects need to be passed to their handler's reconstruct method

# STEP 3: HANDLE CIRCULAR REFERENCES (TWO-PASS APPROACH)
# - First pass: Create placeholder objects for everything that has an "__object_id__"
# - Build a lookup table: object_id -> placeholder object
# - When we encounter a "__cucumber_ref__" marker, replace it with the placeholder
# - Second pass: Fill in the actual state of each placeholder
# - This prevents infinite loops when objects reference each other

# STEP 4: DISPATCH TO HANDLERS FOR RECONSTRUCTION
# - For each object with a "__handler__" marker, find the matching handler
# - Extract the state dict from the IR
# - Recursively reconstruct all values within the state dict first
# - Pass the fully-reconstructed state to handler.reconstruct()
# - Store the reconstructed object in our object_id lookup table

# STEP 5: RECURSIVELY RECONSTRUCT NESTED STATE
# - Before passing state to a handler, ensure all nested objects are reconstructed
# - Traverse through dicts: reconstruct both keys and values
# - Traverse through lists/tuples: reconstruct each element
# - Replace circular reference markers with actual objects from our lookup table
# - This ensures handlers receive fully-reconstructed state, not IR fragments
# STEP 6: HANDLE BASIC COLLECTIONS
# - For lists: reconstruct each element, return as list
# - For tuples: reconstruct each element, return as tuple
# - For sets: reconstruct each element, return as set
# - For frozensets: reconstruct each element, return as frozenset
# - For dicts: reconstruct both keys and values, return as dict
# - These don't have handlers but still need recursive processing

# STEP 7: ERROR HANDLING AND REPORTING
# - Track current reconstruction path (like serialization path)
# - Catch errors during handler dispatch and reconstruction
# - Provide context: which object failed, which handler, what state
# - Support debug mode (log all reconstruction steps)
# - Support verbose mode (detailed output for troubleshooting)

# STEP 8: RETURN THE FINAL OBJECT
# - After all reconstruction is complete, return the top-level object
# - All nested objects should be fully reconstructed with exact state
# - All circular references should be properly connected
# - The returned object should be functionally equivalent to the original

import pickle
import sys
import types
from typing import Any, Dict, List, Optional, Type

from .handlers import ALL_HANDLERS
from .handlers.base_class import Handler


class DeserializationError(Exception):
    """Raised when deserialization fails."""
    pass


class _ReconstructionPlaceholder:
    """
    Placeholder object used during two-pass reconstruction.
    
    When reconstructing an object with circular references in its state,
    we register this placeholder first, then reconstruct the state (which
    may contain circular refs back to this object), then replace the
    placeholder with the real reconstructed object.
    """
    def __init__(self, obj_id: int, type_name: str):
        self.obj_id = obj_id
        self.type_name = type_name
        self.real_object = None  # will be set after reconstruction
    
    def __repr__(self):
        return f"<Placeholder for {self.type_name} id={self.obj_id}>"


class Deserializer:
    """
    Central deserializer that converts pickled bytes back into Python objects.
    
    The deserializer:
    1. Unpickles bytes to get the intermediate representation (IR)
    2. Recursively reconstructs objects from the IR
    3. Handles circular references using a two-pass approach
    4. Dispatches to handlers for complex object reconstruction
    5. Tracks reconstruction path for error reporting
    """
    
    def __init__(
        self,
        handlers: Optional[List[Handler]] = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the deserializer.
        
        Args:
            handlers: List of handler instances (defaults to ALL_HANDLERS)
            debug: Enable debug mode (logs all reconstruction steps)
            verbose: Enable verbose mode (detailed output with paths)
        """
        self.handlers = handlers if handlers is not None else ALL_HANDLERS
        self.debug = debug
        self.verbose = verbose
        
        # object registry: maps object_id -> reconstructed object
        # used for circular reference handling
        self._object_registry: Dict[int, Any] = {}
        
        # reconstruction path: tracks current position in object tree
        # used for error reporting
        self._reconstruction_path: List[str] = []
        
        # reconstruction depth: tracks how deep we are in recursion
        self._reconstruction_depth: int = 0
        
        # track collections currently being reconstructed (by python id) to detect cycles
        self._reconstructing: set = set()
        
        # cache reconstructed IR objects to handle pickle's object deduplication
        # if pickle deduplicated an object (same IR dict/list appears multiple times),
        #   we should return the same reconstructed object each time
        self._reconstructed_cache: Dict[int, Any] = {}
        
        # Debug tracking
        self._all_registered_ids: set = set()  # all IDs registered in pass 1
        self._all_encountered_refs: set = set()  # all __cucumber_ref__ values encountered
    
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes back into a Python object.
        
        Uses two-pass approach:
        Pass 1: Scan IR and register placeholders for all objects with __object_id__
        Pass 2: Reconstruct all objects (circular refs resolve to placeholders)
        
        Args:
            data: Pickled bytes from serializer
            
        Returns:
            Reconstructed Python object with exact state
            
        Raises:
            DeserializationError: If reconstruction fails
        """
        try:
            # inpickle bytes to get intermediate representation
            self._log("Unpickling bytes to intermediate representation...")
            ir = pickle.loads(data)
            
            # clear state for fresh reconstruction
            self._object_registry.clear()
            self._reconstruction_path.clear()
            self._reconstruction_depth = 0
            self._reconstructing.clear()
            self._reconstructed_cache.clear()
            self._all_registered_ids = set()
            self._all_encountered_refs = set()
            
            # PASS 1 - register placeholders for all objects with __object_id__
            self._log("Pass 1: Registering placeholders for all objects...")
            self._register_all_placeholders(ir)
            self._log(f"  Registered {len(self._object_registry)} placeholders")
            
            # PASS 2 - reconstruct the object tree
            self._log("Pass 2: Reconstructing objects...")
            result = self._reconstruct_recursive(ir)
            
            # return the final reconstructed object
            self._log(f"Deserialization complete! Reconstructed {type(result).__name__}")
            return result
            
        except Exception as e:
            if isinstance(e, DeserializationError):
                raise
            raise DeserializationError(f"Failed to deserialize: {e}") from e
    
    def _reconstruct_recursive(self, ir_data: Any) -> Any:
        """
        Recursively reconstruct objects from intermediate representation.
        
        This is the core reconstruction logic that:
        1. Checks if data is a circular reference marker
        2. Checks if data is primitive (already final)
        3. Checks if data has cucumber metadata (needs handler reconstruction) - CHECK BEFORE collections!
        4. Checks if data is a basic collection (list, dict, tuple, set)
        5. Recursively reconstructs all nested data
        
        Args:
            ir_data: Data from the intermediate representation
            
        Returns:
            Fully reconstructed Python object
        """
        # track recursion depth
        self._reconstruction_depth += 1
        try:
            # check cache for already-reconstructed IR objects
            # this handles pickle's object deduplication (same dict/list appearing multiple times)
            ir_id = id(ir_data)
            if ir_id in self._reconstructed_cache:
                return self._reconstructed_cache[ir_id]
            
            # check for circular reference marker
            if self._is_circular_reference(ir_data):
                if self.debug:
                    obj_id = ir_data["__cucumber_ref__"]
                    self._log(f"Found circular reference to object {obj_id}")
                    self._log(f"  Current registry has: {list(self._object_registry.keys())}")
                return self._resolve_circular_reference(ir_data)
            
            # check if data is primitive (already final, no work needed)
            if self._is_primitive(ir_data):
                return ir_data
            
            # check if data is a special collections type that pickle handled correctly
            # these are dict/list subclasses that would otherwise be caught by _is_basic_collection
            #   but should be returned as-is since pickle preserved their type
            if self._is_special_collection_type(ir_data):
                return ir_data
            
            # check if data has cucumber metadata (needs handler reconstruction)
            # NOTE: Check this BEFORE basic collections, because cucumber objects
            #   are dicts with special markers
            if self._has_cucumber_metadata(ir_data):
                return self._reconstruct_from_handler(ir_data)
            
            # check if data is a basic collection (needs recursive processing)
            if self._is_basic_collection(ir_data):
                data_id = id(ir_data)
                
                # check if we're already reconstructing this exact IR object
                if data_id in self._reconstructing:
                    # this happens when pickle deduplicated an object and it appears
                    #   in multiple places in the IR. We're currently reconstructing it,
                    #   so we need to register a placeholder and return it.
                    # the placeholder will be replaced with the final result once complete.
                    
                    # for mutable collections (dict, list, set), create empty placeholder
                    if isinstance(ir_data, dict):
                        placeholder = {}
                    elif isinstance(ir_data, list):
                        placeholder = []
                    elif isinstance(ir_data, set):
                        placeholder = set()
                    else:
                        # for immutable collections (tuple, frozenset), we can't use placeholders
                        # this is a true circular reference that can't be handled
                        raise DeserializationError(
                            f"Cannot reconstruct immutable collection {type(ir_data).__name__} "
                            f"that references itself. Immutable circular refs are not supported."
                        )
                    
                    # cache the placeholder
                    self._reconstructed_cache[data_id] = placeholder
                    return placeholder
                
                # mark as currently reconstructing
                self._reconstructing.add(data_id)
                try:
                    # reconstruct the collection
                    result = self._reconstruct_collection(ir_data)
                    
                    # if we created a placeholder earlier, update it instead of caching a new object
                    if data_id in self._reconstructed_cache:
                        placeholder = self._reconstructed_cache[data_id]
                        if isinstance(placeholder, dict) and isinstance(result, dict):
                            placeholder.update(result)
                            return placeholder
                        elif isinstance(placeholder, list) and isinstance(result, list):
                            placeholder.extend(result)
                            return placeholder
                        elif isinstance(placeholder, set) and isinstance(result, set):
                            placeholder.update(result)
                            return placeholder
                    
                    # cache the result for future references
                    self._reconstructed_cache[data_id] = result
                    return result
                finally:
                    self._reconstructing.discard(data_id)
            
            # if none of above, return as-is
            # this handles edge cases like type objects, modules, etc that pickle handles
            return ir_data
            
        finally:
            # always decrement depth on exit
            self._reconstruction_depth -= 1
    
    def _register_all_placeholders(self, data: Any, visited: Optional[set] = None) -> None:
        """
        PASS 1: Scan the entire IR and register placeholders for all objects with __object_id__.
        
        This ensures that when we reconstruct objects in pass 2, any circular or forward
        references can be resolved immediately.
        
        Args:
            data: IR data to scan
            visited: Set of Python object IDs we've already visited (to avoid infinite loops)
        """
        if visited is None:
            visited = set()
        
        # avoid infinite loops from Python's own object cycles
        data_id = id(data)
        if data_id in visited:
            return
        visited.add(data_id)
        
        # check if this is a cucumber object with __object_id__
        if isinstance(data, dict):
            if "__object_id__" in data:
                obj_id = data["__object_id__"]
                type_name = data.get("__cucumber_type__", "unknown")
                
                # only register if not already registered
                if obj_id not in self._object_registry:
                    placeholder = _ReconstructionPlaceholder(obj_id, type_name)
                    self._object_registry[obj_id] = placeholder
                    self._all_registered_ids.add(obj_id)
                    self._log(f"  Registered placeholder for {type_name} (id={obj_id})")
            
            # recursively scan all dict values
            for value in data.values():
                self._register_all_placeholders(value, visited)
        
        elif isinstance(data, (list, tuple)):
            # recursively scan all list/tuple items
            for item in data:
                self._register_all_placeholders(item, visited)
    
    def _is_circular_reference(self, data: Any) -> bool:
        """
        Check if data is a circular reference marker.
        
        Format: {"__cucumber_ref__": object_id}
        """
        # must be a dict with exactly one key: "__cucumber_ref__"
        if isinstance(data, dict):
            if "__cucumber_ref__" in data:
                if len(data) == 1:
                    return True
                else:
                    raise DeserializationError(
                        f"Malformed circular reference marker: unexpected keys {list(data.keys())}"
                    )
        return False
    
    def _resolve_circular_reference(self, data: Dict[str, Any]) -> Any:
        """
        Resolve a circular reference by looking up object_id in registry.
        
        With two-pass reconstruction, the object should always be in the registry
        (either as a placeholder or as a fully reconstructed object).
        """
        obj_id = data["__cucumber_ref__"]
        self._all_encountered_refs.add(obj_id)
        
        # look up the object in our registry
        if obj_id in self._object_registry:
            obj = self._object_registry[obj_id]
            
            # if it's still a placeholder, that's okay - we'll replace it later
            if isinstance(obj, _ReconstructionPlaceholder):
                self._log(f"Resolved circular reference to placeholder {obj_id}")
            else:
                self._log(f"Resolved circular reference to object {obj_id}")
            
            return obj
        
        # this should never happen with two-pass reconstruction!
        raise DeserializationError(
            f"Circular reference to object {obj_id} not found in registry. "
            f"This suggests a bug in the two-pass reconstruction."
        )
    
    def _is_special_collection_type(self, data: Any) -> bool:
        """
        Check if data is a special collections type that pickle handled correctly.
        
        These are subclasses of basic collections (dict/list/tuple) that have special
        behavior and should not be reconstructed as plain collections.
        
        Examples: Counter, defaultdict, OrderedDict, deque, ChainMap
        """
        try:
            import collections
            
            # check if it's a collections module type
            if isinstance(data, (
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
    
    def _is_primitive(self, data: Any) -> bool:
        """
        Check if data is a primitive type that needs no reconstruction.
        
        Primitives: int, float, str, bool, None, bytes, complex, Ellipsis
        """
        # these types are already final - they came through pickle unchanged
        return isinstance(data, (
            type(None),
            bool,
            int,
            float,
            complex,
            str,
            bytes,
            bytearray,
            type(Ellipsis),
            type(NotImplemented),
        ))
    
    def _is_basic_collection(self, data: Any) -> bool:
        """
        Check if data is a basic collection type.
        
        Basic collections: list, tuple, set, frozenset, dict
        These need recursive reconstruction but don't use handlers.
        """
        # NOTE: We check isinstance for each type individually
        # can't check dict with __cucumber_type__ here - that's handled separately
        return isinstance(data, (list, tuple, set, frozenset, dict))
    
    def _reconstruct_collection(self, data: Any) -> Any:
        """
        Reconstruct a basic collection (list, dict, tuple, set, frozenset).
        
        Recursively reconstructs all elements/keys/values.
        
        Note: By the time we get here, we've already checked for cucumber metadata,
        so all dicts here are plain dicts (no __cucumber_type__ marker).
        
        These are simple collections from the original serialized data that
        pickle handled, not cucumber-wrapped ones.
        """
        # list: reconstruct each element
        if isinstance(data, list):
            return [self._reconstruct_recursive(item) for item in data]
        
        # tuple: reconstruct each element, convert to tuple
        if isinstance(data, tuple):
            return tuple(self._reconstruct_recursive(item) for item in data)
        
        # set: reconstruct each element, convert to set
        if isinstance(data, set):
            return {self._reconstruct_recursive(item) for item in data}
        
        # frozenset: reconstruct each element, convert to frozenset
        if isinstance(data, frozenset):
            return frozenset(self._reconstruct_recursive(item) for item in data)
        
        # dict: reconstruct both keys and values
        if isinstance(data, dict):
            # Plain dict: reconstruct keys and values
            return {
                self._reconstruct_recursive(k): self._reconstruct_recursive(v)
                for k, v in data.items()
            }
        
        # shouldn't reach here
        return data
    
    def _has_cucumber_metadata(self, data: Any) -> bool:
        """
        Check if data has cucumber metadata markers.
        
        Two types of cucumber objects:
        1. Handler objects: {"__cucumber_type__", "__handler__", "state", "__object_id__"?}
        2. Wrapped collections: {"__cucumber_type__": "dict/tuple/set/frozenset", "items": [...]}
        """
        # must be a dict with cucumber markers
        if not isinstance(data, dict):
            return False
        
        # check for __cucumber_type__ marker
        return "__cucumber_type__" in data
    
    def _reconstruct_from_handler(self, data: Dict[str, Any]) -> Any:
        """
        Reconstruct an object using its handler.
        
        Two-pass approach for circular references:
        1. Register placeholder if object has obj_id (might have circular refs)
        2. Reconstruct state (may reference the placeholder)
        3. Call handler.reconstruct(state) to get real object
        4. Replace placeholder with real object in registry
        5. Post-process to replace any placeholder references in the reconstructed state
        """
        type_name = data["__cucumber_type__"]
        
        # check if this is a wrapped pickle-native object (just needs unwrapping)
        if type_name == "pickle_native":
            return self._reconstruct_pickle_native(data)
        
        # check if this is a pickle-native function (module-level function by reference)
        if type_name == "pickle_native_func":
            return self._reconstruct_pickle_native_func(data)
        
        # check if this is a simple instance (fast path - no handler needed)
        if type_name == "simple_class_instance":
            return self._reconstruct_simple_instance(data)
        
        # check if this is a wrapped collection (no handler, just items)
        if "__handler__" not in data and "items" in data:
            return self._reconstruct_wrapped_collection(data)
        
        # otherwise, it's a handler object
        handler_name = data.get("__handler__")
        obj_id = data.get("__object_id__")
        state = data.get("state")
        if state is None:
            raise DeserializationError(
                f"Malformed handler IR for type '{type_name}': missing 'state'"
            )
        
        # update path for error reporting
        self._reconstruction_path.append(type_name)
        
        try:
            # find the appropriate handler
            handler = self._find_handler(type_name, handler_name)
            if handler is None:
                raise DeserializationError(
                    f"No handler found for type '{type_name}' (handler: {handler_name})"
                )
            
            if self.verbose:
                indent = "  " * min(self._reconstruction_depth - 1, 5)
                self._log(f"{indent}[{self._reconstruction_depth}] Reconstructing {type_name} with {handler_name}")
            
            # get placeholder if it exists (from pass 1)
            # if no obj_id, we won't have/need a placeholder
            placeholder = None
            if obj_id is not None:
                placeholder = self._object_registry.get(obj_id)
                if placeholder and isinstance(placeholder, _ReconstructionPlaceholder):
                    self._log(f"Using placeholder for object {obj_id} ({type_name})")
                elif placeholder:
                    # Already fully reconstructed - return it
                    self._log(f"Object {obj_id} already reconstructed, returning cached")
                    return placeholder
            
            # recursively reconstruct all values in state
            # this ensures the handler receives fully-reconstructed state
            # if state has circular refs back to this object, they'll resolve to the placeholder
            reconstructed_state = self._reconstruct_state_dict(state)
            
            # call handler.reconstruct(state)
            try:
                obj = handler.reconstruct(reconstructed_state)
            except Exception as e:
                raise DeserializationError(
                    self._format_error(e, data, handler)
                ) from e
            
            # replace placeholder with real object in registry
            if obj_id is not None:
                self._object_registry[obj_id] = obj
                if placeholder is not None and isinstance(placeholder, _ReconstructionPlaceholder):
                    placeholder.real_object = obj  # Update placeholder for any existing references
                self._log(f"Replaced placeholder with real object {obj_id} ({type_name})")
            
            # post-process to replace placeholders in the reconstructed object
            # if the state contained circular refs, the handler received placeholders
            # we need to replace those with the real object
            if placeholder is not None:
                self._replace_placeholders_in_object(obj, placeholder, obj)
            
            # return reconstructed object
            return obj
            
        finally:
            # always clean up path
            self._reconstruction_path.pop()
    
    def _reconstruct_pickle_native(self, data: Dict[str, Any]) -> Any:
        """
        Reconstruct a wrapped pickle-native object.
        
        These are pickle-native types (datetime, UUID, Path, etc.) that were wrapped
        because they participated in circular references and needed an __object_id__.
        
        Format: {"__cucumber_type__": "pickle_native", "__object_id__": id, "value": obj}
        """
        obj_id = data.get("__object_id__")
        if "value" not in data:
            raise DeserializationError("Malformed pickle_native IR: missing 'value'")
        value = data["value"]
        
        # register the object if it has an ID (for circular refs)
        if obj_id is not None:
            self._object_registry[obj_id] = value
            self._all_registered_ids.add(obj_id)
            self._log(f"Registered pickle-native object {obj_id}")
        
        return value
    
    def _reconstruct_pickle_native_func(self, data: Dict[str, Any]) -> Any:
        """
        Reconstruct a wrapped pickle-native function.
        
        These are module-level functions that can be serialized by reference
        (module + qualname). They were wrapped to support circular references.
        
        Format: {"__cucumber_type__": "pickle_native_func", "__object_id__": id, "value": func}
        """
        obj_id = data.get("__object_id__")
        if "value" not in data:
            raise DeserializationError("Malformed pickle_native_func IR: missing 'value'")
        value = data["value"]
        
        # register the function if it has an ID (for circular refs)
        if obj_id is not None:
            self._object_registry[obj_id] = value
            self._all_registered_ids.add(obj_id)
            self._log(f"Registered pickle-native function {obj_id}")
        
        return value
    
    def _reconstruct_simple_instance(self, data: Dict[str, Any]) -> Any:
        """
        Reconstruct a simple class instance from flat IR format.
        
        Fast path that skips handler dispatch and recursive reconstruction.
        Simple instances have only primitive attrs, so attrs are already final.
        
        Format: {
            "__cucumber_type__": "simple_class_instance",
            "__object_id__": <id>,
            "module": "...",
            "qualname": "...",
            "attrs": {...}
        }
        """
        import importlib
        
        obj_id = data.get("__object_id__")
        module_name = data["module"]
        qualname = data["qualname"]
        attrs = data["attrs"]
        
        # import the class
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise DeserializationError(
                f"Cannot import module '{module_name}' for simple instance. "
                f"Ensure the module exists in the target process."
            ) from e
        
        # navigate to class using qualname (handles nested classes like Outer.Inner)
        parts = qualname.split('.')
        cls = module
        for part in parts:
            try:
                cls = getattr(cls, part)
            except AttributeError as e:
                raise DeserializationError(
                    f"Cannot find class '{qualname}' in module '{module_name}'. "
                    f"Ensure the class definition exists in the target process."
                ) from e
        
        # create instance using __new__ (skip __init__)
        obj = cls.__new__(cls)
        
        # register in object registry for circular reference resolution
        if obj_id is not None:
            self._object_registry[obj_id] = obj
            self._all_registered_ids.add(obj_id)
        
        # populate __dict__ directly (attrs are all primitives, no reconstruction needed)
        obj.__dict__.update(attrs)
        
        self._log(f"Reconstructed simple instance: {qualname}")
        return obj
    
    def _reconstruct_wrapped_collection(self, data: Dict[str, Any]) -> Any:
        """
        Reconstruct a cucumber-wrapped collection.
        
        The serializer wraps certain collections to preserve type and handle
        complex keys/values:
        - dict: {"__cucumber_type__": "dict", "items": [(k, v), ...], "__object_id__"?}
        - tuple: {"__cucumber_type__": "tuple", "items": [items], "__object_id__"?}
        - set: {"__cucumber_type__": "set", "items": [items], "__object_id__"?}
        - frozenset: {"__cucumber_type__": "frozenset", "items": [items], "__object_id__"?}
        
        For circular references, we use two-pass approach:
        1. Create empty placeholder and register it
        2. Fill in contents (which may reference the placeholder)
        """
        type_name = data["__cucumber_type__"]
        items = data["items"]
        obj_id = data.get("__object_id__")
        
        if type_name == "dict":
            # create empty dict placeholder if circular-capable
            if obj_id is not None:
                # register empty placeholder first
                placeholder = {}
                self._object_registry[obj_id] = placeholder
                
                # now reconstruct contents (may reference placeholder)
                for k, v in items:
                    reconstructed_key = self._reconstruct_recursive(k)
                    reconstructed_value = self._reconstruct_recursive(v)
                    placeholder[reconstructed_key] = reconstructed_value
                
                return placeholder
            else:
                # no circular refs, simple reconstruction
                return {
                    self._reconstruct_recursive(k): self._reconstruct_recursive(v)
                    for k, v in items
                }
        
        elif type_name == "list":
            # lists need special handling - can't pre-create with contents
            if obj_id is not None:
                # register empty placeholder first
                placeholder = []
                self._object_registry[obj_id] = placeholder
                
                # now reconstruct and append items (may reference placeholder)
                for item in items:
                    reconstructed_item = self._reconstruct_recursive(item)
                    placeholder.append(reconstructed_item)
                
                return placeholder
            else:
                # no circular refs, simple reconstruction
                return [self._reconstruct_recursive(item) for item in items]
        
        elif type_name == "tuple":
            # tuples are immutable - can't do two-pass
            # if there's a circular ref to a tuple, we have a problem!
            # but tuples with circular refs are rare (can't add to themselves after creation)
            reconstructed_items = [self._reconstruct_recursive(item) for item in items]
            result = tuple(reconstructed_items)
            
            # register after reconstruction
            if obj_id is not None:
                self._object_registry[obj_id] = result
            
            return result
        
        elif type_name == "set":
            # sets are mutable, use two-pass
            if obj_id is not None:
                # register empty placeholder first
                placeholder = set()
                self._object_registry[obj_id] = placeholder
                
                # now reconstruct and add items (may reference placeholder)
                for item in items:
                    reconstructed_item = self._reconstruct_recursive(item)
                    placeholder.add(reconstructed_item)
                
                return placeholder
            else:
                # no circular refs, simple reconstruction
                return {self._reconstruct_recursive(item) for item in items}
        
        elif type_name == "frozenset":
            # frozensets are immutable - same as tuple
            reconstructed_items = [self._reconstruct_recursive(item) for item in items]
            result = frozenset(reconstructed_items)
            
            # register after reconstruction
            if obj_id is not None:
                self._object_registry[obj_id] = result
            
            return result
        
        else:
            raise DeserializationError(
                f"Unknown wrapped collection type: {type_name}"
            )
    
    def _find_handler(self, type_name: str, handler_name: str) -> Optional[Handler]:
        """
        Find a handler by type_name and handler class name.
        
        Returns None if no matching handler found.
        """
        # first, try to find by type_name (fast path)
        for handler in self.handlers:
            if handler.type_name == type_name:
                # Double-check the handler class name matches
                if handler.__class__.__name__ == handler_name:
                    return handler
        
        # if not found, try matching just by handler class name
        # (in case type_name changed between versions)
        for handler in self.handlers:
            if handler.__class__.__name__ == handler_name:
                self._log(f"Warning: Handler found by name '{handler_name}' but type_name doesn't match")
                return handler
        
        # no handler found
        return None
    
    def _reconstruct_state_dict(self, state: Any) -> Dict[str, Any]:
        """
        Recursively reconstruct all values in a state dict.
        
        This ensures handlers receive fully-reconstructed state,
        not intermediate representation fragments.
        
        The state itself might be a wrapped collection, so we need to
        reconstruct it first.
        """
        # first, check if state itself is a wrapped collection
        if isinstance(state, dict) and "__cucumber_type__" in state:
            # State is wrapped - reconstruct it first
            state = self._reconstruct_recursive(state)
        
        # now state should be a plain dict - reconstruct its values
        if not isinstance(state, dict):
            # State is not a dict (shouldn't happen, but handle gracefully)
            return state
        
        # recursively reconstruct each value in the state dict
        reconstructed = {}
        for key, value in state.items():
            # keys are typically strings, but reconstruct them just in case
            reconstructed_key = self._reconstruct_recursive(key) if not isinstance(key, str) else key
            reconstructed_value = self._reconstruct_recursive(value)
            reconstructed[reconstructed_key] = reconstructed_value
        
        return reconstructed
    
    def _replace_placeholders_in_object(self, obj: Any, placeholder: _ReconstructionPlaceholder, real_obj: Any) -> None:
        """
        Replace all references to placeholder with real_obj within obj.
        
        This is needed when an object's state contains circular references back to itself.
        The handler receives state with placeholders, and we need to replace them with
        the real reconstructed object.
        
        Args:
            obj: Object to scan and update
            placeholder: Placeholder to search for
            real_obj: Real object to replace placeholder with
        """
        visited: set[int] = set()

        def _replace(value: Any) -> Any:
            if value is placeholder:
                return real_obj

            if isinstance(value, (str, bytes, bytearray, int, float, bool, type(None))):
                return value

            # Never mutate interpreter/runtime metadata objects.
            if isinstance(value, (
                type,
                types.ModuleType,
                types.FunctionType,
                types.BuiltinFunctionType,
                types.MethodType,
                types.BuiltinMethodType,
                types.CodeType,
                property,
                staticmethod,
                classmethod,
            )):
                return value

            value_id = id(value)
            if value_id in visited:
                return value
            visited.add(value_id)

            if isinstance(value, list):
                for i, item in enumerate(value):
                    value[i] = _replace(item)
                return value

            if isinstance(value, tuple):
                return tuple(_replace(item) for item in value)

            if isinstance(value, dict):
                old_items = list(value.items())
                value.clear()
                for k, v in old_items:
                    value[_replace(k)] = _replace(v)
                return value

            if isinstance(value, set):
                replaced = {_replace(item) for item in value}
                value.clear()
                value.update(replaced)
                return value

            if isinstance(value, frozenset):
                return frozenset(_replace(item) for item in value)

            if hasattr(value, '__dict__'):
                for key, item in list(value.__dict__.items()):
                    try:
                        setattr(value, key, _replace(item))
                    except Exception:
                        continue

            if hasattr(type(value), '__slots__'):
                raw_slots = type(value).__slots__
                slots = (raw_slots,) if isinstance(raw_slots, str) else raw_slots
                for slot in slots:
                    if not isinstance(slot, str):
                        continue
                    try:
                        setattr(value, slot, _replace(getattr(value, slot)))
                    except AttributeError:
                        pass
                    except Exception:
                        continue
            return value

        _replace(obj)
    
    def _log(self, message: str) -> None:
        """Log a message if debug mode is enabled."""
        if self.debug:
            print(f"[CUCUMBER DESERIALIZE] {message}", file=sys.stderr)
    
    def _format_error(
        self,
        error: Exception,
        ir_data: Any,
        handler: Optional[Handler] = None,
    ) -> str:
        """
        Format a clean, informative error message.
        
        Shows:
        - What went wrong (the actual error)
        - Where it happened (reconstruction path)
        - What was being reconstructed (type, handler)
        - Current IR data (truncated)
        """
        lines = []
        lines.append("=" * 70)
        lines.append("DESERIALIZATION ERROR")
        lines.append("=" * 70)
        
        # what went wrong
        lines.append(f"\nError: {type(error).__name__}: {error}")
        
        # where it happened (path through object tree)
        if self._reconstruction_path:
            path_str = " → ".join(self._reconstruction_path)
            lines.append(f"\nPath: {path_str}")
        
        # what was being reconstructed
        if isinstance(ir_data, dict):
            type_name = ir_data.get("__cucumber_type__", "unknown")
            lines.append(f"Type: {type_name}")
        
        if handler:
            lines.append(f"Handler: {handler.__class__.__name__}")
        
        # IR data (truncated for readability)
        data_str = str(ir_data)
        if len(data_str) > 200:
            data_str = data_str[:200] + "..."
        lines.append(f"\nIR Data: {data_str}")
        
        lines.append("=" * 70)
        return "\n".join(lines)
