# add license here

# suitkaise/skfunction/__init__.py

"""
SKFunction - Convenient function creation and management with global registry.

SKFunction provides tools for:
- Wrapping functions with preset arguments and metadata
- Performance tracking and execution statistics
- Global function registry for cross-module access
- Builder pattern for complex function construction
- Automatic cross-process serialization support

Main classes:
    SKFunction: Function wrapper with preset args, metadata, and performance tracking
    SKFunctionBuilder: Builder for step-by-step function construction

Type aliases:
    AnyFunction: Union[Callable, SKFunction] for type hints

Quick start:
    # Simple function creation
    skf = SKFunction(
        func=my_function,
        args=(1, 2),
        kwargs={"debug": True},
        name="my_function"
    )
    
    # Call the function
    result = skf.call()  # or skf()
    
    # Use builder for complex functions
    with SKFunctionBuilder(autoregister=True) as builder:
        builder.add_callable(complex_function)
        builder.add_argument("param1", value1)
        builder.add_kwargs({"param2": value2})
        skf = builder.build()
    
    # Get from global registry
    registered_func = get_function("my_function")

Usage examples:
    # Create and auto-register
    @autoregister(description="Calculates factorial")
    def factorial(n):
        return 1 if n <= 1 else n * factorial(n-1)
    
    # Convert callable to SKFunction
    sk_func = convert_callable(my_function, name="converted")
    
    # Get function from global registry
    my_func = get_function("converted")
    result = my_func.call()
"""

from suitkaise.skfunction.skfunction import (
    # Main classes
    SKFunction,
    SKFunctionBuilder,
    
    # Type aliases
    AnyFunction,
    
    # Exceptions
    SKFunctionError,
    SKFunctionBuilderError,
    SKFunctionBuildError,
    SKFunctionRegistrationError,
    
    # Module-level functions
    edit_skfunction,
    get_function,
    list_functions,
    remove_function,
    convert_callable,
    autoregister,
    can_register_function,
)

# Version info
__version__ = "0.1.0"

# Expose main public API
__all__ = [
    # Main classes
    'SKFunction',
    'SKFunctionBuilder',
    
    # Type aliases
    'AnyFunction',
    
    # Exceptions
    'SKFunctionError',
    'SKFunctionBuilderError',
    'SKFunctionBuildError', 
    'SKFunctionRegistrationError',
    
    # Module-level functions
    'edit_skfunction',
    'get_function',
    'list_functions',
    'remove_function',
    'convert_callable',
    'autoregister',
    'can_register_function',
    
    # Version
    '__version__',
]

# Convenience functions
def create_function(func, *args, name: str = None, description: str = None, 
                   autoregister: bool = True, **kwargs) -> SKFunction:
    """
    Convenience function to create an SKFunction with preset arguments.
    
    Args:
        func: The callable function to wrap
        *args: Positional arguments to preset
        name: Optional name for the function
        description: Optional description
        autoregister: Whether to register in global registry
        **kwargs: Keyword arguments to preset
        
    Returns:
        SKFunction: The created function wrapper
        
    Example:
        # Create function with preset arguments
        add_10 = create_function(lambda x, y: x + y, 10, name="add_10")
        result = add_10.call(additional_args=(5,))  # Returns 15
    """
    return SKFunction(
        func=func,
        args=args,
        kwargs=kwargs,
        name=name,
        description=description,
        autoregister=autoregister
    )

def register_function(func, name: str = None, description: str = None) -> SKFunction:
    """
    Register a function in the global registry.
    
    Args:
        func: Function to register (callable or SKFunction)
        name: Name to register under (defaults to function's __name__)
        description: Optional description
        
    Returns:
        SKFunction: The registered function wrapper
        
    Example:
        # Register a regular function
        sk_func = register_function(my_function, "my_func", "Does something useful")
        
        # Access it later
        same_func = get_function("my_func")
    """
    if isinstance(func, SKFunction):
        if name:
            func.metadata.name = name
        if description:
            func.metadata.description = description
        func.autoregister()
        return func
    else:
        return SKFunction(
            func=func,
            name=name or getattr(func, '__name__', 'unknown'),
            description=description or "",
            autoregister=True
        )

def clear_registry() -> int:
    """
    Clear all functions from the global registry.
    
    Warning: This removes all registered functions.
    
    Returns:
        int: Number of functions that were removed
        
    Example:
        count = clear_registry()
        print(f"Removed {count} functions from registry")
    """
    from suitkaise.rej import RejSingleton
    
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.clear()
    except Exception:
        return 0

def registry_info() -> dict:
    """
    Get information about the global function registry.
    
    Returns:
        dict: Registry information including function count and names
        
    Example:
        info = registry_info()
        print(f"Registry has {info['total_items']} functions")
        print(f"Functions: {info['keys']}")
    """
    from suitkaise.rej import RejSingleton
    
    try:
        skfrej = RejSingleton.get_registry("SKFunctions")
        return skfrej.get_info()
    except Exception:
        return {
            'total_items': 0,
            'keys': [],
            'error': 'Registry not accessible'
        }

# Add convenience functions to __all__
__all__.extend(['create_function', 'register_function', 'clear_registry', 'registry_info'])