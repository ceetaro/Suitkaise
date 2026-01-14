"""
Skfunction Tests

Tests Skfunction wrapper functionality:
- Basic wrapping
- Blocking call detection
- .asynced() for functions with blocking calls
- .retry()
- .timeout()
- .background()
- NotAsyncedError for non-blocking functions
- FunctionTimeoutError
"""

import sys
import time as stdlib_time
import asyncio

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.sk import Skfunction, NotAsyncedError, FunctionTimeoutError


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
# Test Functions
# =============================================================================

def fast_add(a, b):
    """Fast function with no blocking."""
    return a + b


def slow_work(duration=0.02):
    """Slow function with time.sleep."""
    stdlib_time.sleep(duration)
    return "done"


def flaky_function():
    """Function that fails first few times."""
    if not hasattr(flaky_function, 'attempts'):
        flaky_function.attempts = 0
    flaky_function.attempts += 1
    
    if flaky_function.attempts < 3:
        raise ValueError(f"Attempt {flaky_function.attempts} failed")
    
    return "success"


def reset_flaky():
    """Reset flaky function counter."""
    if hasattr(flaky_function, 'attempts'):
        del flaky_function.attempts


# =============================================================================
# Basic Skfunction Tests
# =============================================================================

def test_skfunction_creation():
    """Skfunction should wrap a function."""
    sk_add = Skfunction(fast_add)
    
    assert sk_add is not None
    assert repr(sk_add) == "Skfunction(fast_add)"


def test_skfunction_call():
    """Skfunction should call wrapped function."""
    sk_add = Skfunction(fast_add)
    
    result = sk_add(1, 2)
    
    assert result == 3


def test_skfunction_preserves_args():
    """Skfunction should preserve args and kwargs."""
    def func_with_kwargs(a, b, c=0, d=0):
        return a + b + c + d
    
    sk_func = Skfunction(func_with_kwargs)
    
    result = sk_func(1, 2, c=3, d=4)
    
    assert result == 10


# =============================================================================
# Blocking Detection Tests
# =============================================================================

def test_skfunction_no_blocking():
    """Skfunction should detect no blocking calls."""
    sk_add = Skfunction(fast_add)
    
    assert sk_add.has_blocking_calls == False


def test_skfunction_has_blocking():
    """Skfunction should detect blocking calls."""
    sk_slow = Skfunction(slow_work)
    
    assert sk_slow.has_blocking_calls == True
    assert 'time.sleep' in str(sk_slow.blocking_calls)


# =============================================================================
# asynced() Tests
# =============================================================================

def test_skfunction_asynced_raises_for_non_blocking():
    """asynced() should raise NotAsyncedError for non-blocking function."""
    sk_add = Skfunction(fast_add)
    
    try:
        sk_add.asynced()
        assert False, "Should have raised NotAsyncedError"
    except NotAsyncedError as e:
        assert "fast_add" in str(e)
        assert "no blocking calls" in str(e)


def test_skfunction_asynced_works():
    """asynced() should work for blocking function."""
    async def async_test():
        sk_slow = Skfunction(slow_work)
        async_slow = sk_slow.asynced()
        
        start = stdlib_time.perf_counter()
        result = await async_slow(0.02)
        elapsed = stdlib_time.perf_counter() - start
        
        assert result == "done"
        assert elapsed >= 0.018
    
    asyncio.run(async_test())


def test_skfunction_asynced_concurrent():
    """Async functions should run concurrently."""
    async def async_test():
        sk_slow = Skfunction(slow_work)
        async_slow = sk_slow.asynced()
        
        start = stdlib_time.perf_counter()
        
        await asyncio.gather(
            async_slow(0.02),
            async_slow(0.02),
            async_slow(0.02),
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Should be ~20ms (concurrent), not 60ms
        assert elapsed < 0.05, f"Concurrent should be ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# retry() Tests
# =============================================================================

def test_skfunction_retry_succeeds():
    """retry() should retry on failure and eventually succeed."""
    reset_flaky()
    
    sk_flaky = Skfunction(flaky_function)
    sk_retry = sk_flaky.retry(times=5, delay=0.0)
    
    result = sk_retry()
    
    assert result == "success"


def test_skfunction_retry_fails():
    """retry() should raise after max attempts."""
    reset_flaky()
    
    sk_flaky = Skfunction(flaky_function)
    sk_retry = sk_flaky.retry(times=2, delay=0.0)  # only 2 attempts
    
    try:
        sk_retry()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "failed" in str(e)


def test_skfunction_retry_returns_skfunction():
    """retry() should return Skfunction for chaining."""
    sk_slow = Skfunction(slow_work)
    sk_retry = sk_slow.retry(times=3)
    
    assert isinstance(sk_retry, Skfunction)


def test_skfunction_retry_specific_exception():
    """retry() should only catch specified exceptions."""
    reset_flaky()
    
    sk_flaky = Skfunction(flaky_function)
    # Only retry on TypeError, not ValueError
    sk_retry = sk_flaky.retry(times=5, exceptions=(TypeError,))
    
    try:
        sk_retry()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected


# =============================================================================
# timeout() Tests
# =============================================================================

def test_skfunction_timeout_succeeds():
    """timeout() should allow fast functions to complete."""
    sk_slow = Skfunction(slow_work)
    sk_timeout = sk_slow.timeout(1.0)  # 1 second timeout
    
    result = sk_timeout(0.02)  # 20ms work
    
    assert result == "done"


def test_skfunction_timeout_fails():
    """timeout() should raise FunctionTimeoutError when exceeded."""
    sk_slow = Skfunction(slow_work)
    sk_timeout = sk_slow.timeout(0.01)  # 10ms timeout
    
    try:
        sk_timeout(0.1)  # 100ms work - should timeout
        assert False, "Should have raised FunctionTimeoutError"
    except FunctionTimeoutError:
        pass  # Expected


def test_skfunction_timeout_returns_skfunction():
    """timeout() should return Skfunction for chaining."""
    sk_slow = Skfunction(slow_work)
    sk_timeout = sk_slow.timeout(1.0)
    
    assert isinstance(sk_timeout, Skfunction)


# =============================================================================
# background() Tests
# =============================================================================

def test_skfunction_background_returns_future():
    """background() should return a function that returns Future."""
    sk_slow = Skfunction(slow_work)
    bg_func = sk_slow.background()
    
    future = bg_func(0.02)
    
    # Check it's a Future
    assert hasattr(future, 'result')
    assert hasattr(future, 'done')


def test_skfunction_background_works():
    """background() should run function in background."""
    sk_slow = Skfunction(slow_work)
    bg_func = sk_slow.background()
    
    start = stdlib_time.perf_counter()
    
    future = bg_func(0.02)
    
    # Should return immediately
    submit_time = stdlib_time.perf_counter() - start
    assert submit_time < 0.01, "Should return immediately"
    
    # Wait for result
    result = future.result()
    
    assert result == "done"


def test_skfunction_background_concurrent():
    """Multiple background calls should run concurrently."""
    sk_slow = Skfunction(slow_work)
    bg_func = sk_slow.background()
    
    start = stdlib_time.perf_counter()
    
    futures = [bg_func(0.02) for _ in range(3)]
    
    # Wait for all
    results = [f.result() for f in futures]
    
    elapsed = stdlib_time.perf_counter() - start
    
    assert all(r == "done" for r in results)
    # Should complete in ~20ms (concurrent), not 60ms
    assert elapsed < 0.1, f"Concurrent should be ~20ms, got {elapsed}"


# =============================================================================
# Chaining Tests
# =============================================================================

def test_skfunction_chain_retry_timeout():
    """retry() and timeout() should be chainable."""
    reset_flaky()
    
    def slow_flaky():
        if not hasattr(slow_flaky, 'attempts'):
            slow_flaky.attempts = 0
        slow_flaky.attempts += 1
        
        if slow_flaky.attempts < 2:
            raise ValueError("fail")
        return "success"
    
    if hasattr(slow_flaky, 'attempts'):
        del slow_flaky.attempts
    
    sk_func = Skfunction(slow_flaky)
    # use delay=0.0 so retry doesn't sleep between attempts
    # generous timeout of 5s to allow for test environment overhead
    sk_chain = sk_func.retry(times=3, delay=0.0).timeout(5.0)
    
    result = sk_chain()
    
    assert result == "success"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Skfunction tests."""
    runner = TestRunner("Skfunction Tests")
    
    # Basic tests
    runner.run_test("Skfunction creation", test_skfunction_creation)
    runner.run_test("Skfunction call", test_skfunction_call)
    runner.run_test("Skfunction preserves args", test_skfunction_preserves_args)
    
    # Blocking detection tests
    runner.run_test("Skfunction no blocking", test_skfunction_no_blocking)
    runner.run_test("Skfunction has blocking", test_skfunction_has_blocking)
    
    # asynced() tests
    runner.run_test("Skfunction asynced raises for non-blocking", test_skfunction_asynced_raises_for_non_blocking)
    runner.run_test("Skfunction asynced works", test_skfunction_asynced_works)
    runner.run_test("Skfunction asynced concurrent", test_skfunction_asynced_concurrent)
    
    # retry() tests
    runner.run_test("Skfunction retry succeeds", test_skfunction_retry_succeeds)
    runner.run_test("Skfunction retry fails", test_skfunction_retry_fails)
    runner.run_test("Skfunction retry returns Skfunction", test_skfunction_retry_returns_skfunction)
    runner.run_test("Skfunction retry specific exception", test_skfunction_retry_specific_exception)
    
    # timeout() tests
    runner.run_test("Skfunction timeout succeeds", test_skfunction_timeout_succeeds)
    runner.run_test("Skfunction timeout fails", test_skfunction_timeout_fails)
    runner.run_test("Skfunction timeout returns Skfunction", test_skfunction_timeout_returns_skfunction)
    
    # background() tests
    runner.run_test("Skfunction background returns Future", test_skfunction_background_returns_future)
    runner.run_test("Skfunction background works", test_skfunction_background_works)
    runner.run_test("Skfunction background concurrent", test_skfunction_background_concurrent)
    
    # Chaining tests
    runner.run_test("Skfunction chain retry+timeout", test_skfunction_chain_retry_timeout)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
