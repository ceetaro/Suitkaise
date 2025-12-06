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

from dataclasses import dataclass
import time
from time import perf_counter
import threading
import warnings
from math import fabs
import statistics
from typing import List, Optional, Union, Callable, Any, Dict, Deque
from collections import deque
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
        # Use wall clock to remain compatible with sktime.now()/get_current_time()
        time2 = time.time()
    
    # Return absolute difference so order doesn't matter
    return fabs(time2 - time1)


class Yawn:
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
        self._lock = threading.RLock()
        
    def yawn(self) -> bool:
        """
        Register a yawn. Sleep if threshold is reached.
        
        Returns:
            True if sleep occurred, False otherwise
        """
        with self._lock:
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
        with self._lock:
            self.yawn_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about yawn behavior."""
        with self._lock:
            return {
                'current_yawns': self.yawn_count,
                'yawn_threshold': self.yawn_threshold,
                'total_sleeps': self.total_sleeps,
                'sleep_duration': self.sleep_duration,
                'yawns_until_sleep': self.yawn_threshold - self.yawn_count
            }

class TimerStats:
    """
    Statistics about a timer returned by _Timer.get_statistics()
    """
    def __init__(self, times: List[float], original_start_time: Optional[float], paused_durations: List[float]):
        self.times = times

        self.original_start_time = original_start_time
        self.num_times = len(times)
        self.most_recent = times[-1] if times else None
        self.most_recent_index = len(times) - 1 if times else None
        self.total_time = sum(times)
        self.total_time_paused = sum(paused_durations) if times else None
        
        self.mean = statistics.mean(times) if times else None
        self.median = statistics.median(times) if times else None
        self.slowest_lap = times.index(max(times)) if times else None
        self.fastest_lap = times.index(min(times)) if times else None
        self.slowest_time = max(times) if times else None
        self.fastest_time = min(times) if times else None
        self.min = min(times) if times else None
        self.max = max(times) if times else None
        self.stdev = statistics.stdev(times) if len(times) > 1 else None
        self.variance = statistics.variance(times) if len(times) > 1 else None
        self.percentile_95 = self.percentile(95)
        self.percentile_99 = self.percentile(99)

    def percentile(self, percent: float) -> Optional[float]:
        """Get percentile without acquiring lock."""
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

    def get_time(self, index: int) -> Optional[float]:
        """Get time by index."""
        return self.times[index] if 0 <= index < len(self.times) else None
        
class Timer:
    """
    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    """
    
    def __init__(self):
        """
        Initialize a new concurrent-capable timer.

        Supports multiple concurrent timing sessions (one per thread by default),
        each with stackable measurements in the same thread. The manager aggregates
        all recorded times across sessions for statistics.
        """
        # Earliest start across all sessions
        self.original_start_time: Optional[float] = None

        # Aggregated list of all recorded times across all sessions
        self.times: List[float] = []
        # Parallel list of paused durations per recorded time
        self._paused_durations: List[float] = []

        # Thread safety lock for manager state (times, sessions)
        self._lock = threading.RLock()

        # Session management: keyed by thread ident
        self._sessions: Dict[int, "TimerSession"] = {}

    def _get_or_create_session(self) -> "TimerSession":

        ident = threading.get_ident()

        with self._lock:
            sess = self._sessions.get(ident)
            if sess is None:
                sess = TimerSession(self)
                self._sessions[ident] = sess
            return sess

        
    def start(self) -> float:
        """
        Start timing a new measurement.
        
        Returns:
            Start timestamp
        """
        # Create or get the session for the current thread and start a new frame
        sess = self._get_or_create_session()
        started = sess.start()

        with self._lock:
            if self.original_start_time is None:
                self.original_start_time = started
        return started
    
    def stop(self) -> float:
        """
        Stop timing and record the measurement.
        
        Returns:
            Elapsed time for this measurement
            
        Raises:
            RuntimeError: If timer was not started
        """
        # Stop the current thread's top frame
        sess = self._get_or_create_session()
        elapsed, paused_total = sess.stop()

        with self._lock:
            self.times.append(elapsed)
            self._paused_durations.append(paused_total)
        return elapsed

    def lap(self) -> float:
        """
        Record a lap time.

        Returns:
            Elapsed time for this lap

        Raises:
            RuntimeError: If timer was not started
        """
        # Lap the current thread's top frame (record and continue)
        sess = self._get_or_create_session()
        elapsed, paused_total = sess.lap()

        with self._lock:
            self.times.append(elapsed)
            self._paused_durations.append(paused_total)
        return elapsed

    def pause(self):
        """
        Pause the current timing measurement.

        Returns:
            Current elapsed time when paused

        Raises:
            RuntimeError: If timer is not running
        """
        sess = self._get_or_create_session()
        sess.pause()

    def resume(self):
        """
        Resume the current timing measurement.

        Returns:
            Current elapsed time when resumed

        Raises:
            RuntimeError: If timer is not paused
        """
        sess = self._get_or_create_session()
        sess.resume()
    
    def add_time(self, elapsed_time: float) -> None:
        """
        Manually add a timing measurement.
        
        Args:
            elapsed_time: Time to add to statistics
        """
        with self._lock:
            self.times.append(elapsed_time)
    
    @property
    def num_times(self) -> int:
        """Number of timing measurements recorded."""
        with self._lock:
            return len(self.times)
    
    @property
    def most_recent(self) -> Optional[float]:
        """Most recent timing measurement."""
        with self._lock:
            return self.times[-1] if self.times else None

    @property
    def result(self) -> Optional[float]:
        """Alias for most_recent."""
        return self.most_recent

    @property
    def most_recent_index(self) -> Optional[int]:
        """Index of most recent timing measurement."""
        with self._lock:
            return len(self.times) - 1 if self.times else None

    @property
    def total_time(self) -> Optional[float]:
        """Total time of all timing measurements."""
        with self._lock:
            return sum(self.times) if self.times else None

    @property
    def total_time_paused(self) -> Optional[float]:
        """Total time paused across all recorded measurements."""
        with self._lock:
            if not self._paused_durations:
                return None
            return sum(self._paused_durations)
    
    @property
    def mean(self) -> Optional[float]:
        """Mean (average) of all timing measurements."""
        with self._lock:
            return statistics.mean(self.times) if self.times else None
    
    @property
    def median(self) -> Optional[float]:
        """Median of all timing measurements."""
        with self._lock:
            return statistics.median(self.times) if self.times else None
    
    @property
    def slowest_lap(self) -> Optional[int]:
        """Index number of the slowest timing measurement."""
        with self._lock:
            return self.times.index(max(self.times)) if self.times else None
    
    @property
    def fastest_lap(self) -> Optional[int]:
        """Index of the fastest timing measurement."""
        with self._lock:
            return self.times.index(min(self.times)) if self.times else None

    @property
    def slowest_time(self) -> Optional[float]:
        """Time of the slowest timing measurement."""
        with self._lock:
            return max(self.times) if self.times else None
    
    @property
    def fastest_time(self) -> Optional[float]:
        """Time of the fastest timing measurement."""
        with self._lock:
            return min(self.times) if self.times else None

    @property
    def min(self) -> Optional[float]:
        """Minimum timing measurement."""
        with self._lock:
            return min(self.times) if self.times else None
    
    @property
    def max(self) -> Optional[float]:
        """Maximum timing measurement."""
        with self._lock:
            return max(self.times) if self.times else None
    
    @property
    def stdev(self) -> Optional[float]:
        """Standard deviation of timing measurements."""
        with self._lock:
            if len(self.times) <= 1:
                return None
            return statistics.stdev(self.times)
    
    @property
    def variance(self) -> Optional[float]:
        """Variance of timing measurements."""
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            if not self.times:
                return None
                
            if not 0 <= percent <= 100:
                raise ValueError("Percentile must be between 0 and 100")
            sorted_times = sorted(self.times)
            index = (percent / 100) * (len(sorted_times) - 1)

            if index == int(index):
                return sorted_times[int(index)]

            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return (sorted_times[lower_index] * (1 - weight) + 
                    sorted_times[upper_index] * weight)
    
    def _percentile_unlocked(self, percent: float) -> Optional[float]:
        """Get percentile without acquiring lock (for internal use)."""
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
    
    def get_statistics(self) -> Optional[TimerStats]:
        """Get comprehensive timing statistics."""
        with self._lock:
            if not self.times:
                return None
            return TimerStats(self.times, self.original_start_time, self._paused_durations)
    
    def reset(self) -> None:
        """Clear all timing measurements."""
        with self._lock:
            self.times.clear()
            self.original_start_time = None
            # Reset sessions as well
            self._sessions.clear()
            self._paused_durations.clear()


class TimerSession:
    """Per-thread timing session supporting nested frames (stack)."""

    def __init__(self, manager: Timer):
        self._manager = manager
        self._frames: Deque[Dict[str, Any]] = deque()
        self._lock = threading.RLock()

    def _now(self) -> float:
        # Use high-resolution monotonic clock for intervals
        return perf_counter()

    def start(self) -> float:
        with self._lock:
            frame = {
                'start_time': self._now(),
                'paused': False,
                'pause_started_at': None,
                'total_paused': 0.0,
            }
            self._frames.append(frame)
            return frame['start_time']

    def _top(self) -> Dict[str, Any]:
        if not self._frames:
            raise RuntimeError("Timer is not running. Call start() first.")
        return self._frames[-1]

    def pause(self) -> None:
        with self._lock:
            frame = self._top()
            if frame['paused']:
                warnings.warn("Timer is already paused. Call resume() first.", UserWarning, stacklevel=2)
                return

            frame['paused'] = True
            frame['pause_started_at'] = self._now()

    def resume(self) -> None:
        with self._lock:
            frame = self._top()
            if not frame['paused']:
                warnings.warn("Timer is not paused. Call pause() first.", UserWarning, stacklevel=2)
                return

            pause_duration = self._now() - frame['pause_started_at']  # type: ignore
            frame['total_paused'] += pause_duration
            frame['paused'] = False
            frame['pause_started_at'] = None

    def _elapsed_from_frame(self, frame: Dict[str, Any]) -> float:
        end = self._now()
        paused_extra = 0.0
        if frame['paused'] and frame['pause_started_at'] is not None:
            paused_extra = end - frame['pause_started_at']
            
        return (end - frame['start_time']) - (frame['total_paused'] + paused_extra)

    def _paused_total_from_frame(self, frame: Dict[str, Any]) -> float:
        end = self._now()
        paused_extra = 0.0
        if frame['paused'] and frame['pause_started_at'] is not None:
            paused_extra = end - frame['pause_started_at']
        return frame['total_paused'] + paused_extra

    def stop(self) -> tuple[float, float]:
        with self._lock:
            frame = self._top()
            elapsed = self._elapsed_from_frame(frame)
            paused_total = self._paused_total_from_frame(frame)
            self._frames.pop()
            return elapsed, paused_total

    def lap(self) -> tuple[float, float]:
        with self._lock:
            frame = self._top()
            elapsed = self._elapsed_from_frame(frame)
            paused_total = self._paused_total_from_frame(frame)
            # restart top frame
            frame['start_time'] = self._now()
            frame['total_paused'] = 0.0
            frame['paused'] = False
            frame['pause_started_at'] = None
            return elapsed, paused_total


def _timethis_decorator(timer_instance: Timer):
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
            # Concurrent session-aware: each thread call starts/stops its own session
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
