"""
Handler for advanced/rare Python objects.

Includes code objects, frame objects, properties, descriptors, and contextvars.
These are rarely needed but included for completeness.
"""

import sys
import types
import importlib
from typing import Any, Dict, Optional
from .base_class import Handler

# Try to import contextvars (Python 3.7+)
try:
    import contextvars
    HAS_CONTEXTVARS = True
except ImportError:
    HAS_CONTEXTVARS = False
    contextvars = None  # type: ignore


class AdvancedSerializationError(Exception):
    """Raised when advanced object serialization fails."""
    pass


class CodeObjectHandler(Handler):
    """
    Serializes code objects.
    
    Code objects represent compiled Python bytecode.
    They're used internally by functions and can be serialized.
    
    Note: Code object structure changed in Python 3.8, 3.10, and 3.11+.
    We handle all versions dynamically.
    """
    
    type_name = "code_object"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a code object."""
        return isinstance(obj, types.CodeType)
    
    def extract_state(self, obj: types.CodeType) -> Dict[str, Any]:
        """
        Extract code object components.
        
        Code objects contain bytecode and metadata.
        Python versions have different attributes:
        - 3.8+ added co_posonlyargcount
        - 3.10+ changed line number table (co_lnotab deprecated, use co_linetable)
        - 3.11+ added co_exceptiontable, co_qualname
        """
        # Python version check
        python_version = sys.version_info
        
        # Common attributes across all Python versions
        state = {
            "co_argcount": obj.co_argcount,
            "co_kwonlyargcount": obj.co_kwonlyargcount,
            "co_nlocals": obj.co_nlocals,
            "co_stacksize": obj.co_stacksize,
            "co_flags": obj.co_flags,
            "co_code": obj.co_code,  # Bytecode
            "co_consts": obj.co_consts,
            "co_names": obj.co_names,
            "co_varnames": obj.co_varnames,
            "co_filename": obj.co_filename,
            "co_name": obj.co_name,
            "co_firstlineno": obj.co_firstlineno,
            "co_freevars": obj.co_freevars,
            "co_cellvars": obj.co_cellvars,
            "python_version": python_version[:2],  # Store version for reconstruction
        }
        
        # Python 3.8+ added co_posonlyargcount
        if python_version >= (3, 8):
            state["co_posonlyargcount"] = obj.co_posonlyargcount
        
        # Python 3.10+ uses co_linetable instead of co_lnotab
        if python_version >= (3, 10):
            state["co_linetable"] = obj.co_linetable
        else:
            state["co_lnotab"] = obj.co_lnotab
        
        # Python 3.11+ added more attributes
        if python_version >= (3, 11):
            if hasattr(obj, 'co_exceptiontable'):
                state["co_exceptiontable"] = obj.co_exceptiontable
            if hasattr(obj, 'co_qualname'):
                state["co_qualname"] = obj.co_qualname
        
        return state
    
    def reconstruct(self, state: Dict[str, Any]) -> types.CodeType:
        """
        Reconstruct code object.
        
        Use types.CodeType constructor with appropriate arguments based on Python version.
        """
        python_version = sys.version_info
        
        # Python 3.11+
        if python_version >= (3, 11):
            args = [
                state["co_argcount"],
                state.get("co_posonlyargcount", 0),
                state["co_kwonlyargcount"],
                state["co_nlocals"],
                state["co_stacksize"],
                state["co_flags"],
                state["co_code"],
                state["co_consts"],
                state["co_names"],
                state["co_varnames"],
                state["co_filename"],
                state["co_name"],
                state.get("co_qualname", state["co_name"]),
                state["co_firstlineno"],
                state.get("co_linetable", b''),
                state.get("co_exceptiontable", b''),
                state["co_freevars"],
                state["co_cellvars"],
            ]
            return types.CodeType(*args)
        
        # Python 3.10
        elif python_version >= (3, 10):
            return types.CodeType(
                state["co_argcount"],
                state.get("co_posonlyargcount", 0),
                state["co_kwonlyargcount"],
                state["co_nlocals"],
                state["co_stacksize"],
                state["co_flags"],
                state["co_code"],
                state["co_consts"],
                state["co_names"],
                state["co_varnames"],
                state["co_filename"],
                state["co_name"],
                state["co_firstlineno"],
                state.get("co_linetable", b''),
                state["co_freevars"],
                state["co_cellvars"]
            )
        
        # Python 3.8-3.9
        elif python_version >= (3, 8):
            return types.CodeType(
                state["co_argcount"],
                state.get("co_posonlyargcount", 0),
                state["co_kwonlyargcount"],
                state["co_nlocals"],
                state["co_stacksize"],
                state["co_flags"],
                state["co_code"],
                state["co_consts"],
                state["co_names"],
                state["co_varnames"],
                state["co_filename"],
                state["co_name"],
                state["co_firstlineno"],
                state.get("co_lnotab", b''),
                state["co_freevars"],
                state["co_cellvars"]
            )
        
        else:
            # Python 3.7 and earlier (not officially supported, but try anyway)
            return types.CodeType(
                state["co_argcount"],
                state["co_kwonlyargcount"],
                state["co_nlocals"],
                state["co_stacksize"],
                state["co_flags"],
                state["co_code"],
                state["co_consts"],
                state["co_names"],
                state["co_varnames"],
                state["co_filename"],
                state["co_name"],
                state["co_firstlineno"],
                state.get("co_lnotab", b''),
                state["co_freevars"],
                state["co_cellvars"]
            )


class FrameObjectHandler(Handler):
    """
    Serializes frame objects (2% importance).
    
    Frame objects represent execution frames (stack frames).
    These are VERY tricky to serialize and reconstruct.
    """
    
    type_name = "frame_object"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a frame."""
        return isinstance(obj, types.FrameType)
    
    def extract_state(self, obj: types.FrameType) -> Dict[str, Any]:
        """
        Extract frame state.
        
        Frames contain:
        - Code object
        - Local variables
        - Global variables
        - Previous frame (forms call stack)
        
        Note: Fully serializing frames is extremely complex.
        We extract what we can.
        """
        return {
            "f_code": obj.f_code,  # Will be recursively serialized
            "f_locals": dict(obj.f_locals),  # Local variables
            "f_globals": dict(obj.f_globals),  # Global variables (careful!)
            "f_lineno": obj.f_lineno,  # Current line number
            # Note: We DON'T serialize f_back (previous frame) to avoid
            # serializing the entire call stack
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> types.FrameType:
        """
        Reconstruct frame.
        
        This is extremely limited. Frames are tied to execution state
        and can't be meaningfully reconstructed outside of their context.
        """
        raise NotImplementedError(
            "Frame objects cannot be meaningfully reconstructed outside their "
            "execution context. Serializing execution state is beyond cerial's scope."
        )


class PropertyHandler(Handler):
    """
    Serializes property objects (2% importance).
    
    Properties are descriptors that provide getter/setter/deleter methods.
    """
    
    type_name = "property"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a property."""
        return isinstance(obj, property)
    
    def extract_state(self, obj: property) -> Dict[str, Any]:
        """
        Extract property components.
        
        Properties have:
        - fget: Getter function
        - fset: Setter function (optional)
        - fdel: Deleter function (optional)
        - __doc__: Documentation string
        """
        return {
            "fget": obj.fget,  # Will be recursively serialized
            "fset": obj.fset,
            "fdel": obj.fdel,
            "doc": obj.__doc__,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> property:
        """Reconstruct property with same functions."""
        return property(
            fget=state["fget"],
            fset=state["fset"],
            fdel=state["fdel"],
            doc=state["doc"]
        )


class DescriptorHandler(Handler):
    """
    Serializes descriptor objects (2% importance).
    
    Descriptors implement __get__, __set__, or __delete__.
    This is a catch-all for custom descriptors.
    """
    
    type_name = "descriptor"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a descriptor.
        
        Descriptors have __get__, __set__, or __delete__ methods.
        We check for these but exclude common types we handle elsewhere.
        """
        # Check for descriptor protocol
        has_get = hasattr(type(obj), '__get__')
        has_set = hasattr(type(obj), '__set__')
        has_delete = hasattr(type(obj), '__delete__')
        
        is_descriptor = has_get or has_set or has_delete
        
        # Exclude property (we have separate handler)
        if isinstance(obj, property):
            return False
        
        # Exclude functions (they're descriptors but we handle separately)
        if isinstance(obj, (types.FunctionType, types.MethodType)):
            return False
        
        return is_descriptor
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract descriptor state.
        
        For custom descriptors, we try to extract __dict__.
        """
        return {
            "class_module": type(obj).__module__,
            "class_name": type(obj).__name__,
            "instance_dict": obj.__dict__ if hasattr(obj, '__dict__') else {},
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct descriptor.
        
        Import the class and create new instance.
        """
        import importlib
        
        module = importlib.import_module(state["class_module"])
        cls = getattr(module, state["class_name"])
        
        # Create instance without calling __init__
        obj = cls.__new__(cls)
        obj.__dict__ = state["instance_dict"]
        
        return obj

