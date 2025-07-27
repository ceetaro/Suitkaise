"""
SKTime API - Smart Timing Operations for Suitkaise

This module provides user-friendly timing functionality with statistical analysis,
sophisticated timing classes, and convenient decorators for performance measurement.

Key Features:
- Simple timing functions (now, sleep, elapsed)
- Yawn class for delayed sleep operations  
- Stopwatch with pause/resume and lap functionality
- Timer for statistical timing analysis with decorators and context managers
- Comprehensive timing statistics and analysis

Philosophy: Make timing operations intuitive while providing powerful analysis capabilities.
"""

import time
from typing import List, Optional, Union, Callable, Any, Dict
from functools import wraps

# Import internal time operations with fallback
try:
    from .._int.time.time_ops import (
        _elapsed_time,
        _Yawn,
        _Stopwatch, 
        _Timer,
        _create_timer_context_manager,
        _timethis_decorator,
        _create_standalone_timer_decorator,
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
# Stopwatch Class - Precision Timing with Laps
# ============================================================================

class Stopwatch:
    """
    High-precision stopwatch with pause/resume and lap functionality.
    
    Perfect for measuring code execution time, user interactions,
    or any scenario requiring precise timing with pause capability.
    
    Example:
        ```python
        sw = Stopwatch()
        
        sw.start()
        sleep(2)
        
        sw.pause()
        sleep(999)  # This time won't be counted
        
        sw.resume()  
        sleep(3)
        
        sw.lap()  # Records ~5 seconds
        sleep(2)
        
        total = sw.stop()  # ~7 seconds total
        lap1 = sw.get_laptime(1)  # ~5 seconds
        ```
    """
    
    def __init__(self):
        """Initialize a new stopwatch."""
        self._stopwatch = _Stopwatch()
    
    def start(self) -> float:
        """
        Start the stopwatch.
        
        Returns:
            Start timestamp
            
        Raises:
            RuntimeError: If stopwatch is already running
            
        Example:
            ```python
            start_time = sw.start()
            print(f"Started at: {start_time}")
            ```
        """
        return self._stopwatch.start()
    
    def pause(self) -> float:
        """
        Pause the stopwatch.
        
        Returns:
            Current elapsed time when paused
            
        Raises:
            RuntimeError: If stopwatch is not running or already paused
            
        Example:
            ```python
            elapsed_when_paused = sw.pause()
            print(f"Paused at: {elapsed_when_paused} seconds")
            ```
        """
        return self._stopwatch.pause()
    
    def resume(self) -> float:
        """
        Resume the stopwatch from pause.
        
        Returns:
            Time spent paused
            
        Raises:
            RuntimeError: If stopwatch is not paused
            
        Example:
            ```python
            pause_duration = sw.resume()
            print(f"Was paused for: {pause_duration} seconds")
            ```
        """
        return self._stopwatch.resume()
    
    def lap(self) -> float:
        """
        Record a lap time.
        
        Returns:
            Current elapsed time for this lap
            
        Raises:
            RuntimeError: If stopwatch is not running
            
        Example:
            ```python
            lap_time = sw.lap()
            print(f"Lap completed in: {lap_time} seconds")
            ```
        """
        return self._stopwatch.lap()
    
    def stop(self) -> float:
        """
        Stop the stopwatch.
        
        Returns:
            Total elapsed time
            
        Raises:
            RuntimeError: If stopwatch is not running
            
        Example:
            ```python
            total_time = sw.stop()
            print(f"Total elapsed: {total_time} seconds")
            ```
        """
        return self._stopwatch.stop()
    
    @property
    def total_time(self) -> float:
        """
        Get current elapsed time, accounting for pauses.
        
        Example:
            ```python
            print(f"Current elapsed: {sw.total_time} seconds")
            ```
        """
        return self._stopwatch.total_time
    
    @property
    def elapsed_time(self) -> float:
        """Alias for total_time."""
        return self._stopwatch.elapsed_time
    
    @property 
    def is_running(self) -> bool:
        """Check if stopwatch is currently running."""
        return self._stopwatch.is_running
    
    @property
    def is_paused(self) -> bool:
        """Check if stopwatch is currently paused."""
        return self._stopwatch.is_paused
    
    def get_laptime(self, lap_number: int) -> Optional[float]:
        """
        Get the time for a specific lap.
        
        Args:
            lap_number: 1-based lap number
            
        Returns:
            Lap time or None if lap doesn't exist
            
        Example:
            ```python
            lap1 = sw.get_laptime(1)
            lap2 = sw.get_laptime(2)
            if lap1:
                print(f"First lap: {lap1} seconds")
            ```
        """
        return self._stopwatch.get_laptime(lap_number)
    
    def get_lap_statistics(self) -> Dict[str, float]:
        """
        Get statistical analysis of lap times.
        
        Returns:
            Dictionary with lap statistics
            
        Example:
            ```python
            stats = sw.get_lap_statistics()
            if stats:
                print(f"Average lap: {stats['mean']} seconds")
                print(f"Fastest lap: {stats['fastest']} seconds")
            ```
        """
        return self._stopwatch.get_lap_statistics()
    
    def reset(self) -> None:
        """
        Reset the stopwatch to initial state.
        
        Example:
            ```python
            sw.reset()  # Ready to start timing again
            ```
        """
        self._stopwatch.reset()


# ============================================================================
# Timer Class - Statistical Timing Analysis
# ============================================================================

class Timer:
    """
    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    Can be used as a context manager or with decorators.
    
    Example:
        ```python
        timer = Timer()
        
        # Method 1: Manual timing
        timer.start()
        do_work()
        timer.stop()
        
        # Method 2: Context manager
        with timer:
            do_work()
        
        # Method 3: Decorator
        @timethis(timer)
        def my_function():
            do_work()
        
        # Get statistics
        print(f"Mean time: {timer.mean}")
        print(f"Median time: {timer.median}")
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
    def count(self) -> int:
        """Number of timing measurements recorded."""
        return self._timer.count
    
    @property
    def times(self) -> int:
        """Alias for count - number of measurements."""
        return self.count
    
    @property
    def mostrecent(self) -> Optional[float]:
        """Most recent timing measurement."""
        return self._timer.mostrecent
    
    @property
    def result(self) -> Optional[float]:
        """Alias for mostrecent for context manager compatibility."""
        return self._timer.result
    
    @property
    def mean(self) -> Optional[float]:
        """Mean (average) of all timing measurements."""
        return self._timer.mean
    
    @property
    def median(self) -> Optional[float]:
        """Median of all timing measurements."""
        return self._timer.median
    
    @property
    def longest(self) -> Optional[float]:
        """Longest (maximum) timing measurement."""
        return self._timer.longest
    
    @property
    def shortest(self) -> Optional[float]:
        """Shortest (minimum) timing measurement."""
        return self._timer.shortest
    
    @property
    def std(self) -> Optional[float]:
        """Standard deviation of timing measurements."""
        return self._timer.std
    
    @property
    def variance(self) -> Optional[float]:
        """Variance of timing measurements."""
        return self._timer.variance
    
    def get_a_time(self, index: int) -> Optional[float]:
        """
        Get timing measurement by index (1-based).
        
        Args:
            index: 1-based index of measurement
            
        Returns:
            Timing measurement or None if index is invalid
            
        Example:
            ```python
            first_time = timer.get_a_time(1)
            tenth_time = timer.get_a_time(10)
            ```
        """
        return self._timer.get_a_time(index)
    
    def percentile(self, percent: float) -> Optional[float]:
        """
        Get percentile of timing measurements.
        
        Args:
            percent: Percentile to calculate (0-100)
            
        Returns:
            Percentile value or None if no measurements
            
        Example:
            ```python
            p95 = timer.percentile(95)  # 95th percentile
            p99 = timer.percentile(99)  # 99th percentile
            ```
        """
        return self._timer.percentile(percent)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive timing statistics.
        
        Returns:
            Dictionary with all available statistics
            
        Example:
            ```python
            stats = timer.get_statistics()
            print(f"Count: {stats['count']}")
            print(f"Mean: {stats['mean']}")
            print(f"95th percentile: {stats['percentile_95']}")
            ```
        """
        return self._timer.get_statistics()
    
    def reset(self) -> None:
        """
        Clear all timing measurements.
        
        Example:
            ```python
            timer.reset()  # Start fresh
            ```
        """
        self._timer.reset()
    
    def TimeThis(self):
        """
        Get a context manager for this timer instance.
        
        Allows using with timer.TimeThis() to accumulate statistics
        in this timer while timing code blocks.
        
        Returns:
            Context manager for this timer
            
        Example:
            ```python
            timer = Timer()
            
            for i in range(100):
                with timer.TimeThis():
                    do_work()
            
            print(f"Mean time: {timer.mean}")
            print(f"Times measured: {timer.count}")
            ```
        """
        return _create_timer_context_manager(self._timer)
    
    def __enter__(self):
        """Context manager entry - start timing."""
        return self._timer.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop timing."""
        return self._timer.__exit__(exc_type, exc_val, exc_tb)


# ============================================================================
# Timing Decorators
# ============================================================================

def timethis(timer_instance: Timer) -> Callable:
    """
    Create a timing decorator that accumulates statistics in a Timer instance.
    
    Args:
        timer_instance: Timer to accumulate timing data in
        
    Returns:
        Decorator function
        
    Example:
        ```python
        timer = Timer()
        
        @timethis(timer)
        def do_work():
            sleep(1)
        
        # Call multiple times to build statistics
        for i in range(100):
            do_work()
        
        print(f"Mean execution time: {timer.mean}")
        print(f"Standard deviation: {timer.std}")
        ```
    """
    return _timethis_decorator(timer_instance._timer)


# Note: We don't expose the standalone timer decorator from the internal module
# as the API concept doesn't show this usage pattern. Users should create 
# Timer instances explicitly for better clarity and control.


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
    'Stopwatch',
    'Timer',
    
    # Decorators
    'timethis',
]