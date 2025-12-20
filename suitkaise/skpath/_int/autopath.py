# ============================================================================
# AutoPath Decorator - Automatic Path Conversion
# ============================================================================

def _get_annotation_types(annotation) -> List[type]:
    """
    Extract types from a type annotation, handling Union types.
    
    Args:
        annotation: The type annotation to extract types from
        
    Returns:
        List of types from the annotation
    """
    if annotation == inspect.Parameter.empty:
        return []
    elif hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
        # Union type like str | SKPath or Union[str, Path]
        return list(annotation.__args__)
    else:
        # Single type
        return [annotation]


def _get_target_type(annotation_types: List[type]) -> Optional[type]:
    """
    Determine the target type for conversion based on annotation types.
    
    Priority order: SKPath > Path > str
    
    Args:
        annotation_types: List of types from the parameter annotation
        
    Returns:
        Target type for conversion, or None if no path-like type found
    """
    if not annotation_types:
        # No annotation - no conversion
        return None
    elif SKPath in annotation_types:
        return SKPath
    elif Path in annotation_types:
        return Path
    elif str in annotation_types:
        return str
    else:
        return None


def _convert_to_target_type(
    value: Union[str, Path, SKPath], 
    target_type: type,
    param_name: str,
    debug: bool = False
) -> Union[str, Path, SKPath]:
    """
    Convert a path value to the target type.
    
    Args:
        value: The value to convert
        target_type: The type to convert to
        param_name: Name of the parameter (for debug output)
        debug: Whether to print debug information
        
    Returns:
        Converted value
        
    Raises:
        TypeError: If the value cannot be converted
    """
    original_type = type(value).__name__
    original_value = str(value)
    
    if target_type == SKPath:
        if isinstance(value, SKPath):
            return value  # Already correct type
        result = SKPath(value)
    elif target_type == Path:
        if isinstance(value, Path):
            return value  # Already correct type
        if isinstance(value, SKPath):
            result = value.path_object
        else:
            result = Path(value).resolve()
    elif target_type == str:
        if isinstance(value, str):
            return value  # Already correct type
        if isinstance(value, SKPath):
            result = value.ap
        else:
            result = str(Path(value).resolve())
    else:
        raise TypeError(f"Unsupported target type: {target_type}")
    
    # Debug output only when conversion actually happened
    if debug:
        print(f"[autopath] '{param_name}': {original_type}({original_value!r}) → {type(result).__name__}({str(result)!r})")
    
    return result


def autopath(*, use_caller: bool = False, default: Optional[AnyPath] = None, debug: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        # Type-based automatic conversion

        @autopath()
        def process_file(path: SKPath):
            # strings and Path objects are automatically converted to SKPath
            print(f"Processing {path.np}...")
        
        process_file("my/relative/path")  # string → SKPath
        process_file(Path("other/path"))  # Path → SKPath
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Works with str-only functions too

        @autopath()
        def legacy_func(path: str):
            # SKPath and Path objects are converted to absolute path strings
            print(f"Processing {path}...")
        
        legacy_func(SKPath("my/path"))  # SKPath → str
        legacy_func(Path("other/path")) # Path → str
        ```
    ────────────────────────────────────────────────────────\n
    Decorator that automatically converts path parameters based on type annotations.
    
    Conversion rules (based on parameter's type annotation):
    1. If param accepts `SKPath` (or `AnyPath`): convert `str`/`Path` → `SKPath`
    2. If param accepts `Path` (but not `SKPath`): convert `str`/`SKPath` → `Path`
    3. If param accepts `str` (but not `Path`/`SKPath`): convert `Path`/`SKPath` → `str`
    
    Parameters without path-related type annotations are left unchanged.
    
    Args:
        `use_caller`: If `True`, use caller file path when path parameter is `None`
        `default`: Default path to use when path parameter is `None`
        `debug`: If `True`, print conversion info when a conversion is made
        
    Returns:
        Decorated function with automatic path conversion
        
    ────────────────────────────────────────────────────────
        ```python
        # Using default path

        @autopath(default="output/results.txt")
        def save_data(data, path: SKPath = None):
            # If path is None, uses the default
            with open(path, 'w') as f:
                f.write(data)
        
        save_data("hello")  # saves to output/results.txt
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Using caller file path

        @autopath(use_caller=True)
        def log_here(message: str, path: SKPath = None):
            # If path is None, uses the caller's file path
            print(f"Logging to {path.np}: {message}")
        
        log_here("test")  # path = caller's file location
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Debug mode shows conversions

        @autopath(debug=True)
        def process(path: SKPath):
            pass
        
        process("my/file.txt")
        # Prints: [autopath] 'path': str('my/file.txt') → SKPath('/abs/path/my/file.txt')
        ```
    ────────────────────────────────────────────────────────
    """
    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Bind arguments to get parameter names and values
            bound_args = sig.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, param_value in list(bound_args.arguments.items()):
                param_info = sig.parameters[param_name]
                annotation_types = _get_annotation_types(param_info.annotation)
                target_type = _get_target_type(annotation_types)
                
                # Skip if no path-related type annotation
                if target_type is None:
                    continue
                
                # Handle None values with use_caller/default
                if param_value is None:
                    if default is not None:
                        param_value = default
                    elif use_caller:
                        try:
                            caller_file = _get_non_sk_caller_file_path()
                            if caller_file:
                                param_value = caller_file
                        except Exception:
                            pass  # Leave as None if detection fails
                
                # Skip if still None or not a path-like type
                if param_value is None:
                    continue
                if not isinstance(param_value, (str, Path, SKPath)):
                    continue
                
                # Convert to target type
                try:
                    bound_args.arguments[param_name] = _convert_to_target_type(
                        param_value, target_type, param_name, debug
                    )
                except (OSError, ValueError, TypeError) as e:
                    raise TypeError(
                        f"Failed to convert parameter '{param_name}' to {target_type.__name__}: {e}"
                    ) from e
            
            return func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator