"""
Function wrapper utilities for Skfunction.

Provides retry, timeout, rate_limit, and background execution wrappers.
"""

import asyncio
import functools
import time
import threading
from concurrent.futures import Future
from typing import Callable, Any, TypeVar, ParamSpec, Optional, Type, Tuple, Awaitable

P = ParamSpec('P')
R = TypeVar('R')


class FunctionTimeoutError(Exception):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.sk import FunctionTimeoutError
        ```
    ────────────────────────────────────────────────────────\n

    Raised when a function exceeds its timeout.
    """
    pass


class RateLimiter:
    """
    Simple per-second rate limiter shared across sync/async call paths.
    """
    def __init__(self, per_second: float):
        if per_second <= 0:
            raise ValueError("per_second must be > 0")
        # minimum spacing between calls
        self._min_interval = 1.0 / per_second
        self._lock = threading.Lock()
        # last call timestamp in monotonic time
        self._last_call = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            # compute remaining delay before next allowed call
            wait_time = (self._last_call + self._min_interval) - now
            if wait_time > 0:
                time.sleep(wait_time)
            # update last call after any wait
            self._last_call = time.monotonic()

    async def acquire_async(self) -> None:
        # Use the same lock/state transition path as sync acquire().
        # This avoids sync/async races on _last_call.
        await asyncio.to_thread(self.acquire)


def create_retry_wrapper(
    func: Callable[P, R],
    times: int = 3,
    delay: float = 1.0,
    factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[P, R]:
    """
    Create a wrapper that retries the function on failure.
    
    Args:
        func: Function to wrap
        times: Maximum number of attempts (default 3)
        delay: Initial delay between retries in seconds (default 1.0)
        factor: Multiplier for delay after each retry (default 1.0 = constant)
        exceptions: Exception types to catch and retry on
        
    Returns:
        Wrapped function that retries on failure
    """
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # track last exception to rethrow after retries
        last_exception: Optional[Exception] = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                # call function for this attempt
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    # backoff before next attempt
                    time.sleep(sleep_time)
                    sleep_time *= factor
        
        # all retries exhausted
        raise last_exception  # type: ignore
    
    return wrapper


def create_async_retry_wrapper(
    func: Callable[P, R],
    times: int = 3,
    delay: float = 1.0,
    factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[P, Awaitable[R]]:
    """
    Create an async wrapper that retries the function on failure.
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # track last exception to rethrow after retries
        last_exception: Optional[Exception] = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                # run sync function in thread pool for async usage
                return await asyncio.to_thread(func, *args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    # backoff before next attempt
                    await asyncio.sleep(sleep_time)
                    sleep_time *= factor
        
        raise last_exception  # type: ignore
    
    return wrapper


def create_rate_limit_wrapper(
    func: Callable[P, R],
    per_second: float,
    limiter: Optional["RateLimiter"] = None,
) -> Callable[P, R]:
    """
    Create a wrapper that rate limits function calls.
    """
    # reuse limiter if provided to share state across wrappers
    limiter = limiter or RateLimiter(per_second)

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # block until rate limit allows this call
        limiter.acquire()
        return func(*args, **kwargs)

    return wrapper


def create_async_rate_limit_wrapper(
    func: Callable[P, R],
    per_second: float,
    limiter: Optional["RateLimiter"] = None,
) -> Callable[P, Awaitable[R]]:
    """
    Create an async wrapper that rate limits a sync function.
    """
    # reuse limiter if provided to share state across wrappers
    limiter = limiter or RateLimiter(per_second)

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # await rate limit before running in thread
        await limiter.acquire_async()
        return await asyncio.to_thread(func, *args, **kwargs)
    
    return wrapper


def create_timeout_wrapper(
    func: Callable[P, R],
    seconds: float,
) -> Callable[P, R]:
    """
    Create a wrapper that raises TimeoutError if function takes too long.
    
    Uses threading for sync execution with timeout.
    
    Args:
        func: Function to wrap
        seconds: Maximum execution time in seconds
        
    Returns:
        Wrapped function that times out
    """
    import concurrent.futures
    
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        from suitkaise.sk._int.asyncable import _get_executor
        # run in shared worker pool and wait for timeout
        future = _get_executor().submit(func, *args, **kwargs)
        try:
            return future.result(timeout=seconds)
        except concurrent.futures.TimeoutError:
            future.cancel()
            # raise a consistent timeout error for callers
            raise FunctionTimeoutError(
                f"{func.__name__} timed out after {seconds} seconds"
            )
    
    return wrapper


def create_async_timeout_wrapper(
    func: Callable[P, R],
    seconds: float,
) -> Callable[P, Awaitable[R]]:
    """
    Create an async wrapper that times out.
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            # run sync function in thread and apply asyncio timeout
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=seconds,
            )
        except asyncio.TimeoutError:
            # raise a consistent timeout error for callers
            raise FunctionTimeoutError(
                f"{func.__name__} timed out after {seconds} seconds"
            )
    
    return wrapper


def create_background_wrapper(
    func: Callable[P, R],
) -> Callable[P, Future[R]]:
    """
    Create a wrapper that runs the function in a background thread.
    
    Returns a Future that can be used to get the result later.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that returns a Future
    """
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Future[R]:
        from suitkaise.sk._int.asyncable import _get_executor
        # return Future immediately to avoid blocking
        return _get_executor().submit(func, *args, **kwargs)
    
    return wrapper


def create_async_wrapper(
    func: Callable[P, R],
) -> Callable[P, Awaitable[R]]:
    """
    Create an async wrapper using to_thread.
    
    Args:
        func: Sync function to wrap
        
    Returns:
        Async function that runs the original in a thread pool
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # run sync function in thread pool for async use
        return await asyncio.to_thread(func, *args, **kwargs)
    
    return wrapper


def create_async_timeout_wrapper_v2(
    async_func: Callable[P, Awaitable[R]],
    seconds: float,
) -> Callable[P, Awaitable[R]]:
    """
    Create an async wrapper that times out (for already-async functions).
    """
    @functools.wraps(async_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            # apply timeout to already-async function
            return await asyncio.wait_for(
                async_func(*args, **kwargs),
                timeout=seconds,
            )
        except asyncio.TimeoutError:
            func_name = getattr(async_func, '__name__', 'function')
            # raise a consistent timeout error for callers
            raise FunctionTimeoutError(
                f"{func_name} timed out after {seconds} seconds"
            )
    
    return wrapper


def create_async_retry_wrapper_v2(
    async_func: Callable[P, Awaitable[R]],
    times: int = 3,
    delay: float = 1.0,
    factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[P, Awaitable[R]]:
    """
    Create an async retry wrapper (for already-async functions).
    """
    @functools.wraps(async_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # track last exception to rethrow after retries
        last_exception: Optional[Exception] = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                # call async function for this attempt
                return await async_func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    # backoff before next attempt
                    await asyncio.sleep(sleep_time)
                    sleep_time *= factor
        
        raise last_exception  # type: ignore
    
    return wrapper


def create_async_rate_limit_wrapper_v2(
    async_func: Callable[P, Awaitable[R]],
    per_second: float,
    limiter: Optional["RateLimiter"] = None,
) -> Callable[P, Awaitable[R]]:
    """
    Create an async rate limit wrapper for already-async functions.
    """
    # reuse limiter if provided to share state across wrappers
    limiter = limiter or RateLimiter(per_second)

    @functools.wraps(async_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # await rate limit before calling async function
        await limiter.acquire_async()
        return await async_func(*args, **kwargs)
    
    return wrapper
