"""
Circuit API - Circuit Breaker for Controlled Failure Handling

This module provides a circuit breaker pattern implementation for 
controlled failure handling and resource management in loops.
"""

# import sktime
from suitkaise.sktime import api as sktime


class Circuit:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import circuit
        
        # Create a circuit that breaks after 5 shorts
        breaker = circuit.Circuit(shorts=5, break_sleep=0.5)
        
        while breaker.flowing:
            try:
                result = risky_operation()
            except SomeError:
                breaker.short()  # Count failure, break if limit reached
        ```
    ────────────────────────────────────────────────────────\n

    Circuit breaker for controlled failure handling and resource management.
    
    Provides a clean way to handle failure thresholds and resource limits in loops,
    preventing runaway processes and providing graceful degradation.
    
    Args:
        shorts: Maximum number of shorts before circuit breaks
        break_sleep: Default sleep duration (seconds) when circuit breaks
        
    Attributes:
        flowing: True if circuit is operational (not broken)
        broken: True if circuit has exceeded limits
        times_shorted: Number of times circuit has been shorted
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Retry loop with circuit breaker
        from suitkaise import circuit
        import requests
        
        api_circuit = circuit.Circuit(shorts=3, break_sleep=1.0)
        
        def fetch_with_retry(url):
            while api_circuit.flowing:
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    return response.json()
                except requests.RequestException:
                    api_circuit.short()  # Break after 3 failures
            
            return None  # Circuit broken, give up
        ```
    ────────────────────────────────────────────────────────
    """

    def __init__(self, shorts: int, break_sleep: float = 0.1):
        """
        Initialize a circuit breaker.
        
        Args:
            shorts: Maximum number of shorts before circuit breaks
            break_sleep: Default sleep duration (seconds) when circuit breaks
        """
        self.shorts = shorts
        self.break_sleep = break_sleep
        self.flowing = True
        self.broken = False
        self.times_shorted = 0

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

        Increment failure count and break circuit if limit reached.
        
        Args:
            custom_sleep: Override default break_sleep duration for this short.
                         If the short causes a break, this sleep duration will be used.
        """
        self.times_shorted += 1
        
        # Check if we've reached the short limit
        if self.times_shorted >= self.shorts:
            # Break the circuit and use custom_sleep if provided
            self._break_circuit(custom_sleep if custom_sleep is not None else self.break_sleep)
    
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
            custom_sleep: Override default break_sleep duration for this trip.
        """
        self._break_circuit(custom_sleep if custom_sleep is not None else self.break_sleep)
    
    def reset(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Reset the circuit to operational state
            breaker.reset()
            ```
        ────────────────────────────────────────────────────────\n

        Reset the circuit to operational state.
        
        Clears the broken flag, restores flowing, and resets the short counter.
        """
        self.flowing = True
        self.broken = False
        self.times_shorted = 0
    
    def _break_circuit(self, sleep_duration: float) -> None:
        """
        Internal method to break the circuit and update state.
        
        Args:
            sleep_duration: How long to sleep after breaking (seconds)
        """
        self.flowing = False
        self.broken = True
        self.times_shorted = 0
        
        if sleep_duration > 0:
            sktime.sleep(sleep_duration)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'Circuit',
]
