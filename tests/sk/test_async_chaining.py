"""
AsyncSkfunction Chaining Tests

Tests AsyncSkfunction chaining:
- asynced().timeout()
- asynced().retry()
- asynced().timeout().retry()
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
# Test Functions
# =============================================================================

def slow_work(duration=0.02):
    """Blocking function for testing."""
    stdlib_time.sleep(duration)
    return "done"


# =============================================================================
# asynced().timeout() Tests
# =============================================================================

def test_asynced_timeout_succeeds():
    """asynced().timeout() should allow fast calls to complete."""
    async def async_test():
        sk_func = Skfunction(slow_work)
        async_with_timeout = sk_func.asynced().timeout(1.0)
        
        result = await async_with_timeout(0.02)
        
        assert result == "done"
    
    asyncio.run(async_test())


def test_asynced_timeout_fails():
    """asynced().timeout() should raise FunctionTimeoutError."""
    async def async_test():
        sk_func = Skfunction(slow_work)
        async_with_timeout = sk_func.asynced().timeout(0.01)
        
        try:
            await async_with_timeout(0.1)
            assert False, "Should have raised FunctionTimeoutError"
        except FunctionTimeoutError:
            pass
    
    asyncio.run(async_test())


# =============================================================================
# asynced().retry() Tests
# =============================================================================

def test_asynced_retry_succeeds():
    """asynced().retry() should retry and succeed."""
    async def async_test():
        attempt_count = [0]
        
        def flaky_slow():
            attempt_count[0] += 1
            stdlib_time.sleep(0.01)
            if attempt_count[0] < 3:
                raise ValueError("fail")
            return "success"
        
        sk_func = Skfunction(flaky_slow)
        async_with_retry = sk_func.asynced().retry(times=5, delay=0.0)
        
        result = await async_with_retry()
        
        assert result == "success"
    
    asyncio.run(async_test())


def test_asynced_retry_fails():
    """asynced().retry() should fail after max attempts."""
    async def async_test():
        def always_fail():
            stdlib_time.sleep(0.01)
            raise ValueError("always fails")
        
        sk_func = Skfunction(always_fail)
        async_with_retry = sk_func.asynced().retry(times=2, delay=0.0)
        
        try:
            await async_with_retry()
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    
    asyncio.run(async_test())


# =============================================================================
# Chain Order Tests
# =============================================================================

def test_asynced_timeout_retry():
    """asynced().timeout().retry() should work."""
    async def async_test():
        attempt_count = [0]
        
        def flaky_slow():
            attempt_count[0] += 1
            stdlib_time.sleep(0.01)
            if attempt_count[0] < 2:
                raise ValueError("fail")
            return "success"
        
        sk_func = Skfunction(flaky_slow)
        # timeout(1s) then retry(3 times)
        chained = sk_func.asynced().timeout(1.0).retry(times=3, delay=0.0)
        
        result = await chained()
        
        assert result == "success"
    
    asyncio.run(async_test())


def test_asynced_retry_timeout():
    """asynced().retry().timeout() should work."""
    async def async_test():
        sk_func = Skfunction(slow_work)
        # retry(3 times) then timeout(1s)
        chained = sk_func.asynced().retry(times=3).timeout(1.0)
        
        result = await chained(0.02)
        
        assert result == "done"
    
    asyncio.run(async_test())


# =============================================================================
# Concurrent Chain Tests
# =============================================================================

def test_asynced_concurrent_with_timeout():
    """Multiple asynced().timeout() calls should run concurrently."""
    async def async_test():
        sk_func = Skfunction(slow_work)
        async_with_timeout = sk_func.asynced().timeout(1.0)
        
        start = stdlib_time.perf_counter()
        
        await asyncio.gather(
            async_with_timeout(0.02),
            async_with_timeout(0.02),
            async_with_timeout(0.02),
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Should be ~20ms (concurrent), not 60ms
        assert elapsed < 0.05, f"Concurrent should be ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all AsyncSkfunction chaining tests."""
    runner = TestRunner("AsyncSkfunction Chaining Tests")
    
    # asynced().timeout() tests
    runner.run_test("asynced().timeout() succeeds", test_asynced_timeout_succeeds)
    runner.run_test("asynced().timeout() fails", test_asynced_timeout_fails)
    
    # asynced().retry() tests
    runner.run_test("asynced().retry() succeeds", test_asynced_retry_succeeds)
    runner.run_test("asynced().retry() fails", test_asynced_retry_fails)
    
    # Chain order tests
    runner.run_test("asynced().timeout().retry()", test_asynced_timeout_retry)
    runner.run_test("asynced().retry().timeout()", test_asynced_retry_timeout)
    
    # Concurrent tests
    runner.run_test("Concurrent asynced().timeout()", test_asynced_concurrent_with_timeout)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
