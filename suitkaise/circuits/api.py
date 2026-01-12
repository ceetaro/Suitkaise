"""
circuits API

This module provides circuit breaker pattern implementations for 
controlled failure handling and resource management in loops.

Two circuit types:
- Circuit: Auto-resets after sleeping (for rate limiting, backoff)
- BreakingCircuit: Stays broken until manually reset (for failure limits)
"""

import threading

# import timing
from suitkaise.timing import api as timing


class Circuit:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import Circuit
        
        circ = Circuit(
            num_shorts_to_trip=5, 
            sleep_time_after_trip=0.5,
            factor=1.5,  # exponential backoff
            max_sleep_time=10.0
        )
        
        while something:
            if something_went_wrong():
                circ.short()  # After 5 shorts, sleeps and auto-resets
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
        factor: Exponential backoff multiplier (default 1 = no backoff)
        max_sleep_time: Maximum sleep duration cap (default 10.0)
        
    Attributes:
        times_shorted: Number of shorts since last trip
        total_trips: Lifetime count of all trips
        current_sleep_time: Current sleep duration (after backoff applied)
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Rate limiting with exponential backoff
        from suitkaise import Circuit
        
        rate_limiter = Circuit(
            num_shorts_to_trip=10,
            sleep_time_after_trip=1.0,
            factor=1.5,
            max_sleep_time=30.0
        )
        
        for request in requests:
            if is_rate_limited():
                rate_limiter.short()  # Sleeps with increasing delay
            else:
                process(request)
        ```
    ────────────────────────────────────────────────────────
    """

    def __init__(
        self, 
        num_shorts_to_trip: int, 
        sleep_time_after_trip: float = 0.0,
        factor: float = 1.0,
        max_sleep_time: float = 10.0
    ):
        self.num_shorts_to_trip = num_shorts_to_trip
        self.sleep_time_after_trip = sleep_time_after_trip
        self.factor = factor
        self.max_sleep_time = max_sleep_time
        
        self._times_shorted = 0
        self._total_trips = 0
        self._current_sleep_time = sleep_time_after_trip
        self._lock = threading.RLock()
    
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

    def short(self, custom_sleep: float | None = None) -> bool:
        """
        ────────────────────────────────────────────────────────
            ```python
            circ.short()  # Count a failure
            
            # Returns True if sleep occurred
            if circ.short():
                print("Circuit tripped and slept")
            ```
        ────────────────────────────────────────────────────────\n

        Increment failure count and trip circuit if limit reached.
        
        When tripped, sleeps for current_sleep_time, applies backoff factor,
        and auto-resets the counter.
        
        Args:
            custom_sleep: Override sleep duration for this short only
        
        Returns:
            True if sleep occurred, False otherwise
        """
        should_trip = False
        
        with self._lock:
            self._times_shorted += 1
            
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            return self._trip_circuit(custom_sleep)
        
        return False
    
    def trip(self, custom_sleep: float | None = None) -> bool:
        """
        ────────────────────────────────────────────────────────
            ```python
            circ.trip()  # Immediately trip the circuit
            ```
        ────────────────────────────────────────────────────────\n

        Immediately trip the circuit, bypassing short counting.
        
        Args:
            custom_sleep: Override sleep duration for this trip
            
        Returns:
            True (always sleeps)
        """
        return self._trip_circuit(custom_sleep)
    
    def _trip_circuit(self, custom_sleep: float | None = None) -> bool:
        """
        Internal method to trip the circuit.
        
        Sleeps, applies backoff, and auto-resets counter.
        """
        with self._lock:
            sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
            self._total_trips += 1
            self._times_shorted = 0  # Auto-reset counter
            
            # Apply exponential backoff for next trip
            if self.factor != 1.0:
                self._current_sleep_time = min(
                    self._current_sleep_time * self.factor,
                    self.max_sleep_time
                )
        
        if sleep_duration > 0:
            timing.sleep(sleep_duration)
        
        return True
    
    def reset_backoff(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            circ.reset_backoff()  # Reset sleep time to original
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
            factor=1.1,
            max_sleep_time=10.0
        )
        
        while not circ.broken:
            try:
                result = risky_operation()
            except SomeError:
                circ.short()  # Trip after 5 failures
        
        if circ.broken:
            print("Circuit broken, resetting")
            circ.reset()  # Manual reset, applies backoff
        ```
    ────────────────────────────────────────────────────────\n

    Breaking circuit for controlled failure handling.
    
    Unlike Circuit (which auto-resets), BreakingCircuit stays broken until
    manually reset. Use this for failure limits where you want to stop
    processing after a threshold is reached.
    
    Args:
        num_shorts_to_trip: Maximum number of shorts before circuit trips
        sleep_time_after_trip: Base sleep duration (seconds) when circuit trips
        factor: Exponential backoff multiplier applied on reset (default 1)
        max_sleep_time: Maximum sleep duration cap (default 10.0)
        
    Attributes:
        broken: True if circuit has tripped
        times_shorted: Number of shorts since last trip/reset
        total_failures: Lifetime count of all failures
        current_sleep_time: Current sleep duration (after backoff applied)
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Retry loop with circuit breaker
        from suitkaise import BreakingCircuit
        import requests
        
        api_circuit = BreakingCircuit(
            num_shorts_to_trip=3, 
            sleep_time_after_trip=1.0,
            factor=2.0,
            max_sleep_time=30.0
        )
        
        def fetch_with_retry(url):
            while not api_circuit.broken:
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException:
                    api_circuit.short()  # Trip after 3 failures
            
            return None  # Circuit broken, give up
        ```
    ────────────────────────────────────────────────────────
    """

    def __init__(
        self, 
        num_shorts_to_trip: int, 
        sleep_time_after_trip: float = 0.0,
        factor: float = 1.0,
        max_sleep_time: float = 10.0
    ):
        self.num_shorts_to_trip = num_shorts_to_trip
        self.sleep_time_after_trip = sleep_time_after_trip
        self.factor = factor
        self.max_sleep_time = max_sleep_time
        
        self._broken = False
        self._times_shorted = 0
        self._total_failures = 0
        self._current_sleep_time = sleep_time_after_trip
        self._lock = threading.RLock()
    
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
    def total_failures(self) -> int:
        """Lifetime count of all failures."""
        with self._lock:
            return self._total_failures
    
    @property
    def current_sleep_time(self) -> float:
        """Current sleep duration (after backoff applied)."""
        with self._lock:
            return self._current_sleep_time

    def short(self, custom_sleep: float | None = None) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            breaker.short()  # Count a failure
            
            breaker.short(custom_sleep=2.0)  # Custom sleep if trips
            ```
        ────────────────────────────────────────────────────────\n

        Increment failure count and trip circuit if limit reached.
        
        Args:
            custom_sleep: Override sleep_time_after_trip for this short
        """
        should_trip = False
        sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
        
        with self._lock:
            self._times_shorted += 1
            self._total_failures += 1
            
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            self._break_circuit(sleep_duration)
    
    def trip(self, custom_sleep: float | None = None) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            breaker.trip()  # Immediately trip the circuit
            
            breaker.trip(custom_sleep=5.0)  # Trip with custom sleep
            ```
        ────────────────────────────────────────────────────────\n

        Immediately trip (break) the circuit, bypassing short counting.
        
        Args:
            custom_sleep: Override sleep_time_after_trip for this trip
        """
        with self._lock:
            self._total_failures += 1
        self._break_circuit(custom_sleep if custom_sleep is not None else self._current_sleep_time)
    
    def reset(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            breaker.reset()  # Reset to operational, apply backoff
            ```
        ────────────────────────────────────────────────────────\n

        Reset the circuit to operational state.
        
        Clears the broken flag, resets the short counter,
        and applies exponential backoff factor to sleep time.
        """
        with self._lock:
            self._broken = False
            self._times_shorted = 0
            
            # Apply exponential backoff on reset
            if self.factor != 1.0:
                self._current_sleep_time = min(
                    self._current_sleep_time * self.factor,
                    self.max_sleep_time
                )
    
    def reset_backoff(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            breaker.reset_backoff()  # Reset sleep time to original
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

        if sleep_duration > 0:
            timing.sleep(sleep_duration)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'Circuit',
    'BreakingCircuit',
]
