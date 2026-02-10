"""
Async wrapper generation for Skclass.

Creates async versions of classes by wrapping blocking methods with asyncio.to_thread().
"""

import asyncio
import functools
import inspect
from typing import Type, Dict, List, Any, Callable


def _create_async_method(sync_method: Callable, method_name: str) -> Callable:
    """
    Create an async version of a sync method using to_thread().
    
    Args:
        sync_method: The original synchronous method
        method_name: Name of the method (for debugging)
        
    Returns:
        Async wrapper function
    """
    @functools.wraps(sync_method)
    async def async_wrapper(self, *args, **kwargs):
        # run the sync method in a thread pool
        return await asyncio.to_thread(sync_method, self, *args, **kwargs)
    
    return async_wrapper


def _create_async_passthrough(sync_method: Callable, method_name: str) -> Callable:
    """
    Create a trivial async wrapper for a non-blocking sync method.
    
    Calls the method directly (no thread pool) and returns the result
    so that `await instance.method()` works uniformly on async classes.
    
    Args:
        sync_method: The original synchronous method
        method_name: Name of the method (for debugging)
        
    Returns:
        Async wrapper function
    """
    @functools.wraps(sync_method)
    async def async_wrapper(self, *args, **kwargs):
        return sync_method(self, *args, **kwargs)
    
    return async_wrapper


def create_async_class(
    original_cls: Type,
    blocking_methods: Dict[str, List[str]],
) -> Type:
    """
    Create an async version of a class.
    
    Methods with blocking calls are wrapped with asyncio.to_thread().
    Methods without blocking calls are left as-is (sync).
    
    Args:
        original_cls: The original class to wrap
        blocking_methods: Dict mapping method names to their blocking calls
        
    Returns:
        New class with async versions of blocking methods
    """
    # create a new class that inherits from the original
    class_name = f"_Async{original_cls.__name__}"
    
    # build the new class namespace
    namespace: Dict[str, Any] = {
        '__module__': original_cls.__module__,
        '__doc__': f"Async version of {original_cls.__name__}. Blocking methods use asyncio.to_thread().",
        '_original_class': original_cls,
        '_blocking_methods': blocking_methods,
    }
    
    # copy over all attributes and methods from original class
    for name, member in inspect.getmembers(original_cls):
        # skip special attributes that shouldn't be copied
        if name.startswith('__') and name.endswith('__'):
            if name not in ('__init__', '__repr__', '__str__'):
                continue
        
        # unwrap _ModifiableMethod / _AsyncModifiableMethod descriptors
        # (@sk replaces class methods with these, but we need the raw function)
        raw_func = getattr(member, '_sync_method', None) or getattr(member, '_async_method', None)
        if raw_func is not None:
            member = raw_func
        
        if name in blocking_methods:
            # this method has blocking calls - wrap it
            if callable(member) and not isinstance(member, (type, property)):
                namespace[name] = _create_async_method(member, name)
        elif isinstance(member, property):
            # properties are kept as-is (they're typically quick reads)
            # but if the property has blocking calls, we'd need special handling
            if name in blocking_methods:
                # create an async property getter
                # NOTE: Python doesn't have native async properties, so we use a method
                async_getter = _create_async_method(member.fget, f"{name}_getter")
                namespace[f"get_{name}"] = async_getter
            else:
                namespace[name] = member
        elif callable(member) and not isinstance(member, type):
            # dunder methods must stay sync (Python calls them implicitly)
            if name.startswith('__') and name.endswith('__'):
                namespace[name] = member
            else:
                # non-blocking method — wrap in trivial async so await works uniformly
                namespace[name] = _create_async_passthrough(member, name)
    
    # create the new class
    async_class = type(class_name, (original_cls,), namespace)
    
    return async_class
