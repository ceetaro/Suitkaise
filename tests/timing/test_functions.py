"""
Timing Functions Tests

Tests module-level timing functions:
- time() - get current timestamp
- sleep() - sleep with return value
- sleep.asynced() - async sleep
- elapsed() - calculate elapsed time
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

from suitkaise.timing import time, sleep, elapsed


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
# time() Tests
# =============================================================================

def test_time_returns_float():
    """time() should return a float timestamp."""
    result = time()
    assert isinstance(result, float), f"Should return float, got {type(result)}"


def test_time_is_current():
    """time() should return current Unix timestamp."""
    before = stdlib_time.time()
    result = time()
    after = stdlib_time.time()
    
    assert result >= before, "time() should be >= stdlib before"
    assert result <= after, "time() should be <= stdlib after"


def test_time_increases():
    """Subsequent time() calls should increase."""
    t1 = time()
    stdlib_time.sleep(0.01)
    t2 = time()
    
    assert t2 > t1, f"Second call should be larger: {t1} -> {t2}"


# =============================================================================
# sleep() Tests
# =============================================================================

def test_sleep_blocks():
    """sleep() should block for specified duration."""
    start = stdlib_time.perf_counter()
    sleep(0.02)  # 20ms
    elapsed = stdlib_time.perf_counter() - start
    
    assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"
    assert elapsed < 0.05, f"Should not sleep too long, got {elapsed}"


def test_sleep_returns_time():
    """sleep() should return current time after sleeping."""
    before = time()
    result = sleep(0.01)
    
    assert isinstance(result, float), f"Should return float, got {type(result)}"
    assert result > before, "Returned time should be after before"


def test_sleep_zero():
    """sleep(0) should return quickly."""
    start = stdlib_time.perf_counter()
    sleep(0)
    elapsed = stdlib_time.perf_counter() - start
    
    assert elapsed < 0.01, f"Zero sleep should be fast, got {elapsed}"


def test_sleep_fractional():
    """sleep() should handle fractional seconds."""
    start = stdlib_time.perf_counter()
    sleep(0.015)  # 15ms
    elapsed = stdlib_time.perf_counter() - start
    
    assert elapsed >= 0.013, f"Should sleep ~15ms, got {elapsed}"


# =============================================================================
# sleep.asynced() Tests
# =============================================================================

def test_sleep_asynced_exists():
    """sleep should have .asynced attribute."""
    assert hasattr(sleep, 'asynced'), "sleep should have .asynced method"
    assert callable(sleep.asynced), "sleep.asynced should be callable"


def test_sleep_asynced_works():
    """sleep.asynced() should work in async context."""
    async def async_test():
        start = stdlib_time.perf_counter()
        result = await sleep.asynced()(0.02)  # 20ms
        elapsed = stdlib_time.perf_counter() - start
        
        assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"
        assert isinstance(result, float), f"Should return float, got {type(result)}"
    
    asyncio.run(async_test())


def test_sleep_asynced_returns_time():
    """sleep.asynced() should return time after sleeping."""
    async def async_test():
        before = time()
        result = await sleep.asynced()(0.01)
        
        assert result > before, "Returned time should be after before"
    
    asyncio.run(async_test())


# =============================================================================
# Docstring Examples
# =============================================================================

def test_doc_time_example():
    """Docstring example for time()."""
    start_time = time()
    assert isinstance(start_time, float)


def test_doc_sleep_elapsed_example():
    """Docstring example: sleep with elapsed time."""
    start_time = time()
    sleep(0.01)
    end_time = time()
    elapsed_time = end_time - start_time
    assert elapsed_time >= 0


def test_doc_sleep_return_example():
    """Docstring example: sleep returns end time."""
    start_time = time()
    end_time = sleep(0.01)
    assert end_time >= start_time


def test_doc_sleep_async_example():
    """Docstring example: async sleep via asynced()."""
    async def run():
        end_time = await sleep.asynced()(0.01)
        assert isinstance(end_time, float)
    asyncio.run(run())


def test_doc_elapsed_example():
    """Docstring example for elapsed() order independence."""
    start_time = time()
    sleep(0.01)
    elapsed1 = elapsed(start_time)
    start_time = time()
    sleep(0.01)
    end_time = time()
    elapsed2 = elapsed(start_time, end_time)
    elapsed3 = elapsed(end_time, start_time)
    assert elapsed1 >= 0
    assert elapsed2 >= 0
    assert elapsed3 >= 0


def test_sleep_asynced_concurrent():
    """Multiple sleep.asynced() should run concurrently."""
    async def async_test():
        start = stdlib_time.perf_counter()
        
        # Run 3 sleeps of 20ms concurrently
        await asyncio.gather(
            sleep.asynced()(0.02),
            sleep.asynced()(0.02),
            sleep.asynced()(0.02),
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Should complete in ~20ms (concurrent), not 60ms (sequential)
        assert elapsed < 0.04, f"Concurrent sleeps should be ~20ms total, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# elapsed() Tests
# =============================================================================

def test_elapsed_two_times():
    """elapsed() should calculate difference between two times."""
    t1 = 100.0
    t2 = 150.0
    
    result = elapsed(t1, t2)
    
    assert result == 50.0, f"Should be 50.0, got {result}"


def test_elapsed_order_independent():
    """elapsed() should return positive value regardless of order."""
    t1 = 100.0
    t2 = 150.0
    
    result1 = elapsed(t1, t2)
    result2 = elapsed(t2, t1)
    
    assert result1 == result2, f"Order should not matter: {result1} vs {result2}"
    assert result1 > 0, "Result should be positive"


def test_elapsed_single_time():
    """elapsed() with one argument should use current time."""
    start = time()
    stdlib_time.sleep(0.02)
    result = elapsed(start)
    
    assert result >= 0.018, f"Should be ~20ms, got {result}"
    assert result < 0.05, f"Should not be too large, got {result}"


def test_elapsed_same_time():
    """elapsed() of same time should be zero."""
    t = time()
    result = elapsed(t, t)
    
    assert result == 0.0, f"Same time should give 0, got {result}"


def test_elapsed_precision():
    """elapsed() should handle high precision values."""
    t1 = 1234567890.123456
    t2 = 1234567890.123457
    
    result = elapsed(t1, t2)
    
    assert result < 0.00001, f"Should handle high precision, got {result}"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all timing function tests."""
    runner = TestRunner("Timing Functions Tests")
    
    # time() tests
    runner.run_test("time() returns float", test_time_returns_float)
    runner.run_test("time() is current", test_time_is_current)
    runner.run_test("time() increases", test_time_increases)
    
    # sleep() tests
    runner.run_test("sleep() blocks", test_sleep_blocks)
    runner.run_test("sleep() returns time", test_sleep_returns_time)
    runner.run_test("sleep(0) is fast", test_sleep_zero)
    runner.run_test("sleep() fractional", test_sleep_fractional)
    
    # sleep.asynced() tests
    runner.run_test("sleep.asynced exists", test_sleep_asynced_exists)
    runner.run_test("sleep.asynced() works", test_sleep_asynced_works)
    runner.run_test("sleep.asynced() returns time", test_sleep_asynced_returns_time)
    runner.run_test("sleep.asynced() concurrent", test_sleep_asynced_concurrent)
    
    # elapsed() tests
    runner.run_test("elapsed() two times", test_elapsed_two_times)
    runner.run_test("elapsed() order independent", test_elapsed_order_independent)
    runner.run_test("elapsed() single time", test_elapsed_single_time)
    runner.run_test("elapsed() same time", test_elapsed_same_time)
    runner.run_test("elapsed() precision", test_elapsed_precision)
    
    # docstring examples
    runner.run_test("doc: time()", test_doc_time_example)
    runner.run_test("doc: sleep elapsed", test_doc_sleep_elapsed_example)
    runner.run_test("doc: sleep returns time", test_doc_sleep_return_example)
    runner.run_test("doc: sleep async", test_doc_sleep_async_example)
    runner.run_test("doc: elapsed order", test_doc_elapsed_example)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
