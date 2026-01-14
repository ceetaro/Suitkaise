"""
Function wrapper utilities for Skfunction.

Provides retry, timeout, and background execution wrappers.
"""

import asyncio
import functools
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, TypeVar, ParamSpec, Optional, Type, Tuple

P = ParamSpec('P')
R = TypeVar('R')


class FunctionTimeoutError(Exception):
    """Raised when a function exceeds its timeout."""
    pass


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
        last_exception: Optional[Exception] = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    time.sleep(sleep_time)
                    sleep_time *= factor
        
        # All retries exhausted
        raise last_exception  # type: ignore
    
    return wrapper


def create_async_retry_wrapper(
    func: Callable[P, R],
    times: int = 3,
    delay: float = 1.0,
    factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[P, R]:
    """
    Create an async wrapper that retries the function on failure.
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        last_exception: Optional[Exception] = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                # Run sync function in thread pool
                return await asyncio.to_thread(func, *args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    await asyncio.sleep(sleep_time)
                    sleep_time *= factor
        
        raise last_exception  # type: ignore
    
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
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=seconds)
            except concurrent.futures.TimeoutError:
                raise FunctionTimeoutError(
                    f"{func.__name__} timed out after {seconds} seconds"
                )
    
    return wrapper


def create_async_timeout_wrapper(
    func: Callable[P, R],
    seconds: float,
) -> Callable[P, R]:
    """
    Create an async wrapper that times out.
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(func, *args, **kwargs),
                timeout=seconds,
            )
        except asyncio.TimeoutError:
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
    # Use a shared executor for background tasks
    # This is created lazily and reused
    executor: Optional[ThreadPoolExecutor] = None
    
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Future[R]:
        nonlocal executor
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=4)
        return executor.submit(func, *args, **kwargs)
    
    return wrapper


def create_async_wrapper(
    func: Callable[P, R],
) -> Callable[P, R]:
    """
    Create an async wrapper using to_thread.
    
    Args:
        func: Sync function to wrap
        
    Returns:
        Async function that runs the original in a thread pool
    """
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(func, *args, **kwargs)
    
    return wrapper


def create_async_timeout_wrapper_v2(
    async_func: Callable[P, R],
    seconds: float,
) -> Callable[P, R]:
    """
    Create an async wrapper that times out (for already-async functions).
    """
    @functools.wraps(async_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await asyncio.wait_for(
                async_func(*args, **kwargs),
                timeout=seconds,
            )
        except asyncio.TimeoutError:
            func_name = getattr(async_func, '__name__', 'function')
            raise FunctionTimeoutError(
                f"{func_name} timed out after {seconds} seconds"
            )
    
    return wrapper


def create_async_retry_wrapper_v2(
    async_func: Callable[P, R],
    times: int = 3,
    delay: float = 1.0,
    factor: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[P, R]:
    """
    Create an async retry wrapper (for already-async functions).
    """
    @functools.wraps(async_func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        last_exception: Optional[Exception] = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                return await async_func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    await asyncio.sleep(sleep_time)
                    sleep_time *= factor
        
        raise last_exception  # type: ignore
    
    return wrapper
