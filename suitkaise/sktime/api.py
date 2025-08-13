"""
SKTime API - Smart Timing Operations for Suitkaise

This module provides user-friendly timing functionality with statistical analysis,
sophisticated timing classes, and convenient decorators for performance measurement.

Key Features:
- Simple timing functions (now, sleep, elapsed)
- Yawn class for delayed sleep operations  
- Timer for statistical timing analysis, pause and resume, context manager and decorator

Philosophy: Make timing operations intuitive while providing powerful analysis capabilities.
"""

import time
from typing import List, Optional, Union, Callable, Any, Dict
from functools import wraps

# Import internal time operations with fallback
try:
    from .._int.core.time_ops import (
        _elapsed_time,
        _Yawn,
        _Timer,
        _timethis_decorator,
        _get_current_time,
        _sleep
    )
except ImportError:
    raise ImportError(
        "Internal time operations could not be imported. "
        "Ensure that the internal time operations module is available."
    )


# ============================================================================
# Simple Timing Functions
# ============================================================================

def now() -> float:
    """
    Get current Unix timestamp.
    
    Equivalent to time.time() but with clearer naming for timing operations.
    
    Returns:
        Current Unix timestamp as float
        
    Example:
        ```python
        current_time = now()
        print(f"Current timestamp: {current_time}")
        ```
    """
    return _get_current_time()


def get_current_time() -> float:
    """
    Get current Unix timestamp.
    
    Longer, clearer alias for now(). Use whichever feels more natural.
    
    Returns:
        Current Unix timestamp as float
        
    Example:
        ```python
        start_time = get_current_time()
        # ... do some work ...
        end_time = get_current_time()
        ```
    """
    return _get_current_time()


def sleep(seconds: float) -> None:
    """
    Sleep for specified number of seconds.
    
    Equivalent to time.sleep() but integrated with SKTime naming.
    
    Args:
        seconds: Number of seconds to sleep (can be fractional)
        
    Example:
        ```python
        sleep(1.5)  # Sleep for 1.5 seconds
        sleep(0.1)  # Sleep for 100 milliseconds
        ```
    """
    _sleep(seconds)


def elapsed(time1: float, time2: Optional[float] = None) -> float:
    """
    Calculate elapsed time between two timestamps.
    
    Order doesn't matter - always returns positive elapsed time.
    If only one time provided, calculates elapsed time from that time to now.
    
    Args:
        time1: First timestamp
        time2: Second timestamp (defaults to current time if None)
        
    Returns:
        Absolute elapsed time in seconds
        
    Example:
        ```python
        start = now()
        sleep(2)
        
        # Both of these return ~2.0
        elapsed_time = elapsed(start)           # time1 to now
        elapsed_time = elapsed(start, now())    # explicit time1 to time2
        
        # Order doesn't matter
        elapsed_time = elapsed(now(), start)    # Same result: ~2.0
        ```
    """
    return _elapsed_time(time1, time2)


# ============================================================================
# Yawn Class - Delayed Sleep Operations
# ============================================================================

class Yawn:
    """
    Sleep controller that sleeps after a specified number of "yawns".
    
    Useful for implementing delays that only trigger after repeated calls,
    such as rate limiting, progressive backoff, or periodic maintenance.
    
    Example:
        ```python
        # Sleep for 3 seconds after every 4 yawns
        sleepy = Yawn(3, 4, log_sleep=True)
        
        sleepy.yawn()  # No sleep
        sleepy.yawn()  # No sleep  
        sleepy.yawn()  # No sleep
        sleepy.yawn()  # Sleeps for 3 seconds!
        
        # Cycle repeats
        sleepy.yawn()  # No sleep again
        ```
    """
    
    def __init__(self, sleep_duration: float, yawn_threshold: int, log_sleep: bool = False):
        """
        Initialize a Yawn controller.
        
        Args:
            sleep_duration: How long to sleep when threshold is reached
            yawn_threshold: Number of yawns before sleeping
            log_sleep: Whether to print when sleep occurs
            
        Example:
            ```python
            # Sleep for 2 seconds after every 5 yawns, with logging
            yawn_controller = Yawn(2.0, 5, log_sleep=True)
            ```
        """
        self._yawn = _Yawn(sleep_duration, yawn_threshold, log_sleep)
    
    def yawn(self) -> bool:
        """
        Register a yawn. Sleep if threshold is reached.
        
        Returns:
            True if sleep occurred, False otherwise
            
        Example:
            ```python
            if yawn_controller.yawn():
                print("Just slept!")
            else:
                print("Still counting yawns...")
            ```
        """
        return self._yawn.yawn()
    
    def reset(self) -> None:
        """
        Reset the yawn counter without sleeping.
        
        Example:
            ```python
            yawn_controller.reset()  # Start counting from 0 again
            ```
        """
        self._yawn.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about yawn behavior.
        
        Returns:
            Dictionary with yawn statistics
            
        Example:
            ```python
            stats = yawn_controller.get_stats()
            print(f"Yawns until sleep: {stats['yawns_until_sleep']}")
            print(f"Total sleeps so far: {stats['total_sleeps']}")
            ```
        """
        return self._yawn.get_stats()


# ============================================================================
# Timer Class - Statistical Timing Analysis
# ============================================================================

# TODO add examples from concept.md
class Timer:
    """
    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    Can be used as a context manager or with decorators.
    
    Example:
        ```python
        add examples from concept.md
        ```
    """
    
    def __init__(self):
        """Initialize a new timer."""
        self._timer = _Timer()
    
    def start(self) -> float:
        """
        Start timing a new measurement.
        
        Returns:
            Start timestamp
            
        Example:
            ```python
            start_time = timer.start()
            # ... do work ...
            elapsed = timer.stop()
            ```
        """
        return self._timer.start()
    
    def stop(self) -> float:
        """
        Stop timing and record the measurement.
        
        Returns:
            Elapsed time for this measurement
            
        Raises:
            RuntimeError: If timer was not started
            
        Example:
            ```python
            timer.start()
            do_work()
            elapsed = timer.stop()
            print(f"Work took: {elapsed} seconds")
            ```
        """
        return self._timer.stop()

    def lap(self) -> float:
        """
        Record a lap time.
        """
        return self._timer.lap()

    def pause(self) -> None:
        """
        Pause the timer.
        """
        self._timer.pause()
    
    def resume(self) -> None:
        """
        Resume the timer.
        """
        self._timer.resume()
    
    def add_time(self, elapsed_time: float) -> None:
        """
        Manually add a timing measurement.
        
        Args:
            elapsed_time: Time to add to statistics
            
        Example:
            ```python
            # Add a pre-measured time
            timer.add_time(1.5)
            ```
        """
        self._timer.add_time(elapsed_time)

    @property
    def num_times(self) -> int:
        """
        Number of times measured.
        """
        return self._timer.num_times

    @property
    def original_start_time(self) -> Optional[float]:
        """
        Original start time of the timer.
        """
        return self._timer.original_start_time

    @property
    def most_recent(self) -> Optional[float]:
        """
        Most recent time measured.
        """
        return self._timer.most_recent

    @property
    def most_recent_lap(self) -> Optional[int]:
        """
        Index of the most recent time measured.
        """
        return self._timer.most_recent_index

    @property
    def result(self) -> Optional[float]:
        """
        Alias for most_recent.
        """
        return self._timer.most_recent

    @property
    def total_time(self) -> Optional[float]:
        """
        Total time of all measurements.
        """
        return self._timer.total_time

    @property
    def total_time_paused(self) -> Optional[float]:
        """
        Total time paused across all times.
        """
        return self._timer.total_time_paused
    
    @property
    def mean(self) -> Optional[float]:
        """
        Mean time of all measurements.
        """
        return self._timer.mean

    @property
    def median(self) -> Optional[float]:
        """
        Median time of all measurements.
        """
        return self._timer.median

    @property
    def slowest_lap(self) -> Optional[float]:
        """
        Time of the slowest lap.
        """
        return self._timer.slowest_lap

    @property
    def fastest_lap(self) -> Optional[float]:
        """
        Time of the fastest lap.
        """
        return self._timer.fastest_lap

    @property
    def slowest_time(self) -> Optional[float]:
        """
        Time of the slowest time.
        """
        return self._timer.slowest_time

    @property
    def fastest_time(self) -> Optional[float]:
        """
        Time of the fastest time.
        """
        return self._timer.fastest_time

    @property
    def min(self) -> Optional[float]:
        """
        Minimum time of all measurements.
        """
        return self._timer.min

    @property
    def max(self) -> Optional[float]:
        """
        Maximum time of all measurements.
        """
        return self._timer.max

    @property
    def stdev(self) -> Optional[float]:
        """
        Standard deviation of all measurements.
        """
        return self._timer.stdev

    @property
    def variance(self) -> Optional[float]:
        """
        Variance of all measurements.
        """
        return self._timer.variance

    def get_time(self, index: int) -> Optional[float]:
        """
        Get time by index.
        """
        return self._timer.get_time(index)

    def percentile(self, percent: float) -> Optional[float]:
        """
        Get percentile of all measurements.
        """
        return self._timer.percentile(percent)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics of all measurements.
        """
        return self._timer.get_statistics()

    def reset(self) -> None:
        """
        Reset the timer.
        """
        self._timer.reset()


# ============================================================================
# TimeThis Context Manager
# ============================================================================

class TimeThis:
    """
    Context manager for timing code blocks using Timer.

    Helpful for visualizing what timers are being used for what.
    """

    def __init__(self, timer: Optional[Timer] = None):
        self.timer = timer or Timer()

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
        self.timer.stop()


# ============================================================================
# Timing Decorators
# ============================================================================

def timethis(timer_instance: Optional[Timer] = None) -> Callable:
    """
    Create a timing decorator that accumulates statistics in a Timer instance.
    
    Args:
        timer_instance: Timer to accumulate timing data in. If None, creates
                       a global timer with name pattern: module_[class_]function_timer
        
    Returns:
        Decorator function
        
    Example:
        ```python
        # Method 1: With explicit timer (recommended for analysis)
        timer = Timer()
        
        @timethis(timer)
        def do_work():
            sleep(1)
        
        # Call multiple times to build statistics
        for i in range(100):
            do_work()
        
        print(f"Mean execution time: {timer.mean}")
        print(f"Standard deviation: {timer.stdev}")
        
        # Method 2: With automatic global timer (convenient for quick timing)
        @timethis()
        def quick_task():
            sleep(0.5)
        
        # Access the auto-created timer via function attribute
        quick_task()
        print(f"Last execution: {quick_task.timer.mostrecent}")
        ```
    """
    def decorator(func: Callable) -> Callable:
        # Determine timer to use
        if timer_instance is not None:
            # Use provided timer
            actual_timer = timer_instance._timer
            wrapper = _timethis_decorator(actual_timer)(func)
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
            
            # Get or create global timer
            if not hasattr(timethis, '_global_timers'):
                setattr(timethis, '_global_timers', {})
            
            global_timers = getattr(timethis, '_global_timers')
            if timer_name not in global_timers:
                global_timers[timer_name] = Timer()
            
            actual_timer = global_timers[timer_name]._timer
            wrapper = _timethis_decorator(actual_timer)(func)
            
            # Attach timer to function for easy access
            setattr(wrapper, 'timer', global_timers[timer_name])
        
        return wrapper
    
    return decorator


# Note: We've enhanced timethis() to support both explicit Timer instances and
# automatic global timer creation, providing the best of both worlds: convenience
# when you want quick timing, and explicit control when you need detailed analysis.


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Simple timing functions
    'now',
    'get_current_time', 
    'sleep',
    'elapsed',
    
    # Timing classes
    'Yawn',
    'Timer',

    # Context managers
    'TimeThis',
    
    # Decorators
    'timethis',
]