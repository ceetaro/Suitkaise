"""
Skpath Autopath Decorator

Automatic path type conversion based on function parameter annotations.
Converts inputs to match the declared type: Skpath, Path, or str.
"""

from __future__ import annotations

import functools
import inspect
import sys
import threading
import types
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, TypeVar, Union, get_args, get_origin

from .caller_paths import get_caller_path_raw
from .skpath import Skpath

# thread-safe lock
_autopath_lock = threading.RLock()

# Type variable for decorated function
F = TypeVar("F", bound=Callable[..., Any])

# types that are considered "path-like"
PATH_TYPES: frozenset[type] = frozenset({str, Path, Skpath})


def _is_skpath_type(t: Any) -> bool:
    """Check if a type is Skpath (handles forward references)."""
    if t is Skpath:
        return True
    # handle forward reference strings
    if isinstance(t, str) and t == "Skpath":
        return True
    # handle typing.ForwardRef
    if hasattr(t, "__forward_arg__") and t.__forward_arg__ == "Skpath":
        return True
    return False


def _is_path_type(t: Any) -> bool:
    """Check if a type is Path."""
    return t is Path


def _is_str_type(t: Any) -> bool:
    """Check if a type is str."""
    return t is str


def _is_union_type(origin: Any) -> bool:
    """Check if an origin type is a Union (typing.Union or types.UnionType)."""
    if origin is Union:
        return True
    # Python 3.10+ uses types.UnionType for X | Y syntax
    if sys.version_info >= (3, 10) and origin is types.UnionType:
        return True
    return False


def _get_base_type_from_annotation(annotation: Any) -> type | None:
    """
    Extract the target path type from a type annotation.
    
    Returns:
        - Skpath if annotation is Skpath or AnyPath (Union containing Skpath)
        - Path if annotation is Path
        - str if annotation is str
        - None if annotation is not a path type
    """
    # direct type match
    if _is_skpath_type(annotation):
        return Skpath
    if _is_path_type(annotation):
        return Path
    if _is_str_type(annotation):
        return str
    
    # handle Union types (e.g., AnyPath = str | Path | Skpath)
    # supports both typing.Union and Python 3.10+ X | Y syntax
    origin = get_origin(annotation)
    if _is_union_type(origin):
        args = get_args(annotation)
        # If Skpath is in the union, target Skpath (richest type)
        if any(_is_skpath_type(arg) for arg in args):
            return Skpath
        if any(_is_path_type(arg) for arg in args):
            return Path
        if any(_is_str_type(arg) for arg in args):
            return str
    
    return None


def _get_iterable_element_type(annotation: Any) -> tuple[type | None, type | None]:
    """
    Check if annotation is an iterable of path types.
    
    Returns:
        (container_type, element_type) or (None, None) if not a path iterable
    """
    origin = get_origin(annotation)
    
    # check for common iterables (get_origin returns lowercase in 3.9+)
    if origin is list:
        container = list
    elif origin is tuple:
        container = tuple
    elif origin is set:
        container = set
    elif origin is frozenset:
        container = frozenset
    elif origin is Iterable:
        container = list  # convert to list for general Iterable
    else:
        return None, None
    
    # get the element type
    args = get_args(annotation)
    if not args:
        return None, None
    
    # for tuple, handle tuple[X, ...] and tuple[X, Y, Z]
    element_type = args[0]
    
    # get the base path type from element
    base_type = _get_base_type_from_annotation(element_type)
    if base_type is not None:
        return container, base_type
    
    return None, None


def _convert_value(
    value: Any,
    target_type: type,
    param_name: str,
    debug: bool,
) -> Any:
    """
    Convert a value to the target path type.
    
    All path-like inputs (str, Path) are first normalized through Skpath,
    then converted to the target type. This ensures consistent path handling:
    - Resolved absolute paths
    - Normalized separators (always /)
    - Cross-platform consistency
    
    Args:
        value: Value to convert
        target_type: Target type (Skpath, Path, or str)
        param_name: Parameter name (for debug output)
        debug: Whether to print debug messages
        
    Returns:
        Converted value
    """
    if value is None:
        return None
    
    original_type = type(value).__name__
    original_value = str(value) if isinstance(value, (str, Path)) else None
    
    # all paths flow through Skpath for normalization: input → Skpath → target type
    if target_type is Skpath:
        if isinstance(value, Skpath):
            result = value
        elif isinstance(value, (str, Path)):
            try:
                result = Skpath(value)
            except Exception:
                return value  # can't convert, return as is
        else:
            return value
            
    elif target_type is Path:
        if isinstance(value, Skpath):
            result = Path(value.ap)
        elif isinstance(value, (str, Path)):
            try:
                # normalize through Skpath, then convert to Path
                result = Path(Skpath(value).ap)
            except Exception:
                result = Path(value) if isinstance(value, str) else value
        else:
            return value
            
    elif target_type is str:
        if isinstance(value, Skpath):
            result = value.ap
        elif isinstance(value, (str, Path)):
            try:
                # normalize through Skpath, then extract string
                result = Skpath(value).ap
            except Exception:
                result = str(value) # fall back to simple str conversion
        else:
            return value
    else:
        return value
    
    if debug:
        result_str = str(result) if isinstance(result, (str, Path, Skpath)) else None
        if type(value) != type(result):
            print(f"@autopath: Converted {param_name}: {original_type} → {target_type.__name__}")
        elif original_value is not None and result_str is not None and original_value != result_str:
            print(f"@autopath: Normalized {param_name}: {original_value!r} → {result_str!r}")
    
    return result


def _convert_iterable(
    value: Any,
    container_type: type,
    element_type: type,
    param_name: str,
    debug: bool,
) -> Any:
    """
    Convert an iterable of values to the target types.
    """
    if value is None:
        return None
    
    try:
        converted = [
            _convert_value(item, element_type, f"{param_name}[{i}]", debug)
            for i, item in enumerate(value)
        ]
        return container_type(converted)
    except (TypeError, ValueError):
        return value

def autopath(
    use_caller: bool = False,
    debug: bool = False,
    only: str | list[str] | None = None,
) -> Callable[[F], F]:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import paths

        @autopath()
        def process(path: AnyPath):  
            # path is guaranteed to be an Skpath
            return path.id
            
        @autopath(use_caller=True)
        def log_from(path: AnyPath):
            # path defaults to caller's file if not provided
            print(f"Logging from: {path.rp}")
        
        @autopath()
        def save_file(path: str):
            # path is normalized: "./data\\file.txt" → "/abs/path/data/file.txt"
            with open(path, 'w') as f:
                f.write('data')
        
        @autopath(only="file_path")
        def process_with_data(file_path: str, names: list[str], ids: list[str]):

            # only file_path is normalized, names and ids are left unchanged
            # much faster when names/ids contain thousands of items
            return file_path

        # also works with iterables
        @paths.autopath()
        def batch(paths: list[paths.AnyPath]):
            return [p.ap for p in paths]
        ```
    ────────────────────────────────────────────────────────\n

    Decorator that automatically converts path parameters based on type annotations.
    
    All path-like inputs are normalized through Skpath before conversion to the
    target type. This ensures:
    - Resolved absolute paths
    - Normalized separators (always /)
    - Cross-platform consistency
    
    Converts inputs to match the declared type:
    - Parameters annotated as AnyPath or Skpath → converted to Skpath
    - Parameters annotated as Path → normalized through Skpath, then to Path
    - Parameters annotated as str → normalized through Skpath, returns absolute path string
    
    Also handles iterables: list[AnyPath], tuple[Path, ...], set[Skpath], etc.
    
    Args:
        use_caller: If True, parameters that accept Skpath or Path will use the caller's file path 
        if no value was provided\n

        debug: If True, print messages when conversions occur\n

        only: Only apply autopath to specific params. If None, all path-like params
        are normalized (strs, Paths, Skpaths). If a param accepts str or list[str] and
        is listed in only, autopath will apply. If only is not None AND a param is not listed in only,
        autopath will not be applied to values being passed into that param.
        
    Returns:
        Decorated function
    """
    # normalize 'only' to a set for O(1) lookup
    if only is None:
        allowed_params: set[str] | None = None  # None means all params
    elif isinstance(only, str):
        allowed_params = {only}
    else:
        allowed_params = set(only)
    
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        type_hints = {}
        
        # get type hints, handling forward references
        try:
            type_hints = func.__annotations__.copy()
        except AttributeError:
            pass
        
        # analyze parameters
        param_info: dict[str, dict[str, Any]] = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            
            # skip if path_params specified and this param isn't in the list
            if allowed_params is not None and param_name not in allowed_params:
                continue
            
            annotation = type_hints.get(param_name, param.annotation)
            if annotation is inspect.Parameter.empty:
                continue
            
            # check for direct path type
            base_type = _get_base_type_from_annotation(annotation)
            if base_type is not None:
                param_info[param_name] = {
                    "type": "single",
                    "target_type": base_type,
                    "has_default": param.default is not inspect.Parameter.empty,
                }
                continue
            
            # check for iterable of path types
            container_type, element_type = _get_iterable_element_type(annotation)
            if container_type is not None:
                param_info[param_name] = {
                    "type": "iterable",
                    "container_type": container_type,
                    "element_type": element_type,
                    "has_default": param.default is not inspect.Parameter.empty,
                }
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:

            # get the caller's path if use_caller is enabled
            caller_path: Path | None = None
            if use_caller:
                caller_path = get_caller_path_raw(skip_frames=1)
            
            # convert args to kwargs for easier processing
            bound = sig.bind_partial(*args, **kwargs)
            
            # process each parameter
            for param_name, info in param_info.items():
                value = bound.arguments.get(param_name)
                
                # handle use_caller for missing values
                if value is None and use_caller and caller_path is not None:
                    if info["type"] == "single":
                        target = info["target_type"]
                        if target in (Skpath, Path):
                            value = caller_path
                            bound.arguments[param_name] = value
                            if debug:
                                print(f"@autopath: Using caller path for {param_name}")
                
                # skip if still None
                if value is None:
                    continue
                
                # convert based on type
                if info["type"] == "single":
                    converted = _convert_value(
                        value,
                        info["target_type"],
                        param_name,
                        debug,
                    )
                    bound.arguments[param_name] = converted
                    
                elif info["type"] == "iterable":
                    converted = _convert_iterable(
                        value,
                        info["container_type"],
                        info["element_type"],
                        param_name,
                        debug,
                    )
                    bound.arguments[param_name] = converted
            
            return func(*bound.args, **bound.kwargs)
        
        return wrapper  # type: ignore
    
    return decorator
