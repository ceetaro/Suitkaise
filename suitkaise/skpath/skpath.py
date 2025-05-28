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
from typing import Union
import hashlib

class AutopathError(Exception):
    """Custom exception for autopath decorator."""
    pass

def _resolve_path(path: Union[str, Path]) -> Path:
    """
    Resolve a path to an absolute Path object.
    
    Args:
        path: The path to resolve. If None or empty, uses current file.
        
    Returns:
        Path: Resolved absolute path.
    """
    if not path or not os.path.exists(path):
        path = __file__

    return Path(path).resolve().absolute()

def _normalize_path(path: Union[str, Path]) -> str:
    """
    Normalize a path to a POSIX-style string.
    
    Args:
        path: The path to normalize. If None or empty, uses current file.
        
    Returns:
        str: Normalized POSIX path string.
    """
    if not path or not os.path.exists(path):
        path = __file__

    return _resolve_path(path).as_posix()

def autopath(path: Union[str, Path] = None, path_param_name: str = None):
    """
    Decorator to automatically send a resolved and normalized path to
    the decorated function. Sends current file's path if no path is
    specified.

    Args:
        path: The path to inject. If None, uses the caller's file path.
        path_param_name: Name of the parameter to inject into. If None, 
                        searches for parameters containing 'path'.
                        
    Example:
        @autopath()
        def process_file(path: str = None):
            print(f"Processing: {path}")
            
        @autopath(path="/custom/path")
        def custom_process(file_path: str = None):
            print(f"Custom processing: {file_path}")
            
    Raises:
        AutopathError: If explicit None is passed, invalid path provided,
                      or parameter type is wrong.
    """
    def decorator(func):
        # Resolve the path ONCE when the decorator is applied to a function
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
        
        # Normalize the path once
        normalized_path = _normalize_path(caller_path)

        def wrapper(*args, **kwargs):
            # Find the path parameter name if not specified
            if not path_param_name:
                sig = inspect.signature(func)
                params = sig.parameters
                
                # Look for exact 'path' match first
                if 'path' in params:
                    param_name = 'path'
                else:
                    # Look for any parameter containing 'path'
                    matches = [name for name in params.keys() if 'path' in name.lower()]
                    if matches:
                        param_name = matches[0]  # Use first match
                    else:
                        available_params = list(params.keys())
                        raise AutopathError(f"Function '{func.__name__}' has no parameter "
                                          f"containing 'path' in its name. "
                                          f"Available parameters: {available_params}")
            else:
                param_name = path_param_name
            
            # Get function signature info
            sig = inspect.signature(func)
            params = sig.parameters
            
            if param_name not in params:
                available_params = list(params.keys())
                raise AutopathError(f"Function '{func.__name__}' does not have "
                                  f"parameter '{param_name}'. "
                                  f"Available parameters: {available_params}")
            
            param = params[param_name]
            param_names = list(params.keys())
            param_index = param_names.index(param_name)
            
            # Handle positional arguments
            if param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
                if len(args) <= param_index:
                    # Not enough args - extend and add our auto-detected path
                    args = list(args)
                    while len(args) <= param_index:
                        args.append(None)
                    args[param_index] = normalized_path
                    args = tuple(args)
                elif len(args) > param_index and args[param_index] is None:
                    # User explicitly passed None - raise error
                    raise AutopathError(f"Explicit None passed to path parameter '{param_name}' "
                                      f"in function '{func.__name__}'. If you want auto-detection, "
                                      f"don't pass the parameter at all.")
                elif len(args) > param_index:
                    # User provided a real value - validate and normalize it
                    args = list(args)
                    provided_path = args[param_index]
                    if isinstance(provided_path, (str, Path)):
                        try:
                            args[param_index] = _normalize_path(provided_path)
                        except (OSError, ValueError) as e:
                            raise AutopathError(f"Invalid path '{provided_path}' provided to "
                                              f"parameter '{param_name}' in function '{func.__name__}': {e}")
                    else:
                        raise AutopathError(f"Path parameter '{param_name}' in function '{func.__name__}' "
                                          f"must be a string or Path object, got {type(provided_path).__name__}")
                    args = tuple(args)
                        
            # Handle keyword arguments
            elif param.kind in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
                if param_name not in kwargs:
                    # Parameter not provided - use auto-detected path
                    kwargs[param_name] = normalized_path
                elif kwargs[param_name] is None:
                    # User explicitly passed None - raise error
                    raise AutopathError(f"Explicit None passed to path parameter '{param_name}' "
                                      f"in function '{func.__name__}'. If you want auto-detection, "
                                      f"don't pass the parameter at all.")
                else:
                    # User provided a path - validate and normalize it
                    provided_path = kwargs[param_name]
                    if isinstance(provided_path, (str, Path)):
                        try:
                            kwargs[param_name] = _normalize_path(provided_path)
                        except (OSError, ValueError) as e:
                            raise AutopathError(f"Invalid path '{provided_path}' provided to "
                                              f"parameter '{param_name}' in function '{func.__name__}': {e}")
                    else:
                        raise AutopathError(f"Path parameter '{param_name}' in function '{func.__name__}' "
                                          f"must be a string or Path object, got {type(provided_path).__name__}")
            
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
                # Normalize the path to check consistently
                normalized_caller_path = _normalize_path(caller_path)
                
                # Check if this file is part of the suitkaise package
                # Look for 'suitkaise' in the path components
                if not _is_suitkaise_file(normalized_caller_path):
                    return normalized_caller_path
            
            caller_frame = caller_frame.f_back
        
        # Fallback if we can't find a non-suitkaise file
        # This shouldn't happen in normal usage, but provides safety
        return _normalize_path(__file__)
    finally:
        del frame


def _is_suitkaise_file(file_path: str) -> bool:
    """
    Check if a file path belongs to the suitkaise package.
    
    Args:
        file_path: Normalized file path to check
        
    Returns:
        bool: True if the file is part of suitkaise package, False otherwise  
    """
    # Convert to Path for easier manipulation
    path = Path(file_path)
    
    # Check if 'suitkaise' appears in any of the path parts
    # This handles both development and installed package scenarios:
    # - Development: /Users/ctaro/Suitkaise/suitkaise/skglobals/skglobals.py
    # - Installed: /path/to/site-packages/suitkaise/skglobals/skglobals.py
    path_parts = [part.lower() for part in path.parts]
    
    return 'suitkaise' in path_parts

# Convenience functions for common path operations
def resolve_path(path: Union[str, Path] = None) -> Path:
    """
    Resolve a path to an absolute Path object.
    
    Args:
        path: The path to resolve. If None, uses caller's file path.
        
    Returns:
        Path: Resolved absolute path.
    """
    if path is None or not os.path.exists(path):
        path = get_caller_file_path()
    return Path(path).resolve().absolute()

def normalize_path(path: Union[str, Path] = None) -> str:
    """
    Normalize a path to a POSIX-style string.
    
    Args:
        path: The path to normalize. If None, uses caller's file path.
        
    Returns:
        str: Normalized POSIX path string.
    """
    if path is None or not os.path.exists(path):
        path = get_caller_file_path()
    return _resolve_path(path).as_posix()

def get_current_file_path() -> str:
    """
    Get the path of the file that called this function.
    
    Returns:
        str: Normalized path of the calling file.
    """
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back
        caller_path = caller_frame.f_globals.get('__file__', __file__)
        return _normalize_path(caller_path)
    finally:
        del frame

def get_current_directory() -> str:
    """
    Get the directory of the file that called this function.
    
    Returns:
        str: Normalized directory path of the calling file.
    """
    file_path = get_current_file_path()
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



# Example usage and testing
if __name__ == "__main__":
    
    @autopath()
    def test_basic(path: str = None):
        """Test basic autopath functionality."""
        print(f"Basic test path: {path}")
        return path

    @autopath(path_param_name="file_path")
    def test_custom_param(file_path: str = None):
        """Test with custom parameter name."""
        print(f"Custom param path: {file_path}")
        return file_path

    @autopath(path="/tmp/test")
    def test_custom_path(path: str = None):
        """Test with custom path injection."""
        print(f"Custom path: {path}")
        return path

    @autopath()
    def test_multiple_paths(source_path: str = None, data: str = "default"):
        """Test with multiple parameters containing 'path'."""
        print(f"Source path: {source_path}, Data: {data}")
        return source_path

    @autopath()
    def test_keyword_only(*, path: str = None):
        """Test with keyword-only parameter."""
        print(f"Keyword-only path: {path}")
        return path
    
    @autopath(path=None)  # This should auto-detect
    def test_path_none(path: str = None):
        """Test with explicit None as decorator argument."""
        print(f"Path=None: {path}")
        return path
    
    def test_explicit_none_call():
        """Test calling a function with explicit None argument."""
        try:
            @autopath()
            def temp_func(path: str = None):
                return path
            
            temp_func(None)  # This should raise an error
        except AutopathError as e:
            print(f"Expected error: {e}")
            return "Error caught correctly"

    # Run tests
    print("Testing autopath decorator...")
    print("-" * 40)
    
    result1 = test_basic()
    print(f"Result 1: {result1}\n")
    
    result2 = test_custom_param()
    print(f"Result 2: {result2}\n")
    
    result3 = test_custom_path()
    print(f"Result 3: {result3}\n")
    
    result4 = test_multiple_paths(data="test")
    print(f"Result 4: {result4}\n")
    
    result5 = test_keyword_only()
    print(f"Result 5: {result5}\n")

    result6 = test_path_none()
    print(f"Result 6: {result6}\n")

    result7 = test_explicit_none_call()
    print(f"Result 7: {result7}\n")
    
    # Test convenience functions
    print("Testing convenience functions...")
    print("-" * 40)
    print(f"Current file path: {get_current_file_path()}")
    print(f"Current directory: {get_current_directory()}")
    print(f"Resolved path: {resolve_path()}")
    print(f"Normalized path: {normalize_path()}")
    print(f"Equal paths: {equalpaths('/tmp/test', '/tmp/test')}")
    print(f"ID: {id('/tmp/test')}")
    print(f"Short ID: {idshort('/tmp/test', 6)}")
    print(f"Same path ID: {id('/tmp/test')}")