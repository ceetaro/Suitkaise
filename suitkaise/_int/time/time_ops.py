"""
Complete Time Operations System for Suitkaise.

This module provides internal timing functionality that powers the SKTime module.
It includes sophisticated timing classes, statistical analysis, and timing utilities
for performance measurement and time-based operations.

Key Features:
- Elapsed time calculations with automatic current time detection
- Yawn class for delayed sleep operations
- Stopwatch with pause/resume/lap functionality
- Timer for statistical timing analysis
- Comprehensive timing decorators and context managers

The internal operations handle all the complex timing logic and state management.
"""

import time
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
    return abs(time2 - time1)


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


class _Stopwatch:
    """
    High-precision stopwatch with pause/resume and lap functionality.
    
    Provides precise timing measurements with the ability to pause timing,
    record lap times, and get detailed timing statistics.
    """
    
    def __init__(self):
        """Initialize a new stopwatch."""
        self.start_time: Optional[float] = None
        self.pause_time: Optional[float] = None
        self.total_paused_time: float = 0.0
        self.lap_times: List[float] = []
        self.is_running: bool = False
        self.is_paused: bool = False
        self.final_time: Optional[float] = None
        
    def start(self) -> float:
        """
        Start the stopwatch.
        
        Returns:
            Start timestamp
            
        Raises:
            RuntimeError: If stopwatch is already running
        """
        if self.is_running:
            raise RuntimeError("Stopwatch is already running. Use resume() if paused.")
        
        self.start_time = time.time()
        self.is_running = True
        self.is_paused = False
        self.total_paused_time = 0.0
        self.lap_times.clear()
        
        return self.start_time
    
    def pause(self) -> float:
        """
        Pause the stopwatch.
        
        Returns:
            Current elapsed time when paused
            
        Raises:
            RuntimeError: If stopwatch is not running or already paused
        """
        if not self.is_running:
            raise RuntimeError("Cannot pause stopwatch that is not running.")
        if self.is_paused:
            raise RuntimeError("Stopwatch is already paused.")
        
        self.pause_time = time.time()
        self.is_paused = True
        
        return self.elapsed_time
    
    def resume(self) -> float:
        """
        Resume the stopwatch from pause.
        
        Returns:
            Time spent paused
            
        Raises:
            RuntimeError: If stopwatch is not paused
        """
        if not self.is_running:
            raise RuntimeError("Cannot resume stopwatch that is not running.")
        if not self.is_paused:
            raise RuntimeError("Stopwatch is not paused.")
        
        pause_duration = time.time() - self.pause_time
        self.total_paused_time += pause_duration
        self.pause_time = None
        self.is_paused = False
        
        return pause_duration
    
    def lap(self) -> float:
        """
        Record a lap time.
        
        Returns:
            Current elapsed time for this lap
            
        Raises:
            RuntimeError: If stopwatch is not running
        """
        if not self.is_running:
            raise RuntimeError("Cannot record lap time when stopwatch is not running.")
        
        current_time = self.elapsed_time
        self.lap_times.append(current_time)
        
        return current_time
    
    def stop(self) -> float:
        """
        Stop the stopwatch.
        
        Returns:
            Total elapsed time
            
        Raises:
            RuntimeError: If stopwatch is not running
        """
        if not self.is_running:
            raise RuntimeError("Cannot stop stopwatch that is not running.")
        
        # If paused, resume to calculate final time
        if self.is_paused:
            self.resume()
        
        final_time = self.elapsed_time
        self.final_time = final_time
        self.is_running = False
        
        return final_time
    
    @property
    def elapsed_time(self) -> float:
        """Get current elapsed time, accounting for pauses."""
        if self.start_time is None:
            return 0.0
        
        if not self.is_running and self.final_time is not None:
            return self.final_time
        
        if self.is_paused:
            # Calculate time up to pause point
            return (self.pause_time - self.start_time) - self.total_paused_time
        else:
            # Calculate current time minus pauses
            return (time.time() - self.start_time) - self.total_paused_time
    
    @property
    def total_time(self) -> float:
        """Alias for elapsed_time for compatibility."""
        return self.elapsed_time
    
    def get_laptime(self, lap_number: int) -> Optional[float]:
        """
        Get the time for a specific lap.
        
        Args:
            lap_number: 1-based lap number
            
        Returns:
            Lap time or None if lap doesn't exist
        """
        if 1 <= lap_number <= len(self.lap_times):
            return self.lap_times[lap_number - 1]
        return None
    
    def get_lap_statistics(self) -> Dict[str, float]:
        """Get statistical analysis of lap times."""
        if not self.lap_times:
            return {}
        
        return {
            'count': len(self.lap_times),
            'mean': statistics.mean(self.lap_times),
            'median': statistics.median(self.lap_times),
            'fastest': min(self.lap_times),
            'slowest': max(self.lap_times),
            'stdev': statistics.stdev(self.lap_times) if len(self.lap_times) > 1 else 0.0
        }
    
    def reset(self) -> None:
        """Reset the stopwatch to initial state."""
        self.start_time = None
        self.pause_time = None
        self.total_paused_time = 0.0
        self.lap_times.clear()
        self.is_running = False
        self.is_paused = False
        self.final_time = None


class _Timer:
    """
    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    """
    
    def __init__(self):
        """Initialize a new timer."""
        self.times: List[float] = []
        self.current_start: Optional[float] = None
        
    def start(self) -> float:
        """
        Start timing a new measurement.
        
        Returns:
            Start timestamp
        """
        self.current_start = time.time()
        return self.current_start
    
    def stop(self) -> float:
        """
        Stop timing and record the measurement.
        
        Returns:
            Elapsed time for this measurement
            
        Raises:
            RuntimeError: If timer was not started
        """
        if self.current_start is None:
            raise RuntimeError("Timer was not started. Call start() first.")
        
        elapsed = time.time() - self.current_start
        self.times.append(elapsed)
        self.current_start = None
        
        return elapsed
    
    def add_time(self, elapsed_time: float) -> None:
        """
        Manually add a timing measurement.
        
        Args:
            elapsed_time: Time to add to statistics
        """
        self.times.append(elapsed_time)
    
    @property
    def count(self) -> int:
        """Number of timing measurements recorded."""
        return len(self.times)
    
    @property
    def mostrecent(self) -> Optional[float]:
        """Most recent timing measurement."""
        return self.times[-1] if self.times else None
    
    @property
    def result(self) -> Optional[float]:
        """Alias for mostrecent for context manager compatibility."""
        return self.mostrecent
    
    @property
    def mean(self) -> Optional[float]:
        """Mean (average) of all timing measurements."""
        return statistics.mean(self.times) if self.times else None
    
    @property
    def median(self) -> Optional[float]:
        """Median of all timing measurements."""
        return statistics.median(self.times) if self.times else None
    
    @property
    def longest(self) -> Optional[float]:
        """Longest (maximum) timing measurement."""
        return max(self.times) if self.times else None
    
    @property
    def shortest(self) -> Optional[float]:
        """Shortest (minimum) timing measurement."""
        return min(self.times) if self.times else None
    
    @property
    def std(self) -> Optional[float]:
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
    
    def get_a_time(self, index: int) -> Optional[float]:
        """
        Get timing measurement by index (1-based).
        
        Args:
            index: 1-based index of measurement
            
        Returns:
            Timing measurement or None if index is invalid
        """
        if 1 <= index <= len(self.times):
            return self.times[index - 1]
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
            'count': self.count,
            'mean': self.mean,
            'median': self.median,
            'longest': self.longest,
            'shortest': self.shortest,
            'std': self.std,
            'variance': self.variance,
            'percentile_95': self.percentile(95),
            'percentile_99': self.percentile(99),
            'total_time': sum(self.times)
        }
    
    def reset(self) -> None:
        """Clear all timing measurements."""
        self.times.clear()
        self.current_start = None
    
    def __enter__(self):
        """Context manager entry - start timing."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop timing."""
        if self.current_start is not None:
            self.stop()


def _create_timer_context_manager(timer_instance: _Timer):
    """
    Create a context manager for an existing timer instance.
    
    This allows using timer.TimeThis() to time code blocks while
    accumulating statistics in the timer instance.
    """
    class TimerContextManager:
        def __init__(self, timer: _Timer):
            self.timer = timer
            
        def __enter__(self):
            self.timer.start()
            return self.timer
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.timer.current_start is not None:
                self.timer.stop()
    
    return TimerContextManager(timer_instance)


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


def _create_standalone_timer_decorator():
    """
    Create a standalone timing decorator that uses its own timer instance.
    
    Returns:
        Decorator function
    """
    timer_instance = _Timer()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            timer_instance.start()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                timer_instance.stop()
        
        # Attach timer instance to function for access to statistics
        wrapper.timer = timer_instance
        return wrapper
    
    return decorator


# Convenience functions for direct access
def _get_current_time() -> float:
    """Get current Unix timestamp."""
    return time.time()


def _sleep(seconds: float) -> None:
    """Sleep for specified number of seconds."""
    time.sleep(seconds)
