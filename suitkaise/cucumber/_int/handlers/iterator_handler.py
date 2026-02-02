"""
Handler for iterator objects with state.

Iterators maintain position in a sequence. We attempt to serialize their
current state and remaining values.
"""

import types
from typing import Any, Dict, List
from .base_class import Handler


class IteratorSerializationError(Exception):
    """Raised when iterator serialization fails."""
    pass


class IteratorHandler(Handler):
    """
    Serializes iterator objects (enumerate, zip, filter, map, etc.).
    
    Strategy:
    - Try to exhaust iterator and capture remaining values
    - Capture iterator type and parameters
    - On reconstruction, recreate iterator and advance to same position
    
    Important: Exhausting an iterator is destructive! The original
    iterator will be consumed. This is acceptable for cross-process
    serialization where we're transferring state.
    """
    
    type_name = "iterator"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is an iterator with state.
        
        We check for common iterator types: enumerate, zip, filter, map, etc.
        We avoid handling generator objects here (they have their own handler).
        """
        # check if it has iterator protocol
        if not hasattr(obj, '__iter__') or not hasattr(obj, '__next__'):
            return False
        
        # check type name
        obj_type_name = type(obj).__name__
        
        # handle known iterator types
        known_iterators = ['enumerate', 'zip', 'filter', 'map', 'reversed', 
                          'range_iterator', 'list_iterator', 'tuple_iterator',
                          'dict_keyiterator', 'dict_valueiterator', 'dict_itemiterator']
        
        # don't handle generator objects (they have separate handler)
        if isinstance(obj, types.GeneratorType):
            return False
        
        return obj_type_name in known_iterators
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract iterator state.
        
        What we capture:
        - type_name: Iterator type (enumerate, zip, etc.)
        - remaining_values: Values not yet consumed
        - params: Iterator construction parameters (if available)
        
        Note: This EXHAUSTS the iterator! Original will be empty.
        """
        obj_type_name = type(obj).__name__
        
        # exhaust iterator to get remaining values
        remaining_values = []
        try:
            # limit to prevent infinite iterators from causing issues
            max_items = 100000
            for i, item in enumerate(obj):
                if i >= max_items:
                    # iterator too long, can't serialize
                    raise ValueError(f"Iterator has more than {max_items} items, cannot serialize")
                remaining_values.append(item)
        except Exception as e:
            # some iterators might fail to serialize
            pass
        
        # try to extract iterator parameters (varies by type)
        params = {}
        
        # for enumerate, try to get start value
        if obj_type_name == 'enumerate':
            # can't extract start value after creation, default to 0
            params['start'] = len(remaining_values)
        
        return {
            "type_name": obj_type_name,
            "remaining_values": remaining_values,  # will be recursively serialized
            "params": params,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct iterator from remaining values.
        
        We create an iterator from the remaining values.
        Note: We can't perfectly recreate the original iterator,
        but we can create one with the same remaining values.
        """
        # simply create an iterator over the remaining values
        # this is the best we can do - the original iterator type
        # might not be reconstructible with the same parameters
        return iter(state["remaining_values"])


class RangeHandler(Handler):
    """
    Serializes range objects.
    
    Range objects are immutable sequences representing arithmetic progressions.
    They're actually pretty easy to serialize since they just store start/stop/step.
    """
    
    type_name = "range"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a range."""
        return isinstance(obj, range)
    
    def extract_state(self, obj: range) -> Dict[str, Any]:
        """
        Extract range parameters.
        
        Range objects store start, stop, and step.
        """
        return {
            "start": obj.start,
            "stop": obj.stop,
            "step": obj.step,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> range:
        """Reconstruct range with same parameters."""
        return range(state["start"], state["stop"], state["step"])


class EnumerateHandler(Handler):
    """
    Serializes enumerate objects (with special handling).
    
    Enumerate wraps an iterable and adds a counter.
    We serialize the underlying iterable and current count.
    """
    
    type_name = "enumerate"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is an enumerate."""
        return type(obj).__name__ == 'enumerate'
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract enumerate state.
        
        We exhaust the enumerate and capture:
        - Remaining (index, value) pairs
        """
        remaining = list(obj)  # exhausts the enumerate
        
        return {
            "remaining": remaining,  # list of (index, value) tuples
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct enumerate.
        
        Create iterator over remaining values.
        """
        return iter(state["remaining"])


class ZipHandler(Handler):
    """
    Serializes zip objects.
    
    Zip combines multiple iterables element-wise.
    """
    
    type_name = "zip"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a zip."""
        return type(obj).__name__ == 'zip'
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract zip state.
        
        We exhaust the zip and capture remaining tuples.
        """
        remaining = list(obj)  # exhausts the zip
        
        return {
            "remaining": remaining,  # list of tuples
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """Reconstruct zip from remaining values."""
        return iter(state["remaining"])

