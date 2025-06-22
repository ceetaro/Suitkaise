# add license here

# suitkaise/skglobal/__init__.py

"""
SKGlobal - Global variable management with cross-process support.

This module provides tools for creating and managing global variables 
that can be shared across processes and threads, with automatic persistence
and synchronization.

Main classes:
    SKGlobal: Create and manage individual global variables
    SKGlobalStorage: Low-level storage management
    GlobalLevel: Enum for variable scope levels

Main functions:
    get_project_root: Automatically detect project root directory

Usage:
    from suitkaise.skglobals import SKGlobal, GlobalLevel
    
    # Create a global variable
    my_global = SKGlobal(
        name="my_var",
        value="hello world",
        level=GlobalLevel.TOP
    )
    
    # Use it
    print(my_global.get())  # "hello world"
    my_global.set("updated value")
    
"""

from suitkaise.skglobal.skglobal import (
    # Main classes
    SKGlobal,
    SKGlobalStorage,
    GlobalLevel,
    
    # Utility functions
    get_project_root,
    
    # Exceptions
    SKGlobalError,
    SKGlobalValueError,
    SKGlobalLevelError,
    PlatformNotFoundError,
)

# Version info
__version__ = "0.1.0"

# Expose main public API
__all__ = [
    # Main classes
    'SKGlobal',
    'SKGlobalStorage', 
    'GlobalLevel',
    
    # Utility functions
    'get_project_root',
    
    # Exceptions
    'SKGlobalError',
    'SKGlobalValueError',
    'SKGlobalLevelError',
    'PlatformNotFoundError',
    
    # Version
    '__version__',
]

# Convenience imports for common usage patterns
def create_global(name: str, value=None, level=GlobalLevel.TOP, **kwargs):
    """
    Convenience function to create a global variable.
    
    Args:
        name: Name of the global variable
        value: Initial value
        level: GlobalLevel (TOP or UNDER)
        **kwargs: Additional arguments passed to SKGlobal
        
    Returns:
        SKGlobal: The created global variable
        
    Example:
        my_var = create_global("counter", 0)
        my_var.set(my_var.get() + 1)
    """
    return SKGlobal(name=name, value=value, level=level, **kwargs)

def get_global(name: str, level=GlobalLevel.TOP, **kwargs):
    """
    Convenience function to get an existing global variable.
    
    Args:
        name: Name of the global variable to retrieve
        level: GlobalLevel (TOP or UNDER)
        **kwargs: Additional arguments passed to SKGlobal.get_global
        
    Returns:
        SKGlobal or None: The global variable if found, None otherwise
        
    Example:
        existing_var = get_global("counter")
        if existing_var:
            print(f"Counter value: {existing_var.get()}")
    """
    return SKGlobal.get_global(name=name, level=level, **kwargs)

# Add convenience functions to __all__
__all__.extend(['create_global', 'get_global'])