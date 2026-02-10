"""
Timing Decorator Tests

Tests @timethis decorator:
- Auto-created timers
- Explicit timer
- Threshold filtering
- Multiple decorators
- clear_global_timers()
"""

import sys
import time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.timing import timethis, Sktimer, clear_global_timers


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
# Auto Sktimer Tests
# =============================================================================

def test_timethis_auto_timer():
    """@timethis() should auto-create and attach timer."""
    clear_global_timers()
    
    @timethis()
    def my_func():
        time.sleep(0.01)
        return 42
    
    result = my_func()
    
    assert result == 42, "Function should return normally"
    assert hasattr(my_func, 'timer'), "Should attach .timer attribute"
    assert isinstance(my_func.timer, Sktimer), "Timer should be Sktimer instance"
    assert my_func.timer.num_times == 1, "Should have 1 recorded time"


def test_timethis_auto_timer_accumulates():
    """Auto timer should accumulate across calls."""
    clear_global_timers()
    
    @timethis()
    def my_func():
        time.sleep(0.005)
    
    for _ in range(5):
        my_func()
    
    assert my_func.timer.num_times == 5, f"Should have 5 times, got {my_func.timer.num_times}"


def test_timethis_auto_timer_unique():
    """Each function should get unique auto timer."""
    clear_global_timers()
    
    @timethis()
    def func_a():
        pass
    
    @timethis()
    def func_b():
        pass
    
    func_a()
    func_a()
    func_b()
    
    assert func_a.timer is not func_b.timer, "Functions should have different timers"
    assert func_a.timer.num_times == 2
    assert func_b.timer.num_times == 1


# =============================================================================
# Explicit Sktimer Tests
# =============================================================================

def test_timethis_explicit_timer():
    """@timethis(timer) should use explicit timer."""
    my_timer = Sktimer()
    
    @timethis(my_timer)
    def my_func():
        time.sleep(0.01)
    
    my_func()
    
    assert my_timer.num_times == 1, "Explicit timer should have 1 time"


def test_timethis_explicit_shared():
    """Multiple functions can share explicit timer."""
    shared_timer = Sktimer()
    
    @timethis(shared_timer)
    def func_a():
        time.sleep(0.005)
    
    @timethis(shared_timer)
    def func_b():
        time.sleep(0.005)
    
    func_a()
    func_a()
    func_b()
    
    assert shared_timer.num_times == 3, f"Shared timer should have 3 times, got {shared_timer.num_times}"


def test_timethis_explicit_statistics():
    """Explicit timer should accumulate proper statistics."""
    my_timer = Sktimer()
    
    @timethis(my_timer)
    def variable_work(duration):
        time.sleep(duration)
    
    variable_work(0.01)
    variable_work(0.02)
    variable_work(0.03)
    
    assert my_timer.num_times == 3
    assert my_timer.fastest_time < my_timer.slowest_time


# =============================================================================
# Threshold Tests
# =============================================================================

def test_timethis_threshold_filters():
    """@timethis(threshold=x) should filter short times."""
    clear_global_timers()
    
    @timethis(threshold=0.05)
    def fast_func():
        time.sleep(0.01)  # 10ms < 50ms threshold
    
    fast_func()
    
    assert fast_func.timer.num_times == 0, "Time below threshold should not record"


def test_timethis_threshold_records():
    """@timethis(threshold=x) should record times above threshold."""
    clear_global_timers()
    
    @timethis(threshold=0.01)
    def slow_func():
        time.sleep(0.03)  # 30ms > 10ms threshold
    
    slow_func()
    
    assert slow_func.timer.num_times == 1, "Time above threshold should record"


def test_timethis_threshold_explicit():
    """Threshold should work with explicit timer."""
    my_timer = Sktimer()
    
    @timethis(my_timer, threshold=0.02)
    def work(duration):
        time.sleep(duration)
    
    work(0.01)  # Below threshold - filtered
    work(0.03)  # Above threshold - recorded
    work(0.015)  # Below threshold - filtered
    work(0.04)  # Above threshold - recorded
    
    assert my_timer.num_times == 2, f"Should have 2 recorded, got {my_timer.num_times}"


# =============================================================================
# Return Value / Exception Tests
# =============================================================================

def test_timethis_preserves_return():
    """@timethis should preserve return value."""
    clear_global_timers()
    
    @timethis()
    def returns_value():
        return "hello world"
    
    result = returns_value()
    
    assert result == "hello world", f"Should return original value, got {result}"


def test_timethis_preserves_exception():
    """@timethis should propagate exceptions without recording timing."""
    clear_global_timers()
    
    @timethis()
    def raises_error():
        raise ValueError("test error")
    
    try:
        raises_error()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert str(e) == "test error"
    
    # Time should NOT be recorded on exception (avoid polluting stats)
    assert raises_error.timer.num_times == 0


def test_timethis_preserves_args():
    """@timethis should pass args correctly."""
    clear_global_timers()
    
    @timethis()
    def add(a, b, c=0):
        return a + b + c
    
    result = add(1, 2, c=3)
    
    assert result == 6, f"Should handle args correctly, got {result}"


# =============================================================================
# clear_global_timers Tests
# =============================================================================

def test_clear_global_timers():
    """clear_global_timers() should reset all auto timers."""
    clear_global_timers()
    
    @timethis()
    def my_func():
        pass
    
    my_func()
    my_func()
    
    assert my_func.timer.num_times == 2
    
    # This creates a new timer for subsequent decorations
    clear_global_timers()
    
    # Re-decorate a new function
    @timethis()
    def new_func():
        pass
    
    assert new_func.timer.num_times == 0


# =============================================================================
# Class Method Tests
# =============================================================================

def test_timethis_class_method():
    """@timethis should work on class methods."""
    clear_global_timers()
    
    class MyClass:
        @timethis()
        def my_method(self):
            time.sleep(0.01)
            return "done"
    
    obj = MyClass()
    result = obj.my_method()
    
    assert result == "done"
    assert hasattr(obj.my_method, 'timer') or hasattr(MyClass.my_method, 'timer')


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all decorator tests."""
    runner = TestRunner("@timethis Decorator Tests")
    
    # Auto timer tests
    runner.run_test("@timethis() auto timer", test_timethis_auto_timer)
    runner.run_test("@timethis() auto accumulates", test_timethis_auto_timer_accumulates)
    runner.run_test("@timethis() auto unique", test_timethis_auto_timer_unique)
    
    # Explicit timer tests
    runner.run_test("@timethis(timer) explicit", test_timethis_explicit_timer)
    runner.run_test("@timethis(timer) shared", test_timethis_explicit_shared)
    runner.run_test("@timethis(timer) statistics", test_timethis_explicit_statistics)
    
    # Threshold tests
    runner.run_test("@timethis(threshold) filters", test_timethis_threshold_filters)
    runner.run_test("@timethis(threshold) records", test_timethis_threshold_records)
    runner.run_test("@timethis(timer, threshold)", test_timethis_threshold_explicit)
    
    # Return/exception tests
    runner.run_test("@timethis preserves return", test_timethis_preserves_return)
    runner.run_test("@timethis preserves exception", test_timethis_preserves_exception)
    runner.run_test("@timethis preserves args", test_timethis_preserves_args)
    
    # clear_global_timers tests
    runner.run_test("clear_global_timers()", test_clear_global_timers)
    
    # Class method tests
    runner.run_test("@timethis on class method", test_timethis_class_method)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
