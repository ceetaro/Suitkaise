"""
Lightweight asyncable wrappers for suitkaise internal methods/functions.

These provide .asynced() support without the full Skfunction overhead.
Only .asynced() is supported - retry/timeout/background are for user functions.
"""

import asyncio
import functools
from typing import Callable, TypeVar, ParamSpec, Any, Optional

P = ParamSpec('P')
R = TypeVar('R')


class _AsyncableFunction:
    """
    Wrapper for a function that provides .asynced() support.
    
    When called directly, runs the sync version.
    .asynced() returns the async version.
    """
    
    def __init__(
        self,
        sync_func: Callable[P, R],
        async_func: Callable[P, R],
        *,
        name: Optional[str] = None,
    ):
        self._sync_func = sync_func
        self._async_func = async_func
        self._name = name or sync_func.__name__
        
        # Copy over function metadata
        functools.update_wrapper(self, sync_func)
    
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Call the sync version directly."""
        return self._sync_func(*args, **kwargs)
    
    def asynced(self) -> Callable[P, R]:
        """
        Get the async version of this function.
        
        Returns:
            Async function that can be awaited
        """
        return self._async_func
    
    def __repr__(self) -> str:
        return f"<asyncable function {self._name}>"


class _AsyncableMethod:
    """
    Descriptor that provides .asynced() support for instance methods.
    
    When accessed on an instance, returns an _AsyncableBoundMethod.
    """
    
    def __init__(
        self,
        sync_method: Callable,
        async_method: Callable,
        *,
        name: Optional[str] = None,
    ):
        self._sync_method = sync_method
        self._async_method = async_method
        self._name = name or sync_method.__name__
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            # Accessed on class, return descriptor
            return self
        
        # Accessed on instance, return bound method wrapper
        return _AsyncableBoundMethod(
            obj,
            self._sync_method,
            self._async_method,
            name=self._name,
        )
    
    def __set_name__(self, owner, name):
        self._name = name


class _AsyncableBoundMethod:
    """
    Bound method wrapper with .asynced() support.
    """
    
    def __init__(
        self,
        instance: Any,
        sync_method: Callable,
        async_method: Callable,
        *,
        name: str,
    ):
        self._instance = instance
        self._sync_method = sync_method
        self._async_method = async_method
        self._name = name
    
    def __call__(self, *args, **kwargs):
        """Call the sync version."""
        return self._sync_method(self._instance, *args, **kwargs)
    
    def asynced(self) -> Callable:
        """
        Get the async version of this method.
        
        Returns:
            Async bound method that can be awaited
        """
        instance = self._instance
        async_method = self._async_method
        
        @functools.wraps(self._sync_method)
        async def bound_async(*args, **kwargs):
            return await async_method(instance, *args, **kwargs)
        
        return bound_async
    
    def __repr__(self) -> str:
        return f"<asyncable bound method {type(self._instance).__name__}.{self._name}>"


def asyncable_function(async_func: Callable[P, R]) -> Callable[[Callable[P, R]], _AsyncableFunction]:
    """
    Decorator to make a sync function asyncable.
    
    Usage:
        async def _async_sleep(duration):
            await asyncio.sleep(duration)
        
        @asyncable_function(_async_sleep)
        def sleep(duration):
            time.sleep(duration)
        
        # Now:
        sleep(1.0)  # Sync
        await sleep.asynced()(1.0)  # Async
    """
    def decorator(sync_func: Callable[P, R]) -> _AsyncableFunction:
        return _AsyncableFunction(sync_func, async_func)
    return decorator


def asyncable_method(async_method: Callable) -> Callable[[Callable], _AsyncableMethod]:
    """
    Decorator to make an instance method asyncable.
    
    Usage:
        class Circuit:
            async def _async_short(self, custom_sleep=None):
                # async implementation
                await asyncio.sleep(...)
            
            @asyncable_method(_async_short)
            def short(self, custom_sleep=None):
                # sync implementation
                time.sleep(...)
        
        # Now:
        circuit.short()  # Sync
        await circuit.short.asynced()()  # Async
    """
    def decorator(sync_method: Callable) -> _AsyncableMethod:
        return _AsyncableMethod(sync_method, async_method)
    return decorator
