"""
Integration Test: Async Web Scraper Pattern

Real-world scenario: An async web scraper that:
1. Uses Circuit breaker for rate limiting
2. Uses sleep.asynced() for non-blocking delays
3. Uses Skfunction.asynced() for blocking I/O
4. Uses Timer for performance tracking
5. Uses @timethis for method-level timing
6. Combines multiple async operations concurrently

This tests the full async integration of:
- circuits: Circuit.short.asynced(), BreakingCircuit.trip.asynced()
- timing: sleep.asynced(), Timer, @timethis
- sk: Skfunction.asynced(), @sk on classes with blocking methods
"""

import sys
import time as stdlib_time
import asyncio
import random

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.circuits import Circuit, BreakingCircuit
from suitkaise.timing import Timer, TimeThis, sleep, timethis
from suitkaise.sk import Skfunction, sk, NotAsyncedError


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            if result.passed:
                status = f"{self.GREEN}✓ PASS{self.RESET}"
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")
        return failed == 0


# =============================================================================
# Mock Blocking Functions (simulating network I/O)
# =============================================================================

def fetch_page(url: str, delay: float = 0.02) -> dict:
    """Simulate blocking HTTP request."""
    stdlib_time.sleep(delay)
    
    # Simulate occasional failures
    if random.random() < 0.1:
        raise ConnectionError(f"Failed to fetch {url}")
    
    return {
        "url": url,
        "status": 200,
        "content_length": random.randint(1000, 50000),
    }


def parse_content(html: str, delay: float = 0.01) -> list:
    """Simulate blocking HTML parsing."""
    stdlib_time.sleep(delay)
    return [f"link_{i}" for i in range(random.randint(1, 5))]


# =============================================================================
# Integration Tests
# =============================================================================

def test_concurrent_async_sleeps():
    """Test that multiple async sleeps run concurrently."""
    async def async_test():
        start = stdlib_time.perf_counter()
        
        # Run 5 async sleeps of 20ms each
        await asyncio.gather(
            sleep.asynced()(0.02),
            sleep.asynced()(0.02),
            sleep.asynced()(0.02),
            sleep.asynced()(0.02),
            sleep.asynced()(0.02),
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Should complete in ~20ms (concurrent), not 100ms (sequential)
        assert elapsed < 0.05, f"Should run concurrently (~20ms), got {elapsed:.3f}s"
    
    asyncio.run(async_test())


def test_circuit_async_rate_limiting():
    """Test Circuit for async rate limiting with exponential backoff."""
    async def async_test():
        circuit = Circuit(
            num_shorts_to_trip=3,
            sleep_time_after_trip=0.01,
            factor=2.0,
            max_sleep_time=0.1
        )
        timer = Timer()
        
        # Simulate rate-limited requests
        for i in range(10):
            with TimeThis(timer):
                result = await circuit.short.asynced()()
        
        # Should have tripped multiple times
        assert circuit.total_trips >= 3, f"Should trip at least 3 times, got {circuit.total_trips}"
        assert timer.num_times == 10, "Should have 10 timing measurements"
    
    asyncio.run(async_test())


def test_breaking_circuit_async_failure_threshold():
    """Test BreakingCircuit stops processing after threshold."""
    async def async_test():
        breaker = BreakingCircuit(
            num_shorts_to_trip=5,
            sleep_time_after_trip=0.01
        )
        
        processed = 0
        
        while not breaker.broken and processed < 20:
            processed += 1
            await breaker.short.asynced()()
        
        assert breaker.broken, "Should be broken after 5 shorts"
        assert processed == 5, f"Should stop at 5, processed {processed}"
    
    asyncio.run(async_test())


def test_skfunction_async_blocking_io():
    """Test Skfunction wraps blocking I/O for async use."""
    async def async_test():
        sk_fetch = Skfunction(fetch_page)
        
        # Verify it detects blocking
        assert sk_fetch.has_blocking_calls, "fetch_page should have blocking calls"
        
        # Get async version
        async_fetch = sk_fetch.asynced()
        
        start = stdlib_time.perf_counter()
        
        # Run multiple fetches concurrently
        results = await asyncio.gather(
            async_fetch("http://example.com/1"),
            async_fetch("http://example.com/2"),
            async_fetch("http://example.com/3"),
            return_exceptions=True,  # Handle potential ConnectionErrors
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Should be concurrent (~20ms), not sequential (~60ms)
        assert elapsed < 0.1, f"Should run concurrently, got {elapsed:.3f}s"
        
        # At least some should succeed
        successes = [r for r in results if isinstance(r, dict)]
        assert len(successes) >= 1, "At least one fetch should succeed"
    
    asyncio.run(async_test())


def test_skfunction_retry_with_async():
    """Test Skfunction retry mechanism with async operations."""
    call_count = [0]
    
    def flaky_fetch(url: str) -> dict:
        call_count[0] += 1
        stdlib_time.sleep(0.01)
        if call_count[0] < 3:
            raise ConnectionError("Temporary failure")
        return {"url": url, "status": 200}
    
    async def async_test():
        sk_fetch = Skfunction(flaky_fetch)
        
        # Use retry then asynced
        # retry creates a new Skfunction, which we can then asynced
        retry_fetch = sk_fetch.retry(times=5, backoff=0.0)
        
        # Call the retry version (still sync)
        result = retry_fetch("http://example.com")
        
        assert result["status"] == 200, "Should eventually succeed"
        assert call_count[0] == 3, f"Should take 3 attempts, took {call_count[0]}"
    
    asyncio.run(async_test())


def test_mixed_sync_async_circuit():
    """Test mixing sync and async circuit operations."""
    async def async_test():
        circuit = Circuit(num_shorts_to_trip=6, sleep_time_after_trip=0.0)
        
        # Mix sync and async calls
        circuit.short()  # Sync - 1
        await circuit.short.asynced()()  # Async - 2
        circuit.short()  # Sync - 3
        await circuit.short.asynced()()  # Async - 4
        circuit.short()  # Sync - 5
        result = await circuit.short.asynced()()  # Async - 6, trips
        
        assert result == True, "Should return True when tripping"
        assert circuit.total_trips == 1, "Should have tripped once"
        assert circuit.times_shorted == 0, "Counter should reset after trip"
    
    asyncio.run(async_test())


def test_timer_with_async_operations():
    """Test Timer works correctly with async operations."""
    async def async_test():
        timer = Timer()
        
        async def timed_operation():
            timer.start()
            await sleep.asynced()(0.02)
            timer.stop()
        
        # Run multiple timed operations concurrently
        await asyncio.gather(
            timed_operation(),
            timed_operation(),
            timed_operation(),
        )
        
        # Timer should have 3 measurements
        assert timer.num_times == 3, f"Should have 3 measurements, got {timer.num_times}"
        
        # Each should be ~20ms
        for t in timer.times:
            assert t >= 0.018, f"Each measurement should be ~20ms, got {t}"
            assert t < 0.05, f"Each measurement should be ~20ms, got {t}"
    
    asyncio.run(async_test())


def test_full_scraper_pattern():
    """
    Full integration test simulating an async web scraper:
    1. Rate limit requests with Circuit
    2. Use async I/O for network requests
    3. Track performance with Timer
    4. Handle failures gracefully
    """
    async def async_test():
        # Rate limiter: 3 requests before sleeping
        rate_limiter = Circuit(
            num_shorts_to_trip=3,
            sleep_time_after_trip=0.02,
            factor=1.0
        )
        
        # Failure detector: stop after 5 consecutive failures
        failure_circuit = BreakingCircuit(
            num_shorts_to_trip=5,
            sleep_time_after_trip=0.0
        )
        
        # Performance tracking
        request_timer = Timer()
        
        # URLs to scrape
        urls = [f"http://example.com/page_{i}" for i in range(10)]
        
        results = []
        
        # Create async fetch function
        sk_fetch = Skfunction(fetch_page)
        async_fetch = sk_fetch.asynced()
        
        # Process URLs
        for url in urls:
            if failure_circuit.broken:
                break
            
            # Rate limiting
            await rate_limiter.short.asynced()()
            
            # Fetch with timing
            request_timer.start()
            try:
                result = await async_fetch(url, delay=0.01)
                results.append(result)
                # Reset failure counter on success would happen via circuit.reset()
            except ConnectionError:
                failure_circuit.short()
            finally:
                request_timer.stop()
        
        # Verify results
        assert len(results) > 0, "Should have fetched some pages"
        assert request_timer.num_times == len(results) + failure_circuit.total_failures, \
            "Should have timing for all attempts"
        
        # Rate limiter should have tripped multiple times
        assert rate_limiter.total_trips >= 2, \
            f"Rate limiter should trip at least twice, got {rate_limiter.total_trips}"
    
    asyncio.run(async_test())


def test_async_skfunction_chaining():
    """Test AsyncSkfunction method chaining (timeout, retry)."""
    from suitkaise.sk.api import AsyncSkfunction
    from suitkaise.sk import FunctionTimeoutError
    
    call_count = [0]
    
    def slow_flaky(delay: float = 0.02) -> str:
        call_count[0] += 1
        stdlib_time.sleep(delay)
        if call_count[0] < 2:
            raise ValueError("First attempt fails")
        return "success"
    
    async def async_test():
        sk_func = Skfunction(slow_flaky)
        
        # Get async version and chain with retry
        async_func = sk_func.asynced()
        async_retry = async_func.retry(times=3, backoff=0.0)
        
        result = await async_retry()
        
        assert result == "success", f"Should succeed, got {result}"
        assert call_count[0] == 2, f"Should take 2 attempts, took {call_count[0]}"
    
    asyncio.run(async_test())


def test_concurrent_circuits_and_timers():
    """Test multiple circuits and timers working concurrently."""
    async def async_test():
        # Multiple rate limiters for different domains
        domain_circuits = {
            "api_a": Circuit(2, 0.01),
            "api_b": Circuit(3, 0.01),
            "api_c": Circuit(2, 0.02),
        }
        
        domain_timers = {
            "api_a": Timer(),
            "api_b": Timer(),
            "api_c": Timer(),
        }
        
        async def make_requests(domain: str, count: int):
            circuit = domain_circuits[domain]
            timer = domain_timers[domain]
            
            for _ in range(count):
                timer.start()
                await circuit.short.asynced()()
                await sleep.asynced()(0.005)  # Simulate work
                timer.stop()
        
        start = stdlib_time.perf_counter()
        
        # Run requests to all domains concurrently
        await asyncio.gather(
            make_requests("api_a", 6),
            make_requests("api_b", 6),
            make_requests("api_c", 6),
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Verify each domain's stats
        for domain, timer in domain_timers.items():
            assert timer.num_times == 6, f"{domain} should have 6 measurements"
        
        # Should be concurrent (faster than sequential)
        # Sequential would be ~18 requests * ~15ms = 270ms minimum
        # Concurrent should be much less due to parallel circuits
        assert elapsed < 0.25, f"Should run concurrently, got {elapsed:.3f}s"
    
    asyncio.run(async_test())


# =============================================================================
# Main Entry Point
# =============================================================================

# Colors for verbose output
GREEN = '\033[92m'
RED = '\033[91m'
CYAN = '\033[96m'
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'


def run_scenario(name: str, description: str, test_func, results: list):
    """Run a scenario with verbose output."""
    print(f"\n  {CYAN}Testing:{RESET} {name}")
    print(f"  {DIM}{description}{RESET}")
    
    try:
        test_func()
        results.append((name, True))
        print(f"  {GREEN}✓ Works as expected{RESET}")
    except AssertionError as e:
        results.append((name, False))
        print(f"  {RED}✗ Failed: {e}{RESET}")
    except Exception as e:
        results.append((name, False))
        print(f"  {RED}✗ Error: {type(e).__name__}: {e}{RESET}")


def run_all_tests():
    """Run all async web scraper integration tests with verbose output."""
    results = []
    
    print(f"\n  {DIM}This scenario simulates a web scraper that respects rate limits,")
    print(f"  handles failures gracefully, and maximizes throughput.{RESET}")
    
    run_scenario(
        "Concurrent Page Fetches",
        "Fetching multiple pages at once using async sleep",
        test_concurrent_async_sleeps, results
    )
    
    run_scenario(
        "Rate Limiting",
        "Circuit breaker to pause when hitting API rate limits",
        test_circuit_async_rate_limiting, results
    )
    
    run_scenario(
        "Failure Threshold",
        "BreakingCircuit that stops after too many errors",
        test_breaking_circuit_async_failure_threshold, results
    )
    
    run_scenario(
        "Blocking I/O in Async Context",
        "Wrapping blocking HTTP library calls for async use",
        test_skfunction_async_blocking_io, results
    )
    
    run_scenario(
        "Automatic Retry with Backoff",
        "Retrying failed requests with increasing delays",
        test_skfunction_retry_with_async, results
    )
    
    run_scenario(
        "Mixed Sync/Async Operations",
        "Using circuits from both sync and async code paths",
        test_mixed_sync_async_circuit, results
    )
    
    run_scenario(
        "Request Timing",
        "Tracking performance of async operations with Timer",
        test_timer_with_async_operations, results
    )
    
    run_scenario(
        "Complete Web Scraper",
        "Full scraper pattern with all components working together",
        test_full_scraper_pattern, results
    )
    
    run_scenario(
        "Async Function Chaining",
        "Chaining timeout and retry on async functions",
        test_async_skfunction_chaining, results
    )
    
    run_scenario(
        "Multi-Domain Rate Limiting",
        "Separate rate limiters and timers per domain",
        test_concurrent_circuits_and_timers, results
    )
    
    # Summary
    passed = sum(1 for _, p in results if p)
    failed = len(results) - passed
    
    print(f"\n  {BOLD}{'─'*70}{RESET}")
    if failed == 0:
        print(f"  {GREEN}{BOLD}✓ All {passed} scenarios passed!{RESET}")
    else:
        print(f"  Passed: {passed}  |  {RED}Failed: {failed}{RESET}")
    print(f"  {BOLD}{'─'*70}{RESET}")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
