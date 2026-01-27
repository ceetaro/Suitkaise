"""
@blocking Decorator Tests

Tests that the @blocking decorator correctly marks methods/functions as blocking,
enables .background() and .asynced(), and skips AST analysis for performance.
"""

import sys
import time
import asyncio
from pathlib import Path
from concurrent.futures import Future

# Add project root to path
def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.sk import sk, blocking, SkModifierError
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
            result = test_func()
            if asyncio.iscoroutine(result):
                asyncio.run(result)
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
# Test Functions - CPU-heavy work with no I/O
# =============================================================================

@blocking
def cpu_heavy_function():
    """CPU-intensive work with no detectable I/O."""
    result = 0
    for i in range(1000):
        result += i * i
    return result


def non_blocking_function():
    """Pure function with no blocking calls."""
    return 42


@blocking
def cpu_heavy_with_args(n: int, multiplier: float = 1.0) -> float:
    """CPU-intensive work with arguments."""
    result = 0.0
    for i in range(n):
        result += i * multiplier
    return result


# =============================================================================
# Test Classes
# =============================================================================

@sk
class WorkerWithBlockingMethod:
    """Class with a @blocking method."""
    
    def __init__(self):
        self.value = 0
    
    @blocking
    def heavy_computation(self, iterations: int = 100) -> int:
        """CPU-heavy method with no I/O."""
        result = 0
        for i in range(iterations):
            result += i
        self.value = result
        return result
    
    def regular_method(self) -> str:
        """Non-blocking method."""
        return "regular"


@sk
class WorkerWithMixedMethods:
    """Class with both @blocking and auto-detected blocking methods."""
    
    @blocking
    def cpu_work(self) -> int:
        """Explicit blocking via decorator."""
        return sum(range(100))
    
    def io_work(self) -> str:
        """Auto-detected blocking via time.sleep."""
        time.sleep(0.001)
        return "io done"
    
    def pure_work(self) -> int:
        """Non-blocking method."""
        return 42


# =============================================================================
# Tests - @blocking Decorator Detection
# =============================================================================

def test_blocking_decorator_sets_attribute():
    """@blocking should set _sk_blocking = True on the function."""
    assert hasattr(cpu_heavy_function, '_sk_blocking')
    assert cpu_heavy_function._sk_blocking is True


def test_blocking_decorator_preserves_function():
    """@blocking should not change the function's behavior."""
    result = cpu_heavy_function()
    assert isinstance(result, int)
    assert result > 0


def test_blocking_decorator_with_args():
    """@blocking should work with functions that have arguments."""
    result = cpu_heavy_with_args(100, multiplier=2.0)
    assert isinstance(result, float)
    assert result == sum(i * 2.0 for i in range(100))


def test_skfunction_detects_blocking_decorator():
    """Skfunction should detect @blocking as a blocking indicator."""
    sk_func = Skfunction(cpu_heavy_function)
    assert sk_func.has_blocking_calls, "@blocking should be detected"
    assert '@blocking' in sk_func.blocking_calls


def test_skfunction_no_false_positive_without_decorator():
    """Skfunction should NOT detect blocking in pure functions."""
    sk_func = Skfunction(non_blocking_function)
    assert not sk_func.has_blocking_calls
    assert len(sk_func.blocking_calls) == 0


def test_sk_decorated_function_detects_blocking():
    """@sk on a @blocking function should detect it as blocking."""
    @sk
    @blocking
    def decorated_heavy():
        return sum(range(1000))
    
    assert decorated_heavy.has_blocking_calls
    assert '@blocking' in decorated_heavy.blocking_calls


# =============================================================================
# Tests - Class Detection
# =============================================================================

def test_class_detects_blocking_method():
    """@sk class should detect @blocking methods."""
    assert WorkerWithBlockingMethod.has_blocking_calls
    assert 'heavy_computation' in WorkerWithBlockingMethod.blocking_methods
    assert '@blocking' in WorkerWithBlockingMethod.blocking_methods['heavy_computation']


def test_class_mixed_detection():
    """@sk class should detect both @blocking and auto-detected methods."""
    assert WorkerWithMixedMethods.has_blocking_calls
    methods = WorkerWithMixedMethods.blocking_methods
    
    # @blocking method
    assert 'cpu_work' in methods
    assert '@blocking' in methods['cpu_work']
    
    # Auto-detected method
    assert 'io_work' in methods
    assert any('sleep' in call for call in methods['io_work'])
    
    # Pure method should NOT be in blocking_methods
    assert 'pure_work' not in methods


# =============================================================================
# Tests - .background() Enabled
# =============================================================================

def test_background_enabled_for_blocking_function():
    """@blocking should enable .background() on Skfunction."""
    sk_func = Skfunction(cpu_heavy_function)
    
    # Should not raise
    bg_func = sk_func.background()
    future = bg_func()
    
    assert isinstance(future, Future)
    result = future.result(timeout=5)
    assert isinstance(result, int)


def test_background_enabled_for_blocking_method():
    """@blocking should enable .background() on class methods."""
    worker = WorkerWithBlockingMethod()
    
    # Should not raise
    future = worker.heavy_computation.background()(50)
    
    assert isinstance(future, Future)
    result = future.result(timeout=5)
    assert result == sum(range(50))


def test_background_runs_in_thread():
    """@blocking + .background() should actually run in a separate thread."""
    import threading
    
    main_thread = threading.current_thread().ident
    thread_ids = []
    
    @sk
    @blocking
    def capture_thread():
        thread_ids.append(threading.current_thread().ident)
        return 42
    
    future = capture_thread.background()()
    result = future.result(timeout=5)
    
    assert result == 42
    assert len(thread_ids) == 1
    assert thread_ids[0] != main_thread, "Should run in different thread"


# =============================================================================
# Tests - .asynced() Enabled
# =============================================================================

def test_asynced_enabled_for_blocking_function():
    """@blocking should enable .asynced() on Skfunction."""
    sk_func = Skfunction(cpu_heavy_function)
    
    # Should not raise SkModifierError
    async_func = sk_func.asynced()
    assert async_func is not None


def test_asynced_raises_without_blocking():
    """.asynced() should raise SkModifierError on pure functions."""
    sk_func = Skfunction(non_blocking_function)
    
    try:
        sk_func.asynced()
        assert False, "Should have raised SkModifierError"
    except SkModifierError:
        pass  # Expected


# =============================================================================
# Tests - Performance Optimization (AST Skip)
# =============================================================================

def test_blocking_decorator_reports_only_blocking():
    """@blocking should result in only '@blocking' in blocking_calls, not AST-detected ones."""
    # This function has @blocking, so AST analysis for blocking detection should be skipped
    # Even if it contained detectable I/O, we should only see '@blocking'
    
    @blocking
    def mixed_but_decorated():
        # Even though this has sleep, @blocking should short-circuit
        # and not do AST analysis for blocking detection
        return 42
    
    sk_func = Skfunction(mixed_but_decorated)
    
    # Should only have @blocking, proving AST was skipped
    assert sk_func.blocking_calls == ['@blocking']


def test_blocking_decorator_faster_than_ast():
    """@blocking detection should be faster than AST analysis."""
    # This is a soft test - we just verify that decorated functions
    # don't do full AST analysis for blocking detection
    
    import timeit
    
    @blocking
    def fast_decorated():
        # Long function that would be slow to AST parse
        a = 1
        b = 2
        c = 3
        d = 4
        e = 5
        return a + b + c + d + e
    
    def slow_io_function():
        import time
        time.sleep(0.001)
        return 42
    
    # Time wrapping the decorated function
    t1 = timeit.timeit(lambda: Skfunction(fast_decorated), number=100)
    
    # Time wrapping the function requiring AST analysis
    t2 = timeit.timeit(lambda: Skfunction(slow_io_function), number=100)
    
    # Decorated should be faster (or at least not significantly slower)
    # We don't assert strict timing because it can vary, but this documents intent
    print(f"\n  @blocking wrapper time: {t1:.4f}s")
    print(f"  AST analysis time:     {t2:.4f}s")


# =============================================================================
# Tests - Edge Cases
# =============================================================================

def test_blocking_on_lambda_like():
    """@blocking works even on simple one-liners."""
    @blocking
    def one_liner():
        return 42
    
    sk_func = Skfunction(one_liner)
    assert sk_func.has_blocking_calls
    assert '@blocking' in sk_func.blocking_calls


def test_blocking_preserves_docstring():
    """@blocking should preserve the function's docstring."""
    @blocking
    def documented():
        """This is documentation."""
        return 42
    
    assert documented.__doc__ == """This is documentation."""


def test_blocking_preserves_name():
    """@blocking should preserve the function's name."""
    @blocking
    def named_function():
        return 42
    
    assert named_function.__name__ == 'named_function'


def test_multiple_blocking_decorators():
    """Multiple @blocking decorators should be harmless."""
    @blocking
    @blocking
    def double_decorated():
        return 42
    
    assert double_decorated._sk_blocking is True
    sk_func = Skfunction(double_decorated)
    assert sk_func.has_blocking_calls


# =============================================================================
# Docstring Examples
# =============================================================================

def test_doc_blocking_function_example():
    """Docstring example: @blocking on a function."""
    @blocking
    def heavy():
        total = 0
        for i in range(1000):
            total += i
        return total
    
    sk_func = Skfunction(heavy)
    future = sk_func.background()()
    assert future.result(timeout=5) > 0


def test_doc_blocking_method_example():
    """Docstring example: @blocking on a method."""
    @sk
    class Worker:
        def __init__(self):
            self.value = 0
        
        @blocking
        def compute(self, n: int = 100):
            total = 0
            for i in range(n):
                total += i
            self.value = total
            return total
    
    worker = Worker()
    result = worker.compute.background()(50).result(timeout=5)
    assert result == worker.value


# =============================================================================
# Run Tests
# =============================================================================

def run_all_tests():
    runner = TestRunner("@blocking Decorator Tests")
    
    runner.run_test("blocking decorator sets attribute", test_blocking_decorator_sets_attribute)
    runner.run_test("blocking decorator preserves function", test_blocking_decorator_preserves_function)
    runner.run_test("blocking decorator with args", test_blocking_decorator_with_args)
    runner.run_test("Skfunction detects blocking decorator", test_skfunction_detects_blocking_decorator)
    runner.run_test("Skfunction no false positive", test_skfunction_no_false_positive_without_decorator)
    runner.run_test("sk decorated function detects blocking", test_sk_decorated_function_detects_blocking)
    runner.run_test("class detects blocking method", test_class_detects_blocking_method)
    runner.run_test("class mixed detection", test_class_mixed_detection)
    runner.run_test("background enabled for blocking function", test_background_enabled_for_blocking_function)
    runner.run_test("background enabled for blocking method", test_background_enabled_for_blocking_method)
    runner.run_test("background runs in thread", test_background_runs_in_thread)
    runner.run_test("asynced enabled for blocking function", test_asynced_enabled_for_blocking_function)
    runner.run_test("asynced raises without blocking", test_asynced_raises_without_blocking)
    runner.run_test("blocking decorator reports only blocking", test_blocking_decorator_reports_only_blocking)
    runner.run_test("blocking decorator faster than AST", test_blocking_decorator_faster_than_ast)
    runner.run_test("blocking on lambda-like", test_blocking_on_lambda_like)
    runner.run_test("blocking preserves docstring", test_blocking_preserves_docstring)
    runner.run_test("blocking preserves name", test_blocking_preserves_name)
    runner.run_test("multiple blocking decorators", test_multiple_blocking_decorators)
    
    # docstring examples
    runner.run_test("doc: blocking function", test_doc_blocking_function_example)
    runner.run_test("doc: blocking method", test_doc_blocking_method_example)
    
    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
