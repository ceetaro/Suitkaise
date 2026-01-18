"""
Real-World Scenario: Async Patterns

This test simulates an application that needs to perform multiple I/O operations
concurrently - like a server handling multiple requests, or a client making
parallel API calls while respecting rate limits.

The scenario tests:
1. Using async sleep alongside circuit breakers (e.g., rate-limited API calls)
2. Running multiple operations concurrently to save time
3. Wrapping blocking code to work in async contexts
4. Combining all async features together
"""

import sys
import time as stdlib_time
import asyncio

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


class ScenarioRunner:
    """Runs real-world scenario tests with verbose output."""
    
    def __init__(self, scenario_name: str):
        self.scenario_name = scenario_name
        self.results = []
    
    def run_scenario(self, name: str, description: str, test_func):
        """Run a test scenario with description."""
        print(f"\n  {CYAN}Testing:{RESET} {name}")
        print(f"  {DIM}{description}{RESET}")
        
        try:
            test_func()
            self.results.append((name, True, None))
            print(f"  {GREEN}✓ Works as expected{RESET}")
        except AssertionError as e:
            self.results.append((name, False, str(e)))
            print(f"  {RED}✗ Failed: {e}{RESET}")
        except Exception as e:
            self.results.append((name, False, f"{type(e).__name__}: {e}"))
            print(f"  {RED}✗ Error: {type(e).__name__}: {e}{RESET}")
    
    def print_summary(self):
        """Print final summary."""
        passed = sum(1 for _, p, _ in self.results if p)
        failed = len(self.results) - passed
        
        print(f"\n  {BOLD}{'─'*70}{RESET}")
        if failed == 0:
            print(f"  {GREEN}{BOLD}✓ All {passed} scenarios passed!{RESET}")
        else:
            print(f"  {YELLOW}Passed: {passed}{RESET}  |  {RED}Failed: {failed}{RESET}")
        print(f"  {BOLD}{'─'*70}{RESET}")
        return failed == 0


# =============================================================================
# Scenario 1: Rate-Limited API Client
# =============================================================================

def test_timing_and_circuit_async():
    """
    Scenario: You're building an API client that needs to respect rate limits.
    When you hit the rate limit, you want to pause and retry automatically.
    """
    async def api_client():
        from suitkaise.timing import sleep
        from suitkaise.circuits import Circuit
        
        # Circuit trips after 2 "rate limit hits" and pauses for 20ms
        rate_limiter = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.02)
        
        # Simulate API call with delay
        await sleep.asynced()(0.01)
        
        # Simulate hitting rate limit twice
        await rate_limiter.short.asynced()()  # First warning
        await rate_limiter.short.asynced()()  # Trips and pauses
        
        assert rate_limiter.total_trips == 1, "Should have tripped once"
    
    asyncio.run(api_client())


# =============================================================================
# Scenario 2: Concurrent Request Handling
# =============================================================================

def test_concurrent_sleeps_and_circuits():
    """
    Scenario: Your server receives multiple requests. Each request needs
    to check rate limits. You want to process them all in parallel.
    """
    async def handle_requests():
        from suitkaise.timing import sleep
        from suitkaise.circuits import Circuit
        
        # Each "client" has its own rate limiter
        client_limiters = [
            Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.02) 
            for _ in range(3)
        ]
        
        start = stdlib_time.perf_counter()
        
        # Process all requests concurrently
        await asyncio.gather(
            sleep.asynced()(0.02),           # Some I/O wait
            client_limiters[0].short.asynced()(),  # Client 1 request
            client_limiters[1].short.asynced()(),  # Client 2 request
            client_limiters[2].short.asynced()(),  # Client 3 request
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # All ran concurrently - should take ~20ms, not 80ms
        assert elapsed < 0.05, f"Requests should run in parallel (~20ms), took {elapsed:.3f}s"
    
    asyncio.run(handle_requests())


# =============================================================================
# Scenario 3: Sktimer in a Service Class
# =============================================================================

def test_timer_with_skclass():
    """
    Scenario: You have a service that tracks its own performance.
    You want the Sktimer to work seamlessly with the Sk wrapper system.
    """
    from suitkaise.timing import Sktimer
    from suitkaise.sk import Skclass
    
    # The Sktimer class has _shared_meta, making it compatible
    # with Suitkaise's sharing and async systems
    timer = Sktimer()
    timer.start()
    stdlib_time.sleep(0.01)
    timer.stop()
    
    assert timer.num_times == 1, "Sktimer should record the measurement"
    assert timer.most_recent >= 0.008, "Should have timed ~10ms"


# =============================================================================
# Scenario 4: Making Blocking Code Async
# =============================================================================

def test_skfunction_with_timing():
    """
    Scenario: You have a legacy function that blocks. You need to call it
    from an async context without blocking the event loop.
    """
    async def async_context():
        from suitkaise.timing import sleep
        from suitkaise.sk import Skfunction
        import time as t
        
        # Your legacy blocking function
        def fetch_from_slow_database():
            t.sleep(0.02)  # Simulates blocking I/O
            return {"user": "alice", "score": 100}
        
        # Wrap it so it can run in async context
        async_fetch = Skfunction(fetch_from_slow_database).asynced()
        
        # Now it won't block the event loop!
        result = await async_fetch()
        
        assert result == {"user": "alice", "score": 100}
    
    asyncio.run(async_context())


# =============================================================================
# Scenario 5: Circuit Breaker for Service Health
# =============================================================================

def test_circuit_with_skclass():
    """
    Scenario: You're integrating a Circuit breaker into a service that uses
    the Sk wrapper system for sharing state between processes.
    """
    from suitkaise.circuits import Circuit
    
    # Circuit has _shared_meta, meaning it can be used with Share
    circuit = Circuit(num_shorts_to_trip=5)
    
    assert hasattr(Circuit, '_shared_meta'), "Circuit should have sharing metadata"
    assert 'methods' in Circuit._shared_meta, "Should list its methods"


# =============================================================================
# Scenario 6: Async Failure Handling
# =============================================================================

def test_breaking_circuit_with_skfunction():
    """
    Scenario: You have an async service that should stop accepting requests
    after too many failures, requiring manual reset.
    """
    async def failure_handling():
        from suitkaise.circuits import BreakingCircuit
        
        # After 2 failures, the circuit breaks and stays broken
        failure_circuit = BreakingCircuit(num_shorts_to_trip=2, sleep_time_after_trip=0.01)
        
        # First failure
        await failure_circuit.short.asynced()()
        assert not failure_circuit.broken, "Not broken yet after 1 failure"
        
        # Second failure - breaks!
        await failure_circuit.short.asynced()()
        assert failure_circuit.broken, "Should be broken after 2 failures"
        
        # Manual reset required
        failure_circuit.reset()
        assert not failure_circuit.broken, "Should be operational after reset"
    
    asyncio.run(failure_handling())


# =============================================================================
# Scenario 7: Complete Async Application
# =============================================================================

def test_all_async_together():
    """
    Scenario: A real application combining all async patterns - concurrent
    operations, rate limiting, and legacy code integration.
    """
    async def full_application():
        from suitkaise.timing import sleep, Sktimer
        from suitkaise.circuits import Circuit
        from suitkaise.sk import Skfunction
        import time as t
        
        # Legacy blocking function (e.g., database call)
        def query_database():
            t.sleep(0.01)
            return {"data": [1, 2, 3]}
        
        async_query = Skfunction(query_database).asynced()
        rate_limiter = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.01)
        
        start = stdlib_time.perf_counter()
        
        # Run everything concurrently:
        # - Wait for some external event (sleep)
        # - Check rate limit (circuit)
        # - Query database (blocking -> async)
        results = await asyncio.gather(
            sleep.asynced()(0.01),      # External wait
            rate_limiter.short.asynced()(),  # Rate limit check
            async_query(),                    # Database query
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # All operations ran concurrently
        assert elapsed < 0.03, f"Operations should be concurrent, took {elapsed:.3f}s"
        assert results[2] == {"data": [1, 2, 3]}, "Database query should succeed"
    
    asyncio.run(full_application())


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all async pattern scenario tests."""
    runner = ScenarioRunner("Async Patterns")
    
    print(f"\n  {DIM}This scenario tests an application that performs multiple")
    print(f"  I/O operations concurrently while respecting rate limits.{RESET}")
    
    runner.run_scenario(
        "Rate-Limited API Client",
        "API client that pauses when hitting rate limits",
        test_timing_and_circuit_async
    )
    
    runner.run_scenario(
        "Concurrent Request Handling",
        "Processing multiple requests in parallel to save time",
        test_concurrent_sleeps_and_circuits
    )
    
    runner.run_scenario(
        "Sktimer in Service Class",
        "Performance tracking Sktimer with Sk compatibility",
        test_timer_with_skclass
    )
    
    runner.run_scenario(
        "Making Blocking Code Async",
        "Wrapping legacy blocking functions for async contexts",
        test_skfunction_with_timing
    )
    
    runner.run_scenario(
        "Circuit Breaker Metadata",
        "Circuit breaker compatible with process sharing",
        test_circuit_with_skclass
    )
    
    runner.run_scenario(
        "Async Failure Handling",
        "Breaking circuit that stops after failures, needs manual reset",
        test_breaking_circuit_with_skfunction
    )
    
    runner.run_scenario(
        "Complete Async Application",
        "All async patterns working together in a real app",
        test_all_async_together
    )
    
    return runner.print_summary()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
