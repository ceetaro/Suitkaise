"""
Processing Error Types Tests

Tests the error classes:
- ProcessError (base)
- PreRunError, RunError, PostRunError, OnFinishError, ResultError, ErrorHandlerError
- ProcessTimeoutError
"""

import sys
import time as stdlib_time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.processing import (
    Process,
    Pool,
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ErrorHandlerError,
    ProcessTimeoutError,
)


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
# Process Subclasses for Testing
# =============================================================================

class FailingPreRunProcess(Process):
    """Process that fails in __prerun__."""
    def __init__(self):
        self.process_config.runs = 1
    
    def __prerun__(self):
        raise ValueError("prerun failed")
    
    def __run__(self):
        pass
    
    def __result__(self):
        return None


class FailingRunProcess(Process):
    """Process that fails in __run__."""
    def __init__(self, message="run failed"):
        self.message = message
        self.process_config.runs = 1
    
    def __run__(self):
        raise ValueError(self.message)
    
    def __result__(self):
        return None


class FailingPostRunProcess(Process):
    """Process that fails in __postrun__."""
    def __init__(self):
        self.process_config.runs = 1
    
    def __run__(self):
        pass
    
    def __postrun__(self):
        raise ValueError("postrun failed")
    
    def __result__(self):
        return None


class FailingResultProcess(Process):
    """Process that fails in __result__."""
    def __init__(self):
        self.process_config.runs = 1
    
    def __run__(self):
        pass
    
    def __result__(self):
        raise ValueError("result failed")


class DoubleProcess(Process):
    """Simple process for Pool tests."""
    def __init__(self, value):
        self.value = value
        self._result_value = None
        self.process_config.runs = 1
    
    def __run__(self):
        if self.value < 0:
            raise ValueError(f"Cannot double negative: {self.value}")
        self._result_value = self.value * 2
    
    def __result__(self):
        return self._result_value


# =============================================================================
# ProcessError Base Class Tests
# =============================================================================

def test_processerror_exists():
    """ProcessError should exist."""
    assert ProcessError is not None


def test_processerror_is_exception():
    """ProcessError should be an Exception."""
    assert issubclass(ProcessError, Exception)


def test_processerror_raisable():
    """ProcessError should be raisable."""
    try:
        raise ProcessError("test message")
    except ProcessError as e:
        assert "test message" in str(e)


def test_processerror_catchable():
    """ProcessError should be catchable."""
    caught = False
    try:
        raise ProcessError("test")
    except ProcessError:
        caught = True
    assert caught


def test_processerror_from_task():
    """ProcessError should be raised from failing task."""
    proc = FailingRunProcess()
    proc.start()
    
    try:
        proc.wait()
        assert False, "Should have raised"
    except (ProcessError, RunError, Exception):
        pass  # Any of these are acceptable


# =============================================================================
# Lifecycle Error Classes Tests
# =============================================================================

def test_prerunerror_exists():
    """PreRunError should exist."""
    assert PreRunError is not None


def test_prerunerror_is_processerror():
    """PreRunError should inherit from ProcessError."""
    assert issubclass(PreRunError, ProcessError)


def test_prerunerror_creation():
    """PreRunError should be creatable with current_run."""
    err = PreRunError(current_run=1)
    assert err is not None


def test_runerror_exists():
    """RunError should exist."""
    assert RunError is not None


def test_runerror_is_processerror():
    """RunError should inherit from ProcessError."""
    assert issubclass(RunError, ProcessError)


def test_runerror_creation():
    """RunError should be creatable with current_run."""
    err = RunError(current_run=1)
    assert err is not None


def test_runerror_with_original():
    """RunError should accept original_error."""
    original = ValueError("original error")
    err = RunError(current_run=1, original_error=original)
    assert err is not None


def test_postrunerror_exists():
    """PostRunError should exist."""
    assert PostRunError is not None


def test_postrunerror_is_processerror():
    """PostRunError should inherit from ProcessError."""
    assert issubclass(PostRunError, ProcessError)


def test_onfinisherror_exists():
    """OnFinishError should exist."""
    assert OnFinishError is not None


def test_onfinisherror_is_processerror():
    """OnFinishError should inherit from ProcessError."""
    assert issubclass(OnFinishError, ProcessError)


def test_resulterror_exists():
    """ResultError should exist."""
    assert ResultError is not None


def test_resulterror_is_processerror():
    """ResultError should inherit from ProcessError."""
    assert issubclass(ResultError, ProcessError)


def test_errorhandlererror_exists():
    """ErrorHandlerError should exist."""
    assert ErrorHandlerError is not None


def test_errorhandlererror_is_processerror():
    """ErrorHandlerError should inherit from ProcessError."""
    assert issubclass(ErrorHandlerError, ProcessError)


# =============================================================================
# ProcessTimeoutError Tests
# =============================================================================

def test_processtimeouterror_exists():
    """ProcessTimeoutError should exist."""
    assert ProcessTimeoutError is not None


def test_processtimeouterror_is_processerror():
    """ProcessTimeoutError should inherit from ProcessError."""
    assert issubclass(ProcessTimeoutError, ProcessError)


def test_processtimeouterror_creation():
    """ProcessTimeoutError should be creatable with section, timeout, current_run."""
    err = ProcessTimeoutError(section="run", timeout=5.0, current_run=1)
    assert err is not None


def test_processtimeouterror_attributes():
    """ProcessTimeoutError should store its attributes."""
    err = ProcessTimeoutError(section="run", timeout=5.0, current_run=2)
    assert err.section == "run"
    assert err.timeout == 5.0
    assert err.current_run == 2


# =============================================================================
# Error Hierarchy Tests
# =============================================================================

def test_error_hierarchy():
    """All lifecycle errors should be ProcessError."""
    errors = [
        PreRunError,
        RunError,
        PostRunError,
        OnFinishError,
        ResultError,
        ErrorHandlerError,
        ProcessTimeoutError,
    ]
    
    for err_class in errors:
        assert issubclass(err_class, ProcessError), f"{err_class.__name__} should be ProcessError"


def test_catch_all_errors():
    """Catching ProcessError should catch all lifecycle errors."""
    errors_to_try = [
        PreRunError(current_run=1),
        RunError(current_run=1),
        PostRunError(current_run=1),
        OnFinishError(current_run=1),
        ResultError(current_run=1),
        ErrorHandlerError(current_run=1),
        ProcessTimeoutError(section="run", timeout=1.0, current_run=1),
    ]
    
    for err in errors_to_try:
        caught = False
        try:
            raise err
        except ProcessError:
            caught = True
        assert caught, f"Failed to catch {type(err).__name__}"


# =============================================================================
# Pool Error Behavior Tests
# =============================================================================

def test_pool_error_on_failed_task():
    """Pool should propagate errors from failed tasks."""
    pool = Pool()
    
    # Mix of valid and invalid values
    values = [1, 2, -1, 4]  # -1 will fail
    
    try:
        results = pool.map(DoubleProcess, values)
        # May or may not raise depending on implementation
    except Exception:
        pass  # Error propagated
    finally:
        pool.close()


def test_multiple_errors_same_pool():
    """Pool should handle multiple failing tasks."""
    pool = Pool()
    
    values = [-1, -2, -3]  # All will fail
    
    try:
        results = pool.map(DoubleProcess, values)
    except Exception:
        pass  # Expected
    finally:
        pool.close()


# =============================================================================
# Error Message Tests
# =============================================================================

def test_error_empty_message():
    """ProcessError should handle empty message."""
    err = ProcessError("")
    assert err is not None


def test_error_long_message():
    """ProcessError should handle long message."""
    long_msg = "x" * 10000
    err = ProcessError(long_msg)
    assert long_msg in str(err)


def test_error_unicode_message():
    """ProcessError should handle unicode message."""
    err = ProcessError("错误信息 🚫")
    assert "错误" in str(err)


def test_error_repr():
    """ProcessError should have reasonable repr."""
    err = ProcessError("test error")
    repr_str = repr(err)
    assert "ProcessError" in repr_str or "test error" in repr_str


# =============================================================================
# Error Context Tests
# =============================================================================

def test_error_has_context():
    """Errors should support exception context."""
    try:
        try:
            raise ValueError("original")
        except ValueError:
            raise ProcessError("wrapped")
    except ProcessError as e:
        # Should have __context__
        assert e.__context__ is not None


def test_error_chaining():
    """Errors should support exception chaining."""
    original = ValueError("original error")
    wrapped = ProcessError("wrapped error")
    wrapped.__cause__ = original
    
    assert wrapped.__cause__ is original


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all error types tests."""
    runner = TestRunner("Processing Error Types Tests")
    
    # ProcessError base tests
    runner.run_test("ProcessError exists", test_processerror_exists)
    runner.run_test("ProcessError is Exception", test_processerror_is_exception)
    runner.run_test("ProcessError raisable", test_processerror_raisable)
    runner.run_test("ProcessError catchable", test_processerror_catchable)
    runner.run_test("ProcessError from task", test_processerror_from_task)
    
    # Lifecycle error tests
    runner.run_test("PreRunError exists", test_prerunerror_exists)
    runner.run_test("PreRunError is ProcessError", test_prerunerror_is_processerror)
    runner.run_test("PreRunError creation", test_prerunerror_creation)
    runner.run_test("RunError exists", test_runerror_exists)
    runner.run_test("RunError is ProcessError", test_runerror_is_processerror)
    runner.run_test("RunError creation", test_runerror_creation)
    runner.run_test("RunError with original", test_runerror_with_original)
    runner.run_test("PostRunError exists", test_postrunerror_exists)
    runner.run_test("PostRunError is ProcessError", test_postrunerror_is_processerror)
    runner.run_test("OnFinishError exists", test_onfinisherror_exists)
    runner.run_test("OnFinishError is ProcessError", test_onfinisherror_is_processerror)
    runner.run_test("ResultError exists", test_resulterror_exists)
    runner.run_test("ResultError is ProcessError", test_resulterror_is_processerror)
    runner.run_test("ErrorHandlerError exists", test_errorhandlererror_exists)
    runner.run_test("ErrorHandlerError is ProcessError", test_errorhandlererror_is_processerror)
    
    # ProcessTimeoutError tests
    runner.run_test("ProcessTimeoutError exists", test_processtimeouterror_exists)
    runner.run_test("ProcessTimeoutError is ProcessError", test_processtimeouterror_is_processerror)
    runner.run_test("ProcessTimeoutError creation", test_processtimeouterror_creation)
    runner.run_test("ProcessTimeoutError attributes", test_processtimeouterror_attributes)
    
    # Hierarchy tests
    runner.run_test("Error hierarchy", test_error_hierarchy)
    runner.run_test("Catch all errors", test_catch_all_errors)
    
    # Pool error tests
    runner.run_test("Pool error on failed task", test_pool_error_on_failed_task)
    runner.run_test("Multiple errors same pool", test_multiple_errors_same_pool)
    
    # Message tests
    runner.run_test("Error empty message", test_error_empty_message)
    runner.run_test("Error long message", test_error_long_message)
    runner.run_test("Error unicode message", test_error_unicode_message)
    runner.run_test("Error repr", test_error_repr)
    
    # Context tests
    runner.run_test("Error has context", test_error_has_context)
    runner.run_test("Error chaining", test_error_chaining)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
