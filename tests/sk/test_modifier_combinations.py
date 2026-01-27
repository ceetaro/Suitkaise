"""
Skfunction Modifier Combination Tests

Tests that:
1. Every combination of modifiers works in every order
2. Sync functions execute immediately when called
3. Async functions return coroutines when called
4. Background modifier works with other modifiers
"""

import sys
import time as stdlib_time
import asyncio
import inspect
from concurrent.futures import Future

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.sk import FunctionTimeoutError
from suitkaise.sk.api import Skfunction


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
# Test Functions - used by tests
# =============================================================================

def simple_func(x):
    """Simple function that doubles input."""
    return x * 2


def slow_func(x):
    """Function with blocking call for async detection."""
    stdlib_time.sleep(0.001)
    return x * 2


fail_count = 0

def flaky_func(x):
    """Function that fails first 2 times, succeeds on 3rd."""
    global fail_count
    fail_count += 1
    if fail_count < 3:
        raise ValueError(f"Fail #{fail_count}")
    result = x * 2
    fail_count = 0  # reset for next test
    return result


def reset_flaky():
    global fail_count
    fail_count = 0


# =============================================================================
# SYNC MODIFIER TESTS - Immediate Execution
# =============================================================================

def test_sync_direct_call_executes_immediately():
    """Direct call on Skfunction should execute immediately."""
    sk_func = Skfunction(simple_func)
    
    executed = False
    def tracking_func(x):
        nonlocal executed
        executed = True
        return x * 2
    
    sk_track = Skfunction(tracking_func)
    result = sk_track(5)
    
    assert executed, "Function should have executed"
    assert result == 10, f"Expected 10, got {result}"


def test_sync_retry_executes_immediately():
    """.retry() should return callable that executes immediately when called."""
    sk_func = Skfunction(simple_func)
    
    executed = False
    def tracking_func(x):
        nonlocal executed
        executed = True
        return x * 2
    
    sk_track = Skfunction(tracking_func)
    result = sk_track.retry(3)(5)
    
    assert executed, "Function should have executed immediately"
    assert result == 10, f"Expected 10, got {result}"


def test_sync_timeout_executes_immediately():
    """.timeout() should return callable that executes immediately when called."""
    sk_func = Skfunction(simple_func)
    
    executed = False
    def tracking_func(x):
        nonlocal executed
        executed = True
        return x * 2
    
    sk_track = Skfunction(tracking_func)
    result = sk_track.timeout(10.0)(5)
    
    assert executed, "Function should have executed immediately"
    assert result == 10, f"Expected 10, got {result}"


def test_sync_background_returns_future():
    """.background() should return callable that returns Future."""
    sk_func = Skfunction(simple_func)
    
    future = sk_func.background()(5)
    
    # Should be a Future, not immediate result
    assert isinstance(future, Future), f"Expected Future, got {type(future)}"
    
    result = future.result(timeout=5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_retry_background_returns_future():
    """.retry().background() should return Future and succeed."""
    reset_flaky()
    sk_func = Skfunction(flaky_func)
    
    future = sk_func.retry(times=5, delay=0.01).background()(5)
    
    assert isinstance(future, Future), f"Expected Future, got {type(future)}"
    result = future.result(timeout=5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_timeout_background_returns_future():
    """.timeout().background() should return Future and succeed."""
    sk_func = Skfunction(simple_func)
    
    future = sk_func.timeout(5.0).background()(5)
    
    assert isinstance(future, Future), f"Expected Future, got {type(future)}"
    result = future.result(timeout=5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_retry_timeout_background_returns_future():
    """.retry().timeout().background() should return Future and succeed."""
    sk_func = Skfunction(simple_func)
    
    future = sk_func.retry(3).timeout(5.0).background()(5)
    
    assert isinstance(future, Future), f"Expected Future, got {type(future)}"
    result = future.result(timeout=5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_timeout_retry_background_returns_future():
    """.timeout().retry().background() should return Future and succeed."""
    sk_func = Skfunction(simple_func)
    
    future = sk_func.timeout(5.0).retry(3).background()(5)
    
    assert isinstance(future, Future), f"Expected Future, got {type(future)}"
    result = future.result(timeout=5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_timeout_background_propagates_error():
    """.timeout().background() should surface timeout errors."""
    def very_slow(x):
        stdlib_time.sleep(0.2)
        return x
    
    sk_func = Skfunction(very_slow).timeout(0.01)
    future = sk_func.background()(5)
    
    try:
        future.result(timeout=5)
        assert False, "Should have raised FunctionTimeoutError"
    except FunctionTimeoutError:
        pass  # expected


# =============================================================================
# SYNC MODIFIER COMBINATIONS - All Orders
# =============================================================================

def test_sync_retry_timeout():
    """.retry().timeout() chain should work."""
    sk_func = Skfunction(simple_func)
    result = sk_func.retry(3).timeout(10.0)(5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_timeout_retry():
    """.timeout().retry() chain should work (same behavior as .retry().timeout())."""
    sk_func = Skfunction(simple_func)
    result = sk_func.timeout(10.0).retry(3)(5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_order_does_not_matter():
    """Both orderings should produce the same behavior."""
    sk_func = Skfunction(simple_func)
    
    # Both orderings should work identically
    result1 = sk_func.retry(3).timeout(10.0)(5)
    result2 = sk_func.timeout(10.0).retry(3)(5)
    
    assert result1 == result2 == 10, f"Expected both to be 10, got {result1} and {result2}"


def test_sync_retry_actually_retries():
    """.retry() should actually retry on failure."""
    reset_flaky()
    sk_func = Skfunction(flaky_func)
    
    # Should succeed on 3rd attempt
    result = sk_func.retry(times=5, delay=0.01)(5)
    assert result == 10, f"Expected 10, got {result}"


def test_sync_timeout_actually_times_out():
    """.timeout() should raise FunctionTimeoutError on timeout."""
    def very_slow(x):
        stdlib_time.sleep(10)
        return x
    
    sk_func = Skfunction(very_slow)
    
    try:
        sk_func.timeout(0.1)(5)
        assert False, "Should have raised FunctionTimeoutError"
    except FunctionTimeoutError:
        pass  # expected


# =============================================================================
# ASYNC MODIFIER TESTS - Returns Coroutine
# =============================================================================

def test_async_asynced_returns_coroutine():
    """.asynced()() should return a coroutine."""
    sk_func = Skfunction(slow_func)
    
    coro = sk_func.asynced()(5)
    
    assert inspect.iscoroutine(coro), f"Expected coroutine, got {type(coro)}"
    
    # Clean up - run the coroutine
    result = asyncio.run(coro)
    assert result == 10, f"Expected 10, got {result}"


def test_async_asynced_timeout_returns_coroutine():
    """.asynced().timeout()() should return a coroutine."""
    sk_func = Skfunction(slow_func)
    
    coro = sk_func.asynced().timeout(10.0)(5)
    
    assert inspect.iscoroutine(coro), f"Expected coroutine, got {type(coro)}"
    
    result = asyncio.run(coro)
    assert result == 10, f"Expected 10, got {result}"


def test_async_asynced_retry_returns_coroutine():
    """.asynced().retry()() should return a coroutine."""
    sk_func = Skfunction(slow_func)
    
    coro = sk_func.asynced().retry(3)(5)
    
    assert inspect.iscoroutine(coro), f"Expected coroutine, got {type(coro)}"
    
    result = asyncio.run(coro)
    assert result == 10, f"Expected 10, got {result}"


def test_async_asynced_retry_timeout_returns_coroutine():
    """.asynced().retry().timeout()() should return a coroutine."""
    sk_func = Skfunction(slow_func)
    
    coro = sk_func.asynced().retry(3).timeout(10.0)(5)
    
    assert inspect.iscoroutine(coro), f"Expected coroutine, got {type(coro)}"
    
    result = asyncio.run(coro)
    assert result == 10, f"Expected 10, got {result}"


def test_async_asynced_timeout_retry_returns_coroutine():
    """.asynced().timeout().retry()() should return a coroutine."""
    sk_func = Skfunction(slow_func)
    
    coro = sk_func.asynced().timeout(10.0).retry(3)(5)
    
    assert inspect.iscoroutine(coro), f"Expected coroutine, got {type(coro)}"
    
    result = asyncio.run(coro)
    assert result == 10, f"Expected 10, got {result}"


def test_async_order_does_not_matter():
    """Both orderings should produce the same behavior for async."""
    sk_func = Skfunction(slow_func)
    
    # Both orderings should work identically
    coro1 = sk_func.asynced().retry(3).timeout(10.0)(5)
    result1 = asyncio.run(coro1)
    
    coro2 = sk_func.asynced().timeout(10.0).retry(3)(5)
    result2 = asyncio.run(coro2)
    
    assert result1 == result2 == 10, f"Expected both to be 10, got {result1} and {result2}"


# =============================================================================
# SYNC vs ASYNC BEHAVIOR COMPARISON
# =============================================================================

def test_sync_does_not_return_coroutine():
    """Sync modifiers should NOT return coroutines."""
    sk_func = Skfunction(simple_func)
    
    # Direct call
    result = sk_func(5)
    assert not inspect.iscoroutine(result), "Direct call should not return coroutine"
    assert result == 10
    
    # With retry
    result = sk_func.retry(3)(5)
    assert not inspect.iscoroutine(result), ".retry() should not return coroutine"
    assert result == 10
    
    # With timeout
    result = sk_func.timeout(10.0)(5)
    assert not inspect.iscoroutine(result), ".timeout() should not return coroutine"
    assert result == 10


def test_async_always_returns_coroutine():
    """Async modifiers should ALWAYS return coroutines."""
    sk_func = Skfunction(slow_func)
    
    # asynced only
    coro = sk_func.asynced()(5)
    assert inspect.iscoroutine(coro), ".asynced() should return coroutine"
    asyncio.run(coro)
    
    # asynced + retry
    coro = sk_func.asynced().retry(3)(5)
    assert inspect.iscoroutine(coro), ".asynced().retry() should return coroutine"
    asyncio.run(coro)
    
    # asynced + timeout
    coro = sk_func.asynced().timeout(10.0)(5)
    assert inspect.iscoroutine(coro), ".asynced().timeout() should return coroutine"
    asyncio.run(coro)


# =============================================================================
# Run Tests
# =============================================================================

def run_all_tests():
    """Run all modifier combination tests."""
    runner = TestRunner("Skfunction Modifier Combinations")
    
    # Sync immediate execution
    runner.run_test("sync: direct call executes immediately", test_sync_direct_call_executes_immediately)
    runner.run_test("sync: .retry() executes immediately", test_sync_retry_executes_immediately)
    runner.run_test("sync: .timeout() executes immediately", test_sync_timeout_executes_immediately)
    runner.run_test("sync: .background() returns Future", test_sync_background_returns_future)
    runner.run_test("sync: .retry().background() returns Future", test_sync_retry_background_returns_future)
    runner.run_test("sync: .timeout().background() returns Future", test_sync_timeout_background_returns_future)
    runner.run_test("sync: .retry().timeout().background() returns Future", test_sync_retry_timeout_background_returns_future)
    runner.run_test("sync: .timeout().retry().background() returns Future", test_sync_timeout_retry_background_returns_future)
    runner.run_test("sync: .timeout().background() propagates error", test_sync_timeout_background_propagates_error)
    
    # Sync combinations
    runner.run_test("sync: .retry().timeout() works", test_sync_retry_timeout)
    runner.run_test("sync: .timeout().retry() works", test_sync_timeout_retry)
    runner.run_test("sync: order does not matter", test_sync_order_does_not_matter)
    runner.run_test("sync: .retry() actually retries", test_sync_retry_actually_retries)
    runner.run_test("sync: .timeout() actually times out", test_sync_timeout_actually_times_out)
    
    # Async returns coroutine
    runner.run_test("async: .asynced()() returns coroutine", test_async_asynced_returns_coroutine)
    runner.run_test("async: .asynced().timeout()() returns coroutine", test_async_asynced_timeout_returns_coroutine)
    runner.run_test("async: .asynced().retry()() returns coroutine", test_async_asynced_retry_returns_coroutine)
    runner.run_test("async: .asynced().retry().timeout()() returns coroutine", test_async_asynced_retry_timeout_returns_coroutine)
    runner.run_test("async: .asynced().timeout().retry()() returns coroutine", test_async_asynced_timeout_retry_returns_coroutine)
    runner.run_test("async: order does not matter", test_async_order_does_not_matter)
    
    # Behavior comparison
    runner.run_test("sync: does NOT return coroutine", test_sync_does_not_return_coroutine)
    runner.run_test("async: ALWAYS returns coroutine", test_async_always_returns_coroutine)
    
    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
