"""
Handler for class instances and class objects.

This is the most complex handler - it handles all user-defined class instances
using the extraction strategy hierarchy we designed.

AI helped me with technical details, but:
- all of the basic structure is mine.
- comments and code has all been reviewed (and revised if needed) by me.

Do I know how this works? Yes.
DO I know every internal attribute and method? No. That's where AI came in,
so I didn't have to crawl Stack Overflow myself.

Cheers
"""

import types
import importlib
import inspect
from typing import Any, Dict, List, Tuple
from .base_class import Handler


class ClassInstanceHandler(Handler):
    """
    Serializes instances of user-defined classes.
    
    This is the catch-all for class instances. It uses this strategy:
    
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
        - Has a __dict__, __slots__, or custom serialization methods
        
        We check for this LAST in the handler chain, after all
        specialized handlers have had a chance.

        We DONT want to handle a special object with this more general handler.
        """
        # skip built-in types (handled by base pickle)
        if isinstance(obj, (int, float, str, bytes, bool, type(None),
                           list, tuple, dict, set, frozenset)):
            return False
        
        # skip types from built-in modules
        obj_module = getattr(type(obj), '__module__', '')
        if obj_module in ('builtins', '__builtin__', 'typing'):
            return False
        
        # must have a class
        if not hasattr(obj, '__class__'):
            return False
        
        # must have __dict__, __slots__, OR custom serialization methods
        has_dict = hasattr(obj, '__dict__')
        has_slots = hasattr(type(obj), '__slots__')
        has_serialize = hasattr(obj, '__serialize__')
        has_to_dict = hasattr(obj, 'to_dict')
        
        return has_dict or has_slots or has_serialize or has_to_dict
    
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
        
        # determine extraction strategy
        strategy = self._determine_strategy(obj)
        
        # base state with class identity
        state = {
            "module": obj_class.__module__,
            "qualname": obj_class.__qualname__,
            "strategy": strategy,
        }
        
        # check if this is a locally-defined class (inside a function/method)
        if "<locals>" in obj_class.__qualname__:
            # locally-defined class - must serialize the class definition
            state["class_definition"] = self._serialize_class_definition(obj_class)
        
        # extract nested class definitions if this is a nested class
        nested_classes = self._extract_nested_classes(obj_class)
        if nested_classes:
            state["nested_classes"] = nested_classes

        # if the class lives in __main__, include its definition for reconstruction
        if obj_class.__module__ == "__main__":
            state["class_definition"] = self._serialize_class_definition(
                obj_class,
                allow_callables=True,
            )
        
        # extract state based on strategy
        if strategy == "custom_serialize":
            # user provided __serialize__ method (module-level class)
            state["custom_state"] = obj.__serialize__()
            
        elif strategy == "custom_serialize_local":
            # user provided __serialize__/__deserialize__ for locally-defined class
            # save both the state AND the __deserialize__ function
            state["custom_state"] = obj.__serialize__()
            state["deserialize_function"] = obj_class.__deserialize__
            
        elif strategy == "to_dict":
            # library pattern: to_dict() / from_dict()
            state["dict_state"] = obj.to_dict()
            
        elif strategy == "dict":
            # generic: use __dict__ and walk
            state["instance_dict"] = dict(obj.__dict__)
        
        elif strategy == "slots":
            # __slots__ class: extract slot values
            state["slots_dict"] = self._extract_slots(obj)
        
        elif strategy == "dict_and_slots":
            # class has both __dict__ and __slots__
            state["instance_dict"] = dict(obj.__dict__)
            state["slots_dict"] = self._extract_slots(obj)
        
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return state
    
    def _determine_strategy(self, obj: Any) -> str:
        """
        Determine which extraction strategy to use.
        
        Returns: "custom_serialize", "custom_serialize_local", "to_dict", or "dict"
        """
        obj_class = obj.__class__
        
        # check for __serialize__ / __deserialize__
        if hasattr(obj, '__serialize__'):
            if hasattr(obj_class, '__deserialize__'):
                # check if locally-defined
                if "<locals>" in obj_class.__qualname__:

                    # for locally-defined classes, only use custom_serialize_local
                    #   if __deserialize__ is a staticmethod (not a classmethod)
                    # check the descriptor in __dict__
                    if '__deserialize__' in obj_class.__dict__:
                        deserialize_desc = obj_class.__dict__['__deserialize__']
                        if isinstance(deserialize_desc, staticmethod):
                            return "custom_serialize_local"

                    # else: classmethod or regular method - fall through to dict strategy

                else:
                    # module-level class - use normal custom_serialize
                    return "custom_serialize"
        
        # check for to_dict / from_dict
        # same limitation for locally-defined classes
        if hasattr(obj, 'to_dict'):
            if hasattr(obj_class, 'from_dict'):
                if "<locals>" not in obj_class.__qualname__:
                    return "to_dict"

                # else: fall through to dict strategy
        
        # Check for __slots__
        obj_class = obj.__class__
        has_slots = hasattr(obj_class, '__slots__')
        has_dict = hasattr(obj, '__dict__')
        
        if has_slots and has_dict:
            # class has both (can happen when you inherit)
            return "dict_and_slots"
        elif has_slots:
            # only __slots__
            return "slots"
        elif has_dict:
            # only __dict__
            return "dict"
        
        raise ValueError(f"Cannot determine extraction strategy for {type(obj)}")
    
    def _extract_slots(self, obj: Any) -> Dict[str, Any]:
        """
        Extract values from __slots__ attributes.
        
        __slots__ classes don't have __dict__ by default.
        We need to extract each slot attribute value.
        """
        slots_dict = {}
        obj_class = type(obj)
        
        # collect all slots from class and parent classes
        all_slots = set()
        for cls in obj_class.__mro__:
            if hasattr(cls, '__slots__'):
                slots = cls.__slots__
                # __slots__ can be a string, iterable, or dict
                if isinstance(slots, str):
                    all_slots.add(slots)
                elif isinstance(slots, dict):
                    all_slots.update(slots.keys())
                else:
                    all_slots.update(slots)
        
        # extract value for each slot
        for slot_name in all_slots:
            # skip __dict__ and __weakref__ special slots
            if slot_name in ('__dict__', '__weakref__'):
                continue
            
            try:
                value = getattr(obj, slot_name)
                slots_dict[slot_name] = value
            except AttributeError:
                # slot not set (no value)
                pass
        
        return slots_dict
    
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
        
        # check if this class is nested (has '.' in qualname)
        if '.' not in cls.__qualname__:
            return nested
        
        # get all nested classes
        for name, member in inspect.getmembers(cls, inspect.isclass):
            # check if this class is defined inside our class
            if member.__qualname__.startswith(cls.__qualname__ + '.'):
                # serialize the nested class definition
                nested[member.__qualname__] = self._serialize_class_definition(member)
        
        return nested
    
    def _serialize_class_definition(self, cls: type, allow_callables: bool = False) -> Dict[str, Any]:
        """
        Serialize a class definition (not an instance).
        
        This captures the class structure so we can recreate it with type().
        """
        # get base classes
        bases = [
            {
                "module": base.__module__,
                "name": base.__name__,
            }
            for base in cls.__bases__
            if base is not object  # Exclude object base
        ]
        
        # get class attributes (including methods)
        class_dict = {}
        for name, value in cls.__dict__.items():
            # Skip special attributes
            if name.startswith('__') and name.endswith('__'):
                if name in ('__module__', '__qualname__', '__doc__'):
                    class_dict[name] = value
                continue
            
            # include methods, class variables, etc.
            # these will be recursively serialized by central serializer
            class_dict[name] = value
        
        return {
            "name": cls.__name__,
            "qualname": cls.__qualname__,
            "module": cls.__module__,
            "bases": bases,
            "dict": class_dict,
            "allow_callables": allow_callables,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct class instance using appropriate strategy.
        
        Process:
        1. Reconstruct nested classes if any
        2. Get or create the class
        3. Create instance based on strategy
        """
        # reconstruct nested classes first
        if "nested_classes" in state:
            for qualname, class_def in state["nested_classes"].items():
                self._reconstruct_class_definition(class_def)
        
        # get the class
        # check if this is a locally-defined class (has <locals> in qualname)
        if "<locals>" in state["qualname"]:
            # locally-defined class - must reconstruct from definition
            if "class_definition" in state:
                cls = self._reconstruct_class_definition(state["class_definition"])
            else:
                raise DeserializationError(
                    f"Locally-defined class '{state['qualname']}' has no class definition. "
                    f"Cannot reconstruct."
                )
        elif state.get("module") == "__main__" and "class_definition" in state:
            # __main__ class - reconstruct from definition for cross-process safety
            cls = self._reconstruct_class_definition(state["class_definition"])
        else:
            # regular or nested class - try to import
            cls = self._get_class(state["module"], state["qualname"])
        
        # reconstruct based on strategy
        strategy = state["strategy"]
        
        if strategy == "custom_serialize":
            # use class's __deserialize__ method (module-level class)
            return cls.__deserialize__(state["custom_state"])
            
        elif strategy == "custom_serialize_local":
            # locally-defined class with custom __serialize__/__deserialize__
            # the __deserialize__ function was serialized and should be reconstructed
            deserialize_func = state["deserialize_function"]
            
            # call the function with cls and state
            # NOTE: User should define __deserialize__ as @staticmethod that takes (cls, state)
            return deserialize_func(cls, state["custom_state"])
            
        elif strategy == "to_dict":
            # use class's from_dict method
            return cls.from_dict(state["dict_state"])
            
        elif strategy == "dict":
            # generic reconstruction using __new__
            obj = cls.__new__(cls)  # type: ignore
            # populate __dict__ (already deserialized by central deserializer)
            if isinstance(state["instance_dict"], dict):
                obj.__dict__.update(state["instance_dict"])
            return obj
        
        elif strategy == "slots":
            # __slots__ reconstruction
            obj = cls.__new__(cls)  # type: ignore
            # set each slot value
            if isinstance(state["slots_dict"], dict):
                for slot_name, value in state["slots_dict"].items():
                    try:
                        setattr(obj, slot_name, value)
                    except AttributeError:
                        # slot might be read-only or not exist, skip
                        # it is what it is in this case
                        pass
            return obj
        
        elif strategy == "dict_and_slots":
            # both __dict__ and __slots__
            obj = cls.__new__(cls)  # type: ignore

            # populate __dict__
            if isinstance(state.get("instance_dict"), dict):
                obj.__dict__.update(state["instance_dict"])

            # set slot values
            if isinstance(state.get("slots_dict"), dict):
                for slot_name, value in state["slots_dict"].items():
                    try:
                        setattr(obj, slot_name, value)
                    except AttributeError:
                        pass
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
        # import module
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            raise ImportError(
                f"Cannot import module '{module_name}'. "
                f"Ensure the module exists in the target process."
            )
        
        # navigate to class using qualname
        # qualname might be "Outer.Inner.DeepNested", we need to handle this
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
        
        This is used for nested/locally-defined classes that were serialized.
        
        NOTE: class_def["dict"] contains the IR (intermediate representation) of
        class attributes/methods. We don't deserialize them here - we just pass
        them to type(). This means methods won't work correctly, but the class
        will exist and can be used for isinstance checks.
        
        For fully functional reconstruction of locally-defined classes with
        methods, users should move the class to module level or use pickle directly.

        This is a known limitation of Python, and good practice is to avoid
        locally-defined classes with methods when parallelizing or sending CL.
        """
        # get base classes
        bases = []
        for base_info in class_def["bases"]:
            base_module = importlib.import_module(base_info["module"])
            base_class = getattr(base_module, base_info["name"])
            bases.append(base_class)
        
        if not bases:
            bases = [object]
        
        # NOTE: class_def["dict"] is in IR format (serialized by central serializer)
        # For basic attributes this works fine, but methods will be broken
        # This is a known limitation for locally-defined classes

        # To properly reconstruct, we'd need access to the deserializer here,
        # but that creates circular dependencies. Instead, we create a minimal
        # class definition that can at least be used for isinstance checks.

        # Hey, this is the best that Python lets us do.
        
        allow_callables = class_def.get("allow_callables", False)
        class_dict = {}
        for key, value in class_def["dict"].items():
            # skip anything that's a cerial-serialized object (has __cerial_type__)
            if isinstance(value, dict) and "__cerial_type__" in value:
                continue

            if not allow_callables:
                # skip methods, functions, and descriptors for local classes
                if callable(value) or isinstance(value, (classmethod, staticmethod, property)):
                    continue
                # skip private/special attributes
                if key.startswith('_'):
                    continue

            class_dict[key] = value
        
        # create class using type()
        cls = type(
            class_def["name"],
            tuple(bases),
            class_dict
        )
        
        # set __module__ and __qualname__
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
        # check if class is at module level
        try:
            module = importlib.import_module(obj.__module__)
            # try to get class from module
            module_class = getattr(module, obj.__name__, None)
            is_module_level = module_class is obj
        except (ImportError, AttributeError):
            # module doesn't exist or class not in module - it's dynamic
            is_module_level = False
        except Exception as e:
            # unexpected error - log and treat as dynamic
            import warnings
            warnings.warn(f"Error checking if class is module-level: {e}")
            is_module_level = False
        
        if is_module_level:
            # simple reference
            return {
                "type": "reference",
                "module": obj.__module__,
                "name": obj.__name__,
            }
        else:
            # dynamic class - serialize full definition
            instance_handler = ClassInstanceHandler()
            return {
                "type": "definition",
                "definition": instance_handler._serialize_class_definition(obj),
            }
    
    def reconstruct(self, state: Dict[str, Any]) -> type:
        """Reconstruct class object."""
        if state["type"] == "reference":
            # import and return class
            module = importlib.import_module(state["module"])
            return getattr(module, state["name"])
        else:
            # reconstruct dynamic class
            instance_handler = ClassInstanceHandler()
            return instance_handler._reconstruct_class_definition(state["definition"])

