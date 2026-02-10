"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise import Circuit, BreakingCircuit
    ```
────────────────────────────────────────────────────────\n

API for the circuits module.

Includes two circuits (Circuit and BreakingCircuit) that can be used to
control failure and manage resources in loops.

Circuit is auto-resetting, BreakingCircuit needs the user to manually reset it.

Includes exponential backoff, with max sleep time and jitter options. 

Additionally, supports native async usage with `.asynced()` methods.
"""

import asyncio
import random
import threading

# import timing
from suitkaise.timing import api as timing
from suitkaise.sk._int.asyncable import _AsyncableMethod


class Circuit:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import Circuit
        
        circ = Circuit(
            num_shorts_to_trip=5, 
            sleep_time_after_trip=0.5,
            backoff_factor=1.5,
            max_sleep_time=10.0
            jitter=0.2
        )
        
        while doing_this:
            if something_went_wrong():
                circ.short()  # after 5 shorts, sleeps and auto-resets
            else:
                do_work()
        ```
    ────────────────────────────────────────────────────────\n

    Auto-resetting circuit for rate limiting and progressive backoff.
    
    Unlike BreakingCircuit (which breaks and stops), Circuit sleeps and continues.
    The counter auto-resets after each sleep, and exponential backoff is applied.
    
    Args:
        num_shorts_to_trip: Number of shorts before circuit trips and sleeps
        sleep_time_after_trip: Base sleep duration (seconds) when circuit trips
        backoff_factor: Exponential backoff multiplier (default 1 = no backoff)
        max_sleep_time: Maximum sleep duration cap (default 10.0)
        jitter: Random +/- percent of sleep_time to prevent thundering herd
            - expects a decimal (0.2), NOT a percentage (20)
        
    Attributes:
        times_shorted: Number of shorts since last trip
        total_trips: Lifetime count of all trips
        current_sleep_time: Current sleep duration (after backoff applied)
    
    _shared_meta:
        metadata for `Share` - declares which attributes each method/property
        reads from or writes to. Used by `Share` instances for synchronization.
    
    ────────────────────────────────────────────────────────
        ```python
        # rate limit w/ exponential backoff and jitter
        from suitkaise import Circuit
        
        rate_limiter = Circuit(
            num_shorts_to_trip=10,
            sleep_time_after_trip=1.0,
            backoff_factor=1.5,
            max_sleep_time=30.0,
            jitter=0.1
        )
        
        for request in requests:
            if is_rate_limited():
                rate_limiter.short()
            else:
                process(request)
        ```
    ────────────────────────────────────────────────────────
    """
    
    _share_disallowed = (
        "Circuit cannot be used in Share. Circuit auto-resets and sleeps "
        "on trip — both behaviors break when replayed in the coordinator "
        "process. Use BreakingCircuit in Share instead (sleep is automatically "
        "disabled, state changes work normally)."
    )

    _shared_meta = {
        'methods': {
            'short': {'writes': ['_times_shorted', '_total_trips', '_current_sleep_time']},
            'trip': {'writes': ['_times_shorted', '_total_trips', '_current_sleep_time']},
            'reset_backoff': {'writes': ['_current_sleep_time']},
        },
        'properties': {
            'times_shorted': {'reads': ['_times_shorted']},
            'total_trips': {'reads': ['_total_trips']},
            'current_sleep_time': {'reads': ['_current_sleep_time']},
        }
    }

    def __init__(
        self, 
        num_shorts_to_trip: int,
        *,
        sleep_time_after_trip: float = 0.0,
        backoff_factor: float = 1.0,
        max_sleep_time: float = 10.0,
        jitter: float = 0.0
    ):

        if not num_shorts_to_trip:
            raise ValueError("num_shorts_to_trip is required")

        self._num_shorts_to_trip = num_shorts_to_trip
        self.sleep_time_after_trip = sleep_time_after_trip
        self.backoff_factor = backoff_factor
        self.max_sleep_time = max_sleep_time
        self.jitter = max(0.0, min(1.0, jitter))
        
        self._times_shorted = 0
        self._total_trips = 0
        self._current_sleep_time = sleep_time_after_trip
        self._lock = threading.RLock()
    
    @property
    def num_shorts_to_trip(self) -> int:
        """Number of shorts before trip."""
        with self._lock:
            return self._num_shorts_to_trip

    @property
    def times_shorted(self) -> int:
        """Number of times shorted since last trip."""
        with self._lock:
            return self._times_shorted
    
    @property
    def total_trips(self) -> int:
        """Lifetime count of all trips."""
        with self._lock:
            return self._total_trips
    
    @property
    def current_sleep_time(self) -> float:
        """Current sleep duration (after backoff applied)."""
        with self._lock:
            return self._current_sleep_time



    # async internal methods
    
    async def _async_trip_circuit(self, custom_sleep: float | None = None) -> bool:
        """Async version of _trip_circuit using asyncio.sleep."""
        with self._lock:
            sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
            self._total_trips += 1
            self._times_shorted = 0
            
            if self.backoff_factor != 1.0:
                self._current_sleep_time = min(
                    self._current_sleep_time * self.backoff_factor,
                    self.max_sleep_time
                )
        
        sleep_duration = self._apply_jitter(sleep_duration)
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)
        
        return True
    
    async def _async_short(self, custom_sleep: float | None = None) -> bool:
        """Async version of short()."""
        should_trip = False
        
        with self._lock:
            self._times_shorted += 1
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            return await self._async_trip_circuit(custom_sleep)
        
        return False
    
    async def _async_trip(self, custom_sleep: float | None = None) -> bool:
        """Async version of trip()."""
        return await self._async_trip_circuit(custom_sleep)
    


    # sync methods with .asynced() support

    def _sync_short(self, custom_sleep: float | None = None) -> bool:
        """Sync implementation of short()."""
        should_trip = False
        
        with self._lock:
            self._times_shorted += 1
            
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            return self._trip_circuit(custom_sleep)
        
        return False
    
    short = _AsyncableMethod(_sync_short, _async_short)
    """
    ────────────────────────────────────────────────────────
        ```python
        circ.short()  # count a failure
        
        # returns True if sleep occurred
        if circ.short():
            print("Circuit tripped and slept")
        
        # async version
        await circ.short.asynced()()
        ```
    ────────────────────────────────────────────────────────\n

    Increment failure count and trip circuit if limit reached.
    
    When tripped, sleeps for current_sleep_time, applies backoff factor,
    and auto-resets the counter.
    
    Supports `.asynced()` for async usage with `asyncio.sleep`.
    
    Args:
        custom_sleep: Override sleep duration for this short only
    
    Returns:
        True if sleep occurred, False otherwise
    """
    
    def _sync_trip(self, custom_sleep: float | None = None) -> bool:
        """Sync implementation of trip()."""
        return self._trip_circuit(custom_sleep)
    
    trip = _AsyncableMethod(_sync_trip, _async_trip)
    """
    ────────────────────────────────────────────────────────
        ```python
        circ.trip()  # immediately trip the circuit
        
        # async version
        await circ.trip.asynced()()
        ```
    ────────────────────────────────────────────────────────\n

    Immediately trip the circuit, bypassing the short counter.
    
    Supports `.asynced()` for async usage with `asyncio.sleep`.
    
    Args:
        custom_sleep: Override sleep duration for this trip
        
    Returns:
        True (always sleeps)
    """
    
    def _trip_circuit(self, custom_sleep: float | None = None) -> bool:
        """
        Internal method to trip the circuit.
        
        Sleeps, applies backoff, and auto-resets counter.
        """
        with self._lock:
            sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
            self._total_trips += 1
            self._times_shorted = 0  # auto-reset counter
            
            # apply exponential backoff for next trip
            if self.backoff_factor != 1.0:
                self._current_sleep_time = min(
                    self._current_sleep_time * self.backoff_factor,
                    self.max_sleep_time
                )
        
        sleep_duration = self._apply_jitter(sleep_duration)
        if sleep_duration > 0:
            timing.sleep(sleep_duration)
        
        return True

    def _apply_jitter(self, sleep_duration: float) -> float:
        """Apply randomized jitter to sleep duration."""
        if sleep_duration <= 0:
            return sleep_duration
        jitter_fraction = abs(self.jitter)
        if jitter_fraction <= 0:
            return sleep_duration
        delta = sleep_duration * jitter_fraction
        return max(0.0, sleep_duration + random.uniform(-delta, delta))
    
    def reset_backoff(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            circ.reset_backoff()  # reset sleep time to original
            ```
        ────────────────────────────────────────────────────────\n

        Reset the backoff sleep time to the original value.
        """
        with self._lock:
            self._current_sleep_time = self.sleep_time_after_trip


class BreakingCircuit:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import BreakingCircuit
        
        circ = BreakingCircuit(
            num_shorts_to_trip=5, 
            sleep_time_after_trip=0.5,
            backoff_factor=1.1,
            max_sleep_time=10.0
            jitter=0.2
        )
        
        while not circ.broken:
            try:
                result = something_that_might_fail()
            except SomeError:
                circ.short()  # trip after 5 failures
        
        if circ.broken:
            print("Circuit broken, resetting")
            circ.reset()  # manual reset, applies backoff
        ```
    ────────────────────────────────────────────────────────\n

    Breaking circuit that allows you to control failure handling.
    
    Unlike Circuit (which auto-resets), BreakingCircuit stays broken until
    manually reset. 
    
    Use this for things like stopping processing after a threshold is reached.
    
    Args:
        num_shorts_to_trip: Maximum number of shorts before circuit trips
        sleep_time_after_trip: Base sleep duration (seconds) when circuit trips
        backoff_factor: Exponential backoff multiplier applied on reset (default 1)
        max_sleep_time: Maximum sleep duration cap (default 10.0)
        jitter: Random +/- percent of sleep_time to prevent thundering herd
            - expects a decimal (0.2), NOT a percentage (20)
        
    Attributes:
        broken: True if circuit has tripped
        times_shorted: Number of shorts since last trip/reset
        total_trips: Lifetime count of all trips
        current_sleep_time: Current sleep duration (after backoff applied)
    
    _shared_meta:
        metadata for `Share` - declares which attributes each method/property
        reads from or writes to. Used by `Share` instances for synchronization.
    
    ────────────────────────────────────────────────────────
        ```python
        # retry loop with circuit breaker
        from suitkaise import BreakingCircuit
        import requests
        
        api_circ = BreakingCircuit(
            num_shorts_to_trip=3, 
            sleep_time_after_trip=1.0,
            backoff_factor=2.0,
            max_sleep_time=30.0
            jitter=0.1
        )
        
        def fetch_with_retry(url):
            while not api_circuit.broken:
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException:
                    api_circuit.short()  # trip after 3 failures
            
            return None  # circuit broken, give up
        ```
    ────────────────────────────────────────────────────────
    """
    
    _shared_meta = {
        'methods': {
            'short': {'writes': ['_times_shorted', '_total_trips', '_broken']},
            'trip': {'writes': ['_total_trips', '_broken', '_times_shorted']},
            'reset': {'writes': ['_broken', '_times_shorted', '_current_sleep_time']},
            'reset_backoff': {'writes': ['_current_sleep_time']},
        },
        'properties': {
            'broken': {'reads': ['_broken']},
            'times_shorted': {'reads': ['_times_shorted']},
            'total_trips': {'reads': ['_total_trips']},
            'current_sleep_time': {'reads': ['_current_sleep_time']},
        }
    }

    # When used through Share, short() and trip() are aliased to no-sleep
    # versions. The sleep would execute in the coordinator process (useless),
    # and block it from processing other commands. State changes still apply.
    _share_method_aliases = {
        'short': '_nosleep_short',
        'trip': '_nosleep_trip',
    }

    def __init__(
        self, 
        num_shorts_to_trip: int,
        *,
        sleep_time_after_trip: float = 0.0,
        backoff_factor: float = 1.0,
        max_sleep_time: float = 10.0,
        jitter: float = 0.0
    ):   

        if not num_shorts_to_trip:
            raise ValueError("num_shorts_to_trip is required")

        self._num_shorts_to_trip = num_shorts_to_trip
        self.sleep_time_after_trip = sleep_time_after_trip
        self.backoff_factor = backoff_factor
        self.max_sleep_time = max_sleep_time
        self.jitter = max(0.0, min(1.0, jitter))
        
        self._broken = False
        self._times_shorted = 0
        self._total_trips = 0
        self._current_sleep_time = sleep_time_after_trip
        self._lock = threading.RLock()
    
    @property
    def num_shorts_to_trip(self) -> int:
        """Maximum number of shorts before break."""
        with self._lock:
            return self._num_shorts_to_trip

    @property
    def broken(self) -> bool:
        """Whether the circuit has tripped."""
        with self._lock:
            return self._broken
    
    @property
    def times_shorted(self) -> int:
        """Number of times shorted since last trip/reset."""
        with self._lock:
            return self._times_shorted
    
    @property
    def total_trips(self) -> int:
        """Lifetime count of all trips."""
        with self._lock:
            return self._total_trips
    
    @property
    def current_sleep_time(self) -> float:
        """Current sleep duration (after backoff applied)."""
        with self._lock:
            return self._current_sleep_time



    # async internal methods
    

    async def _async_break_circuit(self, sleep_duration: float) -> None:
        """Async version of _break_circuit using asyncio.sleep."""
        with self._lock:
            self._broken = True
            self._times_shorted = 0

        sleep_duration = self._apply_jitter(sleep_duration)
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)
    
    async def _async_short(self, custom_sleep: float | None = None) -> None:
        """Async version of short()."""
        should_trip = False
        sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
        
        with self._lock:
            self._times_shorted += 1
            self._total_trips += 1
            
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            await self._async_break_circuit(sleep_duration)
    
    async def _async_trip(self, custom_sleep: float | None = None) -> None:
        """Async version of trip()."""
        with self._lock:
            self._total_trips += 1
        await self._async_break_circuit(
            custom_sleep if custom_sleep is not None else self._current_sleep_time
        )
    


    # sync methods with .asynced() support

    def _sync_short(self, custom_sleep: float | None = None) -> None:
        """Sync implementation of short()."""
        should_trip = False
        sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
        
        with self._lock:
            self._times_shorted += 1
            self._total_trips += 1
            
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            self._break_circuit(sleep_duration)
    
    short = _AsyncableMethod(_sync_short, _async_short)
    """
    ────────────────────────────────────────────────────────
        ```python
        breaker.short()  # count a failure
        
        breaker.short(custom_sleep=2.0)  # custom sleep if trips
        
        # async version
        await breaker.short.asynced()()
        ```
    ────────────────────────────────────────────────────────\n

    Increment failure count and trip circuit if limit reached.
    
    Supports `.asynced()` for async usage with `asyncio.sleep`.
    
    Args:
        custom_sleep: Override sleep_time_after_trip for this short
    """
    
    def _sync_trip(self, custom_sleep: float | None = None) -> None:
        """Sync implementation of trip()."""
        with self._lock:
            self._total_trips += 1
        self._break_circuit(custom_sleep if custom_sleep is not None else self._current_sleep_time)
    
    trip = _AsyncableMethod(_sync_trip, _async_trip)
    """
    ────────────────────────────────────────────────────────
        ```python
        breaker.trip()  # immediately trip the circuit
        
        breaker.trip(custom_sleep=5.0)  # trip with custom sleep
        
        # async version
        await breaker.trip.asynced()()
        ```
    ────────────────────────────────────────────────────────\n

    Immediately trip (break) the circuit, bypassing short counting.
    
    Supports `.asynced()` for async usage with `asyncio.sleep`.
    
    Args:
        custom_sleep: Override sleep_time_after_trip for this trip
    """
    
    def reset(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            breaker.reset()  # reset to operational, apply backoff
            ```
        ────────────────────────────────────────────────────────\n

        Reset the circuit to operational state.
        
        Clears the `broken` flag, resets the short counter,
        and applies exponential backoff factor to sleep time.
        """
        with self._lock:
            self._broken = False
            self._times_shorted = 0
            
            # apply exponential backoff on reset
            if self.backoff_factor != 1.0:
                self._current_sleep_time = min(
                    self._current_sleep_time * self.backoff_factor,
                    self.max_sleep_time
                )
    
    def reset_backoff(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            breaker.reset_backoff()  # reset sleep time to original
            ```
        ────────────────────────────────────────────────────────\n

        Reset the backoff sleep time to the original value.
        
        Does NOT reset the broken state - use reset() for that.
        """
        with self._lock:
            self._current_sleep_time = self.sleep_time_after_trip
    
    def _break_circuit(self, sleep_duration: float) -> None:
        """
        Internal method to break the circuit and update state.
        """
        with self._lock:
            self._broken = True
            self._times_shorted = 0

        sleep_duration = self._apply_jitter(sleep_duration)
        if sleep_duration > 0:
            timing.sleep(sleep_duration)

    # ── Share-safe methods (no sleep) ────────────────────────────────────
    # These are called by the coordinator via _share_method_aliases when
    # short() or trip() are invoked through a Share proxy.

    def _nosleep_short(self, custom_sleep: float | None = None) -> None:
        """State-only short: increment counters and break if threshold reached."""
        with self._lock:
            self._times_shorted += 1
            self._total_trips += 1
            if self._times_shorted >= self._num_shorts_to_trip:
                self._broken = True
                self._times_shorted = 0

    def _nosleep_trip(self, custom_sleep: float | None = None) -> None:
        """State-only trip: immediately break the circuit."""
        with self._lock:
            self._total_trips += 1
            self._broken = True
            self._times_shorted = 0

    def _apply_jitter(self, sleep_duration: float) -> float:
        """Apply randomized jitter to sleep duration."""
        if sleep_duration <= 0:
            return sleep_duration
        jitter_fraction = abs(self.jitter)
        if jitter_fraction <= 0:
            return sleep_duration
        delta = sleep_duration * jitter_fraction
        return max(0.0, sleep_duration + random.uniform(-delta, delta))


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'Circuit',
    'BreakingCircuit',
]
