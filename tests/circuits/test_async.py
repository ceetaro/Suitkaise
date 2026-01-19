"""
Circuit Async Tests

Tests .asynced() methods on Circuit and BreakingCircuit:
- short.asynced()
- trip.asynced()
- Concurrent async operations
"""

import sys
import time
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

from suitkaise.circuits import Circuit, BreakingCircuit


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

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()


        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# =============================================================================
# Circuit.short.asynced() Tests
# =============================================================================

def test_circuit_short_asynced_exists():
    """Circuit.short should have .asynced method."""
    circ = Circuit(5)
    
    assert hasattr(circ.short, 'asynced'), "short should have .asynced"
    assert callable(circ.short.asynced), "asynced should be callable"


def test_circuit_short_asynced_works():
    """Circuit.short.asynced() should work in async context."""
    async def async_test():
        circ = Circuit(3, sleep_time_after_trip=0.0)
        
        result = await circ.short.asynced()()
        
        assert result == False  # Not tripped yet
        assert circ.times_shorted == 1
    
    asyncio.run(async_test())


def test_circuit_short_asynced_trips():
    """Circuit.short.asynced() should return True when tripping."""
    async def async_test():
        circ = Circuit(2, sleep_time_after_trip=0.0)
        
        await circ.short.asynced()()  # 1
        result = await circ.short.asynced()()  # 2 - trips
        
        assert result == True
        assert circ.total_trips == 1
    
    asyncio.run(async_test())


def test_circuit_short_asynced_sleeps():
    """Circuit.short.asynced() should use asyncio.sleep when tripping."""
    async def async_test():
        circ = Circuit(2, sleep_time_after_trip=0.02)
        
        await circ.short.asynced()()  # 1
        
        start = time.perf_counter()
        await circ.short.asynced()()  # 2 - trips
        elapsed = time.perf_counter() - start
        
        assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


def test_circuit_short_asynced_concurrent():
    """Multiple async shorts should be able to run concurrently."""
    async def async_test():
        # 3 circuits, each will trip and sleep 20ms
        circuits = [Circuit(1, sleep_time_after_trip=0.02) for _ in range(3)]
        
        start = time.perf_counter()
        
        # Run all trips concurrently
        await asyncio.gather(
            circuits[0].short.asynced()(),
            circuits[1].short.asynced()(),
            circuits[2].short.asynced()(),
        )
        
        elapsed = time.perf_counter() - start
        
        # Should complete in ~20ms (concurrent), not 60ms (sequential)
        assert elapsed < 0.04, f"Concurrent sleeps should be ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# Circuit.trip.asynced() Tests
# =============================================================================

def test_circuit_trip_asynced_exists():
    """Circuit.trip should have .asynced method."""
    circ = Circuit(5)
    
    assert hasattr(circ.trip, 'asynced'), "trip should have .asynced"


def test_circuit_trip_asynced_works():
    """Circuit.trip.asynced() should work."""
    async def async_test():
        circ = Circuit(10, sleep_time_after_trip=0.0)
        
        result = await circ.trip.asynced()()
        
        assert result == True
        assert circ.total_trips == 1
    
    asyncio.run(async_test())


def test_circuit_trip_asynced_sleeps():
    """Circuit.trip.asynced() should use asyncio.sleep."""
    async def async_test():
        circ = Circuit(10, sleep_time_after_trip=0.02)
        
        start = time.perf_counter()
        await circ.trip.asynced()()
        elapsed = time.perf_counter() - start
        
        assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


def test_circuit_trip_asynced_custom_sleep():
    """Circuit.trip.asynced() should accept custom_sleep."""
    async def async_test():
        circ = Circuit(10, sleep_time_after_trip=0.1)
        
        start = time.perf_counter()
        await circ.trip.asynced()(custom_sleep=0.02)
        elapsed = time.perf_counter() - start
        
        assert elapsed >= 0.018
        assert elapsed < 0.05  # Not 100ms
    
    asyncio.run(async_test())


# =============================================================================
# BreakingCircuit.short.asynced() Tests
# =============================================================================

def test_breaking_short_asynced_exists():
    """BreakingCircuit.short should have .asynced method."""
    circ = BreakingCircuit(5)
    
    assert hasattr(circ.short, 'asynced'), "short should have .asynced"


def test_breaking_short_asynced_works():
    """BreakingCircuit.short.asynced() should work."""
    async def async_test():
        circ = BreakingCircuit(3, sleep_time_after_trip=0.0)
        
        await circ.short.asynced()()
        
        assert circ.times_shorted == 1
        assert circ.broken == False
    
    asyncio.run(async_test())


def test_breaking_short_asynced_breaks():
    """BreakingCircuit.short.asynced() should break at threshold."""
    async def async_test():
        circ = BreakingCircuit(2, sleep_time_after_trip=0.0)
        
        await circ.short.asynced()()  # 1
        await circ.short.asynced()()  # 2 - breaks
        
        assert circ.broken == True
    
    asyncio.run(async_test())


def test_breaking_short_asynced_sleeps():
    """BreakingCircuit.short.asynced() should use asyncio.sleep when breaking."""
    async def async_test():
        circ = BreakingCircuit(2, sleep_time_after_trip=0.02)
        
        await circ.short.asynced()()  # 1
        
        start = time.perf_counter()
        await circ.short.asynced()()  # 2 - breaks
        elapsed = time.perf_counter() - start
        
        assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# BreakingCircuit.trip.asynced() Tests
# =============================================================================

def test_breaking_trip_asynced_exists():
    """BreakingCircuit.trip should have .asynced method."""
    circ = BreakingCircuit(5)
    
    assert hasattr(circ.trip, 'asynced'), "trip should have .asynced"


def test_breaking_trip_asynced_works():
    """BreakingCircuit.trip.asynced() should work."""
    async def async_test():
        circ = BreakingCircuit(10, sleep_time_after_trip=0.0)
        
        await circ.trip.asynced()()
        
        assert circ.broken == True
    
    asyncio.run(async_test())


def test_breaking_trip_asynced_sleeps():
    """BreakingCircuit.trip.asynced() should use asyncio.sleep."""
    async def async_test():
        circ = BreakingCircuit(10, sleep_time_after_trip=0.02)
        
        start = time.perf_counter()
        await circ.trip.asynced()()
        elapsed = time.perf_counter() - start
        
        assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# Mixed Sync/Async Tests
# =============================================================================

def test_circuit_mixed_sync_async():
    """Circuit should work with mixed sync and async calls."""
    async def async_test():
        circ = Circuit(4, sleep_time_after_trip=0.0)
        
        circ.short()  # Sync - 1
        await circ.short.asynced()()  # Async - 2
        circ.short()  # Sync - 3
        result = await circ.short.asynced()()  # Async - 4, trips
        
        assert result == True
        assert circ.total_trips == 1
    
    asyncio.run(async_test())


def test_breaking_mixed_sync_async():
    """BreakingCircuit should work with mixed sync and async calls."""
    async def async_test():
        circ = BreakingCircuit(3, sleep_time_after_trip=0.0)
        
        circ.short()  # Sync - 1
        await circ.short.asynced()()  # Async - 2
        circ.short()  # Sync - 3, breaks
        
        assert circ.broken == True
    
    asyncio.run(async_test())


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all circuit async tests."""
    runner = TestRunner("Circuit Async Tests")
    
    # Circuit.short.asynced() tests
    runner.run_test("Circuit.short.asynced exists", test_circuit_short_asynced_exists)
    runner.run_test("Circuit.short.asynced() works", test_circuit_short_asynced_works)
    runner.run_test("Circuit.short.asynced() trips", test_circuit_short_asynced_trips)
    runner.run_test("Circuit.short.asynced() sleeps", test_circuit_short_asynced_sleeps)
    runner.run_test("Circuit.short.asynced() concurrent", test_circuit_short_asynced_concurrent)
    
    # Circuit.trip.asynced() tests
    runner.run_test("Circuit.trip.asynced exists", test_circuit_trip_asynced_exists)
    runner.run_test("Circuit.trip.asynced() works", test_circuit_trip_asynced_works)
    runner.run_test("Circuit.trip.asynced() sleeps", test_circuit_trip_asynced_sleeps)
    runner.run_test("Circuit.trip.asynced() custom_sleep", test_circuit_trip_asynced_custom_sleep)
    
    # BreakingCircuit.short.asynced() tests
    runner.run_test("BreakingCircuit.short.asynced exists", test_breaking_short_asynced_exists)
    runner.run_test("BreakingCircuit.short.asynced() works", test_breaking_short_asynced_works)
    runner.run_test("BreakingCircuit.short.asynced() breaks", test_breaking_short_asynced_breaks)
    runner.run_test("BreakingCircuit.short.asynced() sleeps", test_breaking_short_asynced_sleeps)
    
    # BreakingCircuit.trip.asynced() tests
    runner.run_test("BreakingCircuit.trip.asynced exists", test_breaking_trip_asynced_exists)
    runner.run_test("BreakingCircuit.trip.asynced() works", test_breaking_trip_asynced_works)
    runner.run_test("BreakingCircuit.trip.asynced() sleeps", test_breaking_trip_asynced_sleeps)
    
    # Mixed tests
    runner.run_test("Circuit mixed sync/async", test_circuit_mixed_sync_async)
    runner.run_test("BreakingCircuit mixed sync/async", test_breaking_mixed_sync_async)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
