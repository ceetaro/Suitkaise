"""
Handler for class instances and class objects.

This is the most complex handler - it handles all user-defined class instances
using the extraction strategy hierarchy we designed.
"""

import types
import importlib
import inspect
from typing import Any, Dict, List, Tuple
from .base_class import Handler


class ClassInstanceHandler(Handler):
    """
    Serializes instances of user-defined classes.
    
    This is the "catch-all" handler for class instances. It uses the
    extraction strategy hierarchy:
    
    1. Try __serialize__ / __deserialize__ methods (highest priority)
    2. Try to_dict() / from_dict() methods (common library pattern)
    3. Fall back to __dict__ access (works for most classes)
    
    Also handles:
    - Nested classes (classes defined inside other classes)
    - Classes in __main__ (which pickle can't handle)
    - Dynamically created classes
    """
    
    type_name = "class_instance"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a class instance.
        
        We handle any object that:
        - Is not a built-in type
        - Is not a primitive type
        - Has a __dict__ or custom serialization methods
        
        We check for this LAST in the handler chain, after all
        specialized handlers have had a chance.
        """
        # Skip built-in types (they're handled elsewhere or by pickle)
        if isinstance(obj, (int, float, str, bytes, bool, type(None),
                           list, tuple, dict, set, frozenset)):
            return False
        
        # Skip types from built-in modules
        obj_module = getattr(type(obj), '__module__', '')
        if obj_module in ('builtins', '__builtin__', 'typing'):
            return False
        
        # Must have a class
        if not hasattr(obj, '__class__'):
            return False
        
        # Must have __dict__ OR custom serialization methods
        has_dict = hasattr(obj, '__dict__')
        has_serialize = hasattr(obj, '__serialize__')
        has_to_dict = hasattr(obj, 'to_dict')
        
        return has_dict or has_serialize or has_to_dict
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract class instance state using strategy hierarchy.
        
        Process:
        1. Try __serialize__ method (user custom serialization)
        2. Try to_dict/from_dict pattern (library pattern)
        3. Fall back to __dict__ (generic)
        
        Also extracts:
        - Class identity (module + qualname)
        - Nested class definitions (if class is nested)
        """
        obj_class = obj.__class__
        
        # Determine extraction strategy
        strategy = self._determine_strategy(obj)
        
        # Base state with class identity
        state = {
            "module": obj_class.__module__,
            "qualname": obj_class.__qualname__,
            "strategy": strategy,
        }
        
        # Extract nested class definitions if this is a nested class
        nested_classes = self._extract_nested_classes(obj_class)
        if nested_classes:
            state["nested_classes"] = nested_classes
        
        # Extract state based on strategy
        if strategy == "custom_serialize":
            # User provided __serialize__ method
            state["custom_state"] = obj.__serialize__()
            
        elif strategy == "to_dict":
            # Library pattern: to_dict() / from_dict()
            state["dict_state"] = obj.to_dict()
            
        elif strategy == "dict":
            # Generic: use __dict__
            state["instance_dict"] = dict(obj.__dict__)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return state
    
    def _determine_strategy(self, obj: Any) -> str:
        """
        Determine which extraction strategy to use.
        
        Returns: "custom_serialize", "to_dict", or "dict"
        """
        # Check for __serialize__ / __deserialize__
        if hasattr(obj, '__serialize__'):
            obj_class = obj.__class__
            if hasattr(obj_class, '__deserialize__'):
                return "custom_serialize"
        
        # Check for to_dict / from_dict
        if hasattr(obj, 'to_dict'):
            obj_class = obj.__class__
            if hasattr(obj_class, 'from_dict'):
                return "to_dict"
        
        # Fall back to __dict__
        if hasattr(obj, '__dict__'):
            return "dict"
        
        raise ValueError(f"Cannot determine extraction strategy for {type(obj)}")
    
    def _extract_nested_classes(self, cls: type) -> Dict[str, Dict]:
        """
        Extract nested class definitions.
        
        If a class is defined inside another class, we need to serialize
        the nested class definition so we can reconstruct it.
        
        Example:
            class Outer:
                class Inner:
                    pass
        
        We need to serialize Inner's definition.
        
        TODO: This implementation has limitations:
        - Does not handle decorators on nested classes
        - Does not handle metaclasses properly
        - Does not handle __slots__
        - May fail with complex class hierarchies
        - Dynamically created nested classes might not reconstruct correctly
        
        For production use, consider:
        1. Requiring users to define nested classes at module level
        2. Implementing custom __serialize__/__deserialize__ for complex nested classes
        3. Or accepting these limitations for simple nested classes only
        """
        nested = {}
        
        # Check if this class is nested (has '.' in qualname)
        if '.' not in cls.__qualname__:
            return nested
        
        # Get all nested classes
        for name, member in inspect.getmembers(cls, inspect.isclass):
            # Check if this class is defined inside our class
            if member.__qualname__.startswith(cls.__qualname__ + '.'):
                # Serialize the nested class definition
                nested[member.__qualname__] = self._serialize_class_definition(member)
        
        return nested
    
    def _serialize_class_definition(self, cls: type) -> Dict[str, Any]:
        """
        Serialize a class definition (not an instance).
        
        This captures the class structure so we can recreate it with type().
        """
        # Get base classes
        bases = [
            {
                "module": base.__module__,
                "name": base.__name__,
            }
            for base in cls.__bases__
            if base is not object  # Exclude object base
        ]
        
        # Get class attributes (including methods)
        class_dict = {}
        for name, value in cls.__dict__.items():
            # Skip special attributes
            if name.startswith('__') and name.endswith('__'):
                if name in ('__module__', '__qualname__', '__doc__'):
                    class_dict[name] = value
                continue
            
            # Include methods, class variables, etc.
            # These will be recursively serialized by central serializer
            class_dict[name] = value
        
        return {
            "name": cls.__name__,
            "qualname": cls.__qualname__,
            "module": cls.__module__,
            "bases": bases,
            "dict": class_dict,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct class instance using appropriate strategy.
        
        Process:
        1. Reconstruct nested classes if any
        2. Get or create the class
        3. Create instance based on strategy
        """
        # Reconstruct nested classes first
        if "nested_classes" in state:
            for qualname, class_def in state["nested_classes"].items():
                self._reconstruct_class_definition(class_def)
        
        # Get the class
        cls = self._get_class(state["module"], state["qualname"])
        
        # Reconstruct based on strategy
        strategy = state["strategy"]
        
        if strategy == "custom_serialize":
            # Use class's __deserialize__ method
            return cls.__deserialize__(state["custom_state"])
            
        elif strategy == "to_dict":
            # Use class's from_dict method
            return cls.from_dict(state["dict_state"])
            
        elif strategy == "dict":
            # Generic reconstruction using __new__
            obj = cls.__new__(cls)  # type: ignore
            # Populate __dict__ (already deserialized by central deserializer)
            if isinstance(state["instance_dict"], dict):
                obj.__dict__.update(state["instance_dict"])
            return obj
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    
    def _get_class(self, module_name: str, qualname: str) -> type:
        """
        Get class by module name and qualified name.
        
        Handles:
        - Regular classes (e.g., "MyClass")
        - Nested classes (e.g., "Outer.Inner")
        - Classes in __main__
        """
        # Import module
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            raise ImportError(
                f"Cannot import module '{module_name}'. "
                f"Ensure the module exists in the target process."
            )
        
        # Navigate to class using qualname
        # qualname might be "Outer.Inner.DeepNested"
        parts = qualname.split('.')
        obj: Any = module
        
        for part in parts:
            try:
                obj = getattr(obj, part)
            except AttributeError:
                raise AttributeError(
                    f"Cannot find class '{qualname}' in module '{module_name}'. "
                    f"Ensure the class definition exists in the target process."
                )
        
        if not isinstance(obj, type):
            raise TypeError(f"'{qualname}' is not a class")
        
        return obj
    
    def _reconstruct_class_definition(self, class_def: Dict[str, Any]) -> type:
        """
        Reconstruct a class definition using type().
        
        This is used for nested classes that were serialized.
        """
        # Get base classes
        bases = []
        for base_info in class_def["bases"]:
            base_module = importlib.import_module(base_info["module"])
            base_class = getattr(base_module, base_info["name"])
            bases.append(base_class)
        
        if not bases:
            bases = [object]
        
        # Create class using type()
        cls = type(
            class_def["name"],
            tuple(bases),
            class_def["dict"]
        )
        
        # Set __module__ and __qualname__
        cls.__module__ = class_def["module"]
        cls.__qualname__ = class_def["qualname"]
        
        return cls


class ClassObjectHandler(Handler):
    """
    Serializes class objects themselves (not instances).
    
    Example:
        cls = MyClass  # The class itself, not an instance
    
    For classes defined at module level, we just store module + name.
    For dynamic classes, we serialize the full definition.
    """
    
    type_name = "class_object"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a class object.
        
        Note: We only handle user-defined classes, not built-ins.
        """
        return (
            isinstance(obj, type) and
            not obj.__module__ in ('builtins', '__builtin__')
        )
    
    def extract_state(self, obj: type) -> Dict[str, Any]:
        """
        Extract class object.
        
        For module-level classes, just store module + name.
        For dynamic classes, serialize full definition.
        """
        # Check if class is at module level
        try:
            module = importlib.import_module(obj.__module__)
            # Try to get class from module
            module_class = getattr(module, obj.__name__, None)
            is_module_level = module_class is obj
        except:
            is_module_level = False
        
        if is_module_level:
            # Simple reference
            return {
                "type": "reference",
                "module": obj.__module__,
                "name": obj.__name__,
            }
        else:
            # Dynamic class - serialize full definition
            instance_handler = ClassInstanceHandler()
            return {
                "type": "definition",
                "definition": instance_handler._serialize_class_definition(obj),
            }
    
    def reconstruct(self, state: Dict[str, Any]) -> type:
        """Reconstruct class object."""
        if state["type"] == "reference":
            # Import and return class
            module = importlib.import_module(state["module"])
            return getattr(module, state["name"])
        else:
            # Reconstruct dynamic class
            instance_handler = ClassInstanceHandler()
            return instance_handler._reconstruct_class_definition(state["definition"])

