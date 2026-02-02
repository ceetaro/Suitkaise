"""
Handler for weakref objects.

Weak references allow referring to objects without preventing garbage collection.
Serializing them is tricky because the referenced object might not exist anymore.
"""

import weakref
from typing import Any, Dict, Optional
from .base_class import Handler


class WeakrefSerializationError(Exception):
    """Raised when weakref serialization fails."""
    pass


class WeakrefHandler(Handler):
    """
    Serializes weakref.ref objects.
    
    Strategy:
    - Try to dereference the weak reference
    - If object still exists, serialize it
    - If object is gone, store None
    - On reconstruction, create strong reference (not weak)
    
    NOTE: Weak references become strong references after deserialization.
    This is necessary because weak references don't make sense across processes -
    we can't preserve the original object identity and garbage collection state.
    """
    
    type_name = "weakref"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a weakref.ref."""
        return isinstance(obj, weakref.ref)
    
    def extract_state(self, obj: weakref.ref) -> Dict[str, Any]:
        """
        Extract weak reference state.
        
        What we capture:
        - referenced_object: The object being referenced (if still alive)
        - is_dead: Whether the reference is dead (object was garbage collected)
        
        NOTE: We serialize the actual object, not the weak reference itself.
        This means the reference becomes strong after deserialization.
        """
        # try to dereference the weak reference
        try:
            referenced_object = obj()
            is_dead = referenced_object is None
        except (TypeError, ReferenceError):
            referenced_object = None
            is_dead = True
        
        return {
            "referenced_object": referenced_object,  # will be recursively serialized
            "is_dead": is_dead,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct weak reference.
        
        Since weak references don't make sense across processes (object identity
        is process-local), we have two options:
        1. Return the referenced object directly (strong reference)
        2. Create a new weak reference to the deserialized object
        
        We choose option 2 to maintain the weak reference semantics, but note
        that this is a NEW object, not the original.
        """
        if state["is_dead"]:
            # reference was dead, create a dead reference
            # we can't create a truly dead weakref, so return a lambda that returns None
            return lambda: None
        
        # create new weak reference to deserialized object
        if state["referenced_object"] is not None:
            return weakref.ref(state["referenced_object"])
        else:
            return lambda: None


class WeakValueDictionaryHandler(Handler):
    """
    Serializes weakref.WeakValueDictionary objects.
    
    Weak value dictionaries store weak references as values, allowing
    values to be garbage collected.
    """
    
    type_name = "weak_value_dict"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a WeakValueDictionary."""
        return isinstance(obj, weakref.WeakValueDictionary)
    
    def extract_state(self, obj: weakref.WeakValueDictionary) -> Dict[str, Any]:
        """
        Extract WeakValueDictionary state.
        
        We snapshot the current key-value pairs (values that still exist).
        """
        # get all current key-value pairs where value still exists
        items = {}
        for key in list(obj.keys()):
            try:
                value = obj[key]
                if value is not None:
                    items[key] = value
            except KeyError:
                # value was garbage collected between keys() and now
                pass
        
        return {
            "items": items,  # will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> weakref.WeakValueDictionary:
        """
        Reconstruct WeakValueDictionary.
        
        Creates new WeakValueDictionary and populates it with deserialized items.
        Note: Values become strong references during serialization, then weak
        again when inserted into the new WeakValueDictionary.
        """
        wvd = weakref.WeakValueDictionary()
        
        # add items back
        for key, value in state["items"].items():
            wvd[key] = value
        
        return wvd


class WeakKeyDictionaryHandler(Handler):
    """
    Serializes weakref.WeakKeyDictionary objects.
    
    Weak key dictionaries store weak references as keys, allowing
    keys to be garbage collected.
    """
    
    type_name = "weak_key_dict"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a WeakKeyDictionary."""
        return isinstance(obj, weakref.WeakKeyDictionary)
    
    def extract_state(self, obj: weakref.WeakKeyDictionary) -> Dict[str, Any]:
        """
        Extract WeakKeyDictionary state.
        
        We snapshot the current key-value pairs (keys that still exist).
        Note: This is tricky because weak keys might not be hashable after
        serialization.
        """
        # get all current key-value pairs where key still exists
        items = []
        for key in list(obj.keys()):
            try:
                value = obj[key]
                items.append((key, value))
            except KeyError:
                # key was garbage collected between keys() and now
                pass
        
        return {
            "items": items,  # will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> weakref.WeakKeyDictionary:
        """
        Reconstruct WeakKeyDictionary.
        
        Creates new WeakKeyDictionary and populates it with deserialized items.
        """
        wkd = weakref.WeakKeyDictionary()
        
        # add items back
        for key, value in state["items"]:
            try:
                wkd[key] = value
            except TypeError:
                # key might not be weakly referenceable (e.g., int, str)
                # skip these items
                pass
        
        return wkd

