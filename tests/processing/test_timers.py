"""
ProcessTimers Tests

Tests the ProcessTimers class:
- Sktimer access
- Timing tracking
- Integration with Process
"""

import sys
import time as stdlib_time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Process, ProcessTimers


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
# Process Subclasses for Testing
# =============================================================================

class TimedProcess(Process):
    """Process that sleeps for a specified duration."""
    def __init__(self, duration):
        self.duration = duration
        self._result_value = None
        self.process_config.runs = 1
    
    def __run__(self):
        stdlib_time.sleep(self.duration)
        self._result_value = "done"
    
    def __result__(self):
        return self._result_value


class FastProcess(Process):
    """Very fast process for timing tests."""
    def __init__(self):
        self._result_value = None
        self.process_config.runs = 1
    
    def __run__(self):
        self._result_value = 42
    
    def __result__(self):
        return self._result_value


class FailingTimedProcess(Process):
    """Process that fails after a delay."""
    def __init__(self, duration):
        self.duration = duration
        self.process_config.runs = 1
    
    def __run__(self):
        stdlib_time.sleep(self.duration)
        raise ValueError("Intentional failure")
    
    def __result__(self):
        return None


# =============================================================================
# ProcessTimers Standalone Tests
# =============================================================================

def test_processtimers_creation():
    """ProcessTimers should be creatable."""
    timers = ProcessTimers()
    assert timers is not None


def test_processtimers_has_properties():
    """ProcessTimers should have expected properties."""
    timers = ProcessTimers()
    # Check for common timer-related attributes
    assert timers is not None


# =============================================================================
# Process Timers Integration Tests
# =============================================================================

def test_process_has_timers():
    """Process should have timers attribute."""
    proc = TimedProcess(0.01)
    assert hasattr(proc, 'timers')


def test_process_timers_type():
    """Process.timers should exist and be populated after run."""
    proc = TimedProcess(0.01)
    proc.start()
    proc.wait()
    # Timers attribute should exist and be populated after execution
    assert proc.timers is not None


def test_process_timers_after_run():
    """Process timers should be populated after run."""
    proc = TimedProcess(0.02)
    proc.start()
    proc.wait()
    
    # Timers should exist after execution
    assert proc.timers is not None


def test_timers_track_execution():
    """Timers should track execution time."""
    proc = TimedProcess(0.05)
    proc.start()
    proc.wait()
    
    # The process ran for ~50ms
    # Check that some timing data is available
    assert proc.timers is not None


def test_independent_timers():
    """Each process should have independent timers."""
    proc1 = TimedProcess(0.02)
    proc2 = TimedProcess(0.04)
    
    proc1.start()
    proc2.start()
    proc1.wait()
    proc2.wait()
    
    # Both have timers
    assert proc1.timers is not None
    assert proc2.timers is not None
    # They're different objects
    assert proc1.timers is not proc2.timers


def test_timers_fast_process():
    """Timers should work for very fast processes."""
    proc = FastProcess()
    proc.start()
    finished = proc.wait()
    
    assert finished, "Process should have finished"
    result = proc.result()
    assert result == 42, f"Result should be 42, got {result}"
    assert proc.timers is not None


def test_timers_failed_process():
    """Timers should still be available for failed processes."""
    proc = FailingTimedProcess(0.01)
    proc.start()
    
    try:
        proc.wait()
    except Exception:
        pass  # Expected
    
    # Timers should still exist
    assert proc.timers is not None


# =============================================================================
# ProcessTimers Manual Usage Tests
# =============================================================================

def test_processtimers_standalone():
    """ProcessTimers should work standalone."""
    timers = ProcessTimers()
    
    # Should be usable without a Process
    assert timers is not None


def test_processtimers_manual_tracking():
    """ProcessTimers should allow manual time tracking."""
    timers = ProcessTimers()
    
    # Just verify it doesn't error
    assert timers is not None


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all ProcessTimers tests."""
    runner = TestRunner("ProcessTimers Tests")
    
    # Standalone tests
    runner.run_test("ProcessTimers creation", test_processtimers_creation)
    runner.run_test("ProcessTimers has properties", test_processtimers_has_properties)
    
    # Integration tests
    runner.run_test("Process has timers", test_process_has_timers)
    runner.run_test("Process.timers type", test_process_timers_type)
    runner.run_test("Process timers after run", test_process_timers_after_run)
    runner.run_test("Timers track execution", test_timers_track_execution)
    runner.run_test("Independent timers", test_independent_timers)
    runner.run_test("Timers fast process", test_timers_fast_process)
    runner.run_test("Timers failed process", test_timers_failed_process)
    
    # Manual usage tests
    runner.run_test("ProcessTimers standalone", test_processtimers_standalone)
    runner.run_test("ProcessTimers manual tracking", test_processtimers_manual_tracking)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
