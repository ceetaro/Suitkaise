"""
@sk Decorator Tests

Tests the @sk decorator that auto-wraps classes and functions.
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

from suitkaise.sk import sk, Skclass, Skfunction, SkModifierError


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
# @sk on Classes Tests
# =============================================================================

def test_sk_on_class():
    """@sk should return the original class with attributes attached."""
    @sk
    class Counter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
    
    # Counter is still a class (type), not a wrapper
    assert isinstance(Counter, type)
    # But has sk attributes attached
    assert hasattr(Counter, '_shared_meta')
    assert hasattr(Counter, 'has_blocking_calls')
    assert hasattr(Counter, 'asynced')


def test_sk_class_instantiation():
    """@sk class should allow creating instances."""
    @sk
    class Counter:
        def __init__(self, start=0):
            self.value = start
        
        def increment(self):
            self.value += 1
    
    counter = Counter(start=5)
    
    assert counter.value == 5
    counter.increment()
    assert counter.value == 6


def test_sk_class_has_shared_meta():
    """@sk class should have _shared_meta."""
    @sk
    class Counter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
    
    assert hasattr(Counter, '_shared_meta')


def test_sk_class_with_blocking():
    """@sk class with blocking calls should support asynced()."""
    @sk
    class SlowCounter:
        def __init__(self):
            self.value = 0
        
        def slow_increment(self):
            stdlib_time.sleep(0.01)
            self.value += 1
    
    # has_blocking_calls is now a class attribute (not property on Skclass)
    assert SlowCounter.has_blocking_calls == True
    # asynced is now a staticmethod on the class
    AsyncCounter = SlowCounter.asynced()
    assert AsyncCounter is not None


def test_sk_class_without_blocking():
    """@sk class without blocking should raise on asynced()."""
    @sk
    class FastCounter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
    
    # has_blocking_calls is now a class attribute
    assert FastCounter.has_blocking_calls == False
    
    # asynced() should raise SkModifierError
    try:
        FastCounter.asynced()
        assert False, "Should have raised SkModifierError"
    except SkModifierError:
        pass


def test_sk_class_method_modifiers_sync():
    """@sk class should expose modifiers on sync methods."""
    @sk
    class Worker:
        def __init__(self):
            self.calls = 0
        
        def work(self):
            return "ok"
        
        def flaky(self):
            self.calls += 1
            if self.calls < 3:
                raise ValueError("fail")
            return "ok"
        
        def with_timeout_param(self, timeout=None):
            return timeout
    
    worker = Worker()
    
    # retry
    worker.calls = 0
    assert worker.flaky.retry(times=3)() == "ok"
    
    # timeout
    assert worker.work.timeout(1.0)() == "ok"
    
    # background
    future = worker.work.background()()
    assert future.result() == "ok"
    
    # asynced
    result = asyncio.run(worker.work.asynced()())
    assert result == "ok"
    
    # timeout param disables modifier
    try:
        worker.with_timeout_param.timeout(1.0)()
        assert False, "Should have raised SkModifierError"
    except SkModifierError:
        pass


def test_sk_class_method_modifiers_async():
    """@sk class should expose modifiers on async methods."""
    @sk
    class AsyncWorker:
        def __init__(self):
            self.calls = 0
        
        async def work(self):
            await asyncio.sleep(0)
            return "ok"
        
        async def flaky(self):
            self.calls += 1
            if self.calls < 3:
                raise ValueError("fail")
            return "ok"
    
    worker = AsyncWorker()
    
    async def run_checks():
        # asynced (no-op for async)
        assert await worker.work.asynced()() == "ok"
        
        # timeout
        assert await worker.work.timeout(1.0)() == "ok"
        
        # retry
        worker.calls = 0
        assert await worker.flaky.retry(times=3)() == "ok"
        
        # background returns Task
        task = worker.work.background()()
        assert await task == "ok"
    
    asyncio.run(run_checks())


# =============================================================================
# @sk on Functions Tests
# =============================================================================

def test_sk_on_function():
    """@sk should return the original function with attributes attached."""
    @sk
    def add(a, b):
        return a + b
    
    # add is still a function, not a wrapper
    assert callable(add)
    # But has sk attributes attached
    assert hasattr(add, 'has_blocking_calls')
    assert hasattr(add, 'asynced')
    assert hasattr(add, 'retry')
    assert hasattr(add, 'timeout')
    assert hasattr(add, 'background')


def test_sk_function_call():
    """@sk function should be callable."""
    @sk
    def add(a, b):
        return a + b
    
    result = add(1, 2)
    
    assert result == 3


def test_sk_function_has_blocking():
    """@sk function with blocking should support asynced()."""
    @sk
    def slow_work():
        stdlib_time.sleep(0.01)
        return "done"
    
    assert slow_work.has_blocking_calls == True


def test_sk_function_asynced():
    """@sk function should support asynced() if blocking."""
    async def async_test():
        @sk
        def slow_work():
            stdlib_time.sleep(0.02)
            return "done"
        
        async_slow = slow_work.asynced()
        result = await async_slow()
        
        assert result == "done"
    
    asyncio.run(async_test())


def test_sk_function_retry():
    """@sk function should support retry()."""
    attempt_count = [0]
    
    @sk
    def flaky():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise ValueError("fail")
        return "success"
    
    result = flaky.retry(times=5, delay=0.0)()
    
    assert result == "success"


def test_sk_function_timeout():
    """@sk function should support timeout()."""
    @sk
    def slow_work():
        stdlib_time.sleep(0.02)
        return "done"
    
    result = slow_work.timeout(1.0)()
    
    assert result == "done"


def test_sk_function_background():
    """@sk function should support background()."""
    @sk
    def slow_work():
        stdlib_time.sleep(0.02)
        return "done"
    
    future = slow_work.background()()
    result = future.result()
    
    assert result == "done"


# =============================================================================
# Error Cases
# =============================================================================

def test_sk_on_invalid():
    """@sk should raise TypeError on non-class/function."""
    try:
        sk("not a class or function")
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "can only decorate classes or functions" in str(e)


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all @sk decorator tests."""
    runner = TestRunner("@sk Decorator Tests")
    
    # Class tests
    runner.run_test("@sk on class", test_sk_on_class)
    runner.run_test("@sk class instantiation", test_sk_class_instantiation)
    runner.run_test("@sk class has _shared_meta", test_sk_class_has_shared_meta)
    runner.run_test("@sk class with blocking", test_sk_class_with_blocking)
    runner.run_test("@sk class without blocking", test_sk_class_without_blocking)
    runner.run_test("@sk class method modifiers (sync)", test_sk_class_method_modifiers_sync)
    runner.run_test("@sk class method modifiers (async)", test_sk_class_method_modifiers_async)
    
    # Function tests
    runner.run_test("@sk on function", test_sk_on_function)
    runner.run_test("@sk function call", test_sk_function_call)
    runner.run_test("@sk function has blocking", test_sk_function_has_blocking)
    runner.run_test("@sk function asynced", test_sk_function_asynced)
    runner.run_test("@sk function retry", test_sk_function_retry)
    runner.run_test("@sk function timeout", test_sk_function_timeout)
    runner.run_test("@sk function background", test_sk_function_background)
    
    # Error cases
    runner.run_test("@sk on invalid", test_sk_on_invalid)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
