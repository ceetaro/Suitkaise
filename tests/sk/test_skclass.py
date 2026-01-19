"""
Skclass Tests

Tests Skclass wrapper functionality:
- Auto _shared_meta generation
- Blocking call detection
- .asynced() for classes with blocking calls
- SkModifierError for non-blocking classes
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

from suitkaise.sk import Skclass, SkModifierError


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
# Test Classes
# =============================================================================

class SimpleCounter:
    """A simple class with no blocking calls."""
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1
    
    def decrement(self):
        self.value -= 1
    
    def get_value(self):
        return self.value


class SlowWorker:
    """A class with blocking calls."""
    def __init__(self):
        self.result = None
    
    def slow_work(self):
        """Does slow blocking work."""
        stdlib_time.sleep(0.02)  # 20ms
        self.result = "done"
        return self.result
    
    def fast_work(self):
        """Does fast non-blocking work."""
        self.result = "fast"
        return self.result


class MultiAttrClass:
    """A class with various attribute patterns."""
    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0
    
    def set_x(self):
        self.x = 1
    
    def set_y(self):
        self.y = 2
    
    def set_all(self):
        self.x = 1
        self.y = 2
        self.z = 3
    
    def read_all(self):
        return self.x + self.y + self.z


# =============================================================================
# Basic Skclass Tests
# =============================================================================

def test_skclass_creation():
    """Skclass should wrap a class."""
    SkCounter = Skclass(SimpleCounter)
    
    assert SkCounter is not None
    assert repr(SkCounter) == "Skclass(SimpleCounter)"


def test_skclass_instantiation():
    """Skclass should allow creating instances."""
    SkCounter = Skclass(SimpleCounter)
    
    counter = SkCounter()
    
    assert counter.value == 0
    counter.increment()
    assert counter.value == 1


def test_skclass_shared_meta_generated():
    """Skclass should generate _shared_meta."""
    SkCounter = Skclass(SimpleCounter)
    
    assert hasattr(SkCounter, '_shared_meta')
    meta = SkCounter._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta


def test_skclass_shared_meta_on_original():
    """_shared_meta should also be attached to original class."""
    SkCounter = Skclass(SimpleCounter)
    
    # Check that original class also has _shared_meta
    assert hasattr(SimpleCounter, '_shared_meta')


def test_skclass_shared_meta_methods():
    """_shared_meta should include methods."""
    SkMulti = Skclass(MultiAttrClass)
    
    meta = SkMulti._shared_meta
    methods = meta['methods']
    
    assert 'set_x' in methods
    assert 'set_y' in methods
    assert 'set_all' in methods
    assert 'read_all' in methods


def test_skclass_shared_meta_writes():
    """_shared_meta should detect write attributes."""
    SkMulti = Skclass(MultiAttrClass)
    
    meta = SkMulti._shared_meta
    
    # set_x writes to x
    assert 'x' in meta['methods']['set_x'].get('writes', [])
    
    # set_all writes to x, y, z
    set_all_writes = meta['methods']['set_all'].get('writes', [])
    assert 'x' in set_all_writes
    assert 'y' in set_all_writes
    assert 'z' in set_all_writes


# =============================================================================
# Blocking Detection Tests
# =============================================================================

def test_skclass_no_blocking():
    """Skclass should detect no blocking calls in SimpleCounter."""
    SkCounter = Skclass(SimpleCounter)
    
    assert SkCounter.has_blocking_calls == False
    assert len(SkCounter.blocking_methods) == 0


def test_skclass_has_blocking():
    """Skclass should detect blocking calls in SlowWorker."""
    SkWorker = Skclass(SlowWorker)
    
    assert SkWorker.has_blocking_calls == True
    assert len(SkWorker.blocking_methods) > 0
    assert 'slow_work' in SkWorker.blocking_methods


def test_skclass_blocking_methods():
    """blocking_methods should list the blocking methods."""
    SkWorker = Skclass(SlowWorker)
    
    blocking = SkWorker.blocking_methods
    
    # slow_work has time.sleep
    assert 'slow_work' in blocking
    # fast_work has no blocking calls
    assert 'fast_work' not in blocking


# =============================================================================
# asynced() Tests
# =============================================================================

def test_skclass_asynced_raises_for_non_blocking():
    """asynced() should raise SkModifierError for non-blocking class."""
    SkCounter = Skclass(SimpleCounter)
    
    try:
        SkCounter.asynced()
        assert False, "Should have raised SkModifierError"
    except SkModifierError as e:
        assert "SimpleCounter" in str(e)
        assert "no blocking calls" in str(e)


def test_skclass_asynced_works_for_blocking():
    """asynced() should return async class for blocking class."""
    SkWorker = Skclass(SlowWorker)
    
    AsyncWorker = SkWorker.asynced()
    
    assert AsyncWorker is not None


def test_skclass_asynced_cached():
    """asynced() should cache the async class."""
    SkWorker = Skclass(SlowWorker)
    
    AsyncWorker1 = SkWorker.asynced()
    AsyncWorker2 = SkWorker.asynced()
    
    assert AsyncWorker1 is AsyncWorker2


def test_skclass_async_methods_work():
    """Async class methods should work in async context."""
    async def async_test():
        SkWorker = Skclass(SlowWorker)
        AsyncWorker = SkWorker.asynced()
        
        worker = AsyncWorker()
        
        start = stdlib_time.perf_counter()
        result = await worker.slow_work()
        elapsed = stdlib_time.perf_counter() - start
        
        assert result == "done"
        assert elapsed >= 0.018, f"Should take ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


def test_skclass_async_non_blocking_methods():
    """Non-blocking methods should still work (sync) in async class."""
    async def async_test():
        SkWorker = Skclass(SlowWorker)
        AsyncWorker = SkWorker.asynced()
        
        worker = AsyncWorker()
        
        # fast_work is not blocking, should work normally
        result = worker.fast_work()
        
        assert result == "fast"
    
    asyncio.run(async_test())


def test_skclass_async_concurrent():
    """Async methods should run concurrently."""
    async def async_test():
        SkWorker = Skclass(SlowWorker)
        AsyncWorker = SkWorker.asynced()
        
        workers = [AsyncWorker() for _ in range(3)]
        
        start = stdlib_time.perf_counter()
        
        await asyncio.gather(
            workers[0].slow_work(),
            workers[1].slow_work(),
            workers[2].slow_work(),
        )
        
        elapsed = stdlib_time.perf_counter() - start
        
        # Should complete in ~20ms (concurrent), not 60ms (sequential)
        assert elapsed < 0.05, f"Concurrent should be ~20ms, got {elapsed}"
    
    asyncio.run(async_test())


# =============================================================================
# Forward Attributes Tests
# =============================================================================

def test_skclass_forwards_class_attrs():
    """Skclass should forward class attribute access."""
    class WithClassAttr:
        CLASS_CONST = 42
        
        def method(self):
            pass
    
    SkClass = Skclass(WithClassAttr)
    
    assert SkClass.CLASS_CONST == 42


def test_skclass_forwards_docstring():
    """Skclass should preserve original class info."""
    SkCounter = Skclass(SimpleCounter)
    
    # Can access original class
    assert SkCounter._original_class is SimpleCounter


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Skclass tests."""
    runner = TestRunner("Skclass Tests")
    
    # Basic tests
    runner.run_test("Skclass creation", test_skclass_creation)
    runner.run_test("Skclass instantiation", test_skclass_instantiation)
    runner.run_test("Skclass _shared_meta generated", test_skclass_shared_meta_generated)
    runner.run_test("Skclass _shared_meta on original", test_skclass_shared_meta_on_original)
    runner.run_test("Skclass _shared_meta methods", test_skclass_shared_meta_methods)
    runner.run_test("Skclass _shared_meta writes", test_skclass_shared_meta_writes)
    
    # Blocking detection tests
    runner.run_test("Skclass no blocking", test_skclass_no_blocking)
    runner.run_test("Skclass has blocking", test_skclass_has_blocking)
    runner.run_test("Skclass blocking_methods", test_skclass_blocking_methods)
    
    # asynced() tests
    runner.run_test("Skclass asynced raises for non-blocking", test_skclass_asynced_raises_for_non_blocking)
    runner.run_test("Skclass asynced works for blocking", test_skclass_asynced_works_for_blocking)
    runner.run_test("Skclass asynced cached", test_skclass_asynced_cached)
    runner.run_test("Skclass async methods work", test_skclass_async_methods_work)
    runner.run_test("Skclass async non-blocking methods", test_skclass_async_non_blocking_methods)
    runner.run_test("Skclass async concurrent", test_skclass_async_concurrent)
    
    # Forward attributes tests
    runner.run_test("Skclass forwards class attrs", test_skclass_forwards_class_attrs)
    runner.run_test("Skclass forwards docstring", test_skclass_forwards_docstring)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
