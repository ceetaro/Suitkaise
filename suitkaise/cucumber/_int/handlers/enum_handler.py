"""
Handler for enum objects.

Enums (from the enum module) are commonly used in Python for defining
named constants. We need to handle both Enum instances and Enum classes.
"""

import enum
import importlib
from typing import Any, Dict
from .base_class import Handler


class EnumSerializationError(Exception):
    """Raised when enum serialization fails."""
    pass


class EnumHandler(Handler):
    """
    Serializes enum.Enum instances.
    
    Strategy:
    - Store the enum class (module + qualname) and the enum value
    - On reconstruction, import the enum class and get the member by value
    
    Example:
        from enum import Enum
        class Color(Enum):
            RED = 1
            GREEN = 2
            BLUE = 3
        
        color = Color.RED
        # Serializes as: {"module": "__main__", "enum_name": "Color", "value": 1}
    
    This works for:
    - Standard Enum
    - IntEnum
    - Flag
    - IntFlag
    - Custom enum subclasses
    """
    
    type_name = "enum"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is an Enum instance.
        
        We check if the object is an instance of enum.Enum.
        """
        return isinstance(obj, enum.Enum)
    
    def extract_state(self, obj: enum.Enum) -> Dict[str, Any]:
        """
        Extract enum instance state.
        
        What we capture:
        - module: Module name where enum is defined
        - enum_name: Name of the enum class
        - member_name: Name of the specific enum member
        - value: Value of the enum member
        
        We store both name and value for robustness. If the enum changes
        between serialization and deserialization, we can still try to
        match by value.
        """
        enum_class = type(obj)
        definition = None
        if not self._is_module_level_enum(enum_class):
            definition = self._extract_enum_definition(enum_class)
        
        member_names = None
        if isinstance(obj, enum.Flag):
            member_names = [member.name for member in enum_class if member in obj]
        
        return {
            "module": enum_class.__module__,
            "enum_name": enum_class.__name__,
            "qualname": enum_class.__qualname__,
            "member_name": obj.name,
            "value": obj.value,  # the actual value (int, str, etc.)
            "member_names": member_names,
            "definition": definition,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> enum.Enum:
        """
        Reconstruct enum instance.
        
        Process:
        1. Import the enum class by module + name
        2. Try to get member by name (fastest, most reliable)
        3. If that fails, try to get member by value (fallback)
        4. If both fail, raise error
        """
        enum_class = None
        try:
            module = importlib.import_module(state["module"])
            parts = state["qualname"].split('.')
            enum_class = module
            for part in parts:
                enum_class = getattr(enum_class, part)
            if not isinstance(enum_class, type) or not issubclass(enum_class, enum.Enum):
                enum_class = None
        except Exception:
            enum_class = None
        
        if enum_class is None and state.get("definition"):
            enum_class = self._reconstruct_enum_definition(state["definition"])
        
        if enum_class is None:
            raise EnumSerializationError(
                f"Cannot resolve enum '{state['qualname']}' from module '{state['module']}'."
            )
        
        # try to get enum member by name first (most reliable)
        try:
            return enum_class[state["member_name"]]
        except KeyError:
            # member name doesn't exist, try by value
            pass

        # handle Flag/IntFlag combined members
        member_names = state.get("member_names") or []
        if member_names:
            try:
                combined = None
                for name in member_names:
                    member = enum_class[name]
                    combined = member if combined is None else combined | member
                if combined is not None:
                    return combined
            except Exception:
                pass
        
        # fallback: try to get member by value
        try:
            return enum_class(state["value"])
        except ValueError as e:
            raise EnumSerializationError(
                f"Cannot reconstruct enum {state['enum_name']}.{state['member_name']}. "
                f"Neither member name '{state['member_name']}' nor value {state['value']} "
                f"exist in the enum. The enum definition may have changed."
            ) from e

    def _is_module_level_enum(self, enum_class: type) -> bool:
        try:
            module = importlib.import_module(enum_class.__module__)
            module_enum = getattr(module, enum_class.__name__, None)
            return module_enum is enum_class
        except Exception:
            return False

    def _extract_enum_definition(self, enum_class: type) -> Dict[str, Any]:
        members = {}
        for member in enum_class:
            members[member.name] = member.value
        
        base_type = None
        for base in enum_class.__mro__[1:]:
            if base in (enum.Enum, enum.IntEnum, enum.Flag, enum.IntFlag):
                base_type = base.__name__
                break
        
        if base_type is None:
            base_type = "Enum"
        
        return {
            "type": "definition",
            "name": enum_class.__name__,
            "members": members,
            "base_type": base_type,
        }

    def _reconstruct_enum_definition(self, definition: Dict[str, Any]) -> type:
        base_type = getattr(enum, definition["base_type"], enum.Enum)
        return base_type(definition["name"], definition["members"])


class EnumClassHandler(Handler):
    """
    Serializes enum.Enum classes (not instances, the class itself).
    
    Example:
        from enum import Enum
        class Color(Enum):
            RED = 1
            GREEN = 2
        
        cls = Color  # The class itself, not an instance
    
    For module-level enums, we just store the module + name.
    For dynamically created enums, we store the full definition.
    """
    
    type_name = "enum_class"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is an Enum class (not instance).
        
        We check if it's a type that is a subclass of enum.Enum.
        """
        return (
            isinstance(obj, type) and
            issubclass(obj, enum.Enum) and
            obj is not enum.Enum  # Exclude the Enum base class itself
        )
    
    def extract_state(self, obj: type) -> Dict[str, Any]:
        """
        Extract enum class.
        
        For module-level enums, just store module + name.
        For dynamic enums, serialize the full definition.
        """
        # check if enum is at module level
        try:
            module = importlib.import_module(obj.__module__)
            module_enum = getattr(module, obj.__name__, None)
            is_module_level = module_enum is obj
        except (ImportError, AttributeError):
            # module doesn't exist or enum not in module - it's dynamic
            is_module_level = False
        except Exception as e:
            # unexpected error - log and treat as dynamic
            import warnings
            warnings.warn(f"Error checking if enum is module-level: {e}")
            is_module_level = False
        
        if is_module_level:
            # simple reference
            return {
                "type": "reference",
                "module": obj.__module__,
                "name": obj.__name__,
            }
        else:
            # dynamic enum - serialize definition
            # get all members and their values
            members = {}
            for member in obj:
                members[member.name] = member.value
            
            # get base enum type (Enum, IntEnum, Flag, etc.)
            base_type = None
            for base in obj.__mro__[1:]:
                if base in (enum.Enum, enum.IntEnum, enum.Flag, enum.IntFlag):
                    base_type = base.__name__
                    break
            
            if base_type is None:
                base_type = "Enum"  # default
            
            return {
                "type": "definition",
                "name": obj.__name__,
                "members": members,
                "base_type": base_type,
            }
    
    def reconstruct(self, state: Dict[str, Any]) -> type:
        """Reconstruct enum class."""
        if state["type"] == "reference":
            # import and return enum class
            module = importlib.import_module(state["module"])
            return getattr(module, state["name"])
        else:
            # reconstruct dynamic enum
            base_type = getattr(enum, state["base_type"], enum.Enum)
            
            # create enum using functional API
            return base_type(state["name"], state["members"])

