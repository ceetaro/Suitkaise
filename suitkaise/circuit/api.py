"""
Circuit API - Circuit Breaker for Controlled Failure Handling

This module provides a circuit breaker pattern implementation for 
controlled failure handling and resource management in loops.
"""

import threading

# import sktime
from suitkaise.sktime import api as sktime


class Circuit:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import circuit
        
        # Create a circuit that trips after 5 shorts
        breaker = circuit.Circuit(num_shorts_to_trip=5, sleep_time_after_trip=0.5)
        
        while not breaker.broken:
            try:
                result = risky_operation()
            except SomeError:
                breaker.short()  # Count failure, trip if limit reached
        ```
    ────────────────────────────────────────────────────────\n

    Circuit breaker for controlled failure handling and resource management.
    
    Provides a clean way to handle failure thresholds and resource limits in loops,
    preventing runaway processes and providing graceful degradation.
    
    Args:
        num_shorts_to_trip: Maximum number of shorts before circuit trips
        sleep_time_after_trip: Default sleep duration (seconds) when circuit trips
        
    Attributes:
        broken: True if circuit has tripped
        times_shorted: Number of times circuit has been shorted since last trip
        total_failures: Lifetime count of all failures
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Retry loop with circuit breaker
        from suitkaise import circuit
        import requests
        
        api_circuit = circuit.Circuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)
        
        def fetch_with_retry(url):
            while not api_circuit.broken:
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException:
                    api_circuit.short()  # Trip after 3 failures
            
            return None  # Circuit tripped, give up
        ```
    ────────────────────────────────────────────────────────
    """

    def __init__(self, num_shorts_to_trip: int, sleep_time_after_trip: float = 0.0):
        """
        Initialize a circuit breaker.
        
        Args:
            num_shorts_to_trip: Maximum number of shorts before circuit trips
            sleep_time_after_trip: Default sleep duration (seconds) when circuit trips
        """
        self.num_shorts_to_trip = num_shorts_to_trip
        self.sleep_time_after_trip = sleep_time_after_trip
        self._broken = False
        self._times_shorted = 0
        self._total_failures = 0
        self._lock = threading.RLock()
    
    @property
    def broken(self) -> bool:
        """Whether the circuit has tripped."""
        with self._lock:
            return self._broken
    
    @property
    def times_shorted(self) -> int:
        """Number of times shorted since last trip."""
        with self._lock:
            return self._times_shorted
    
    @property
    def total_failures(self) -> int:
        """Lifetime count of all failures."""
        with self._lock:
            return self._total_failures

    def short(self, custom_sleep: float | None = None) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Count a failure
            breaker.short()
            
            # Count a failure with custom sleep duration
            breaker.short(custom_sleep=2.0)
            ```
        ────────────────────────────────────────────────────────\n

        Increment failure count and trip circuit if limit reached.
        
        Args:
            custom_sleep: Override default sleep_time_after_trip for this short.
                         If the short causes a trip, this sleep duration will be used.
        """
        should_trip = False
        sleep_duration = custom_sleep if custom_sleep is not None else self.sleep_time_after_trip
        
        with self._lock:
            self._times_shorted += 1
            self._total_failures += 1
            
            # Check if we've reached the short limit
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            self._break_circuit(sleep_duration)
    
    def trip(self, custom_sleep: float | None = None) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Immediately trip the circuit
            breaker.trip()
            
            # Trip with custom sleep duration
            breaker.trip(custom_sleep=5.0)
            ```
        ────────────────────────────────────────────────────────\n

        Immediately trip (break) the circuit, bypassing short counting.
        
        In circuit breaker terminology, when a breaker activates it "trips".
        This method provides immediate circuit breaking without counting shorts.
        
        Args:
            custom_sleep: Override default sleep_time_after_trip for this trip.
        """
        with self._lock:
            self._total_failures += 1
        self._break_circuit(custom_sleep if custom_sleep is not None else self.sleep_time_after_trip)
    
    def reset(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Reset the circuit to operational state
            breaker.reset()
            ```
        ────────────────────────────────────────────────────────\n

        Reset the circuit to operational state.
        
        Clears the broken flag and resets the short counter.
        """
        with self._lock:
            self._broken = False
            self._times_shorted = 0
    
    def _break_circuit(self, sleep_duration: float) -> None:
        """
        Internal method to break the circuit and update state.
        
        Args:
            sleep_duration: How long to sleep after breaking (seconds)
        """
        with self._lock:
            self._broken = True
            self._times_shorted = 0

        if sleep_duration > 0:
            sktime.sleep(sleep_duration)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'Circuit',
]
