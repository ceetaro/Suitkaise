"""
Complete Time Operations System for Suitkaise.

This module provides internal timing functionality that powers the SKTime module.
It includes sophisticated timing classes, statistical analysis, and timing utilities
for performance measurement and time-based operations.

Key Features:
- Elapsed time calculations with automatic current time detection
- Yawn class for delayed sleep operations
- Timer class for statistical timing analysis with pause and resume
- Comprehensive timing decorators and context managers

The internal operations handle all the complex timing logic and state management.
"""

import time
from math import fabs
import statistics
from typing import List, Optional, Union, Callable, Any, Dict
from functools import wraps
from contextlib import contextmanager


def _elapsed_time(time1: float, time2: Optional[float] = None) -> float:
    """
    Calculate elapsed time between two timestamps.
    
    Args:
        time1: First timestamp
        time2: Second timestamp (defaults to current time if None)
        
    Returns:
        Absolute difference between timestamps in seconds
    """
    if time2 is None:
        time2 = time.time()
    
    # Return absolute difference so order doesn't matter
    return fabs(time2 - time1)


class _Yawn:
    """
    Sleep controller that sleeps after a specified number of "yawns".
    
    Useful for implementing delays that only trigger after repeated calls,
    such as rate limiting or progressive backoff scenarios.
    """
    
    def __init__(self, sleep_duration: float, yawn_threshold: int, log_sleep: bool = False):
        """
        Initialize a Yawn controller.
        
        Args:
            sleep_duration: How long to sleep when threshold is reached
            yawn_threshold: Number of yawns before sleeping
            log_sleep: Whether to print when sleep occurs
        """
        self.sleep_duration = sleep_duration
        self.yawn_threshold = yawn_threshold
        self.log_sleep = log_sleep
        self.yawn_count = 0
        self.total_sleeps = 0
        
    def yawn(self) -> bool:
        """
        Register a yawn. Sleep if threshold is reached.
        
        Returns:
            True if sleep occurred, False otherwise
        """
        self.yawn_count += 1
        
        if self.yawn_count >= self.yawn_threshold:
            if self.log_sleep:
                print(f"Yawn threshold reached ({self.yawn_count}/{self.yawn_threshold}). Sleeping for {self.sleep_duration}s...")
            
            time.sleep(self.sleep_duration)
            self.yawn_count = 0  # Reset counter
            self.total_sleeps += 1
            return True
        
        return False
    
    def reset(self) -> None:
        """Reset the yawn counter without sleeping."""
        self.yawn_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about yawn behavior."""
        return {
            'current_yawns': self.yawn_count,
            'yawn_threshold': self.yawn_threshold,
            'total_sleeps': self.total_sleeps,
            'sleep_duration': self.sleep_duration,
            'yawns_until_sleep': self.yawn_threshold - self.yawn_count
        }

class _Timer:
    """
    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    """
    
    def __init__(self):
        """Initialize a new timer."""
        # first _Timer.start() call
        self.original_start_time: Optional[float] = None

        # list of all times recorded
        self.times: List[float] = []

        # current _Timer.start() call
        self.current_start_time: Optional[float] = None
        self.current_pause_time: Optional[float] = None

        # whether the current _Timer.start() call is paused
        self.paused = False

        
    def start(self) -> float:
        """
        Start timing a new measurement.
        
        Returns:
            Start timestamp
        """
        if self.original_start_time is None:
            self.original_start_time = time.time()

        self.current_start_time = time.time()
        return self.current_start_time
    
    def stop(self) -> float:
        """
        Stop timing and record the measurement.
        
        Returns:
            Elapsed time for this measurement
            
        Raises:
            RuntimeError: If timer was not started
        """
        if self.current_start_time is None:
            raise RuntimeError("Timer was not started. Call start() first.")

        if self.paused:
            self.resume()
        
        elapsed = time.time() - self.current_start_time
        self.times.append(elapsed)
        self.current_start_time = None
        
        return elapsed

    def lap(self) -> float:
        """
        Record a lap time.
        """
        if self.current_start_time is None:
            raise RuntimeError("Timer was not started. Call start() first.")

        self.stop()
        self.start()
        return self.most_recent # type: ignore

    def pause(self):
        """
        Pause the current timing measurement.

        Returns:
            Current elapsed time when paused

        Raises:
            RuntimeError: If timer is not running
        """
        if self.current_start_time is None:
            raise RuntimeError("Timer is not running. Call start() first.")

        if self.paused:
            # TODO raise warning
            return
        
        self.current_pause_time = time.time()
        self.paused = True

    def resume(self):
        """
        Resume the current timing measurement.

        Returns:
            Current elapsed time when resumed

        Raises:
            RuntimeError: If timer is not paused
        """
        if self.current_start_time is None:
            raise RuntimeError("Timer is not running. Call start() first.")
        
        if not self.paused:
            # TODO raise warning
            return
        
        # Calculate how long we were paused and adjust start time
        pause_duration = time.time() - self.current_pause_time # type: ignore
        self.current_start_time += pause_duration
        self.paused = False
    
    def add_time(self, elapsed_time: float) -> None:
        """
        Manually add a timing measurement.
        
        Args:
            elapsed_time: Time to add to statistics
        """
        self.times.append(elapsed_time)
    
    @property
    def num_times(self) -> int:
        """Number of timing measurements recorded."""
        return len(self.times)
    
    @property
    def most_recent(self) -> Optional[float]:
        """Most recent timing measurement."""
        return self.times[-1] if self.times else None

    @property
    def most_recent_index(self) -> Optional[int]:
        """Index of most recent timing measurement."""
        return len(self.times) - 1 if self.times else None

    @property
    def total_time(self) -> Optional[float]:
        """Total time of all timing measurements."""
        return sum(self.times) if self.times else None

    @property
    def total_time_paused(self) -> Optional[float]:
        """Total time paused across all times."""
        if not self.total_time:
            return None

        return time.time() - self.original_start_time - self.total_time # type: ignore
    
    @property
    def mean(self) -> Optional[float]:
        """Mean (average) of all timing measurements."""
        return statistics.mean(self.times) if self.times else None
    
    @property
    def median(self) -> Optional[float]:
        """Median of all timing measurements."""
        return statistics.median(self.times) if self.times else None
    
    @property
    def slowest_lap(self) -> Optional[float]:
        """Index number of the slowest timing measurement."""
        return self.times.index(max(self.times)) if self.times else None
    
    @property
    def fastest_lap(self) -> Optional[float]:
        """Index of the fastest timing measurement."""
        return self.times.index(min(self.times)) if self.times else None

    @property
    def slowest_time(self) -> Optional[float]:
        """Time of the slowest timing measurement."""
        return max(self.times) if self.times else None
    
    @property
    def fastest_time(self) -> Optional[float]:
        """Time of the fastest timing measurement."""
        return min(self.times) if self.times else None

    @property
    def min(self) -> Optional[float]:
        """Minimum timing measurement."""
        return min(self.times) if self.times else None
    
    @property
    def max(self) -> Optional[float]:
        """Maximum timing measurement."""
        return max(self.times) if self.times else None
    
    @property
    def stdev(self) -> Optional[float]:
        """Standard deviation of timing measurements."""
        if len(self.times) <= 1:
            return None
        return statistics.stdev(self.times)
    
    @property
    def variance(self) -> Optional[float]:
        """Variance of timing measurements."""
        if len(self.times) <= 1:
            return None
        return statistics.variance(self.times)
    
    def get_time(self, index: int) -> Optional[float]:
        """
        Get timing measurement by index (0-based).
        
        Args:
            index: 0-based index of measurement
            
        Returns:
            Timing measurement or None if index is invalid
        """
        if 0 <= index < len(self.times):
            return self.times[index]
        return None
    
    def percentile(self, percent: float) -> Optional[float]:
        """
        Get percentile of timing measurements.
        
        Args:
            percent: Percentile to calculate (0-100)
            
        Returns:
            Percentile value or None if no measurements
        """
        if not self.times:
            return None
        
        if not 0 <= percent <= 100:
            raise ValueError("Percentile must be between 0 and 100")
        
        sorted_times = sorted(self.times)
        index = (percent / 100) * (len(sorted_times) - 1)
        
        if index == int(index):
            return sorted_times[int(index)]
        else:
            # Linear interpolation between two values
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            return (sorted_times[lower_index] * (1 - weight) + 
                   sorted_times[upper_index] * weight)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive timing statistics."""
        if not self.times:
            return {'count': 0}
        
        return {
            'num_times': self.num_times,
            'most_recent': self.most_recent,
            'most_recent_index': self.most_recent_index,
            'total_time': self.total_time,
            'total_time_paused': self.total_time_paused,
            'mean': self.mean,
            'median': self.median,
            'slowest_lap': self.slowest_lap,
            'fastest_lap': self.fastest_lap,
            'slowest_time': self.slowest_time,
            'fastest_time': self.fastest_time,
            'min': self.min,
            'max': self.max,
            'stdev': self.stdev,
            'variance': self.variance,
            'percentile_95': self.percentile(95),
            'percentile_99': self.percentile(99),
            'total_time': sum(self.times)
        }
    
    def reset(self) -> None:
        """Clear all timing measurements."""
        self.times.clear()
        self.current_start_time = None
        self.current_pause_time = None
        self.paused = False
        self.original_start_time = None

def _timethis_decorator(timer_instance: _Timer):
    """
    Create a timing decorator for an existing timer instance.
    
    Args:
        timer_instance: Timer to accumulate statistics in
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_instance.start()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                timer_instance.stop()
        return wrapper
    return decorator

# Convenience functions for direct access
def _get_current_time() -> float:
    """Get current Unix timestamp."""
    return time.time()


def _sleep(seconds: float) -> None:
    """Sleep for specified number of seconds."""
    time.sleep(seconds)
