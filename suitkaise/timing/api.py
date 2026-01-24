"""
SKTime API - Smart Timing Operations for Suitkaise

This module provides user-friendly timing functionality with statistical analysis,
sophisticated timing classes, and convenient decorators for performance measurement.

Key Features:
- Simple timing functions (time, sleep, elapsed)
- Sktimer for statistical timing analysis, pause and resume, context manager and decorator

Philosophy: Make timing operations intuitive while providing powerful analysis capabilities.
"""

import time
import asyncio
import threading
from typing import List, Optional, Union, Callable, Any, Dict
from functools import wraps

# Import internal time operations with fallback
try:
    from ._int.time_ops import (
        _elapsed_time,
        Sktimer,
        _timethis_decorator,
        _get_current_time,
        _sleep,
    )
except ImportError:
    raise ImportError(
        "Internal time operations could not be imported. "
        "Ensure that the internal time operations module is available."
    )

# Import asyncable wrapper
from suitkaise.sk._int.asyncable import _AsyncableFunction


# ============================================================================
# Simple Timing Functions
# ============================================================================

def time() -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import timing
        
        start_time = timing.time()
        ```
    ────────────────────────────────────────────────────────\n

    Get current Unix timestamp.
    
    Equivalent to `time.time()`.
    
    Returns:
        Current Unix timestamp as a float
    """
    return _get_current_time()


def _sync_sleep(seconds: float) -> float:
    """Sync implementation of sleep."""
    _sleep(seconds)
    return _get_current_time()


async def _async_sleep(seconds: float) -> float:
    """Async implementation of sleep using asyncio.sleep."""
    await asyncio.sleep(seconds)
    return _get_current_time()


# Create the asyncable sleep function
_sleep_impl = _AsyncableFunction(_sync_sleep, _async_sleep, name='sleep')


def sleep(seconds: float) -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import timing

        start_time = timing.time()
        
        # sleep for 2 seconds
        timing.sleep(2)

        end_time = timing.time()

        # elapsed time should be about 2 seconds
        elapsed_time = end_time - start_time
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import timing
        
        start_time = timing.time()
        
        end_time = timing.sleep(2)
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Async version
        from suitkaise import timing
        
        end_time = await timing.sleep.asynced()(2)
        ```
    ────────────────────────────────────────────────────────\n

    Sleep the current thread for a given number of seconds.

    Optionally returns the current time after sleeping.
    
    Sleep is functionally equivalent to `time.sleep()`.
    
    Supports `.asynced()` for async usage:
        `await sleep.asynced()(seconds)` uses `asyncio.sleep` internally.
    
    Args:
        `seconds`: Number of seconds to sleep (can be fractional)

    Returns:
        Current time after sleeping
    """
    return _sleep_impl(seconds)


# Attach asynced method to sleep function
sleep.asynced = _sleep_impl.asynced


def elapsed(time1: float, time2: Optional[float] = None) -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import timing
        
        start_time = timing.time()
        
        timing.sleep(2)
        
        elapsed = timing.elapsed(start_time) # end time automatically set to current time
        
        # with 2 times
        start_time = timing.time() # 100
        timing.sleep(2)
        end_time = timing.time() # 102
        
        elapsed1 = timing.elapsed(start_time, end_time)  # |100 - 102| = 2
        elapsed2 = timing.elapsed(end_time, start_time)  # |102 - 100| = 2
        
        elapsed3 = timing.elapsed(start_time)       # Uses current time as end
        ```
    ────────────────────────────────────────────────────────\n

    Order-independent elapsed time calculation with automatic precision.
    
    Order doesn't matter - always returns positive elapsed time.
    If only one time is provided, calculates elapsed time from that time to when `elapsed()` is called.
    Uses `math.fabs()` for best precision when calculating absolute value of floats.
    
    Args:
        `time1`: First timestamp
        `time2`: Second timestamp (defaults to current time if `None`)
        
    Returns:
        Absolute elapsed time in seconds as a float
    
    """
    return _elapsed_time(time1, time2)


# ============================================================================
# Sktimer - imported directly from _int.time_ops
# ============================================================================
# Sktimer class is now imported directly from the internal module.
# This simplifies serialization and removes unnecessary wrapper indirection.


# ============================================================================
# TimeThis Context Manager
# ============================================================================

class TimeThis:
    """
    ────────────────────────────────────────────────────────
        ```python
        # create a one-use timer
        from suitkaise import timing

        with timing.TimeThis() as timer:

            # ... timed ...

        # timer is automatically stopped and single measurement is recorded

        # ... untimed ...
        print(f"Time taken: {timer.most_recent:.3f}s")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # create a context manager for an existing timer
        from suitkaise import timing

        my_timer = timing.Sktimer()
    
        def function1():
            with timing.TimeThis(my_timer):

                # ... timed ...
                return create_random_object()

        def function2(object):

            # ... untimed ...
            if not is_valid(object):
                return None

            with timing.TimeThis(my_timer):

                # ... timed ...
                process_object(object)

            # a time measurement is recorded when you exit the context manager

            # ... untimed ...
            return generate_data()

        function1()
        function2()

        print(f"Total time: {my_timer.total_time:.3f}s")
        ```
    ────────────────────────────────────────────────────────\n

    Context manager for timing code blocks with automatic timer management.
    
    Provides clean, easy-to-read timing for code blocks. Can work with
    independent timing contexts or accumulate statistics with explicit `Sktimer`.
    Supports pause/resume and lap timing within context blocks.
    
    When to Use What:
    - Use `TimeThis()` without `Sktimer` for quick, one-off timing measurements
    - Use `TimeThis(timer)` with explicit `Sktimer` for statistical analysis across multiple runs
    
    ────────────────────────────────────────────────────────
        ```python
        # Independent timing context

        # Real example: File compression comparison
        from suitkaise import timing

        large_dataset = get_large_dataset()

        with timing.TimeThis() as gzip_timer:
            compress_file_with_gzip("large_dataset.csv")
        
        print(f"GZIP compression took: {gzip_timer.most_recent:.3f}s")
        
        with timing.TimeThis() as lzma_timer:
            compress_file_with_lzma("large_dataset.csv")
            
        print(f"LZMA compression took: {lzma_timer.most_recent:.3f}s")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Independent timing context

        # Real example: Database query with user interaction
        from suitkaise import timing

        exported = False

        with timing.TimeThis() as timer:
            results = database.query("SELECT * FROM users WHERE active=1")
            
            # Pause timing while user reviews results
            timer.pause()
            user_wants_export = input(f"Found {len(results)} users. Export to CSV? (y/n): ")

            if user_wants_export.lower() == 'y':
                timer.resume()
                export_to_csv(results)
                timer.stop()

            else:
                timer.stop()

        print(f"Database operation took: {timer.most_recent:.3f}s (excluding user input)")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Explicit timer

        # Real example: API call performance monitoring
        from suitkaise import timing
        import requests

        api_timer = timing.Sktimer()
        
        # Time multiple API calls to build statistics
        with timing.TimeThis(api_timer) as timer:
            response = requests.get("https://api.github.com/users/octocat")
        
        print(f"API call 1: {timer.most_recent:.3f}s")
        
        with timing.TimeThis(api_timer) as timer:
            response = requests.get("https://api.github.com/users/torvalds")
        
        print(f"API call 2: {timer.most_recent:.3f}s")
        print(f"Average API time: {api_timer.mean:.3f}s")
        ```
        ────────────────────────────────────────────────────────\n
    
    Args:
        timer: Sktimer instance to use (creates new one if None)
        threshold: Minimum elapsed time to record (default 0.0)
    """

    def __init__(self, timer: Optional[Sktimer] = None, threshold: float = 0.0):
        self.timer = timer or Sktimer()
        self.threshold = threshold

    def pause(self):
        self.timer.pause()

    def resume(self):
        self.timer.resume()

    def lap(self):
        self.timer.lap()

    def __enter__(self):
        self.timer.start()
        return self.timer
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Get elapsed time without recording
        elapsed = self.timer.discard()
        
        # Only record if above threshold
        if elapsed >= self.threshold:
            self.timer.add_time(elapsed)


# ============================================================================
# Timing Decorators
# ============================================================================

def timethis(
    timer: Optional[Sktimer] = None,
    threshold: float = 0.0,
    max_times: Optional[int] = None,
) -> Callable:
    """
    Create a timing decorator that accumulates statistics in a `Sktimer` instance.
    
    The `@timethis` decorator supports both explicit `Sktimer` instances and automatic 
    global timer creation, providing the ultimate convenience.
    
    Args:
        `timer`: `Sktimer` to accumulate timing data in. If `None`, creates
                       a global timer with name pattern: `module_[class_]function_timer`
        `threshold`: Minimum elapsed time to record (default 0.0). Times below
                    this threshold are discarded and not recorded in statistics.
        `max_times`: Keep only the most recent N measurements (rolling window).

    Returns:
        Decorator function

    ────────────────────────────────────────────────────────\n

    Auto-created `Sktimer` (quickest way to use `Sktimer`):

        ```python
        from suitkaise import timing

        # No timer argument - creates global Sktimer automatically
        @timing.timethis()  
        def quick_function():
            # Code to time
            pass
        
        # Call the function
        quick_function()
        
        # Access the auto-created timer with super simple access
        print(f"Last execution: {quick_function.timer.most_recent:.3f}s")
        
        # Call multiple times to build statistics
        for i in range(100):
            quick_function()
        
        print(f"Average: {quick_function.timer.mean:.3f}s")
        ```
    ────────────────────────────────────────────────────────\n

    Explicit `Sktimer` (for gathering data from multiple functions):

        ```python
        from suitkaise import timing
        import random

        performance_timer = timing.Sktimer()
        
        @timing.timethis()
        @timing.timethis(performance_timer)
        def multiply(a: int, b: int) -> int:
            return a * b

        @timing.timethis()
        @timing.timethis(performance_timer)
        def divide(a: int, b: int) -> float:
            return a / b

        set_a = []
        set_b = []
        for i in range(1000):
            set_a.append(random.randint(1, 100))
            set_b.append(random.randint(1, 100))

        # Build statistics over many calls
        for a, b in zip(set_a, set_b):
            multiply(a, b)
            divide(a, b)

    
        # Analyze performance for each function separately
        print(f"Average execution: {multiply.timer.mean:.3f}s")
        print(f"Slowest execution: {multiply.timer.slowest_time:.3f}s")

        print(f"Average execution: {divide.timer.mean:.3f}s")
        print(f"Slowest execution: {divide.timer.slowest_time:.3f}s")

        # Analyze performance for both functions together
        print(f"Average execution: {performance_timer.mean:.3f}s")
        print(f"Slowest execution: {performance_timer.slowest_time:.3f}s")
        ```
    ────────────────────────────────────────────────────────\n
    
    Note:
        Global `@timethis` timer naming convention (for debugging):
        - Module-level functions: `module_function_timer`
        - Class methods: `module_ClassName_method_timer`
        - Each function gets its own dedicated timer
        - Zero runtime overhead looking up the timer (resolved at decoration time)

    Note:
        `@timethis` decorator supports multiple decorators on the same function.
        The `timer` parameter is used to specify the timer to use.
        If `None`, a global timer is created.
        
    """
    def decorator(func: Callable) -> Callable:
        # Determine timer to use
        if timer is not None:
            if max_times is not None:
                timer.set_max_times(max_times)
            # Use provided timer directly (no longer a wrapper)
            wrapper = _timethis_decorator(timer, threshold)(func)
        else:
            # Create global timer with naming convention (do this once at decoration time)
            import inspect
            
            frame = inspect.currentframe()
            if frame is not None and frame.f_back is not None:
                module_name = frame.f_back.f_globals.get('__name__', 'unknown')
            else:
                module_name = 'unknown'
            
            # Extract just the module name (remove package path)
            if '.' in module_name:
                module_name = module_name.split('.')[-1]
            
            # Check if function is in a class by looking at qualname
            func_qualname = func.__qualname__
            if '.' in func_qualname:
                # Function is in a class: Class.method
                class_name, func_name = func_qualname.rsplit('.', 1)
                timer_name = f"{module_name}_{class_name}_{func_name}_timer"
            else:
                # Function is at module level
                func_name = func_qualname
                timer_name = f"{module_name}_{func_name}_timer"
            
            # Get or create global timer (thread-safe)
            if not hasattr(timethis, '_global_timers'):
                setattr(timethis, '_global_timers', {})
                setattr(timethis, '_timers_lock', threading.RLock())
            
            lock = getattr(timethis, '_timers_lock')
            with lock:
                global_timers = getattr(timethis, '_global_timers')
                if timer_name not in global_timers:
                    global_timers[timer_name] = Sktimer(max_times=max_times)
                elif max_times is not None:
                    global_timers[timer_name].set_max_times(max_times)
            
            wrapper = _timethis_decorator(global_timers[timer_name], threshold)(func)
            
            # Attach timer to function for easy access
            setattr(wrapper, 'timer', global_timers[timer_name])
        
        return wrapper
    
    return decorator


def clear_global_timers() -> None:
    """Clear all auto-created global timers used by the timethis decorator.

    This is useful for long-lived processes or test environments to release
    references and start fresh for subsequently decorated functions.
    """
    if hasattr(timethis, '_timers_lock') and hasattr(timethis, '_global_timers'):
        lock = getattr(timethis, '_timers_lock')
        with lock:
            timers = getattr(timethis, '_global_timers')
            timers.clear()


# Note: We've enhanced timethis() to support both explicit Sktimer instances and
# automatic global timer creation, providing the best of both worlds: convenience
# when you want quick timing, and explicit control when you need detailed analysis.


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Simple timing functions
    'time',
    'sleep',
    'elapsed',
    
    # Timing classes
    'Sktimer',

    # Context managers
    'TimeThis',
    
    # Decorators
    'timethis',
    'clear_global_timers',
]