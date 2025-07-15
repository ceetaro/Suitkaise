"""
Public API for fdl.
"""

from typing import Set, List, Optional

# Import internal components with multiple fallback strategies
try:
    # Try relative import first (standard package structure)
    from .._int._fdl.core.format_class import (
        # Exceptions
        FormatError,
        InvalidFormatError, 
        CircularReferenceError,
        FormatNotFoundError,
        
        # Internal functions
        _compile_format_string,
        _register_compiled_format,
        _get_compiled_format,
        _format_exists_internal,
        _list_all_formats_internal, 
        _clear_all_formats_internal,
        _get_format_dependencies_internal,
    )
except ImportError:
    try:
        # Try absolute import (when running from project root)
        from suitkaise._int._fdl.core.format_class import (
            # Exceptions
            FormatError,
            InvalidFormatError, 
            CircularReferenceError,
            FormatNotFoundError,
            
            # Internal functions
            _compile_format_string,
            _register_compiled_format,
            _get_compiled_format,
            _format_exists_internal,
            _list_all_formats_internal, 
            _clear_all_formats_internal,
            _get_format_dependencies_internal,
        )
    except ImportError as e:
        raise ImportError(f"Cannot import internal format_class module. Make sure suitkaise/_int/_fdl/core/format_class.py exists and is accessible. Error: {e}")




class Format:
    """
    Pre-compiled format for maximum performance fdl formatting.
    
    Creates a named, reusable format that can be applied anywhere in fdl strings.
    Format strings are parsed and compiled once during creation, then applied
    instantly using pre-compiled ANSI sequences and state transitions.
    
    Key features:
    - 50x faster than Rich Style formatting
    - Format inheritance and combination support  
    - Thread-safe global registry
    - Immediate error detection during creation
    - No dependency on changing module-level defaults
    
    Args:
        name (str): Unique name for this format
        format_string (str): fdl format commands (e.g., "</red, bold>")
        
    Raises:
        InvalidFormatError: If format string contains invalid syntax
        FormatNotFoundError: If format references another format that doesn't exist
        CircularReferenceError: If format creates circular dependencies
        
    Example:
        # Basic format
        error = Format("error", "</red, bold>")
        
        # Format inheritance
        critical = Format("critical", "</fmt error, bkg yellow>")
        
        # Use in fdl.print
        fdl.print("</fmt critical>System failure!</fmt critical>")
    """
    
    def __init__(self, name: str, format_string: str):
        """
        Create and compile a new format.
        
        The format is immediately parsed, validated, compiled, and registered
        in the global format registry for use throughout your application.
        """
        if not name or not isinstance(name, str):
            raise InvalidFormatError("Format name must be a non-empty string")
        
        if not format_string or not isinstance(format_string, str):
            raise InvalidFormatError("Format string must be a non-empty string")
        
        self.name = name
        self.original_string = format_string
        
        # Compile and register the format
        try:
            self._compiled = _compile_format_string(name, format_string)
            _register_compiled_format(self._compiled)
            
        except Exception as e:
            if isinstance(e, (InvalidFormatError, FormatNotFoundError, CircularReferenceError)):
                raise
            else:
                raise InvalidFormatError(f"Format compilation failed: {e}")
    
    @property 
    def direct_ansi(self) -> str:
        """
        Get the direct ANSI sequence for this format.
        
        Returns the pre-compiled ANSI escape sequence that will achieve
        this format from a blank/unformatted state (standard Python print).
        
        Returns:
            str: ANSI escape sequence
        """
        return self._compiled.direct_ansi
    
    @property
    def referenced_formats(self) -> Set[str]:
        """
        Get the names of other formats this format depends on.
        
        Returns:
            Set[str]: Set of format names this format inherits from
        """
        return self._compiled.referenced_formats.copy()
    
    def __repr__(self) -> str:
        """Developer representation showing name and format string."""
        return f"Format(name='{self.name}', format='{self.original_string}')"
    
    def __str__(self) -> str:
        """User-friendly string showing name and format."""
        return f"{self.name}: {self.original_string}"


def get_format(name: str) -> Optional[Format]:
    """
    Retrieve a format by name from the global registry.
    
    Args:
        name (str): Name of the format to retrieve
        
    Returns:
        Optional[Format]: Format object if found, None otherwise
        
    Example:
        error_fmt = get_format("error")
        if error_fmt:
            print(f"Error format: {error_fmt.original_string}")
    """
    compiled = _get_compiled_format(name)
    if compiled:
        # Create Format object from compiled data
        format_obj = object.__new__(Format)
        format_obj.name = compiled.name
        format_obj.original_string = compiled.original_string
        format_obj._compiled = compiled
        return format_obj
    return None


def format_exists(name: str) -> bool:
    """
    Check if a format exists in the global registry.
    
    Args:
        name (str): Name of the format to check
        
    Returns:
        bool: True if format exists, False otherwise
        
    Example:
        if format_exists("error"):
            print("Error format is available")
    """
    return _format_exists_internal(name)


def list_formats() -> List[str]:
    """
    Get a list of all registered format names.
    
    Returns:
        List[str]: Alphabetically sorted list of format names
        
    Example:
        print("Available formats:", list_formats())
        # Output: Available formats: ['error', 'success', 'warning']
    """
    return _list_all_formats_internal()


def clear_formats() -> None:
    """
    Clear all formats from the global registry.
    
    This removes all registered formats, useful for testing or
    resetting the format system. Use with caution in production code.
    
    Example:
        clear_formats()  # All formats are now gone
        assert len(list_formats()) == 0
    """
    _clear_all_formats_internal()


def get_format_dependencies(name: str) -> Set[str]:
    """
    Get all formats that a given format depends on (recursive).
    
    This includes both direct dependencies (formats explicitly referenced)
    and indirect dependencies (formats referenced by the direct dependencies).
    
    Args:
        name (str): Name of the format to analyze
        
    Returns:
        Set[str]: Set of all format names this format depends on
        
    Example:
        # If 'critical' references 'error' and 'error' references 'base'
        deps = get_format_dependencies("critical")
        print(deps)  # {'base', 'error'}
    """
    return _get_format_dependencies_internal(name)


# Export the exception classes for user error handling
__all__ = [
    'Format',
    'get_format', 
    'format_exists',
    'list_formats',
    'clear_formats',
    'get_format_dependencies',
    'FormatError',
    'InvalidFormatError',
    'CircularReferenceError', 
    'FormatNotFoundError'
]