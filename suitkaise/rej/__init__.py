# add license here

# suitkaise/rej/__init__.py

"""
Rej - Simple registry classes for storing and managing collections of objects.

Rej provides basic registry functionality, while RejSingleton creates globally
accessible registries that can be shared across processes using SKGlobal storage.

Main classes:
    Rej: Basic registry for storing key-value pairs with metadata
    RejSingleton: Singleton registry that's globally accessible and cross-process

Quick start:
    # Get a global registry
    my_registry = RejSingleton.get_registry("my_items")
    
    # Register something
    my_registry.register("key1", some_object)
    
    # Get it back
    obj = my_registry.get("key1")
    
    # List all registries
    all_registries = RejSingleton.list_registries()

Usage examples:
    # Basic registry
    registry = Rej[str]("my_strings")
    registry.register("greeting", "Hello World")
    
    # Global singleton registry
    global_reg = RejSingleton.get_registry("functions")
    global_reg.register("my_func", some_function)
    
    # Access from anywhere
    same_reg = RejSingleton.get_registry("functions")
    func = same_reg.get("my_func")
"""
from typing import List
from suitkaise.rej.rej import (
    # Main classes
    Rej,
    RejSingleton,
    
    # Exceptions
    RejError,
    RejKeyError,
    RejDuplicateError,
    RejSerializationError,
)

# Version info
__version__ = "0.1.0"

# Expose main public API
__all__ = [
    # Main classes
    'Rej',
    'RejSingleton',
    
    # Exceptions
    'RejError',
    'RejKeyError', 
    'RejDuplicateError',
    'RejSerializationError',
    
    # Version
    '__version__',
]

# Convenience functions
def getrej(name: str, **kwargs) -> RejSingleton:
    """
    Get or create a global singleton registry by name.
    
    Args:
        name: Unique name for the registry
        **kwargs: Additional arguments passed to get_registry()
        
    Returns:
        RejSingleton: The singleton registry instance
        
    Example:
        my_registry = getrej("my_items")
        my_registry.register("key1", value1)
    """
    return RejSingleton.get_registry(name, **kwargs)

def listrej() -> List[str]:
    """
    Get a list of all singleton registry names that exist.
    
    Returns:
        List[str]: List of registry names
        
    Example:
        all_registries = listrej()
        print(f"Available registries: {all_registries}")
    """
    return RejSingleton.list_registries()

def removerej(name: str) -> bool:
    """
    Remove a singleton registry entirely.
    
    Warning: This removes the registry from global storage and memory.
    
    Args:
        name: Name of the registry to remove
        
    Returns:
        bool: True if registry existed and was removed, False if it didn't exist
        
    Example:
        success = removerej("old_registry")
        if success:
            print("Registry removed successfully")
    """
    return RejSingleton.remove_registry(name)

# Add convenience functions to __all__
__all__.extend(['getrej', 'listrej', 'removerej'])