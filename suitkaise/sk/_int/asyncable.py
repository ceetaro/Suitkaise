"""
Lightweight asyncable wrappers for suitkaise internal methods/functions.

These provide .asynced() support without the full Skfunction overhead.
For user functions, retry, rate_limit, background, timeout, and asynced are available via the sk module.

For internal suitkaise methods that fetch results (like Process.result),
we also provide .timeout() and .background() via _ModifiableMethod.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, TypeVar, ParamSpec, Any, Optional

P = ParamSpec('P')
R = TypeVar('R')

# shared executor for background operations
_background_executor: ThreadPoolExecutor | None = None


class SkModifierError(Exception):
    """Raised when an unsupported sk modifier is accessed."""
    pass

def _get_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor."""
    global _background_executor
    if _background_executor is None:
        _background_executor = ThreadPoolExecutor(max_workers=32, thread_name_prefix="sk_bg_")
    return _background_executor


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
        
        # copy over function metadata
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
            # accessed on class, return descriptor
            return self
        
        # accessed on instance, return bound method wrapper
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


# modifiable methods - for result-fetching operations

# these support .timeout(), .background(), and .asynced() modifiers

# used for Process.result(), Process.wait(), Process.listen(), etc.


class _ModifiableMethod:
    """
    Descriptor that provides modifiers for blocking methods.
    
    Supports:
    - retry: retry on failure with backoff rules
    - rate_limit: throttle calls per second
    - background: return Future immediately
    - timeout: raise error if call takes too long
    - asynced: return coroutine for await
    """
    
    def __init__(
        self,
        sync_method: Callable,
        async_method: Callable | None = None,
        *,
        name: Optional[str] = None,
        timeout_error: type[Exception] | None = None,
        has_timeout_modifier: bool = True,
        has_background_modifier: bool = True,
        has_retry_modifier: bool = True,
    ):
        """
        Args:
            sync_method: The synchronous implementation
            async_method: The async implementation (optional, will use to_thread if None)
            name: Method name for repr
            timeout_error: Exception type to raise on timeout (default: TimeoutError)
            has_timeout_modifier: Whether to expose .timeout() modifier (False if method has timeout param)
            has_background_modifier: Whether to expose .background() modifier
            has_retry_modifier: Whether to expose .retry() modifier
        """
        self._sync_method = sync_method
        self._async_method = async_method
        self._name = name or sync_method.__name__
        self._timeout_error = timeout_error or TimeoutError
        self._has_timeout_modifier = has_timeout_modifier
        self._has_background_modifier = has_background_modifier
        self._has_retry_modifier = has_retry_modifier
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        return _ModifiableBoundMethod(
            obj,
            self._sync_method,
            self._async_method,
            name=self._name,
            timeout_error=self._timeout_error,
            has_timeout_modifier=self._has_timeout_modifier,
            has_background_modifier=self._has_background_modifier,
            has_retry_modifier=self._has_retry_modifier,
        )
    
    def __set_name__(self, owner, name):
        self._name = name


class _ModifiableBoundMethod:
    """
    Bound method wrapper with .timeout(), .background(), and .asynced() support.
    
    Usage:
        # Direct call (blocks)
        result = process.result()
        
        # With timeout as modifier (blocks, raises on timeout)
        result = process.result.timeout(10.0)()
        
        # Background (returns Future immediately)
        future = process.result.background()()
        result = future.result()  # blocks here
        
        # Async (returns coroutine)
        result = await process.result.asynced()()
    """
    
    def __init__(
        self,
        instance: Any,
        sync_method: Callable,
        async_method: Callable | None,
        *,
        name: str,
        timeout_error: type[Exception],
        has_timeout_modifier: bool = True,
        has_background_modifier: bool = True,
        has_retry_modifier: bool = True,
    ):
        self._instance = instance
        self._sync_method = sync_method
        self._async_method = async_method
        self._name = name
        self._timeout_error = timeout_error
        self._has_timeout_modifier = has_timeout_modifier
        self._has_background_modifier = has_background_modifier
        self._has_retry_modifier = has_retry_modifier
    
    def __call__(self, *args, **kwargs):
        """Call the sync version directly (blocks)."""
        return self._sync_method(self._instance, *args, **kwargs)
    
    def timeout(self, seconds: float) -> "_TimeoutModifier":
        """
        Add a timeout to the method call.
        
        Args:
            seconds: Maximum time to wait
        
        Returns:
            Callable that will raise timeout_error if exceeded
        
        Usage:
            result = process.result.timeout(10.0)()
        
        Note:
            Not available for methods that have a timeout parameter.
        """
        if not self._has_timeout_modifier:
            raise SkModifierError(
                f"'{self._name}' has a timeout parameter. "
                f"Use {self._name}(timeout=...) instead of {self._name}.timeout(...)()."
            )
        return _TimeoutModifier(
            self._instance,
            self._sync_method,
            self._async_method,
            timeout_seconds=seconds,
            timeout_error=self._timeout_error,
        )
    
    def retry(
        self,
        times: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 1.0,
        exceptions: tuple = (Exception,),
    ) -> Callable:
        """
        Add retry behavior to the method call.
        """
        if not self._has_retry_modifier:
            raise SkModifierError(f"{self._name} does not support .retry()")
        from .function_wrapper import create_retry_wrapper
        
        instance = self._instance
        sync_method = self._sync_method
        
        def bound_sync(*args, **kwargs):
            return sync_method(instance, *args, **kwargs)
        
        return create_retry_wrapper(
            bound_sync,
            times=times,
            delay=delay,
            factor=backoff_factor,
            exceptions=exceptions,
        )
    
    def background(self) -> "_BackgroundModifier":
        """
        Run the method in a background thread.
        
        Returns:
            Callable that returns a Future immediately
        
        Usage:
            future = process.result.background()()
            # ... do other work ...
            result = future.result()
        """
        if not self._has_background_modifier:
            raise SkModifierError(f"{self._name} does not support .background()")
        return _BackgroundModifier(
            self._instance,
            self._sync_method,
        )
    
    def rate_limit(self, per_second: float) -> Callable:
        """
        Add rate limiting to the method call.
        """
        from .function_wrapper import create_rate_limit_wrapper
        
        instance = self._instance
        sync_method = self._sync_method
        
        def bound_sync(*args, **kwargs):
            return sync_method(instance, *args, **kwargs)
        
        return create_rate_limit_wrapper(bound_sync, per_second)
    
    def asynced(self) -> Callable:
        """
        Get the async version of this method.
        
        Returns:
            Async callable that can be awaited
        
        Usage:
            result = await process.result.asynced()()
        """
        instance = self._instance
        async_method = self._async_method
        sync_method = self._sync_method
        
        if async_method is not None:
            @functools.wraps(sync_method)
            async def bound_async(*args, **kwargs):
                return await async_method(instance, *args, **kwargs)
        else:
            # No explicit async implementation - use to_thread
            @functools.wraps(sync_method)
            async def bound_async(*args, **kwargs):
                return await asyncio.to_thread(sync_method, instance, *args, **kwargs)
        
        return bound_async
    
    def __repr__(self) -> str:
        return f"<modifiable bound method {type(self._instance).__name__}.{self._name}>"



# modifiable async methods - for async instance methods
class _AsyncModifiableMethod:
    """
    Descriptor that provides .retry(), .rate_limit(), .background(), .timeout(),
    and .asynced() support for async instance methods.
    """
    
    def __init__(
        self,
        async_method: Callable,
        *,
        name: Optional[str] = None,
    ):
        self._async_method = async_method
        self._name = name or async_method.__name__
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        return _AsyncModifiableBoundMethod(
            obj,
            self._async_method,
            name=self._name,
        )
    
    def __set_name__(self, owner, name):
        self._name = name


class _AsyncModifiableBoundMethod:
    """
    Bound method wrapper with .retry(), .rate_limit(), .background(), .timeout(),
    and .asynced() support for async methods.
    """
    
    def __init__(
        self,
        instance: Any,
        async_method: Callable,
        *,
        name: str,
    ):
        self._instance = instance
        self._async_method = async_method
        self._name = name
    
    def __call__(self, *args, **kwargs):
        return self._async_method(self._instance, *args, **kwargs)
    
    def timeout(self, seconds: float) -> Callable:
        """
        Add a timeout to the async method call.
        """
        from .function_wrapper import create_async_timeout_wrapper_v2
        
        async_method = self._async_method
        instance = self._instance
        
        async def bound_async(*args, **kwargs):
            return await async_method(instance, *args, **kwargs)
        
        return create_async_timeout_wrapper_v2(bound_async, seconds)
    
    def retry(
        self,
        times: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 1.0,
        exceptions: tuple = (Exception,),
    ) -> Callable:
        """
        Add retry behavior to the async method call.
        """
        from .function_wrapper import create_async_retry_wrapper_v2
        
        async_method = self._async_method
        instance = self._instance
        
        async def bound_async(*args, **kwargs):
            return await async_method(instance, *args, **kwargs)
        
        return create_async_retry_wrapper_v2(
            bound_async,
            times=times,
            delay=delay,
            factor=backoff_factor,
            exceptions=exceptions,
        )
    
    def background(self) -> Callable:
        """
        Run the async method in the background as a Task.
        """
        async_method = self._async_method
        instance = self._instance
        
        def wrapper(*args, **kwargs):
            loop = asyncio.get_running_loop()
            return loop.create_task(async_method(instance, *args, **kwargs))
        
        return wrapper

    def rate_limit(self, per_second: float) -> Callable:
        """
        Add rate limiting to the async method call.
        """
        from .function_wrapper import create_async_rate_limit_wrapper_v2
        
        async_method = self._async_method
        instance = self._instance
        
        async def bound_async(*args, **kwargs):
            return await async_method(instance, *args, **kwargs)
        
        return create_async_rate_limit_wrapper_v2(bound_async, per_second)
    
    def asynced(self) -> Callable:
        """
        Return the async bound method (already async).
        """
        async_method = self._async_method
        instance = self._instance
        
        async def bound_async(*args, **kwargs):
            return await async_method(instance, *args, **kwargs)
        
        return bound_async
    
    def __repr__(self) -> str:
        return f"<modifiable async method {type(self._instance).__name__}.{self._name}>"


class _TimeoutModifier:
    """
    Modifier that adds timeout behavior to a method call.
    """
    
    def __init__(
        self,
        instance: Any,
        sync_method: Callable,
        async_method: Callable | None,
        *,
        timeout_seconds: float,
        timeout_error: type[Exception],
    ):
        self._instance = instance
        self._sync_method = sync_method
        self._async_method = async_method
        self._timeout_seconds = timeout_seconds
        self._timeout_error = timeout_error
    
    def __call__(self, *args, **kwargs):
        """
        Call with timeout (sync, blocks up to timeout_seconds).
        
        Uses a background thread with timeout to achieve this.
        """
        executor = _get_executor()
        future = executor.submit(self._sync_method, self._instance, *args, **kwargs)
        
        try:
            return future.result(timeout=self._timeout_seconds)
        except TimeoutError:
            # Cancel the future (best effort)
            future.cancel()
            raise self._timeout_error(
                f"{self._sync_method.__name__}() timed out after {self._timeout_seconds}s"
            )
    
    def asynced(self) -> Callable:
        """
        Get async version with timeout.
        
        Usage:
            result = await process.result.timeout(10.0).asynced()()
        """
        instance = self._instance
        async_method = self._async_method
        sync_method = self._sync_method
        timeout_seconds = self._timeout_seconds
        timeout_error = self._timeout_error
        
        async def async_with_timeout(*args, **kwargs):
            if async_method is not None:
                coro = async_method(instance, *args, **kwargs)
            else:
                coro = asyncio.to_thread(sync_method, instance, *args, **kwargs)
            
            try:
                return await asyncio.wait_for(coro, timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise timeout_error(
                    f"{sync_method.__name__}() timed out after {timeout_seconds}s"
                )
        
        return async_with_timeout
    
    def __repr__(self) -> str:
        return f"<timeout modifier ({self._timeout_seconds}s)>"


class _BackgroundModifier:
    """
    Modifier that runs a method in the background, returning a Future.
    """
    
    def __init__(
        self,
        instance: Any,
        sync_method: Callable,
    ):
        self._instance = instance
        self._sync_method = sync_method
    
    def __call__(self, *args, **kwargs) -> Future:
        """
        Submit to background thread and return Future immediately.
        """
        executor = _get_executor()
        return executor.submit(self._sync_method, self._instance, *args, **kwargs)
    
    def __repr__(self) -> str:
        return f"<background modifier>"


def modifiable_method(
    async_method: Callable | None = None,
    *,
    timeout_error: type[Exception] | None = None,
) -> Callable[[Callable], _ModifiableMethod]:
    """
    Decorator to make an instance method modifiable with .timeout(), .background(), .asynced().
    
    Usage:
        class Process:
            async def _async_result(self):
                # async implementation
                ...
            
            @modifiable_method(_async_result, timeout_error=ProcessTimeoutError)
            def result(self):
                # sync implementation
                ...
        
        # Now:
        process.result()                          # Sync, blocks
        process.result.timeout(10.0)()            # Sync with timeout
        future = process.result.background()()   # Returns Future
        await process.result.asynced()()         # Async
    """
    def decorator(sync_method: Callable) -> _ModifiableMethod:
        return _ModifiableMethod(
            sync_method,
            async_method,
            timeout_error=timeout_error,
        )
    return decorator
