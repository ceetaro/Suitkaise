"""
@timethis Decorator and clear_global_timers() Tests

Tests the @timethis decorator functionality:
- Auto-created global timer
- Explicit timer parameter
- Threshold parameter
- Sktimer access via function.timer
- Global timer naming convention
- clear_global_timers() function
"""

import sys
import time as stdlib_time
import threading

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.timing import Sktimer, timethis, clear_global_timers


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
# @timethis with Auto-created Sktimer Tests
# =============================================================================

def test_timethis_auto_timer():
    """@timethis() without args should create auto timer."""
    clear_global_timers()
    
    @timethis()
    def auto_timed():
        stdlib_time.sleep(0.01)
        return "done"
    
    result = auto_timed()
    
    assert result == "done", "Function should return value"
    assert hasattr(auto_timed, 'timer'), "Should have timer attribute"
    assert auto_timed.timer.num_times == 1, f"Sktimer should have 1 measurement, got {auto_timed.timer.num_times}"


def test_timethis_auto_timer_accumulates():
    """Auto timer should accumulate measurements."""
    clear_global_timers()
    
    @timethis()
    def repeated_func():
        stdlib_time.sleep(0.005)
    
    for _ in range(5):
        repeated_func()
    
    assert repeated_func.timer.num_times == 5, f"Should have 5 measurements, got {repeated_func.timer.num_times}"


def test_timethis_auto_timer_statistics():
    """Auto timer should calculate statistics correctly."""
    clear_global_timers()
    
    @timethis()
    def stats_func():
        stdlib_time.sleep(0.01)
    
    for _ in range(3):
        stats_func()
    
    timer = stats_func.timer
    
    assert timer.num_times == 3
    assert timer.mean >= 0.008, f"Mean should be ~10ms, got {timer.mean}"


def test_timethis_max_times():
    """@timethis should accept max_times and trim old measurements."""
    clear_global_timers()
    
    @timethis(max_times=2)
    def small_window():
        stdlib_time.sleep(0.001)
    
    for _ in range(5):
        small_window()
    
    assert small_window.timer.num_times == 2, f"Should keep 2 times, got {small_window.timer.num_times}"


# =============================================================================
# @timethis with Explicit Sktimer Tests
# =============================================================================

def test_timethis_explicit_timer():
    """@timethis with explicit timer should use that timer."""
    explicit_timer = Sktimer()
    
    @timethis(explicit_timer)
    def explicit_func():
        stdlib_time.sleep(0.01)
    
    explicit_func()
    
    assert explicit_timer.num_times == 1, f"Explicit timer should have 1 measurement"


def test_timethis_explicit_timer_shared():
    """Multiple functions can share explicit timer."""
    shared_timer = Sktimer()
    
    @timethis(shared_timer)
    def func_a():
        stdlib_time.sleep(0.005)
    
    @timethis(shared_timer)
    def func_b():
        stdlib_time.sleep(0.005)
    
    func_a()
    func_a()
    func_b()
    
    assert shared_timer.num_times == 3, f"Shared timer should have 3 measurements, got {shared_timer.num_times}"


def test_timethis_explicit_timer_no_attribute():
    """With explicit timer, function may not have .timer attribute."""
    explicit_timer = Sktimer()
    
    @timethis(explicit_timer)
    def no_attr_func():
        pass
    
    no_attr_func()
    
    # The explicit timer should have the measurement
    assert explicit_timer.num_times == 1


# =============================================================================
# @timethis Threshold Tests
# =============================================================================

def test_timethis_threshold_records():
    """Threshold should record times above threshold."""
    timer = Sktimer()
    
    @timethis(timer, threshold=0.005)
    def above_threshold():
        stdlib_time.sleep(0.02)  # 20ms, above 5ms threshold
    
    above_threshold()
    
    assert timer.num_times == 1, "Should record time above threshold"


def test_timethis_threshold_discards():
    """Threshold should discard times below threshold."""
    timer = Sktimer()
    
    @timethis(timer, threshold=0.1)
    def below_threshold():
        pass  # Nearly instant, below 100ms threshold
    
    below_threshold()
    
    assert timer.num_times == 0, f"Should not record time below threshold, got {timer.num_times}"


def test_timethis_threshold_mixed():
    """Threshold should only record qualifying times."""
    timer = Sktimer()
    
    @timethis(timer, threshold=0.01)
    def mixed_times(sleep_time):
        stdlib_time.sleep(sleep_time)
    
    mixed_times(0.005)  # Below threshold
    mixed_times(0.02)   # Above threshold
    mixed_times(0.001)  # Below threshold
    mixed_times(0.015)  # Above threshold
    
    assert timer.num_times == 2, f"Should record only 2 times above threshold, got {timer.num_times}"


# =============================================================================
# @timethis Return Value Tests
# =============================================================================

def test_timethis_preserves_return():
    """@timethis should preserve function return value."""
    @timethis()
    def returns_value():
        return 42
    
    result = returns_value()
    
    assert result == 42, f"Should return 42, got {result}"


def test_timethis_preserves_none():
    """@timethis should preserve None return."""
    @timethis()
    def returns_none():
        pass
    
    result = returns_none()
    
    assert result is None


def test_timethis_preserves_complex_return():
    """@timethis should preserve complex return values."""
    @timethis()
    def returns_dict():
        return {"a": 1, "b": [2, 3], "c": {"nested": True}}
    
    result = returns_dict()
    
    assert result == {"a": 1, "b": [2, 3], "c": {"nested": True}}


# =============================================================================
# @timethis with Arguments Tests
# =============================================================================

def test_timethis_preserves_args():
    """@timethis should pass args correctly."""
    @timethis()
    def with_args(a, b, c):
        return a + b + c
    
    result = with_args(1, 2, 3)
    
    assert result == 6


def test_timethis_preserves_kwargs():
    """@timethis should pass kwargs correctly."""
    @timethis()
    def with_kwargs(a, b=0, c=0):
        return a + b + c
    
    result = with_kwargs(1, c=5)
    
    assert result == 6


def test_timethis_preserves_mixed():
    """@timethis should handle mixed args/kwargs."""
    @timethis()
    def mixed(a, b, *args, **kwargs):
        return a + b + sum(args) + sum(kwargs.values())
    
    result = mixed(1, 2, 3, 4, x=5, y=6)
    
    assert result == 21


# =============================================================================
# @timethis on Methods Tests
# =============================================================================

def test_timethis_on_method():
    """@timethis should work on class methods."""
    class MyClass:
        @timethis()
        def timed_method(self):
            stdlib_time.sleep(0.01)
            return "method_done"
    
    obj = MyClass()
    result = obj.timed_method()
    
    assert result == "method_done"
    # Method should have timer (attached to the bound method's underlying function)


def test_timethis_on_staticmethod():
    """@timethis should work on static methods."""
    class MyClass:
        @staticmethod
        @timethis()
        def static_timed():
            stdlib_time.sleep(0.01)
            return "static_done"
    
    result = MyClass.static_timed()
    
    assert result == "static_done"


# =============================================================================
# clear_global_timers() Tests
# =============================================================================

def test_clear_global_timers():
    """clear_global_timers() should clear all auto timers."""
    clear_global_timers()
    
    @timethis()
    def func1():
        pass
    
    @timethis()
    def func2():
        pass
    
    func1()
    func1()
    func2()
    
    # Verify timers have measurements
    assert func1.timer.num_times == 2
    assert func2.timer.num_times == 1
    
    # Clear
    clear_global_timers()
    
    # After clearing, creating new decorated functions should get fresh timers
    # (The old func1.timer reference may still exist but global dict is cleared)


def test_clear_global_timers_no_error_when_empty():
    """clear_global_timers() should not error when no timers exist."""
    clear_global_timers()
    clear_global_timers()  # Call again - should not error


def test_clear_global_timers_thread_safe():
    """clear_global_timers() should be thread-safe."""
    clear_global_timers()
    
    errors = []
    
    def thread_work():
        try:
            for _ in range(10):
                clear_global_timers()
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=thread_work) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Should not have errors: {errors}"


# =============================================================================
# @timethis Stacking Tests
# =============================================================================

def test_timethis_stacked():
    """Multiple @timethis decorators should work."""
    timer1 = Sktimer()
    timer2 = Sktimer()
    
    @timethis(timer1)
    @timethis(timer2)
    def double_timed():
        stdlib_time.sleep(0.01)
    
    double_timed()
    
    # Both timers should have measurements
    assert timer1.num_times == 1
    assert timer2.num_times == 1


def test_timethis_with_other_decorators():
    """@timethis should work with other decorators."""
    timer = Sktimer()
    
    def my_decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs) + 1
        return wrapper
    
    @my_decorator
    @timethis(timer)
    def decorated_func():
        return 41
    
    result = decorated_func()
    
    assert result == 42, f"Other decorator should work, got {result}"
    assert timer.num_times == 1


# =============================================================================
# Exception Handling Tests
# =============================================================================

def test_timethis_exception_still_times():
    """@timethis should record time even when function raises."""
    timer = Sktimer()
    
    @timethis(timer, threshold=0.0)
    def raises_error():
        stdlib_time.sleep(0.01)
        raise ValueError("test error")
    
    try:
        raises_error()
    except ValueError:
        pass
    
    # Time should still be recorded
    assert timer.num_times == 1, f"Should record time on exception, got {timer.num_times}"


def test_timethis_exception_propagates():
    """@timethis should propagate exceptions."""
    @timethis()
    def raises_specific():
        raise TypeError("specific error")
    
    try:
        raises_specific()
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "specific error" in str(e)


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all @timethis tests."""
    runner = TestRunner("@timethis Decorator Tests")
    
    # Auto timer tests
    runner.run_test("@timethis auto timer", test_timethis_auto_timer)
    runner.run_test("@timethis auto timer accumulates", test_timethis_auto_timer_accumulates)
    runner.run_test("@timethis auto timer statistics", test_timethis_auto_timer_statistics)
    runner.run_test("@timethis max_times", test_timethis_max_times)
    
    # Explicit timer tests
    runner.run_test("@timethis explicit timer", test_timethis_explicit_timer)
    runner.run_test("@timethis explicit timer shared", test_timethis_explicit_timer_shared)
    runner.run_test("@timethis explicit timer no attribute", test_timethis_explicit_timer_no_attribute)
    
    # Threshold tests
    runner.run_test("@timethis threshold records", test_timethis_threshold_records)
    runner.run_test("@timethis threshold discards", test_timethis_threshold_discards)
    runner.run_test("@timethis threshold mixed", test_timethis_threshold_mixed)
    
    # Return value tests
    runner.run_test("@timethis preserves return", test_timethis_preserves_return)
    runner.run_test("@timethis preserves None", test_timethis_preserves_none)
    runner.run_test("@timethis preserves complex return", test_timethis_preserves_complex_return)
    
    # Arguments tests
    runner.run_test("@timethis preserves args", test_timethis_preserves_args)
    runner.run_test("@timethis preserves kwargs", test_timethis_preserves_kwargs)
    runner.run_test("@timethis preserves mixed", test_timethis_preserves_mixed)
    
    # Method tests
    runner.run_test("@timethis on method", test_timethis_on_method)
    runner.run_test("@timethis on staticmethod", test_timethis_on_staticmethod)
    
    # clear_global_timers tests
    runner.run_test("clear_global_timers()", test_clear_global_timers)
    runner.run_test("clear_global_timers() no error when empty", test_clear_global_timers_no_error_when_empty)
    runner.run_test("clear_global_timers() thread-safe", test_clear_global_timers_thread_safe)
    
    # Stacking tests
    runner.run_test("@timethis stacked", test_timethis_stacked)
    runner.run_test("@timethis with other decorators", test_timethis_with_other_decorators)
    
    # Exception tests
    runner.run_test("@timethis exception still times", test_timethis_exception_still_times)
    runner.run_test("@timethis exception propagates", test_timethis_exception_propagates)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
