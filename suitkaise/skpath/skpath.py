# add license here

# suitkaise/skpath/skpath.py

"""
Module containing SKPath functionality.

@autopath
def get_path_from_registry(path: str = None):
    
if path is None, the @autopath decorator will fill it with the current file's path.

"""
import os
import inspect
from pathlib import Path
import hashlib

class AutopathError(Exception):
    """Custom exception for autopath decorator."""
    pass

def _normalize_path(path: str | Path, allow_fallback: bool = True) -> str:
    """
    Normalize path, with optional fallback control.
    
    Args:
        path: The path to normalize (string, Path object, or None/empty)
        allow_fallback: If True, fallback to caller detection when path is None/empty/invalid
        
    Returns:
        str: Normalized absolute path
        
    Raises:
        AutopathError: If path is invalid and fallback is disabled
    """
    # Handle None or empty string/whitespace - this is when we should fallback
    if not path or (isinstance(path, str) and not path.strip()):
        if allow_fallback:
            # Use caller detection as fallback
            return get_caller_file_path()
        else:
            raise AutopathError("Empty path provided and fallback disabled")
    
    # We have a non-empty path - try to normalize it
    try:
        # Convert to string first and handle cross-platform path separators
        path_str = str(path)
        
        # Fix for cross-platform separator issues - normalize separators first
        # Replace backslashes with forward slashes on Unix-like systems
        if os.name == 'posix' and '\\' in path_str:
            path_str = path_str.replace('\\', '/')
        
        path_obj = Path(path_str)
        normpath = str(path_obj.resolve().absolute())
        
        # In strict mode, verify the path exists
        if not allow_fallback and not os.path.exists(normpath):
            raise AutopathError(f"Path '{normpath}' does not exist (strict mode)")
        
        # For non-strict mode, apply smart fallback logic
        if allow_fallback and not os.path.exists(normpath):
            # Determine if we should fallback based on the nature of the path
            
            # These patterns suggest a temporary/test file that we should normalize, not fallback
            temp_indicators = ['/tmp', '/temp', '/var/folders', 'temp', 'test']
            is_temp_path = any(indicator in normpath.lower() for indicator in temp_indicators)
            
            # These patterns suggest a clearly invalid path that should fallback
            clearly_invalid = (
                len(normpath) < 5 or  # Very short paths
                normpath.count('/') < 2  # Paths with very few components
            )
            
            if is_temp_path and not clearly_invalid:
                # Temp/test path - return normalized even if doesn't exist
                return normpath
            elif not is_temp_path and not clearly_invalid:
                # Regular non-existent path - fallback to caller
                return get_caller_file_path()
            else:
                # Clearly invalid - fallback to caller
                return get_caller_file_path()
        else:
            # Path exists or we're in strict mode
            return normpath
            
    except (OSError, ValueError) as e:
        # Path couldn't be processed at all
        if allow_fallback:
            return get_caller_file_path()
        else:
            raise AutopathError(f"Invalid path '{path}': {e}")



def autopath(path: str | Path = None, path_param_name: str = None, strict: bool = False):
    """
    Decorator to automatically send a resolved and normalized path to
    the decorated function. Sends current file's path if no path is
    specified.

    Args:
        path: The path to inject. If None, uses the caller's file path.
        path_param_name: Name of the parameter to inject into. If None, 
                        searches for parameters containing 'path'.
        strict: If True, raises errors for invalid paths instead of using fallbacks.
                        
    Example:
    ```python
        @autopath()
        def process_file(path: str = None):
            print(f"Processing: {path}")
            
        @autopath(path="/custom/path")
        def custom_process(file_path: str = None):
            print(f"Custom processing: {file_path}")
            
    Raises:
        AutopathError: If explicit None is passed, invalid path provided,
                      parameter doesn't exist, or parameter type is wrong.
    ```
    """
    def decorator(func):
        # === DECORATION TIME LOGIC ===
        # Get function signature and validate parameters NOW
        sig = inspect.signature(func)
        params = sig.parameters
        
        # Determine and validate the target parameter name
        if path_param_name:
            # User specified parameter name - validate it exists
            if path_param_name not in params:
                available_params = list(params.keys())
                raise AutopathError(f"Function '{func.__name__}' does not have "
                                  f"parameter '{path_param_name}'. "
                                  f"Available parameters: {available_params}")
            target_param_name = path_param_name
        else:
            # Auto-detect parameter name
            if 'path' in params:
                target_param_name = 'path'
            else:
                # Look for any parameter containing 'path'
                matches = [name for name in params.keys() if 'path' in name.lower()]
                if matches:
                    target_param_name = matches[0]  # Use first match
                else:
                    available_params = list(params.keys())
                    raise AutopathError(f"Function '{func.__name__}' has no parameter "
                                      f"containing 'path' in its name. "
                                      f"Available parameters: {available_params}")
        
        # Get information about the target parameter
        target_param = params[target_param_name]
        param_names = list(params.keys())
        param_index = param_names.index(target_param_name)
        
        # Resolve the path to inject ONCE at decoration time
        if path is None:
            # Get the frame of the code where the decorated function is defined
            frame = inspect.currentframe()
            try:
                caller_frame = frame.f_back  # Go up 1 frame to get the file with the decorated function
                caller_path = caller_frame.f_globals.get('__file__', __file__)
            finally:
                del frame  # Avoid reference cycles
        else:
            caller_path = path
        
        # Normalize the path once at decoration time
        try:
            normalized_path = _normalize_path(caller_path, allow_fallback=not strict)
        except AutopathError:
            # If we can't resolve the path at decoration time, we'll try at runtime
            normalized_path = None
            decoration_time_path = caller_path

        def wrapper(*args, **kwargs):
            # === RUNTIME LOGIC ===
            
            # If we couldn't resolve path at decoration time, try now
            if normalized_path is None:
                try:
                    resolved_path = _normalize_path(decoration_time_path, allow_fallback=not strict)
                except AutopathError as e:
                    raise AutopathError(f"Path resolution failed in function '{func.__name__}': {e}")
            else:
                resolved_path = normalized_path
            
            # Check if user provided the target parameter
            user_provided_path = False
            user_path_value = None
            
            # Check positional arguments
            if len(args) > param_index:
                user_provided_path = True
                user_path_value = args[param_index]
            
            # Check keyword arguments (keyword takes precedence)
            if target_param_name in kwargs:
                user_provided_path = True
                user_path_value = kwargs[target_param_name]
            
            if user_provided_path:
                # User provided a path - validate and normalize it
                if user_path_value is None:
                    raise AutopathError(f"Explicit None passed to path parameter '{target_param_name}' "
                                      f"in function '{func.__name__}'. If you want auto-detection, "
                                      f"don't pass the parameter at all.")
                
                if not isinstance(user_path_value, (str, Path)):
                    raise AutopathError(f"Path parameter '{target_param_name}' in function '{func.__name__}' "
                                      f"must be a string or Path object, got {type(user_path_value).__name__}")
                
                try:
                    normalized_user_path = _normalize_path(user_path_value, allow_fallback=not strict)
                except AutopathError as e:
                    raise AutopathError(f"Invalid path '{user_path_value}' provided to "
                                      f"parameter '{target_param_name}' in function '{func.__name__}': {e}")
                
                # Inject the normalized user path
                if target_param_name in kwargs:
                    kwargs[target_param_name] = normalized_user_path
                else:
                    # User provided positionally - update args
                    args = list(args)
                    args[param_index] = normalized_user_path
                    args = tuple(args)
            
            else:
                # User didn't provide path - inject our auto-detected path
                # Use positional-first, keyword-fallback strategy
                injected = False
                
                # Try positional injection if we're exactly at the right position
                if (target_param.kind in (target_param.POSITIONAL_ONLY, target_param.POSITIONAL_OR_KEYWORD) 
                    and len(args) == param_index):
                    # Perfect position for positional injection - append to args
                    args = args + (resolved_path,)
                    injected = True
                
                # If we couldn't inject positionally, try keyword injection
                if not injected and target_param.kind in (target_param.POSITIONAL_OR_KEYWORD, target_param.KEYWORD_ONLY):
                    kwargs[target_param_name] = resolved_path
                    injected = True
                
                # Special case: POSITIONAL_ONLY parameters that we can't inject at the right position
                if not injected and target_param.kind == target_param.POSITIONAL_ONLY:
                    # This is a problem - we must inject positionally but can't
                    raise AutopathError(f"Cannot inject path parameter '{target_param_name}' in function '{func.__name__}': "
                                       f"parameter is positional-only but wrong number of arguments provided. "
                                       f"Expected {param_index} arguments, got {len(args)}")
                
                # If we still couldn't inject, that's an error (shouldn't happen with proper validation)
                if not injected:
                    raise AutopathError(f"Could not inject path parameter '{target_param_name}' in function '{func.__name__}': "
                                       f"parameter type {target_param.kind} not supported")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_caller_file_path() -> str:
    """
    Get the path of the file that called this function, skipping all suitkaise module files.
    
    This function walks up the call stack until it finds a file that's not part of the
    suitkaise package, returning the first non-suitkaise file it encounters.
    
    Returns:
        str: Normalized path of the first non-suitkaise calling file.
    """
    frame = inspect.currentframe()
    try:
        # Start from the caller's frame
        caller_frame = frame.f_back
        
        # Keep going up the stack until we find a frame that's not from suitkaise
        while caller_frame is not None:
            caller_path = caller_frame.f_globals.get('__file__')
            
            if caller_path:
                # Get the raw path without normalization to avoid recursion
                try:
                    normalized_caller_path = str(Path(caller_path).resolve().absolute())
                except (OSError, ValueError):
                    # If we can't normalize this path, skip it
                    caller_frame = caller_frame.f_back
                    continue
                
                # Check if this file is part of the suitkaise package
                if not _is_suitkaise_file(normalized_caller_path):
                    return normalized_caller_path
            
            caller_frame = caller_frame.f_back
        
        # Fallback if we can't find a non-suitkaise file
        # This shouldn't happen in normal usage, but provides safety
        return str(Path(__file__).resolve().absolute())
    finally:
        del frame


def _is_suitkaise_file(file_path: str) -> bool:
    """
    Check if a file is actually part of the suitkaise package/library code.
    
    Uses multiple methods to accurately identify suitkaise package files:
    1. Import suitkaise and check actual package location
    2. Look for proper package structure with __init__.py
    3. Fallback to heuristics for development scenarios
    """
    path = Path(file_path)
    
    # Method 1: Try to import suitkaise and get its actual location
    try:
        import suitkaise
        
        # Case A: Regular package with __file__
        if hasattr(suitkaise, '__file__') and suitkaise.__file__:
            suitkaise_root = Path(suitkaise.__file__).parent
            try:
                path.relative_to(suitkaise_root)
                return True  # File is within the actual suitkaise package
            except ValueError:
                return False  # File is outside the package
        
        # Case B: Namespace package with __path__
        elif hasattr(suitkaise, '__path__'):
            for pkg_path in suitkaise.__path__:
                try:
                    path.relative_to(Path(pkg_path))
                    return True
                except ValueError:
                    continue
            return False
            
    except ImportError:
        # Suitkaise not installed/importable, continue to fallback methods
        pass
    
    # Method 2: Development mode - look for proper package structure
    # Pattern: .../suitkaise/__init__.py indicates the real package root
    path_parts = path.parts
    
    for i, part in enumerate(path_parts):
        if part.lower() == 'suitkaise':
            # Found a 'suitkaise' directory, verify it's actually a package
            potential_package_root = Path(*path_parts[:i+1])
            
            # Check if this directory has __init__.py (making it a real Python package)
            if (potential_package_root / '__init__.py').exists():
                try:
                    # Check if our file is within this package
                    path.relative_to(potential_package_root)
                    return True
                except ValueError:
                    continue  # Try other 'suitkaise' directories in the path
    
    # Method 3: Final fallback - check for specific module patterns
    # Files directly in suitkaise modules (like skpath/skpath.py)
    if len(path_parts) >= 2:
        # Look for pattern: suitkaise/module_name/module_name.py
        for i, part in enumerate(path_parts):
            if part.lower() == 'suitkaise' and i + 2 < len(path_parts):
                module_dir = path_parts[i + 1]
                filename = path_parts[i + 2]
                # Check if this looks like a suitkaise module structure
                if filename.startswith(module_dir) or filename == '__init__.py':
                    return True
    
    return False


def normalize_path(path: str | Path = None, strict: bool = False) -> str:
    """
    Normalize a path to an absolute path.
    
    Args:
        path: The path to normalize. If None, uses the caller's file path.
        strict: If True, raises errors for non-existent paths instead of normalizing them.
        
    Returns:
        str: Normalized absolute path
        
    Raises:
        AutopathError: If path is invalid or doesn't exist (in strict mode)
    """
    return _normalize_path(path, allow_fallback=not strict)

def get_current_file_path() -> str:
    """
    Get the path of the file that called this function.
    
    Returns:
        str: Normalized path of the calling file.
    """
    frame = inspect.currentframe()
    try:
        # Get the caller's frame
        caller_frame = frame.f_back
        if caller_frame is None:
            return str(Path(__file__).resolve().absolute())
        
        # Get caller's file path
        caller_path = caller_frame.f_globals.get('__file__')
        if not caller_path:
            return str(Path(__file__).resolve().absolute())
        
        # Return normalized path with better error handling
        try:
            return str(Path(caller_path).resolve().absolute())
        except (OSError, ValueError):
            return str(Path(__file__).resolve().absolute())
    finally:
        del frame


def get_current_directory() -> str:
    """
    Get the directory of the file that called this function.
    
    Returns:
        str: Normalized directory path of the calling file.
    """
    file_path = get_caller_file_path()
    return str(Path(file_path).parent)


def equalpaths(path1: str | Path, path2: str | Path) -> bool:
    """
    Check if two paths are equal.
    
    Args:
        path1: First path to compare.
        path2: Second path to compare.
        
    Returns:
        bool: True if paths are equal, False otherwise.
    """
    return _normalize_path(path1) == _normalize_path(path2)

@autopath()
def id(path: str | Path) -> str:
    """
    Create a reproducible ID for a path.

    Will be the same every time you run your program,
    as long as the path is the same.
    
    ID is a number based on the hash of the path.
    """
    path = _normalize_path(path)
    return hashlib.md5(path.encode()).hexdigest()

@autopath()
def idshort(path: str | Path, digits: int = 8) -> str:
    """
    Generate an ID using id(), but shorten it to a specified number of digits.

    Warning: Do not use this on its own for ID'ing paths, as it may not be unique.

    Intended usage:
    ```python
    idnum = idshort(path, 6)
    dirname = path.split('/')[-1]
    key = f"directory_{dirname}_{idnum}"

    # example result: directory_appdata_232698
    ```
    """
    path = _normalize_path(path)
    id_num = id(path)
    return str(id_num)[:digits]
