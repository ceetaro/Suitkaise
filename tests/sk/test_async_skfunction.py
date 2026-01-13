"""
AsyncSkfunction Tests

Tests the AsyncSkfunction class:
- Creation from functions with blocking calls
- Chained methods (retry, timeout, background)
- Await behavior
- Error handling
- Concurrent execution

Note: AsyncSkfunction only works with functions that have blocking calls
(e.g., time.sleep, file I/O, network calls). Functions without blocking
calls will raise NotAsyncedError when calling .asynced().
"""

import sys
import asyncio
import time as stdlib_time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.sk import Skfunction, sk
from suitkaise.sk.api import AsyncSkfunction, NotAsyncedError


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
            # Handle async tests
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func())
            else:
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
# Test Functions with Blocking Calls
# =============================================================================

def blocking_return_42():
    """Blocking function that returns 42."""
    stdlib_time.sleep(0.001)
    return 42


def blocking_add(a, b):
    """Blocking function that adds two numbers."""
    stdlib_time.sleep(0.001)
    return a + b


def blocking_greet(name, prefix="Hello"):
    """Blocking function with kwargs."""
    stdlib_time.sleep(0.001)
    return f"{prefix}, {name}!"


def blocking_error():
    """Blocking function that raises an error."""
    stdlib_time.sleep(0.001)
    raise ValueError("intentional error")


def blocking_flaky():
    """Blocking function that fails sometimes."""
    stdlib_time.sleep(0.001)
    if not hasattr(blocking_flaky, '_count'):
        blocking_flaky._count = 0
    blocking_flaky._count += 1
    if blocking_flaky._count < 3:
        raise ValueError("flaky failure")
    result = blocking_flaky._count
    blocking_flaky._count = 0  # Reset for next test
    return result


# =============================================================================
# AsyncSkfunction Creation Tests
# =============================================================================

def test_asyncskfunction_from_skfunction():
    """AsyncSkfunction should be creatable from Skfunction.asynced()."""
    sk_func = Skfunction(blocking_return_42)
    async_func = sk_func.asynced()
    
    assert async_func is not None
    assert isinstance(async_func, AsyncSkfunction)


async def test_asyncskfunction_callable():
    """AsyncSkfunction should be awaitable."""
    sk_func = Skfunction(blocking_return_42)
    async_func = sk_func.asynced()
    
    result = await async_func()
    
    assert result == 42


async def test_asyncskfunction_with_args():
    """AsyncSkfunction should pass args correctly."""
    sk_func = Skfunction(blocking_add)
    async_func = sk_func.asynced()
    
    result = await async_func(3, 4)
    
    assert result == 7


async def test_asyncskfunction_with_kwargs():
    """AsyncSkfunction should pass kwargs correctly."""
    sk_func = Skfunction(blocking_greet)
    async_func = sk_func.asynced()
    
    result = await async_func("World", prefix="Hi")
    
    assert result == "Hi, World!"


def test_non_blocking_raises_error():
    """Calling asynced() on non-blocking function should raise NotAsyncedError."""
    def pure_func():
        return 42
    
    sk_func = Skfunction(pure_func)
    
    try:
        sk_func.asynced()
        assert False, "Should have raised NotAsyncedError"
    except NotAsyncedError:
        pass  # Expected


# =============================================================================
# @sk Decorator Tests
# =============================================================================

def test_sk_decorated_has_asynced():
    """@sk decorated function should have asynced method."""
    @sk
    def decorated():
        stdlib_time.sleep(0.001)
        return 42
    
    assert hasattr(decorated, 'asynced'), "Should have asynced method"


async def test_sk_decorated_asynced_works():
    """@sk decorated function with blocking calls should work async."""
    @sk
    def decorated():
        stdlib_time.sleep(0.001)
        return 42
    
    async_func = decorated.asynced()
    result = await async_func()
    
    assert result == 42


# =============================================================================
# Chaining Tests
# =============================================================================

async def test_asyncskfunction_retry_chain():
    """AsyncSkfunction.retry() should chain correctly."""
    # Reset the counter
    if hasattr(blocking_flaky, '_count'):
        blocking_flaky._count = 0
    
    sk_func = Skfunction(blocking_flaky)
    async_func = sk_func.asynced()
    
    # Retry 5 times - should succeed on attempt 3
    result = await async_func.retry(times=5)()
    
    assert result == 3


def test_asyncskfunction_timeout_chain():
    """AsyncSkfunction.timeout() should return chainable object."""
    sk_func = Skfunction(blocking_return_42)
    async_func = sk_func.asynced()
    
    chained = async_func.timeout(5.0)
    
    assert chained is not None


def test_skfunction_background_chain():
    """Skfunction.background() should return Future-like object."""
    # Note: AsyncSkfunction doesn't have .background() - use Skfunction instead
    sk_func = Skfunction(blocking_return_42)
    
    bg = sk_func.background()
    
    # Should be callable and return a Future
    future = bg()
    assert future is not None
    # Get the result
    result = future.result(timeout=5.0)
    assert result == 42


# =============================================================================
# Concurrent Execution Tests
# =============================================================================

async def test_asyncskfunction_concurrent():
    """Multiple async functions should run concurrently."""
    def slow_double(n):
        stdlib_time.sleep(0.05)
        return n * 2
    
    sk_func = Skfunction(slow_double)
    async_func = sk_func.asynced()
    
    # Run 3 concurrently - should take ~50ms total, not ~150ms
    start = stdlib_time.time()
    results = await asyncio.gather(
        async_func(1),
        async_func(2),
        async_func(3),
    )
    elapsed = stdlib_time.time() - start
    
    assert results == [2, 4, 6]
    # Should be much faster than sequential (0.15s)
    assert elapsed < 0.12, f"Too slow: {elapsed}s"


# =============================================================================
# Error Handling Tests
# =============================================================================

async def test_asyncskfunction_propagates_error():
    """AsyncSkfunction should propagate errors."""
    sk_func = Skfunction(blocking_error)
    async_func = sk_func.asynced()
    
    try:
        await async_func()
        assert False, "Should have raised"
    except ValueError as e:
        assert "intentional" in str(e)


async def test_asyncskfunction_retry_exhausted():
    """AsyncSkfunction.retry() should fail after exhausting retries."""
    def always_fails():
        stdlib_time.sleep(0.001)
        raise ValueError("always fails")
    
    sk_func = Skfunction(always_fails)
    async_func = sk_func.asynced()
    
    try:
        await async_func.retry(times=2)()
        assert False, "Should have raised"
    except ValueError:
        pass  # Expected


# =============================================================================
# Return Value Tests
# =============================================================================

async def test_asyncskfunction_returns_none():
    """AsyncSkfunction should handle None return."""
    def returns_none():
        stdlib_time.sleep(0.001)
        return None
    
    sk_func = Skfunction(returns_none)
    async_func = sk_func.asynced()
    
    result = await async_func()
    
    assert result is None


async def test_asyncskfunction_returns_complex():
    """AsyncSkfunction should handle complex return types."""
    def returns_complex():
        stdlib_time.sleep(0.001)
        return {"list": [1, 2, 3], "nested": {"key": "value"}}
    
    sk_func = Skfunction(returns_complex)
    async_func = sk_func.asynced()
    
    result = await async_func()
    
    assert result == {"list": [1, 2, 3], "nested": {"key": "value"}}


# =============================================================================
# Arguments Tests
# =============================================================================

async def test_asyncskfunction_empty_args():
    """AsyncSkfunction should handle no-arg functions."""
    result = await Skfunction(blocking_return_42).asynced()()
    assert result == 42


async def test_asyncskfunction_many_args():
    """AsyncSkfunction should handle many positional args."""
    def many_args(a, b, c, d, e):
        stdlib_time.sleep(0.001)
        return a + b + c + d + e
    
    sk_func = Skfunction(many_args)
    result = await sk_func.asynced()(1, 2, 3, 4, 5)
    
    assert result == 15


async def test_asyncskfunction_star_args():
    """AsyncSkfunction should handle *args."""
    def star_args(*args):
        stdlib_time.sleep(0.001)
        return sum(args)
    
    sk_func = Skfunction(star_args)
    result = await sk_func.asynced()(1, 2, 3, 4)
    
    assert result == 10


async def test_asyncskfunction_star_kwargs():
    """AsyncSkfunction should handle **kwargs."""
    def star_kwargs(**kwargs):
        stdlib_time.sleep(0.001)
        return kwargs
    
    sk_func = Skfunction(star_kwargs)
    result = await sk_func.asynced()(a=1, b=2)
    
    assert result == {"a": 1, "b": 2}


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all AsyncSkfunction tests."""
    runner = TestRunner("AsyncSkfunction Tests")
    
    # Creation tests
    runner.run_test("AsyncSkfunction from Skfunction", test_asyncskfunction_from_skfunction)
    runner.run_test("AsyncSkfunction callable", test_asyncskfunction_callable)
    runner.run_test("AsyncSkfunction with args", test_asyncskfunction_with_args)
    runner.run_test("AsyncSkfunction with kwargs", test_asyncskfunction_with_kwargs)
    runner.run_test("Non-blocking raises error", test_non_blocking_raises_error)
    
    # @sk decorator tests
    runner.run_test("@sk has asynced", test_sk_decorated_has_asynced)
    runner.run_test("@sk asynced works", test_sk_decorated_asynced_works)
    
    # Chaining tests
    runner.run_test("AsyncSkfunction retry chain", test_asyncskfunction_retry_chain)
    runner.run_test("AsyncSkfunction timeout chain", test_asyncskfunction_timeout_chain)
    runner.run_test("Skfunction background chain", test_skfunction_background_chain)
    
    # Concurrent tests
    runner.run_test("AsyncSkfunction concurrent", test_asyncskfunction_concurrent)
    
    # Error handling tests
    runner.run_test("AsyncSkfunction propagates error", test_asyncskfunction_propagates_error)
    runner.run_test("AsyncSkfunction retry exhausted", test_asyncskfunction_retry_exhausted)
    
    # Return value tests
    runner.run_test("AsyncSkfunction returns None", test_asyncskfunction_returns_none)
    runner.run_test("AsyncSkfunction returns complex", test_asyncskfunction_returns_complex)
    
    # Arguments tests
    runner.run_test("AsyncSkfunction empty args", test_asyncskfunction_empty_args)
    runner.run_test("AsyncSkfunction many args", test_asyncskfunction_many_args)
    runner.run_test("AsyncSkfunction *args", test_asyncskfunction_star_args)
    runner.run_test("AsyncSkfunction **kwargs", test_asyncskfunction_star_kwargs)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
