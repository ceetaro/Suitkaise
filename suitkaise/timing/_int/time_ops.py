"""
Complete Time Operations System for Suitkaise.

This module provides internal timing functionality that powers the timing module.
It includes sophisticated timing classes, statistical analysis, and timing utilities
for performance measurement and time-based operations.

Key Features:
- Elapsed time calculations with automatic current time detection
- Sktimer class for statistical timing analysis with pause and resume
- Comprehensive timing decorators and context managers

The internal operations handle all the complex timing logic and state management.
"""

from dataclasses import dataclass
import inspect
import os
import sys
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
        # use wall clock to remain compatible with timing.time()
        time2 = time.time()
    
    # return absolute difference so order doesn't matter
    return fabs(time2 - time1)


class TimerStats:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import timing
        
        timer = timing.Sktimer()
        # ... record multiple timings ...
        
        # Get frozen snapshot
        snapshot = timer.get_statistics()
        
        print(snapshot.mean)
        print(snapshot.stdev)
        print(snapshot.percentile(95))
        ```
    ────────────────────────────────────────────────────────\n

    Frozen snapshot of timer statistics returned by `Sktimer.get_statistics()`.
    
    This is an immutable snapshot taken at the time `get_statistics()` was called.
    All values are pre-computed and won't change even if the timer continues recording.
    
    For live (always up-to-date) statistics, access properties directly.
    
    Attributes:
        `times`: List of all recorded timing measurements
        `num_times`: Number of timing measurements
        `mean`: Average of all times
        `median`: Median of all times
        `min` / `max`: Fastest / slowest times
        `stdev`: Standard deviation
        `variance`: Variance
        `total_time`: Sum of all times
        `total_time_paused`: Total time spent paused
    """
    def __init__(self, times: List[float], original_start_time: Optional[float], paused_durations: List[float]):
        self.times = times.copy()  # make a copy to ensure immutability

        self.original_start_time = original_start_time
        self.num_times = len(times)
        self.most_recent = times[-1] if times else None
        self.most_recent_index = len(times) - 1 if times else None
        self.total_time = sum(times) if times else None
        self.total_time_paused = sum(paused_durations) if paused_durations else None
        
        self.mean = statistics.mean(times) if times else None
        self.median = statistics.median(times) if times else None
        self.slowest_index = times.index(max(times)) if times else None
        self.fastest_index = times.index(min(times)) if times else None
        self.slowest_time = max(times) if times else None
        self.fastest_time = min(times) if times else None
        self.min = min(times) if times else None
        self.max = max(times) if times else None
        self.stdev = statistics.stdev(times) if len(times) > 1 else None
        self.variance = statistics.variance(times) if len(times) > 1 else None
        # removed hardcoded percentile_95 and percentile_99 - use percentile() method instead

    def percentile(self, percent: float) -> Optional[float]:
        """
        Calculate any percentile of the recorded times.
        
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
            # linear interpolation between two values
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
        
            return (sorted_times[lower_index] * (1 - weight) + 
                   sorted_times[upper_index] * weight)

    def get_time(self, index: int) -> Optional[float]:
        """Get time by index."""
        return self.times[index] if 0 <= index < len(self.times) else None


class Sktimer:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import timing
        
        timer = timing.Sktimer()
        
        for i in range(100):
            timer.start()
            do_work()
            timer.stop()
        
        # Access statistics directly on the timer
        print(f"Mean: {timer.mean:.3f}s")
        print(f"Std Dev: {timer.stdev:.3f}s")
        print(f"95th percentile: {timer.percentile(95):.3f}s")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Pause/resume to exclude user input from timing
        timer = timing.Sktimer()
        timer.start()
        
        do_initial_work()
        
        timer.pause()
        user_input = input("Continue? ")  # Not counted in timing
        timer.resume()
        
        do_more_work()
        elapsed = timer.stop()  # Only counts work, not user input
        ```
    ────────────────────────────────────────────────────────\n

    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    
    All statistics are accessed directly on the timer:
    - `timer.mean`
    - `timer.stdev`
    - `timer.percentile(95)`
    
    Features:
    - Thread-safe with per-thread timing sessions
    - Supports nested timing (stackable frames)
    - Pause/resume functionality
    - Discard unwanted measurements
    - Optional rolling window (keep last N measurements)
    
    Control Methods:
        `start()`: Start timing
        `stop()`: Stop and record measurement
        `discard()`: Stop without recording
        `lap()`: Record time and continue timing
        `pause()` / `resume()`: Pause/resume timing
        `add_time(float)`: Manually add a measurement
        `set_max_times(int|None)`: Set rolling window size
        `reset()`: Clear all measurements
    
    Statistics Properties:
        `num_times`: Number of recorded measurements
        `most_recent` / `result`: Most recent timing
        `total_time`: Sum of all times
        `total_time_paused`: Total time spent paused
        `mean`: Average of all times
        `median`: Median of all times  
        `min` / `max`: Fastest / slowest times
        `fastest_time` / `slowest_time`: Aliases for min/max
        `fastest_index` / `slowest_index`: Indices of fastest/slowest
        `stdev`: Standard deviation
        `variance`: Variance
        
    Statistics Methods:
        `get_time(index)`: Get specific measurement by index
        `percentile(percent)`: Calculate any percentile (0-100)
        `get_statistics()` / `get_stats()`: Frozen snapshot (TimerStats)
    """
    
    # metadata for Share - declares which attributes each method/property
    #   reads from or writes to 
    # used by the Share for synchronization
    _shared_meta = {
        'methods': {
            'add_time': {'writes': ['times', '_paused_durations']},
            'set_max_times': {'writes': ['times', '_paused_durations', '_max_times']},
            'reset': {'writes': ['times', '_sessions', '_paused_durations', 'original_start_time']},
            'get_statistics': {'reads': ['times']},
            'get_stats': {'reads': ['times']},
            'get_time': {'reads': ['times']},
            'percentile': {'reads': ['times']},
        },
        'properties': {
            'num_times': {'reads': ['times']},
            'most_recent': {'reads': ['times']},
            'result': {'reads': ['times']},
            'most_recent_index': {'reads': ['times']},
            'total_time': {'reads': ['times']},
            'total_time_paused': {'reads': ['_paused_durations']},
            'mean': {'reads': ['times']},
            'median': {'reads': ['times']},
            'slowest_index': {'reads': ['times']},
            'fastest_index': {'reads': ['times']},
            'slowest_time': {'reads': ['times']},
            'fastest_time': {'reads': ['times']},
            'min': {'reads': ['times']},
            'max': {'reads': ['times']},
            'stdev': {'reads': ['times']},
            'variance': {'reads': ['times']},
            'max_times': {'reads': ['_max_times']},
        }
    }

    # methods that are blocked when accessed through Share's proxy.
    # start/stop/pause/resume/lap/discard rely on perf_counter() and
    # thread-local sessions - they would silently produce meaningless
    # measurements when replayed in the coordinator process.
    _share_blocked_methods = {
        'start':   "Sktimer.start() cannot be used through Share — timing would be measured in the coordinator process, not your subprocess. Use timer.add_time(elapsed) to aggregate pre-computed durations across processes.",
        'stop':    "Sktimer.stop() cannot be used through Share — timing would be measured in the coordinator process, not your subprocess. Use timer.add_time(elapsed) to aggregate pre-computed durations across processes.",
        'pause':   "Sktimer.pause() cannot be used through Share — timing sessions are thread-local and cannot cross process boundaries. Use timer.add_time(elapsed) to aggregate pre-computed durations across processes.",
        'resume':  "Sktimer.resume() cannot be used through Share — timing sessions are thread-local and cannot cross process boundaries. Use timer.add_time(elapsed) to aggregate pre-computed durations across processes.",
        'lap':     "Sktimer.lap() cannot be used through Share — timing would be measured in the coordinator process, not your subprocess. Use timer.add_time(elapsed) to aggregate pre-computed durations across processes.",
        'discard': "Sktimer.discard() cannot be used through Share — timing sessions are thread-local and cannot cross process boundaries.",
    }

    _PROCESS_LOCAL_ATTRS = frozenset({
        "_owner_pid",
        "_ensure_process_local_state",
        "_lock",
        "_sessions",
        "__class__",
        "__dict__",
        "__getattribute__",
    })
    
    def __init__(self, max_times: Optional[int] = None):
        """
        ────────────────────────────────────────────────────────
            ```python
            from suitkaise import timing
            
            timer = timing.Sktimer()
            ```
        ────────────────────────────────────────────────────────\n

        Initialize a new concurrent-capable timer.

        Supports multiple concurrent timing sessions (one per thread by default),
        each with stackable measurements in the same thread. The manager aggregates
        all recorded times across sessions for statistics.
        
        Args:
            max_times: Keep only the most recent N measurements (rolling window)
        """
        # earliest start across all sessions
        self.original_start_time: Optional[float] = None

        # aggregated list of all recorded times across all sessions
        self.times: List[float] = []
        # parallel list of paused durations per recorded time
        self._paused_durations: List[float] = []
        
        # optional rolling window size (None = keep all)
        self._max_times: Optional[int] = None

        # thread safety lock for manager state (times, sessions)
        self._lock = threading.RLock()
        self._owner_pid = os.getpid()

        # session management: keyed by thread ident
        self._sessions: Dict[int, "TimerSession"] = {}
        
        if max_times is not None:
            self.set_max_times(max_times)

    def __getattribute__(self, name: str):
        # Ensure process-local locks/session state are refreshed after fork
        # before most attribute access paths touch self._lock.
        if name not in object.__getattribute__(self, "_PROCESS_LOCAL_ATTRS"):
            try:
                owner_pid = object.__getattribute__(self, "_owner_pid")
            except Exception:
                owner_pid = None
            if owner_pid is not None and os.getpid() != owner_pid:
                object.__getattribute__(self, "_ensure_process_local_state")()
        return object.__getattribute__(self, name)
        


    # statistics properties (live, always up-to-date)

    @property
    def num_times(self) -> int:
        """Number of timing measurements recorded."""
        with self._lock:
            return len(self.times)
    
    @property
    def max_times(self) -> Optional[int]:
        """Maximum number of timing measurements to keep (rolling window)."""
        with self._lock:
            return self._max_times
    
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
    def slowest_index(self) -> Optional[int]:
        """Index of the slowest timing measurement."""
        with self._lock:
            return self.times.index(max(self.times)) if self.times else None
    
    @property
    def fastest_index(self) -> Optional[int]:
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
        """Minimum timing measurement (alias for fastest_time)."""
        return self.fastest_time
    
    @property
    def max(self) -> Optional[float]:
        """Maximum timing measurement (alias for slowest_time)."""
        return self.slowest_time
    
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
        Calculate any percentile of timing measurements.
        
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



    # internal session management

    def _ensure_process_local_state(self) -> None:
        """Reset process-local synchronization state after a fork."""
        current_pid = os.getpid()
        if current_pid == self._owner_pid:
            return
        # A fork can inherit an RLock in an unusable state.
        # Recreate lock/session bookkeeping in the child process.
        self._lock = threading.RLock()
        self._sessions = {}
        self._owner_pid = current_pid

    def _get_or_create_session(self) -> "TimerSession":
        self._ensure_process_local_state()

        ident = threading.get_ident()

        with self._lock:
            sess = self._sessions.get(ident)
            if sess is None:
                sess = TimerSession(self)
                self._sessions[ident] = sess
                # periodically purge sessions for dead threads to prevent
                # unbounded memory growth in long-running / many-thread apps
                self._purge_dead_sessions()
            return sess

    def _purge_dead_sessions(self) -> None:
        """Remove sessions for threads that no longer exist.
        
        Must be called while holding self._lock.
        """
        # threading.enumerate() may deadlock in forked children when parent
        # threads held interpreter locks at fork time. Use frame keys instead.
        alive_ids = set(sys._current_frames().keys())
        dead = [tid for tid in self._sessions if tid not in alive_ids]
        for tid in dead:
            del self._sessions[tid]
    
    def _has_active_frame(self) -> bool:
        """Check if current thread has an active timing frame."""
        self._ensure_process_local_state()
        ident = threading.get_ident()
        with self._lock:
            sess = self._sessions.get(ident)
            if sess is None:
                return False
            with sess._lock:
                return len(sess._frames) > 0

        
    def start(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.start()
            do_work()
            elapsed = timer.stop()
            ```
        ────────────────────────────────────────────────────────\n

        Start timing a new measurement.
        
        Issues a `UserWarning` if called while timing is already in progress
        (which creates a nested timing frame).
        
        Returns:
            Start timestamp (from `perf_counter()`)
        """
        self._ensure_process_local_state()

        # warn if there's already an active frame (user might not intend nesting)
        if self._has_active_frame():
            warnings.warn(
                "Sktimer.start() called while timing is already in progress. "
                "This creates a nested timing frame. Use stop() or discard() first "
                "if you want to restart timing.",
                UserWarning,
                stacklevel=2
            )
        
        # create or get the session for the current thread and start a new frame
        sess = self._get_or_create_session()
        started = sess.start()

        with self._lock:
            if self.original_start_time is None:
                self.original_start_time = started
        return started
    
    def stop(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.start()
            do_work()
            elapsed = timer.stop()  # returns elapsed time, records it
            
            print(timer.most_recent)  # same as elapsed
            ```
        ────────────────────────────────────────────────────────\n

        Stop timing and record the measurement.
        
        Returns:
            Elapsed time for this measurement (in seconds)
            
        Raises:
            `RuntimeError`: If timer was not started
        """
        # stop the current thread's top frame
        sess = self._get_or_create_session()
        elapsed, paused_total = sess.stop()

        with self._lock:
            self.times.append(elapsed)
            self._paused_durations.append(paused_total)
            self._trim_to_max()
        return elapsed

    def discard(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.start()
            try:
                result = risky_operation()
                timer.stop()  # record successful timing
            except Exception:
                timer.discard()  # don't record failed timing
            ```
        ────────────────────────────────────────────────────────\n

        Stop timing but do NOT record the measurement.
        
        Use this when you want to abandon the current timing session
        without polluting your statistics (e.g., an error occurred,
        or this was a warm-up run).
        
        Returns:
            Elapsed time that was discarded (for reference)
            
        Raises:
            `RuntimeError`: If timer was not started
        """
        # stop the current thread's top frame but don't record it
        sess = self._get_or_create_session()
        elapsed, _ = sess.stop()
        # intentionally NOT appending to self.times or self._paused_durations
        return elapsed

    def lap(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.start()
            
            for i in range(100):
                do_work()
                timer.lap()  # records time since last lap/start, continues timing

            timer.discard() # don't record the 101st measurement that is still running
            
            # 100 measurements recorded
            print(timer.mean)
            ```
        ────────────────────────────────────────────────────────\n

        Record a lap time (stop + start in one call).
        
        Records the elapsed time since the last `start()` or `lap()` call,
        then immediately starts a new timing period.

        Returns:
            Elapsed time for this lap (in seconds)

        Raises:
            `RuntimeError`: If timer was not started
        """
        # lap the current thread's top frame (record and continue)
        sess = self._get_or_create_session()
        elapsed, paused_total = sess.lap()

        with self._lock:
            self.times.append(elapsed)
            self._paused_durations.append(paused_total)
            self._trim_to_max()
        return elapsed

    def pause(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.start()

            do_something()
            
            timer.pause() # pause timer

            # user input time not counted because timer is paused
            user_input = input("Continue? ")

            timer.resume() # resume timer
            
            do_something_else()
            ```
        ────────────────────────────────────────────────────────\n

        Pause the current timing measurement.
        
        Time spent paused is excluded from the final elapsed time.
        Issues a `UserWarning` if already paused.

        Raises:
            `RuntimeError`: If timer is not running
        """
        sess = self._get_or_create_session()
        sess.pause()

    def resume(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.start()

            do_something()
            
            timer.pause() # pause timer

            # user input time not counted because timer is paused
            user_input = input("Continue? ")

            timer.resume() # resume timer
            
            do_something_else()
            ```
        ────────────────────────────────────────────────────────\n

        Resume a paused timing measurement.
        
        Issues a `UserWarning` if not currently paused.

        Raises:
            `RuntimeError`: If timer is not running
        """
        sess = self._get_or_create_session()
        sess.resume()
    
    def add_time(self, elapsed_time: float) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer = timing.Sktimer()
            
            # add pre-measured times
            timer.add_time(1.5)
            timer.add_time(2.3)
            timer.add_time(1.8)
            
            print(timer.mean)  # 1.867
            ```
        ────────────────────────────────────────────────────────\n

        Manually add a timing measurement.
        
        Args:
            `elapsed_time`: Time to add to statistics (in seconds)
        """
        with self._lock:
            self.times.append(elapsed_time)
            self._paused_durations.append(0.0)
            self._trim_to_max()
    
    
    def get_statistics(self) -> Optional[TimerStats]:
        """
        ────────────────────────────────────────────────────────
            ```python
            # get frozen snapshot of statistics
            snapshot = timer.get_statistics()
            
            # snapshot won't change even if timer continues
            timer.start()
            do_more_work()
            timer.stop()
            
            # snapshot still has old values
            print(snapshot.mean)
            ```
        ────────────────────────────────────────────────────────\n

        Get a frozen snapshot of all timing statistics.
        
        Returns a `TimerStats` object containing all statistics calculated
        at the moment this method was called. The snapshot is immutable
        and won't change even if the timer continues recording.
        
        For live (always up-to-date) statistics, access properties directly on the timer.
        
        Returns:
            `TimerStats` snapshot or `None` if no measurements recorded
        """
        with self._lock:
            if not self.times:
                return None
            return TimerStats(self.times, self.original_start_time, self._paused_durations)
    
    def get_stats(self) -> Optional[TimerStats]:
        """
        ────────────────────────────────────────────────────────
            ```python
            snapshot = timer.get_stats()  # same as get_statistics()
            ```
        ────────────────────────────────────────────────────────\n

        Alias for `get_statistics()`.
        
        Returns:
            `TimerStats` snapshot or `None` if no measurements recorded
        """
        return self.get_statistics()
    
    def reset(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            timer.reset()  # clears all measurements, like a new Sktimer()
            ```
        ────────────────────────────────────────────────────────\n

        Clear all timing measurements.
        
        Resets the timer to its initial state as if it was just created.
        """
        with self._lock:
            self.times.clear()
            self.original_start_time = None
            # reset sessions as well
            self._sessions.clear()
            self._paused_durations.clear()

    def set_max_times(self, max_times: Optional[int]) -> None:
        """
        Set the rolling window size for stored measurements.
        
        Args:
            max_times: Keep only the most recent N times. None keeps all.
        """
        if max_times is not None and max_times <= 0:
            raise ValueError("max_times must be a positive integer or None")
        
        with self._lock:
            self._max_times = max_times
            self._trim_to_max()

    def _trim_to_max(self) -> None:
        """Trim stored measurements to the rolling window size."""
        if self._max_times is None:
            return
        excess = len(self.times) - self._max_times
        if excess <= 0:
            return
        del self.times[:excess]
        del self._paused_durations[:excess]


class TimerSession:
    """Per-thread timing session supporting nested frames (stack)."""

    def __init__(self, manager: Sktimer):
        self._manager = manager
        self._frames: Deque[Dict[str, Any]] = deque()
        self._lock = threading.RLock()

    def _now(self) -> float:
        # use high-resolution monotonic clock for intervals
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
            raise RuntimeError("Sktimer is not running. Call start() first.")
        return self._frames[-1]

    def pause(self) -> None:
        with self._lock:
            frame = self._top()
            if frame['paused']:
                warnings.warn("Sktimer is already paused. Call resume() first.", UserWarning, stacklevel=2)
                return

            frame['paused'] = True
            frame['pause_started_at'] = self._now()

    def resume(self) -> None:
        with self._lock:
            frame = self._top()
            if not frame['paused']:
                warnings.warn("Sktimer is not paused. Call pause() first.", UserWarning, stacklevel=2)
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


def _timethis_decorator(timer: Sktimer, threshold: float = 0.0):
    """
    Create a timing decorator for an existing timer instance.
    
    Args:
        timer: Sktimer to accumulate statistics in
        threshold: Minimum elapsed time to record (default 0.0)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # avoid nested timing frames on the same timer
                if timer._has_active_frame():
                    start = perf_counter()
                    try:
                        result = await func(*args, **kwargs)
                    except BaseException:
                        # don't record partial timing on exception
                        raise
                    elapsed = perf_counter() - start
                    if elapsed >= threshold:
                        timer.add_time(elapsed)
                    return result
                else:
                    # concurrent session-aware: each thread call starts/stops its own session
                    timer.start()
                    try:
                        result = await func(*args, **kwargs)
                    except BaseException:
                        # don't record partial timing on exception;
                        # discard the frame so the timer doesn't leak a session
                        try:
                            timer.discard()
                        except Exception:
                            pass
                        raise
                    # success path: record timing
                    elapsed = timer.discard()
                    if elapsed >= threshold:
                        timer.add_time(elapsed)
                    return result
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # avoid nested timing frames on the same timer
                if timer._has_active_frame():
                    start = perf_counter()
                    try:
                        result = func(*args, **kwargs)
                    except BaseException:
                        # don't record partial timing on exception
                        raise
                    elapsed = perf_counter() - start
                    if elapsed >= threshold:
                        timer.add_time(elapsed)
                    return result
                else:
                    # concurrent session-aware: each thread call starts/stops its own session
                    timer.start()
                    try:
                        result = func(*args, **kwargs)
                    except BaseException:
                        # don't record partial timing on exception;
                        # discard the frame so the timer doesn't leak a session
                        try:
                            timer.discard()
                        except Exception:
                            pass
                        raise
                    # success path: record timing
                    elapsed = timer.discard()
                    if elapsed >= threshold:
                        timer.add_time(elapsed)
                    return result
        
        # if the wrapped function has @sk modifiers, redirect them to use
        # the timed wrapper so retry/timeout/background go through timing
        _sk_update = getattr(func, '_sk_update_source', None)
        if _sk_update is not None:
            _sk_update(wrapper)
        
        return wrapper
    return decorator

# convenience functions for direct access
def _get_current_time() -> float:
    """Get current Unix timestamp."""
    return time.time()


def _sleep(seconds: float) -> None:
    """Sleep for specified number of seconds."""
    time.sleep(seconds)
