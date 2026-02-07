"""
Handler for advanced/rare Python objects.

Includes code objects, frame objects, properties, descriptors, and contextvars.

These are rarely needed but important for cucumber's completeness.

AI helped me with technical details, but:
- all of the basic structure is mine.
- comments and code has all been reviewed (and revised if needed) by me.

Do I know how this works? Yes (for the most part).
DO I know every internal attribute and method? No. That's where AI came in,
so I didn't have to crawl Stack Overflow myself.

Cheers
"""

import sys
import types
import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
from .base_class import Handler

# try to import contextvars (3.7+)
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
        # python version check
        python_version = sys.version_info
        
        # common attrs across all python versions
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
        
        # 3.8 added co_posonlyargcount
        if python_version >= (3, 8):
            state["co_posonlyargcount"] = obj.co_posonlyargcount
        
        # 3.10+ uses co_linetable instead of co_lnotab
        if python_version >= (3, 10):
            state["co_linetable"] = obj.co_linetable
        else:
            state["co_lnotab"] = obj.co_lnotab
        
        # 3.11 added these attrs
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
        
        # 3.11+
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
        
        # 3.10
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
        
        # 3.8 - 3.9
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
            # 3.7 and earlier (not officialy supported, but whatever)
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


@dataclass
class FrameInfo:
    """
    Represents serialized frame state.
    
    This is the return type when deserializing frame objects. Python doesn't
    expose a FrameType constructor, so we cannot reconstruct actual frames.
    FrameInfo captures all the useful data from a frame for debugging,
    logging, and error reporting purposes.

    You can use this in Share objects to keep tabs on other processes' frames.
    
    Attributes:
        filename: Source file path
        function_name: Name of the function
        qualname: Qualified name (Python 3.11+)
        lineno: Current line number
        lasti: Index of last attempted instruction in bytecode
        locals: Local variables dict (serializable values only)
        globals_keys: Keys present in globals (full globals not stored)
        code: The code object (fully reconstructed)
        stack_depth: Depth in call stack (0 = innermost)
        parent: Parent FrameInfo (if call stack was serialized)
    
    Example:
        >>> import inspect
        >>> from suitkaise.cucumber import serialize, deserialize
        >>> frame = inspect.currentframe()
        >>> data = serialize(frame)
        >>> info = deserialize(data)  # Returns FrameInfo, not a frame
        >>> print(f"{info.function_name} at {info.filename}:{info.lineno}")
    """
    filename: str
    function_name: str
    qualname: str
    lineno: int
    lasti: int
    locals: Dict[str, Any] = field(default_factory=dict)
    globals_keys: Tuple[str, ...] = field(default_factory=tuple)
    code: Optional[types.CodeType] = None
    stack_depth: int = 0
    parent: Optional["FrameInfo"] = None
    
    def __repr__(self) -> str:
        return (
            f"FrameInfo({self.function_name!r} at {self.filename}:{self.lineno}, "
            f"locals={list(self.locals.keys())}, depth={self.stack_depth})"
        )


class FrameObjectHandler(Handler):
    """
    Serializes frame objects.
    
    Frame objects represent execution frames (stack frames).
    They contain code, local/global variables, and form the call stack.
    
    Features:
    - Extracts code object (fully reconstructible)
    - Captures local variables (serializable ones)
    - Records global variable keys (not values - too large)
    - Optionally captures parent frames (call stack)
    
    Limitation:
        Frame objects CANNOT be fully reconstructed. Python doesn't expose
        a FrameType constructor - frames are created internally by the
        interpreter during function execution. On reconstruction, this
        handler returns a FrameInfo dataclass instead of an actual frame.
        
        This is sufficient for debugging, logging, and error reporting,
        but you cannot resume execution from a serialized frame.
    """
    
    type_name = "frame_object"
    
    # types that are safe to include in locals serialization
    _SAFE_TYPES = (int, float, str, bytes, bool, type(None), list, dict, tuple, set, frozenset)
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a frame."""
        return isinstance(obj, types.FrameType)
    
    def _is_serializable_value(self, value: Any) -> bool:
        """
        Check if a value is safe to serialize.
        
        We skip complex objects like modules, frames, and tracebacks
        to avoid infinite recursion and large serialization.
        """
        # basic types are always safe
        if isinstance(value, self._SAFE_TYPES):
            return True
        
        # skip problematic types
        if isinstance(value, (types.ModuleType, types.FrameType, types.TracebackType)):
            return False
        
        # skip callables that might be complex closures
        if callable(value) and not isinstance(value, type):
            return False
        
        # allow other types (will be handled by other handlers)
        return True
    
    def _extract_safe_locals(self, frame: types.FrameType) -> Dict[str, Any]:
        """
        Extract local variables that are safe to serialize.
        
        Filters out modules, frames, tracebacks, and other problematic types.
        """
        safe_locals = {}
        for key, value in frame.f_locals.items():
            if self._is_serializable_value(value):
                safe_locals[key] = value
        return safe_locals
    
    def extract_state(
        self, 
        obj: types.FrameType, 
        *, 
        include_parent: bool = True,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Extract comprehensive frame state.
        
        Frames contain:
        - f_code: Code object (bytecode, names, etc.)
        - f_locals: Local variables
        - f_globals: Global namespace (we only store keys)
        - f_lineno: Current line number
        - f_lasti: Last bytecode instruction index
        - f_back: Previous frame in call stack
        - f_builtins: Built-in namespace (not stored)
        - f_trace: Tracing function (not stored)
        
        Args:
            obj: Frame object to serialize
            include_parent: Whether to include parent frames (call stack)
            max_depth: Maximum call stack depth to serialize
            
        Returns:
            State dict with frame data
        """
        code = obj.f_code
        
        state = {
            # location info
            "filename": code.co_filename,
            "function_name": code.co_name,
            "qualname": getattr(code, 'co_qualname', code.co_name),  # 3.11+
            "lineno": obj.f_lineno,
            "lasti": obj.f_lasti,
            
            # code object (will be recursively serialized by CodeObjectHandler)
            "code": code,
            
            # variables
            "locals": self._extract_safe_locals(obj),
            "globals_keys": tuple(obj.f_globals.keys()),
            
            # stack info
            "stack_depth": 0,
            "has_parent": obj.f_back is not None,
        }
        
        # optionally serialize parent frame (call stack)
        if include_parent and obj.f_back is not None and max_depth > 0:
            parent_state = self.extract_state(
                obj.f_back,
                include_parent=True,
                max_depth=max_depth - 1
            )
            parent_state["stack_depth"] = state["stack_depth"] + 1
            state["parent"] = parent_state
        else:
            state["parent"] = None
        
        return state
    
    def reconstruct(self, state: Dict[str, Any]) -> FrameInfo:
        """
        Reconstruct frame as FrameInfo.
        
        Python doesn't expose a FrameType constructor, so we can't create
        actual frame objects. Instead, we return a FrameInfo dataclass
        that captures all the serialized frame data.

        This is the best that Python lets us do.

        Nothing else even tries so I wanted to at least give info.
        
        The FrameInfo object contains:
        - All location/metadata info
        - The reconstructed code object
        - Local variables
        - Parent frame info (if serialized)
        
        Returns:
            FrameInfo object with frame state
        """
        # reconstruct parent first (if present)
        parent_info = None
        if state.get("parent"):
            parent_info = self.reconstruct(state["parent"])
        
        return FrameInfo(
            filename=state["filename"],
            function_name=state["function_name"],
            qualname=state.get("qualname", state["function_name"]),
            lineno=state["lineno"],
            lasti=state["lasti"],
            locals=state.get("locals", {}),
            globals_keys=tuple(state.get("globals_keys", ())),
            code=state.get("code"),  # will be reconstructed by CodeObjectHandler
            stack_depth=state.get("stack_depth", 0),
            parent=parent_info,
        )


class PropertyHandler(Handler):
    """
    Serializes property objects.
    
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
            "fget": obj.fget,  # will be recursively serialized
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
    Serializes descriptor objects.
    
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
        # check for descriptor protocol
        has_get = hasattr(type(obj), '__get__')
        has_set = hasattr(type(obj), '__set__')
        has_delete = hasattr(type(obj), '__delete__')
        
        is_descriptor = has_get or has_set or has_delete
        
        # exclude property (we have a separate handler)
        if isinstance(obj, property):
            return False
        
        # exclude functions (we handle separately)
        if isinstance(obj, (types.FunctionType, types.MethodType)):
            return False
        
        return is_descriptor
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract descriptor state.
        
        For custom descriptors, we try to extract __dict__.
        """
        owner = getattr(obj, "__objclass__", None)
        owner_module = getattr(owner, "__module__", None) if owner is not None else None
        owner_name = getattr(owner, "__name__", None) if owner is not None else None
        attr_name = getattr(obj, "__name__", None)

        return {
            "class_module": type(obj).__module__,
            "class_name": type(obj).__name__,
            "instance_dict": obj.__dict__ if hasattr(obj, '__dict__') else {},
            "owner_module": owner_module,
            "owner_name": owner_name,
            "attr_name": attr_name,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct descriptor using __new__.
        
        Import the class and create new instance.
        """
        import importlib
        import types
        from dataclasses import dataclass
        
        @dataclass
        class _DescriptorPlaceholder:
            class_module: str
            class_name: str
            instance_dict: dict
            
            def __repr__(self) -> str:
                return f"<descriptor {self.class_module}.{self.class_name} (placeholder)>"
        
        owner_module = state.get("owner_module")
        owner_name = state.get("owner_name")
        attr_name = state.get("attr_name")
        if owner_module and owner_name and attr_name:
            try:
                owner_mod = importlib.import_module(owner_module)
                owner_cls = getattr(owner_mod, owner_name)
                return getattr(owner_cls, attr_name)
            except Exception:
                pass

        module = importlib.import_module(state["class_module"])
        try:
            cls = getattr(module, state["class_name"])
        except AttributeError:
            # Some builtin descriptor types report module "builtins" but live in types.
            type_map = {
                "wrapper_descriptor": getattr(types, "WrapperDescriptorType", None),
                "method_descriptor": getattr(types, "MethodDescriptorType", None),
                "builtin_function_or_method": getattr(types, "BuiltinFunctionType", None),
                "method-wrapper": getattr(types, "MethodWrapperType", None),
            }
            cls = type_map.get(state["class_name"])
            if cls is None:
                return _DescriptorPlaceholder(
                    state["class_module"],
                    state["class_name"],
                    state.get("instance_dict", {}),
                )
        
        # create instance without calling __init__
        try:
            obj = cls.__new__(cls)
            obj.__dict__ = state["instance_dict"]
            return obj
        except Exception:
            # Fall back to returning the descriptor type itself.
            return cls

