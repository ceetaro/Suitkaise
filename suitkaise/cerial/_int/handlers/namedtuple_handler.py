"""
Handler for NamedTuple objects.

NamedTuples come in two flavors:
1. collections.namedtuple() - factory function (pickle-native)
2. typing.NamedTuple - class-based syntax (may need special handling)

Both create tuple subclasses with named fields.
"""

from typing import Any, Dict
from .base_class import Handler


class NamedTupleSerializationError(Exception):
    """Raised when NamedTuple serialization fails."""
    pass


class NamedTupleHandler(Handler):
    """
    Serializes NamedTuple objects.
    
    Strategy:
    - Extract the values and field names
    - Store the class definition (module + name)
    - On reconstruction, recreate using the class
    
    Note: collections.namedtuple instances are usually pickle-native,
    but we handle them explicitly for consistency and to support
    dynamically created namedtuples that might not be importable.
    """
    
    type_name = "namedtuple"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a NamedTuple instance.
        
        NamedTuples are tuple subclasses with _fields attribute.
        """
        # Must be a tuple subclass
        if not isinstance(obj, tuple):
            return False
        
        # Must have _fields attribute (namedtuples have this)
        if not hasattr(type(obj), '_fields'):
            return False
        
        # Must have _make classmethod (namedtuples have this)
        if not hasattr(type(obj), '_make'):
            return False
        
        return True
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract NamedTuple state.
        
        What we capture:
        - module: Class module
        - class_name: Class name
        - fields: Field names
        - values: Field values (as tuple)
        - defaults: Default values (if any)
        """
        obj_class = type(obj)
        
        # Get field names
        fields = obj_class._fields
        
        # Get values (just the tuple values)
        values = tuple(obj)
        
        # Get defaults (if any)
        defaults = getattr(obj_class, '_field_defaults', {})
        
        return {
            "module": obj_class.__module__,
            "class_name": obj_class.__name__,
            "qualname": getattr(obj_class, '__qualname__', obj_class.__name__),
            "fields": fields,
            "values": values,  # Will be recursively serialized
            "defaults": defaults,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct NamedTuple.
        
        Try to import the class, or recreate it if needed.
        """
        import importlib
        from collections import namedtuple
        
        # Try to import the class
        try:
            module = importlib.import_module(state["module"])
            parts = state["qualname"].split('.')
            cls = module
            for part in parts:
                cls = getattr(cls, part)
            
            # Verify it's the right namedtuple
            if hasattr(cls, '_fields') and cls._fields == state["fields"]:
                # Use the existing class
                return cls(*state["values"])
        except (ImportError, AttributeError):
            pass
        
        # Can't import or class doesn't match - recreate it
        # Create a new namedtuple class
        cls = namedtuple(
            state["class_name"],
            state["fields"],
            defaults=list(state["defaults"].values()) if state["defaults"] else None
        )
        
        # Create instance
        return cls(*state["values"])


class TypedDictHandler(Handler):
    """
    Serializes typing.TypedDict instances.
    
    TypedDicts are dictionaries with type annotations for keys.
    They're just regular dicts at runtime, but we handle them
    explicitly to preserve type information if needed.
    """
    
    type_name = "typeddict"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a TypedDict instance.
        
        TypedDicts are regular dicts, but their class has __annotations__.
        """
        # Must be a dict
        if not isinstance(obj, dict):
            return False
        
        # Check if the type has __annotations__ and __total__ (TypedDict markers)
        obj_type = type(obj)
        has_annotations = hasattr(obj_type, '__annotations__')
        has_total = hasattr(obj_type, '__total__')
        
        # TypedDict classes have these special attributes
        return has_annotations and has_total and obj_type is not dict
    
    def extract_state(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract TypedDict state.
        
        TypedDicts are just dicts at runtime, so we just need the values.
        """
        obj_class = type(obj)
        
        return {
            "module": obj_class.__module__,
            "class_name": obj_class.__name__,
            "data": dict(obj),  # The actual dict data
            "annotations": getattr(obj_class, '__annotations__', {}),
            "total": getattr(obj_class, '__total__', True),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reconstruct TypedDict.
        
        At runtime, TypedDicts are just dicts, so we can return a regular dict.
        Type information is primarily for static analysis.
        """
        # Try to import the TypedDict class
        import importlib
        
        try:
            module = importlib.import_module(state["module"])
            cls = getattr(module, state["class_name"])
            # Create instance (TypedDict classes can be called like constructors)
            return cls(**state["data"])
        except (ImportError, AttributeError):
            # Can't import - just return regular dict
            # Type information is lost but data is preserved
            return state["data"]

